"""5.1 · Distribuir els grups del 2n semestre a les aules, amb l'horari d'avui (sense moure cap dia ni hora).

Ús (des de l'arrel del repositori, amb el .venv actiu):

    python nivell2/p51_aules/aules.py --sortida lliuraments/proposta-aules.csv --informe nivell2/p51_aules/informe-aules.json

Aquí no es premia trobar una assignació vàlida (n'hi ha), sinó fer-la bona:
- una aula base estable per grup: les teories d'un mateix grup (cohort i línia) a la mateixa aula, i cada activitat
  setmanal a la mateixa aula tot el semestre;
- pocs canvis d'aula entre classes seguides: els PAUL i SEM a l'aula de la teoria del seu grup o al mateix passadís;
- pocs canvis respecte d'avui: tota aula d'avui que sigui vàlida es manté.

Ordre: primer es mantenen les aules vàlides d'avui; després les teories (de més a menys alumnes), després la resta;
per a cada activitat es prova una sola aula per a totes les setmanes i, si no, setmana a setmana. Al final, una passada
de millora porta cada activitat a l'aula de les classes veïnes del seu grup si és vàlida. Es comprova amb el
verificador oficial en mode --nomes-aules.
"""
from __future__ import annotations

import argparse
import collections
import csv
import json
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
ROOT = AQUI.parents[1]
sys.path.insert(0, str(ROOT / 'repte-horaris-escola'))
sys.path.insert(0, str(ROOT / 'nivell2' / 'p53_imprevist'))
sys.path.insert(0, str(ROOT / 'nivell2' / 'p52_torns'))

from horaris.check import avalua, passadis  # noqa: E402
from horaris.model import DIES, a_traslladar, carrega_base, fmt  # noqa: E402
from imprevist import a_fila, llegeix_files_csv  # noqa: E402
from torns import HorariT, aula_ok_avui, millora_aules, optimitza_aules  # noqa: E402  (motor compartit amb el 5.2)

PAQUET = ROOT / 'repte-horaris-escola' / 'paquet'


def claus_grup(s) -> list[tuple]:
    """Grup d'alumnes per a l'aula base: (cohort, línia), com l'indicador R6 del verificador."""
    return [(c, s.linia) for c in s.cohorts]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--partida', default=str(PAQUET / 'proposta_partida.csv'))
    ap.add_argument('--sortida', required=True)
    ap.add_argument('--informe')
    a = ap.parse_args(argv)

    b = carrega_base(PAQUET, semestre=2)
    files_csv, _ = llegeix_files_csv(Path(a.partida))
    files_in = [a_fila(r, i) for i, r in enumerate(files_csv, start=2) if r['id_sessio'].strip() in b.sessions]
    h = HorariT(b, files_in)

    # 1. sessions que necessiten aula: buida o no vàlida, i que se'ls pot canviar (no PLAB, no doble, no fixada amb aula)
    necessiten, vistes = [], set()
    for sid in b.ordre:
        s = b.sessions[sid]
        if s.tipus == 'PLAB' or s.sense_espai or s.unitat in vistes:
            continue
        u = [x for x in h.unitats[s.unitat] if x in h.pos]
        aula = h.pos[sid][2]
        if aula and aula_ok_avui(b, u, aula):
            continue
        if s.fixada and s.aula and not a_traslladar(s.aula):
            continue
        vistes.add(s.unitat)
        for x in u:
            if h.pos[x][2]:
                h.mou(x, aula='')
        necessiten.extend(u)
    lliures = set(necessiten)

    # aules de teoria ja usades per cada grup (cohort, línia), per anar-hi fent l'aula base
    aules_te: dict = collections.defaultdict(collections.Counter)
    for sid, (d, i, au) in h.pos.items():
        s = b.sessions[sid]
        if s.tipus == 'TE' and au in b.aules and not s.sense_espai:
            for k in claus_grup(s):
                aules_te[k][au] += 1

    # 2. per activitat: teories primer, de més a menys alumnes
    per_act = collections.defaultdict(list)
    for sid in necessiten:
        per_act[b.sessions[sid].activitat or sid].append(sid)
    ordre = sorted(per_act.values(), key=lambda v: (b.sessions[v[0]].tipus != 'TE',
                                                    -max(b.sessions[x].alumnes for x in v), -len(v), v[0]))
    sense = []
    for v in ordre:
        s0 = b.sessions[v[0]]
        unitats = {}
        for x in v:
            unitats.setdefault(b.sessions[x].unitat, [y for y in h.unitats[b.sessions[x].unitat] if y in h.pos])
        unitats = sorted(unitats.values(), key=lambda u: b.sessions[u[0]].data)
        # preferències: aula d'avui de l'activitat, aula base del grup, el seu passadís, la més petita on hi càpiga
        pref = [x for x in dict.fromkeys(
            [b.sessions[x].aula for x in v if b.sessions[x].aula in b.aules] +
            [au for k in claus_grup(s0) for au, _ in aules_te[k].most_common()])]
        ref = pref[0] if pref else ''
        cands = list(dict.fromkeys(pref + h.candidates(unitats[0], ref)))
        triada = None
        for au in cands:
            if all(h.aula_valida(u, au, h.pos[u[0]][0], h.pos[u[0]][1], h.pos[u[0]][1] + b.sessions[u[0]].durada)
                   for u in unitats):
                triada = au
                break
        if triada:
            for u in unitats:
                for x in u:
                    h.mou(x, aula=triada)
            if s0.tipus == 'TE':
                for k in claus_grup(s0):
                    aules_te[k][triada] += len(unitats)
            continue
        for u in unitats:   # setmana a setmana
            d, i = h.pos[u[0]][0], h.pos[u[0]][1]
            au = next((c for c in cands if h.aula_valida(u, c, d, i, i + b.sessions[u[0]].durada)), None)
            if au:
                for x in u:
                    h.mou(x, aula=au)
            else:
                sense.extend(u)

    log: list[str] = []
    millora_aules(h, lliures, log)
    optimitza_aules(h, lliures, log)
    optimitza_aules(h, lliures, log, per_unitat=True)

    with open(a.sortida, 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(['id_sessio', 'dia', 'h_ini', 'aula'])
        for r in files_csv:
            sid = r['id_sessio'].strip()
            if sid in h.pos:
                d, i, au = h.pos[sid]
                w.writerow([sid, DIES[d.weekday()], fmt(i), au])
            else:
                w.writerow([sid, r.get('dia', ''), r.get('h_ini', ''), r.get('aula', '')])

    files_out = [a_fila(r, i) for i, r in enumerate(llegeix_files_csv(Path(a.sortida))[0], start=2)
                 if r['id_sessio'].strip() in b.sessions]
    inf = avalua(b, files_out, nomes_aules=True)
    rec = inf.recompte()
    res = {'veredicte': inf.veredicte, 'compten': {k: v['compten'] for k, v in rec.items() if v['compten']},
           'objectius': inf.objectius, 'sessions_reassignades': len(necessiten), 'sense_aula': sense,
           'accions': log}
    print(f"Sessions que han rebut aula nova: {len(necessiten)} · sense aula: {len(sense)}")
    print('\n'.join(log))
    print(f"Veredicte (--nomes-aules): {res['veredicte']} · compten: {res['compten']}")
    print(f"Objectius: {res['objectius']}")
    if a.informe:
        Path(a.informe).write_text(json.dumps(res, ensure_ascii=False, indent=2, default=str) + '\n', encoding='utf-8')
    return 0 if res['veredicte'] == 'VALIDA' else 1


if __name__ == '__main__':
    sys.exit(main())
