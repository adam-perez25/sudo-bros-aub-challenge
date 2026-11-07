"""5.4 · Un grau nou de 40 places: col·loca les seves sessions sobre una proposta sense trencar res.

Ús (des de l'arrel del repositori, amb el .venv actiu):

    python nivell2/p54_grau_nou/grau_nou.py lliuraments/proposta-torns.csv \
        --sortida lliuraments/proposta-grau-nou.csv --informe nivell2/p54_grau_nou/informe-encaix.json

Parteix de QUALSEVOL proposta (la del 5.2; si no n'hi ha, proposta_partida.csv, com diu l'enunciat) i NO toca cap
sessió existent. Per a les 235 sessions del grau nou del 2n semestre (escenari grau-nou-40):

1. Mantenen el dia i l'hora que porten (l'estructura de 1r de GED) i reben aula: una per activitat setmanal si es
   pot (aula base estable), la més petita que hi càpiga, i els PAUL al mateix passadís que la teoria del grup.
2. Si a la seva hora no hi ha cap aula lliure, la sessió es mou a una altra franja de matí de la mateixa setmana on
   l'alumnat, el docent i una aula estiguin lliures (calendari i reserva de la regla 8 respectats).
3. Si tot i així no hi cap, ho diu: quina sessió, on, i quantes aules ordinàries lliures hi ha a cada franja.

També calcula el marge: a cada franja de matí, quantes aules ordinàries queden lliures un cop col·locat el grau nou
(per sobre de les 2 de reserva). Això és la prova constructiva que hi cap, i diu quant espai queda.

Al final es comprova amb el verificador oficial que les sessions noves no incompleixen res i que la resta de la
proposta no té cap incompliment nou. Codi de sortida 0 si tot és correcte.
"""
from __future__ import annotations

import argparse
import collections
import csv
import datetime as dt
import json
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
ROOT = AQUI.parents[1]
sys.path.insert(0, str(ROOT / 'repte-horaris-escola'))
sys.path.insert(0, str(ROOT / 'nivell2' / 'p53_imprevist'))

from horaris.check import FRANGES, RESERVA_MIN, _dins_finestra, _torn_ok, avalua, passadis  # noqa: E402
from horaris.model import DIES, MATI, TARDA, carrega_base, fmt  # noqa: E402
from imprevist import Horari, a_fila, clau, llegeix_files_csv  # noqa: E402  (motor compartit amb el 5.3)

PAQUET = ROOT / 'repte-horaris-escola' / 'paquet'
ESCENARI = PAQUET / 'escenaris' / 'grau-nou-40'
PAS_MIN = 30


def sessions_noves(base, files_in) -> list[str]:
    """Les sessions de l'escenari que la proposta d'entrada no porta (les del grau nou)."""
    dins = {f.id for f in files_in}
    return [sid for sid in base.ordre if sid not in dins]


def activitats(base, sids: list[str]) -> list[list[str]]:
    """Agrupa per activitat setmanal (codi, grup, dia, hora): les sessions extra no porten activitat_id."""
    g: dict[tuple, list[str]] = collections.defaultdict(list)
    for sid in sids:
        s = base.sessions[sid]
        g[(s.codi, s.grup, s.cohorts, s.dia, s.ini)].append(sid)
    # primer les teories (40 alumnes) i les activitats més llargues: són les més difícils de col·locar
    return sorted(g.values(), key=lambda v: (base.sessions[v[0]].tipus != 'TE', -base.sessions[v[0]].alumnes,
                                             -len(v), v[0]))


def aula_teoria(h: Horari, base, s) -> str:
    """Aula de la teoria de la mateixa línia i cohort (per posar-hi els PAUL al costat, regla 6)."""
    for sid, (d, i, a) in h.pos.items():
        o = base.sessions[sid]
        if o.tipus == 'TE' and a and o.codi == s.codi and set(o.cohorts) & set(s.cohorts) and o.linia == s.linia:
            return a
    return ''


def treu(h: Horari, sid: str) -> None:
    """Desfà la col·locació d'una sessió nova (deixa de ser a l'horari)."""
    h._desindexa(sid)
    del h.pos[sid]


