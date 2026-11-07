"""5.3 · Un imprevist: repara una proposta davant dels quatre imprevistos de l'escenari «contingencies».

Ús (des de l'arrel del repositori, amb el .venv actiu):

    python nivell2/p53_imprevist/imprevist.py lliuraments/proposta-torns.csv \
        --sortida lliuraments/proposta-imprevist.csv --relaxacions lliuraments/relaxacions-imprevist.csv

Parteix de QUALSEVOL proposta (la del 5.2 quan estigui feta; mentrestant, proposta_partida.csv) i canvia el mínim:

1. Aula tancada (Q3/0013 del 15 al 19/3, Q1/1003 el 10/3): cada classe afectada canvia NOMÉS d'aula, al mateix
   dia i hora, a una aula lliure del tipus que toca, prou gran, preferentment del mateix passadís.
2. Grup que creix (Transmissió de Calor i Termotècnia TE/21, 91 -> 130): les sessions que ja no hi caben passen
   totes a UNA mateixa aula prou gran i lliure (aula base estable); si no n'hi ha cap per a totes, sessió a sessió.
3. Sessió cancel·lada (S11527, 8/3): es recupera en el primer forat vàlid fins al 19/3 (alumnat, docents i una
   aula lliures; calendari, torn, finestra i reserva de la regla 8 respectats). La fila porta la columna `data`.

Les sessions fixades (R1) i els PLAB (R7) que eren en una aula tancada s'han de canviar d'aula per força (R3-TANCADA
no es pot relaxar): l'eina les declara al CSV de relaxacions amb la justificació.

Al final es comprova amb el verificador oficial que (a) els imprevistos han quedat resolts i (b) la reparació no
introdueix CAP incompliment nou respecte de la proposta d'entrada. Codi de sortida 0 si tot és correcte.
"""
from __future__ import annotations

import argparse
import collections
import csv
import datetime as dt
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPTE = ROOT / 'repte-horaris-escola'
sys.path.insert(0, str(REPTE))

from horaris.check import (FRANGES, RESERVA_MIN, Informe, _alumnat_comparteix, _col_loca,  # noqa: E402
                           _dins_finestra, _espai_ok, _torn_ok, avalua, passadis)
from horaris.model import DIES, MATI, TARDA, Fila, a_traslladar, carrega_base, fmt  # noqa: E402

PAQUET = REPTE / 'paquet'
ESCENARI = PAQUET / 'escenaris' / 'contingencies'
PAS_MIN = 30   # granularitat de les hores candidates per a la recuperació


class Horari:
    """La proposta col·locada (sessió -> data, hora, aula) amb índexs per comprovar conflictes ràpidament."""

    def __init__(self, base, files: list[Fila]):
        self.base = base
        inf = Informe()
        col = _col_loca(base, files, inf)   # mateixa lògica que el verificador (data = dia dins la setmana ISO)
        self.pos = {sid: [c.data, c.ini, c.aula] for sid, c in col.items()}
        self.unitats: dict[str, list[str]] = collections.defaultdict(list)
        for sid in base.ordre:
            self.unitats[base.sessions[sid].unitat].append(sid)
        self.ordinaries = {a for a, x in base.aules.items() if x.ordinaria}
        self.per_aula: dict[tuple, dict[str, tuple]] = collections.defaultdict(dict)   # (aula, data) -> sid -> (ini, fi)
        self.per_data: dict[dt.date, set] = collections.defaultdict(set)
        for sid in self.pos:
            self._indexa(sid)

    # --------------------------------------------------------------------------------------- índexs
    def _indexa(self, sid: str) -> None:
        data, ini, aula = self.pos[sid]
        s = self.base.sessions[sid]
        self.per_data[data].add(sid)
        if aula and not s.sense_espai:
            self.per_aula[(aula, data)][sid] = (ini, ini + s.durada)

    def _desindexa(self, sid: str) -> None:
        data, ini, aula = self.pos[sid]
        self.per_data[data].discard(sid)
        self.per_aula.get((aula, data), {}).pop(sid, None)

    def mou(self, sid: str, data=None, ini=None, aula=None) -> None:
        if sid in self.pos:
            self._desindexa(sid)
            d0, i0, a0 = self.pos[sid]
        else:
            d0 = i0 = a0 = None
        self.pos[sid] = [data if data is not None else d0, ini if ini is not None else i0,
                         aula if aula is not None else a0]
        self._indexa(sid)

    # ---------------------------------------------------------------------------------- comprovacions
    def tancada(self, aula: str, data, ini: int, fi: int) -> bool:
        return any(t.aula == aula and t.data_ini <= data <= t.data_fi and ini < t.fi and fi > t.ini
                   for t in self.base.tancaments)

    def aula_lliure(self, aula: str, data, ini: int, fi: int, unitat: str) -> bool:
        for sid, (a, b) in self.per_aula.get((aula, data), {}).items():
            if self.base.sessions[sid].unitat != unitat and a < fi and b > ini:
                return False
        return True

    def reserva_ok(self, aula: str, data, ini: int, fi: int, unitat: str) -> bool:
        """Regla 8: després de posar-hi la classe, a cada franja tocada hi ha d'haver >= 2 aules ordinàries lliures."""
        if aula not in self.ordinaries:
            return True
        for f0 in FRANGES:
            if not (ini < f0 + 60 and fi > f0):
                continue
            ocupades = {aula}
            for a in self.ordinaries:
                for sid, (x, y) in self.per_aula.get((a, data), {}).items():
                    if x < f0 + 60 and y > f0 and self.base.sessions[sid].unitat != unitat:
                        ocupades.add(a)
                        break
            if len(self.ordinaries) - len(ocupades) < RESERVA_MIN:
                return False
        return True

    def aula_valida(self, sids: list[str], aula: str, data, ini: int, fi: int) -> bool:
        b = self.base
        if aula not in b.aules:
            return False
        ses = [b.sessions[x] for x in sids if not b.sessions[x].sense_espai]
        if not ses:
            return True
        if not all(_espai_ok(b, s, aula) for s in ses):
            return False
        if sum(s.alumnes for s in ses) > b.aules[aula].capacitat:
            return False
        unitat = ses[0].unitat
        return (not self.tancada(aula, data, ini, fi) and self.aula_lliure(aula, data, ini, fi, unitat)
                and self.reserva_ok(aula, data, ini, fi, unitat))

    def persones_lliures(self, sid: str, data, ini: int, fi: int) -> bool:
        """Cap solapament nou de docent, d'alumnat ni de PLAB de la mateixa assignatura (regla 4)."""
        s = self.base.sessions[sid]
        for oid in self.per_data.get(data, ()):
            o = self.base.sessions[oid]
            if o.unitat == s.unitat:
                continue
            oi = self.pos[oid][1]
            if not (oi < fi and oi + o.durada > ini):
                continue
            if s.docents & o.docents or _alumnat_comparteix(s, o):
                return False
            tipus = {s.tipus, o.tipus}
            if s.codi == o.codi and 'PLAB' in tipus and tipus & {'TE', 'PAUL'}:
                return False
        return True

    def candidates(self, sids: list[str], aula_original: str) -> list[str]:
        """Aules ordenades per preferència: si és teoria, primer les que el grup (cohort, línia) ja fa servir per a la
        teoria (així no puja l'indicador d'aules extra, R6); després mateix passadís i la més petita que hi càpiga."""
        b = self.base
        alumnes = sum(b.sessions[x].alumnes for x in sids if not b.sessions[x].sense_espai)
        pas = passadis(aula_original) if aula_original else ''
        del_grup = self.aules_te_grup(sids)
        return sorted((a for a, x in b.aules.items() if x.capacitat >= alumnes),
                      key=lambda a: (a not in del_grup, passadis(a) != pas, b.aules[a].capacitat, a))

    def aules_te_grup(self, sids: list[str]) -> set[str]:
        """Aules on els grups (cohort, línia) d'aquestes sessions de teoria ja fan altres classes de teoria."""
        b = self.base
        claus = {(c, b.sessions[x].linia) for x in sids if b.sessions[x].tipus == 'TE' for c in b.sessions[x].cohorts}
        if not claus:
            return set()
        propies = set(sids)
        out = set()
        for oid, (d, i, a) in self.pos.items():
            if a and oid not in propies:
                o = b.sessions[oid]
                if o.tipus == 'TE' and any((c, o.linia) in claus for c in o.cohorts):
                    out.add(a)
        return out