def col_loca_activitat(h: Horari, base, sids: list[str], log: list) -> list[str]:
    """Hora original i una sola aula per a tota l'activitat; si no, sessió a sessió. Retorna les no col·locades."""
    s0 = base.sessions[sids[0]]
    prop = aula_teoria(h, base, s0) if s0.tipus != 'TE' else ''
    for a in h.candidates([sids[0]], prop):
        # tot o res: cada sessió es comprova després de col·locar les anteriors, i si una falla es desfà el lot
        posades = []
        for x in sids:
            s = base.sessions[x]
            if not (h.persones_lliures(x, s.data, s.ini, s.fi) and h.aula_valida([x], a, s.data, s.ini, s.fi)):
                break
            h.mou(x, data=s.data, ini=s.ini, aula=a)
            posades.append(x)
        if len(posades) == len(sids):
            log.append(f'{s0.codi} {s0.grup} {s0.dia} {fmt(s0.ini)}: {len(sids)} sessions a {a}')
            return []
        for x in posades:
            treu(h, x)
    pendents = []
    for x in sids:
        s = base.sessions[x]
        a = next((a for a in h.candidates([x], prop) if h.persones_lliures(x, s.data, s.ini, s.fi)
                  and h.aula_valida([x], a, s.data, s.ini, s.fi)), None)
        if a:
            h.mou(x, data=s.data, ini=s.ini, aula=a)
        else:
            pendents.append(x)
    log.append(f'{s0.codi} {s0.grup} {s0.dia} {fmt(s0.ini)}: sessió a sessió, {len(sids) - len(pendents)} '
               f'col·locades a la seva hora, {len(pendents)} pendents')
    return pendents


def mou_a_una_altra_franja(h: Horari, base, sid: str, log: list) -> bool:
    """Una altra franja de matí de la mateixa setmana ISO (mateix dia primer) amb persones i aula lliures."""
    s = base.sessions[sid]
    dilluns = s.data - dt.timedelta(days=s.data.weekday())
    dies = sorted((dilluns + dt.timedelta(days=k) for k in range(5)), key=lambda d: (d != s.data, abs((d - s.data).days)))
    finestres = [MATI] if s.torn == 'mati' else [TARDA] if s.torn == 'tarda' else [MATI, TARDA]
    hores = [t for a, z in finestres for t in range(a, z - s.durada + 1, PAS_MIN)]
    hores.sort(key=lambda t: abs(t - s.ini))
    prop = aula_teoria(h, base, s) if s.tipus != 'TE' else ''
    for d in dies:
        if d in base.dies_sense_classe:
            continue
        for t in hores:
            fi = t + s.durada
            if not _dins_finestra(t, fi) or _torn_ok(s.torn, t, fi) is False:
                continue
            if d != s.data or t != s.ini:
                if any(t < z and fi > a for a, z in base.aturades.get(d, ())):
                    continue
            if not h.persones_lliures(sid, d, t, fi):
                continue
            a = next((a for a in h.candidates([sid], prop) if h.aula_valida([sid], a, d, t, fi)), None)
            if a:
                h.mou(sid, data=d, ini=t, aula=a)
                log.append(f'Moguda: {sid} ({s.codi} {s.grup}) {s.data} {fmt(s.ini)} -> {d} {DIES[d.weekday()]} '
                           f'{fmt(t)} a {a}')
                return True
    return False