# ------------------------------------------------------------------------------------------- reparacions
def repara_tancades(h: Horari, log: list) -> list[str]:
    """Classes en una aula tancada: mateix dia i hora, una altra aula. Retorna les sessions fixades/PLAB mogudes."""
    b = h.base
    fixades_mogudes = []
    vistes = set()
    for sid in list(h.pos):
        data, ini, aula = h.pos[sid]
        s = b.sessions[sid]
        if s.sense_espai or not aula or s.unitat in vistes:
            continue
        if not h.tancada(aula, data, ini, ini + s.durada):
            continue
        vistes.add(s.unitat)
        sids = [x for x in h.unitats[s.unitat] if x in h.pos]
        nova = next((a for a in h.candidates(sids, aula) if a != aula
                     and h.aula_valida(sids, a, data, ini, ini + s.durada)), None)
        if nova is None:
            log.append(f'SENSE SOLUCIÓ: {sid} ({s.codi} {s.grup}) {data} {fmt(ini)} a {aula} tancada: cap aula lliure')
            continue
        for x in sids:
            h.mou(x, aula=nova)
            sx = b.sessions[x]
            # el verificador només hi veu R1-FIXADA / R7-PLAB si la sessió tenia aula a la partida (un PLAB, sempre)
            if sx.fixada and (sx.tipus == 'PLAB' or (sx.aula and not a_traslladar(sx.aula))):
                fixades_mogudes.append(x)
        log.append(f'Aula tancada: {", ".join(sids)} ({s.codi} {s.grup}) {data} {fmt(ini)}: {aula} -> {nova}')
    return fixades_mogudes


def repara_aforament(h: Horari, grups: set[tuple], log: list) -> list[str]:
    """Grups que creixen: totes les sessions que ja no hi caben, a una mateixa aula si es pot."""
    b = h.base
    pendents = []   # unitats que ja no hi caben
    for unitat, sids in h.unitats.items():
        sids = [x for x in sids if x in h.pos]
        if not sids or not any((b.sessions[x].codi, b.sessions[x].grup) in grups for x in sids):
            continue
        aula = h.pos[sids[0]][2]
        if aula not in b.aules:
            continue
        if sum(b.sessions[x].alumnes for x in sids if not b.sessions[x].sense_espai) > b.aules[aula].capacitat:
            pendents.append(sids)
    if not pendents:
        return []
    aula0 = h.pos[pendents[0][0]][2]
    # 1) una sola aula per a totes les sessions (aula base estable)
    for a in h.candidates(pendents[0], aula0):
        if all(h.aula_valida(sids, a, h.pos[sids[0]][0], h.pos[sids[0]][1],
                             h.pos[sids[0]][1] + b.sessions[sids[0]].durada) for sids in pendents):
            for sids in pendents:
                for x in sids:
                    h.mou(x, aula=a)
            log.append(f'Aforament: {len(pendents)} sessions de {sorted(grups)} passen totes de {aula0} a {a}')
            return []
    # 2) sessió a sessió; el que no tingui aula es declara (desdoblament)
    sense = []
    for sids in pendents:
        d, i = h.pos[sids[0]][0], h.pos[sids[0]][1]
        nova = next((a for a in h.candidates(sids, aula0)
                     if h.aula_valida(sids, a, d, i, i + b.sessions[sids[0]].durada)), None)
        if nova:
            for x in sids:
                h.mou(x, aula=nova)
            log.append(f'Aforament: {sids} {d} {fmt(i)}: -> {nova}')
        else:
            sense.extend(sids)
            log.append(f'Aforament SENSE AULA: {sids} {d} {fmt(i)}: es declara desdoblament (R3-AFORAMENT)')
    return sense


def hores_candidates(s, torn: str) -> list[int]:
    finestres = [MATI] if torn == 'mati' else [TARDA] if torn == 'tarda' else [MATI, TARDA]
    out = []
    for a, z in finestres:
        t = a
        while t + s.durada <= z:
            out.append(t)
            t += PAS_MIN
    return out


def repara_cancellades(h: Horari, log: list) -> dict[str, dt.date]:
    """Recupera cada sessió cancel·lada al primer forat vàlid: mateixa hora si es pot, i la data més propera."""
    b = h.base
    recuperades = {}
    for sid, fins in b.cancellades.items():
        s = b.sessions[sid]
        # aula preferida: la que el grup fa servir més (després de les altres reparacions)
        usades = collections.Counter(h.pos[x][2] for x in h.pos
                                     if b.sessions[x].codi == s.codi and b.sessions[x].grup == s.grup and h.pos[x][2])
        preferides = [a for a, _ in usades.most_common()]
        hores = hores_candidates(s, s.torn)
        hores.sort(key=lambda t: (t != s.ini, abs(t - s.ini)))
        trobat = None
        d = s.data + dt.timedelta(days=1)
        while d <= fins and trobat is None:
            if d.weekday() < 5 and d not in b.dies_sense_classe:
                for t in hores:
                    fi = t + s.durada
                    if not _dins_finestra(t, fi) or _torn_ok(s.torn, t, fi) is False:
                        continue
                    if any(t < z and fi > a for a, z in b.aturades.get(d, ())):
                        continue
                    if not h.persones_lliures(sid, d, t, fi):
                        continue
                    sids = [sid]
                    aula = next((a for a in preferides + h.candidates(sids, s.aula)
                                 if h.aula_valida(sids, a, d, t, fi)), None)
                    if aula:
                        trobat = (d, t, aula)
                        break
            d += dt.timedelta(days=1)
        if trobat is None:
            log.append(f'SENSE SOLUCIÓ: {sid} cancel·lada no es pot recuperar abans del {fins}')
            continue
        d, t, aula = trobat
        h.mou(sid, data=d, ini=t, aula=aula)
        recuperades[sid] = d
        log.append(f'Recuperació: {sid} ({s.codi} {s.grup}) cancel·lada el {s.data} -> {d} '
                   f'{DIES[d.weekday()]} {fmt(t)}-{fmt(t + s.durada)} a {aula}')
    return recuperades


# --------------------------------------------------------------------------------------------- E/S
def llegeix_files_csv(path: Path) -> tuple[list[dict], list[str]]:
    with open(path, encoding='utf-8-sig', newline='') as f:
        rd = csv.DictReader(f)
        return list(rd), list(rd.fieldnames or [])


def a_fila(r: dict, i: int) -> Fila:
    return Fila(r['id_sessio'].strip(), (r.get('dia') or '').strip().upper(), (r.get('h_ini') or '').strip(),
                (r.get('aula') or '').strip(), i, (r.get('data') or '').strip())