def marge(h: Horari, base, noves: set[str]) -> dict:
    """Aules ordinàries lliures a cada franja de matí, abans i després del grau nou (sense les 2 de reserva)."""
    ords = h.ordinaries
    dates = sorted({h.pos[x][0] for x in h.pos})
    abans, despres = [], []
    pitjor = None
    for d in dates:
        for f0 in [f for f in FRANGES if f < MATI[1]]:
            ocup_tot, ocup_vell = set(), set()
            for a in ords:
                for sid, (x, y) in h.per_aula.get((a, d), {}).items():
                    if x < f0 + 60 and y > f0:
                        ocup_tot.add(a)
                        if sid not in noves:
                            ocup_vell.add(a)
            if not any(x in h.pos and h.pos[x][0] == d for x in noves) and not ocup_vell:
                continue
            ll_v, ll_t = len(ords) - len(ocup_vell), len(ords) - len(ocup_tot)
            abans.append(ll_v)
            despres.append(ll_t)
            if pitjor is None or ll_t < pitjor[0]:
                pitjor = (ll_t, str(d), fmt(f0))
    hist = collections.Counter(despres)
    return {'min_lliures_abans': min(abans) if abans else None, 'min_lliures_despres': min(despres) if despres else None,
            'pitjor_franja': pitjor, 'reserva': RESERVA_MIN,
            'franges_per_aules_lliures_despres': dict(sorted(hist.items()))}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('proposta', help='proposta de partida (la del 5.2; si no, proposta_partida.csv)')
    ap.add_argument('--sortida', required=True, help='proposta amb el grau nou (proposta-grau-nou.csv)')
    ap.add_argument('--relaxacions', help="relaxacions de la proposta d'entrada (les del 5.2), per a la comprovació")
    ap.add_argument('--informe', help='resum en JSON')
    ap.add_argument('--paquet', default=str(PAQUET))
    ap.add_argument('--escenari', default=str(ESCENARI))
    a = ap.parse_args(argv)

    base = carrega_base(Path(a.paquet), semestre=2, escenari=Path(a.escenari))
    files_csv, _ = llegeix_files_csv(Path(a.proposta))
    files_in = [a_fila(r, i) for i, r in enumerate(files_csv, start=2) if r['id_sessio'].strip() in base.sessions]
    noves = sessions_noves(base, files_in)
    h = Horari(base, files_in)
    log: list[str] = []

    pendents = []
    for sids in activitats(base, noves):
        pendents += col_loca_activitat(h, base, sids, log)
    no_cap = [x for x in pendents if not mou_a_una_altra_franja(h, base, x, log)]
    for x in no_cap:
        s = base.sessions[x]
        log.append(f'NO HI CAP: {x} ({s.codi} {s.grup}) {s.data} {fmt(s.ini)}: cap franja de matí d\'aquella '
                   f'setmana amb alumnat, docent i aula lliures')

    # sortida: la proposta d'entrada tal com era + les sessions noves col·locades
    with open(a.sortida, 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(['id_sessio', 'dia', 'h_ini', 'aula'])
        for r in files_csv:
            w.writerow([r['id_sessio'], r.get('dia', ''), r.get('h_ini', ''), r.get('aula', '')])
        for x in noves:
            if x in h.pos:
                d, i, au = h.pos[x]
                w.writerow([x, DIES[d.weekday()], fmt(i), au])
            else:   # no hi cap: hora original i sense aula (el verificador ho marcarà com R5-SENSE-AULA)
                s = base.sessions[x]
                w.writerow([x, s.dia, fmt(s.ini), ''])

    # comprovació amb el verificador oficial
    from horaris.model import llegeix_relaxacions
    rel = llegeix_relaxacions(Path(a.relaxacions)) if a.relaxacions else []
    files_out = [a_fila(r, i) for i, r in enumerate(llegeix_files_csv(Path(a.sortida))[0], start=2)
                 if r['id_sessio'].strip() in base.sessions]
    inf_in = avalua(base, files_in, rel)
    inf_out = avalua(base, files_out, rel)
    nset = set(noves)
    abans = {clau(v) for v in inf_in.violacions if v.compta and v.regla != 'R5-FALTA'}
    de_noves = [v for v in inf_out.violacions if v.compta and set(v.sessions) & nset]
    noves_altres = [v for v in inf_out.violacions if v.compta and not set(v.sessions) & nset and clau(v) not in abans]
    moviments = sum(1 for x in noves if x in h.pos and (h.pos[x][0], h.pos[x][1]) !=
                    (base.sessions[x].data, base.sessions[x].ini))
    aules_usades = collections.Counter(h.pos[x][2] for x in noves if x in h.pos)
    res = {'sessions_noves': len(noves), 'col_locades': sum(1 for x in noves if x in h.pos), 'no_hi_caben': no_cap,
           'mogudes_de_franja': moviments, 'aules_usades': dict(aules_usades.most_common()),
           'incompliments_de_les_noves': [(v.regla, v.sessions, v.detall) for v in de_noves],
           'incompliments_nous_a_la_resta': [(v.regla, v.sessions, v.detall) for v in noves_altres],
           'veredicte_entrada': inf_in.veredicte, 'veredicte_sortida': inf_out.veredicte,
           'marge': marge(h, base, nset), 'accions': log}

    print('\n'.join(log))
    m = res['marge']
    print(f"\nSessions noves: {res['col_locades']} de {res['sessions_noves']} col·locades "
          f"({res['mogudes_de_franja']} mogudes de franja); no hi caben: {len(no_cap)}")
    print(f"Aules fetes servir: {res['aules_usades']}")
    print(f"Incompliments de les sessions noves: {len(de_noves)} · incompliments nous a la resta: {len(noves_altres)}")
    for v in (de_noves + noves_altres)[:20]:
        print('   ', v.regla, v.sessions, v.detall)
    print(f"Marge (aules ordinàries lliures al matí, mínim de totes les franges): {m['min_lliures_abans']} abans -> "
          f"{m['min_lliures_despres']} després (la regla 8 en demana {m['reserva']}); pitjor franja {m['pitjor_franja']}")
    print(f"Veredicte: entrada «{res['veredicte_entrada']}» -> sortida «{res['veredicte_sortida']}»")
    if a.informe:
        Path(a.informe).write_text(json.dumps(res, ensure_ascii=False, indent=2, default=str) + '\n', encoding='utf-8')
    return 0 if not no_cap and not de_noves and not noves_altres else 1


if __name__ == '__main__':
    sys.exit(main())