def escriu(path: Path, files: list[dict], h: Horari, recuperades: dict) -> None:
    with open(path, 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(['id_sessio', 'dia', 'h_ini', 'aula', 'data'])
        for r in files:
            sid = r['id_sessio'].strip()
            if sid in h.pos:
                d, ini, aula = h.pos[sid]
                w.writerow([sid, DIES[d.weekday()], fmt(ini), aula, recuperades[sid].isoformat()
                            if sid in recuperades else ''])
            else:   # sessions de l'altre semestre o no col·locables: tal com venien
                w.writerow([sid, r.get('dia', ''), r.get('h_ini', ''), r.get('aula', ''), r.get('data', '')])


def escriu_relaxacions(path: Path, h: Horari, fixades: list[str], sense_aula: list[str],
                       previes: list[dict] | None = None) -> int:
    """Escriu les relaxacions del 5.3; si la proposta d'entrada ja en tenia (les del 5.2), les copia al davant."""
    b = h.base
    files = [(r['restriccio'], r['sessions'].split('|'), r.get('justificacio', '')) for r in (previes or [])]
    r1 = [x for x in fixades if b.sessions[x].fixada.startswith('R1')]
    r7 = [x for x in fixades if b.sessions[x].fixada.startswith('R7')]
    if r1:
        files.append(('R1-FIXADA', r1, "Sessions fixades (GEI/GEET 1r-2n) que l'escenari deixa en una aula tancada "
                      "(acte a Q3/0013 del 15 al 19/3, avaria de Q1/1003 el 10/3). R3-TANCADA no es pot relaxar: "
                      "es mantenen dia i hora i només canvien d'aula, a una del mateix tipus, prou gran i del mateix "
                      "passadís quan n'hi ha cap de lliure."))
    if r7:
        files.append(('R7-PLAB', r7, "Laboratoris PLAB que avui es fan en una aula ordinària (Q3/0013) tancada per "
                      "l'acte del 15 al 19/3: es mantenen dia i hora i només canvien a una altra aula del mateix "
                      "tipus i prou gran, ja que R3-TANCADA no es pot relaxar."))
    if sense_aula:
        files.append(('R3-AFORAMENT', sense_aula, "El grup creix a 130 alumnes i a aquestes hores no hi ha cap aula "
                      "de 130 places lliure: es desdobla (el format no permet afegir sessions noves)."))
    with open(path, 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(['restriccio', 'sessions', 'justificacio'])
        for regla, sids, just in files:
            w.writerow([regla, '|'.join(sorted(sids)), just])
    return len(files)


# ------------------------------------------------------------------------------------------ comprovació
def clau(v) -> tuple:
    return (v.regla, v.sessions if v.sessions else (v.detall,))


def comprova(base, files_in: list[Fila], files_out: list[Fila], rel_path: Path | None, grups: set,
             rel_in_path: Path | None = None) -> dict:
    """Verificador oficial abans i després: què s'ha resolt i què (no) s'ha trencat."""
    from horaris.model import llegeix_relaxacions
    rel = llegeix_relaxacions(rel_path) if rel_path else []
    inf_in = avalua(base, files_in, llegeix_relaxacions(rel_in_path) if rel_in_path else [])
    inf_out = avalua(base, files_out, rel, referencia=files_in)
    abans = {clau(v) for v in inf_in.violacions if v.compta}
    despres = [v for v in inf_out.violacions if v.compta]
    noves = [v for v in despres if clau(v) not in abans]
    afectades = {sid for sid, s in base.sessions.items() if (s.codi, s.grup) in grups}
    escenari_restant = [v for v in inf_out.violacions if not v.declarada and (
        v.regla in ('R3-TANCADA', 'R5-RECUPERACIO') or (v.regla == 'R3-AFORAMENT' and set(v.sessions) & afectades))]
    escenari_abans = [v for v in inf_in.violacions if v.regla in ('R3-TANCADA', 'R5-RECUPERACIO') or (
        v.regla == 'R3-AFORAMENT' and set(v.sessions) & afectades)]
    return {'veredicte_entrada': inf_in.veredicte, 'veredicte_sortida': inf_out.veredicte,
            'imprevistos_abans': len(escenari_abans), 'imprevistos_despres': len(escenari_restant),
            'incompliments_nous': [(v.regla, v.sessions, v.detall) for v in noves],
            'declarats': sum(1 for v in inf_out.violacions if v.declarada and not v.heretada),
            'objectius': inf_out.objectius, 'recompte': inf_out.recompte()}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('proposta', help='proposta de partida (la del 5.2), CSV id_sessio,dia,h_ini,aula')
    ap.add_argument('--sortida', required=True, help='proposta reparada (proposta-imprevist.csv)')
    ap.add_argument('--relaxacions', help='CSV de relaxacions que cal declarar (relaxacions-imprevist.csv)')
    ap.add_argument('--relaxacions-entrada', help="relaxacions de la proposta d'entrada (les del 5.2): es copien "
                    "al CSV de sortida perquè el 5.3 es pugui comprovar amb un sol fitxer")
    ap.add_argument('--informe', help="resum de la reparació en JSON")
    ap.add_argument('--anticipa-52', help="escriu aquí una versió del 5.2 que ja fa servir les aules de la reparació "
                    "(totes menys les de les sessions fixades/PLAB i la cancel·lada, que al 5.2 no es poden tocar), "
                    "perquè el 5.3 hagi de canviar el mínim respecte del 5.2")
    ap.add_argument('--paquet', default=str(PAQUET))
    ap.add_argument('--escenari', default=str(ESCENARI))
    a = ap.parse_args(argv)

    base = carrega_base(Path(a.paquet), semestre=2, escenari=Path(a.escenari))
    cfg = json.loads((Path(a.escenari) / 'escenari.json').read_text(encoding='utf-8'))
    grups = {(g['codi'], g['grup']) for g in cfg.get('alumnes', [])}
    files_csv, _ = llegeix_files_csv(Path(a.proposta))
    files_in = [a_fila(r, i) for i, r in enumerate(files_csv, start=2) if r['id_sessio'].strip() in base.sessions]

    h = Horari(base, files_in)
    log: list[str] = []
    fixades = repara_tancades(h, log)
    sense_aula = repara_aforament(h, grups, log)
    recuperades = repara_cancellades(h, log)
    # una aula nova pot haver deixat alguna sessió fixada/PLAB en una aula tancada? (no: s'han filtrat) — i la
    # recuperació o l'aforament no fan servir aules tancades (aula_valida ho comprova)

    escriu(Path(a.sortida), files_csv, h, recuperades)
    if a.anticipa_52:
        intocables = set(fixades) | set(recuperades)
        with open(a.anticipa_52, 'w', encoding='utf-8', newline='') as f:
            w = csv.writer(f)
            w.writerow(['id_sessio', 'dia', 'h_ini', 'aula'])
            for r in files_csv:
                sid = r['id_sessio'].strip()
                aula = r.get('aula', '')
                if sid in h.pos and sid not in intocables:
                    aula = h.pos[sid][2]
                w.writerow([sid, r.get('dia', ''), r.get('h_ini', ''), aula])
        log.append(f'5.2 anticipat escrit a {a.anticipa_52} (aules de la reparació, sense tocar {len(intocables)} sessions)')
    rel_path = Path(a.relaxacions) if a.relaxacions else None
    rel_in = Path(a.relaxacions_entrada) if a.relaxacions_entrada else None
    previes = llegeix_files_csv(rel_in)[0] if rel_in else []
    if previes and not rel_path:
        ap.error('--relaxacions-entrada necessita --relaxacions (on escriure-les juntes)')
    n_rel = escriu_relaxacions(rel_path, h, fixades, sense_aula, previes) if rel_path else 0

    files_out = [a_fila(r, i) for i, r in enumerate(llegeix_files_csv(Path(a.sortida))[0], start=2)
                 if r['id_sessio'].strip() in base.sessions]
    res = comprova(base, files_in, files_out, rel_path, grups, rel_in)
    res['accions'] = log
    res['relaxacions_declarades'] = n_rel

    print('\n'.join(log))
    print(f"\nImprevistos pendents: {res['imprevistos_abans']} abans -> {res['imprevistos_despres']} després")
    print(f"Incompliments nous introduïts per la reparació: {len(res['incompliments_nous'])}")
    for v in res['incompliments_nous'][:20]:
        print('   ', v)
    print(f"Veredicte: entrada «{res['veredicte_entrada']}» -> sortida «{res['veredicte_sortida']}» "
          f"({res['declarats']} incompliments declarats)")
    print(f"Canvis respecte de l'entrada: franja {res['objectius'].get('canvis_franja_vs_referencia')}, "
          f"aula {res['objectius'].get('canvis_aula_vs_referencia')}")
    if a.informe:
        Path(a.informe).write_text(json.dumps(res, ensure_ascii=False, indent=2, default=str) + '\n', encoding='utf-8')
    return 0 if res['imprevistos_despres'] == 0 and not res['incompliments_nous'] else 1


if __name__ == '__main__':
    sys.exit(main())
