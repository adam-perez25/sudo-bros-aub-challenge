"""5.2 · Torns nous: 1r i 2n al matí; 3r, 4t, dobles i màsters a la tarda. Genera proposta-torns.csv.

Ús (des de l'arrel del repositori, amb el .venv actiu):

    python nivell2/p52_torns/torns.py --sortida lliuraments/proposta-torns.csv \
        --relaxacions lliuraments/relaxacions.csv --informe nivell2/p52_torns/informe-torns.json

Parteix de l'horari d'avui (proposta_partida.csv) i canvia el mínim, en aquest ordre:

1. Es mantenen totes les sessions que ja compleixen el seu torn, amb la seva aula si és vàlida.
2. Reben aula, primer, les sessions que NO es mouen de franja (són les menys flexibles): una aula per activitat
   setmanal si pot ser (aula base estable), l'aula d'avui si és vàlida, després el mateix passadís i la més petita
   on hi càpiga. Respecta tipus, aforament, solapaments i la reserva de 2 aules ordinàries (regla 8).
3. Cada activitat fora de torn (no fixada) es mou en bloc al torn que li toca: el mateix dia de la setmana i la
   mateixa hora totes les setmanes, les sessions compartides juntes. Es tria la franja lliure per a alumnat, docents
   i una aula que deixi menys hores mortes (enganxada a les altres classes del grup aquell dia), que eviti les
   franges més plenes i que, si pot, mantingui el dia. Calendari, finestres i setmana ISO respectats.
4. El que no es pot complir es declara com a relaxació amb la justificació (sobretot: els grups fixats de GEI i
   GEET+GEST de 1r i 2n que avui són a la tarda, que en rebre aula deixen de ser «heretats»).

Al final es passa el verificador oficial i s'escriu un informe amb el recompte per regla i els objectius.
"""
from __future__ import annotations

import argparse
import collections
import csv
import datetime as dt
import json
import os
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
ROOT = AQUI.parents[1]
sys.path.insert(0, str(ROOT / 'repte-horaris-escola'))
sys.path.insert(0, str(ROOT / 'nivell2' / 'p53_imprevist'))

from horaris.check import (FRANGES, _alumnat_comparteix, _dins_finestra, _espai_ok, _torn_ok,  # noqa: E402
                           avalua, passadis)
from horaris.model import DIES, MATI, TARDA, a_traslladar, carrega_base, fmt, llegeix_relaxacions  # noqa: E402
from imprevist import Horari, a_fila, llegeix_files_csv  # noqa: E402  (motor compartit amb el 5.3 i el 5.4)
sys.path.insert(0, str(AQUI))
from aules_cpsat import reassigna_aules  # noqa: E402

PAQUET = ROOT / 'repte-horaris-escola' / 'paquet'
PAS_MIN = 30


class HorariT(Horari):
    """Horari amb índexs per persona (cohort, docent, assignatura) per comprovar solapaments molt més de pressa."""

    def __init__(self, base, files):
        self.per_coh: dict = collections.defaultdict(set)
        self.per_doc: dict = collections.defaultdict(set)
        self.per_codi: dict = collections.defaultdict(set)
        super().__init__(base, files)

    def _indexa(self, sid):
        super()._indexa(sid)
        d = self.pos[sid][0]
        s = self.base.sessions[sid]
        for c in s.cohorts:
            self.per_coh[(d, c)].add(sid)
        for t in s.docents:
            self.per_doc[(d, t)].add(sid)
        self.per_codi[(d, s.codi)].add(sid)

    def _desindexa(self, sid):
        d = self.pos[sid][0]
        s = self.base.sessions[sid]
        super()._desindexa(sid)
        for c in s.cohorts:
            self.per_coh[(d, c)].discard(sid)
        for t in s.docents:
            self.per_doc[(d, t)].discard(sid)
        self.per_codi[(d, s.codi)].discard(sid)

    def treu(self, sid):
        self._desindexa(sid)
        del self.pos[sid]

    def veins(self, s, data):
        out = set()
        for c in s.cohorts:
            out |= self.per_coh.get((data, c), set())
        for t in s.docents:
            out |= self.per_doc.get((data, t), set())
        out |= self.per_codi.get((data, s.codi), set())
        return out

    def persones_lliures(self, sid, data, ini, fi):
        s = self.base.sessions[sid]
        for oid in self.veins(s, data):
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

    def ocupacio_ordinaries(self, data, ini, fi) -> int:
        """Nombre màxim d'aules ordinàries ocupades en alguna franja entre ini i fi (per evitar les hores punta)."""
        mx = 0
        for f0 in FRANGES:
            if not (ini < f0 + 60 and fi > f0):
                continue
            n = sum(1 for a in self.ordinaries if any(x < f0 + 60 and y > f0
                                                       for x, y in self.per_aula.get((a, data), {}).values()))
            mx = max(mx, n)
        return mx


# ----------------------------------------------------------------------------------------------- utilitats
def fora_de_torn(s, ini, fi) -> bool:
    return _torn_ok(s.torn, ini, fi) is False or not _dins_finestra(ini, fi)


def aula_ok_avui(base, sids, aula) -> bool:
    """L'aula que porta la sessió és vàlida (a l'aulari, tipus, aforament de la classe física)?"""
    if aula not in base.aules:
        return bool(aula) and not a_traslladar(aula)   # B3/0021 i QC/1082 es poden quedar
    ses = [base.sessions[x] for x in sids if not base.sessions[x].sense_espai]
    return (all(_espai_ok(base, s, aula) for s in ses)
            and sum(s.alumnes for s in ses) <= base.aules[aula].capacitat)


def blocs(base, sids) -> list[list[str]]:
    """Activitats setmanals unides per les sessions compartides: cada bloc es mou sencer."""
    pare: dict = {}

    def arrel(x):
        while pare.setdefault(x, x) != x:
            pare[x] = pare[pare[x]]
            x = pare[x]
        return x
    act = {sid: base.sessions[sid].activitat or sid for sid in sids}
    per_unitat = collections.defaultdict(list)
    for sid in sids:
        per_unitat[base.sessions[sid].unitat].append(sid)
    for xs in per_unitat.values():
        for x in xs[1:]:
            pare[arrel(act[x])] = arrel(act[xs[0]])
    g = collections.defaultdict(list)
    for sid in sids:
        g[arrel(act[sid])].append(sid)
    return list(g.values())


def data_objectiu(s, k: int) -> dt.date:
    return s.data + dt.timedelta(days=k - s.data.weekday())


def dia_bloquejat(base, s, d: dt.date, ini: int, fi: int) -> bool:
    """R2-CALENDARI tal com el comprova el verificador."""
    if d.weekday() >= 5:
        return True
    if d != s.data and d in base.dies_sense_classe:
        return True
    if (d, ini) == (s.data, s.ini):
        return False
    if any(ini < z and fi > a for a, z in base.aturades.get(d, ())):
        return not (d == s.data and any(s.ini < z and s.fi > a for a, z in base.aturades.get(s.data, ())))
    return False


# ------------------------------------------------------------------------------------- fase 2: aules fixes
def assigna_aules(h: HorariT, sids_necessiten: list[str], log: list) -> list[str]:
    """Aula a sessions que no canvien de franja: una per activitat si es pot, si no unitat a unitat."""
    b = h.base
    per_act = collections.defaultdict(list)
    for sid in sids_necessiten:
        per_act[b.sessions[sid].activitat or sid].append(sid)
    ordre = sorted(per_act.values(), key=lambda v: (-max(b.sessions[x].alumnes for x in v), -len(v)))
    sense = []
    for v in ordre:
        unitats = collections.defaultdict(list)
        for x in v:
            for y in h.unitats[b.sessions[x].unitat]:
                if y in h.pos:
                    unitats[b.sessions[x].unitat].append(y)
        unitats = [sorted(set(u)) for u in unitats.values()]
        orig = next((b.sessions[x].aula for x in v if b.sessions[x].aula in b.aules), '')
        cands = h.candidates(unitats[0], orig)
        if orig in cands:
            cands.remove(orig)
            cands.insert(0, orig)
        triada = None
        for a in cands:
            if all(h.aula_valida(u, a, h.pos[u[0]][0], h.pos[u[0]][1], h.pos[u[0]][1] + b.sessions[u[0]].durada)
                   for u in unitats):
                triada = a
                break
        if triada:
            for u in unitats:
                for x in u:
                    h.mou(x, aula=triada)
            continue
        for u in unitats:   # unitat a unitat
            d, i = h.pos[u[0]][0], h.pos[u[0]][1]
            a = next((a for a in h.candidates(u, orig)
                      if h.aula_valida(u, a, d, i, i + b.sessions[u[0]].durada)), None)
            if a:
                for x in u:
                    h.mou(x, aula=a)
            else:
                sense.extend(u)
    if sense:
        log.append(f'Sense aula a la seva franja: {len(sense)} sessions')
    return sense


# ------------------------------------------------------------------------------------ fase 3: moure blocs
def puntuacio(h: HorariT, s, d: dt.date, ini: int, fi: int, k_orig: int, k: int) -> float:
    """Com més baix, millor: hores mortes del grup aquell dia, hora punta i canvi de dia."""
    mati = ini < MATI[1]
    gap = None
    for c in s.cohorts:
        for oid in h.per_coh.get((d, c), ()):
            o = h.base.sessions[oid]
            if o.unitat == s.unitat or not _alumnat_comparteix(s, o):
                continue
            oi, of = h.pos[oid][1], h.pos[oid][1] + o.durada
            if (oi < MATI[1]) != mati:
                continue
            g = max(0, ini - of, oi - fi)
            gap = g if gap is None else min(gap, g)
    pg = 1.5 if gap is None else gap / 60          # una classe sola aquell dia: viatge sense res més
    punta = max(0, h.ocupacio_ordinaries(d, ini, fi) - 14) * 0.6
    return pg + punta + (0.8 if k != k_orig else 0)


def mou_bloc(h: HorariT, bloc: list[str], log: list) -> bool:
    b = h.base
    s0 = min((b.sessions[x] for x in bloc), key=lambda s: s.data)
    torns = {b.sessions[x].torn for x in bloc}
    torn = s0.torn if len(torns) == 1 else None
    finestres = [MATI] if torn == 'mati' else [TARDA] if torn == 'tarda' else [MATI, TARDA]
    durada = s0.durada
    hores = [t for a, z in finestres for t in range(a, z - durada + 1, PAS_MIN)]
    orig = next((b.sessions[x].aula for x in bloc if b.sessions[x].aula in b.aules), '')
    for x in bloc:
        h.treu(x)
    k0 = s0.data.weekday()
    cands = []
    for k in range(5):
        d = data_objectiu(s0, k)
        for t in hores:
            if dia_bloquejat(b, s0, d, t, t + durada) or not h.persones_lliures(s0.id, d, t, t + durada):
                continue
            cands.append((puntuacio(h, s0, d, t, t + durada, k0, k), k, t))
    cands.sort()
    unitats = collections.defaultdict(list)
    for x in bloc:
        unitats[b.sessions[x].unitat].append(x)
    unitats = sorted(unitats.values(), key=lambda u: b.sessions[u[0]].data)
    sense_espai = all(b.sessions[x].sense_espai for x in bloc)
    # experiment (TORNS_PREF_AULA_AVUI=N): entre les N millors franges, primer la primera on cada unitat pot fer-se a
    # la seva aula d'avui (així no compta a `canvis_aula`); si no n'hi ha cap, el criteri de sempre
    n_pref = int(os.environ.get('TORNS_PREF_AULA_AVUI', 0))
    if n_pref and not sense_espai:
        for _, k, t in cands[:n_pref]:
            pla = []
            for u in unitats:
                s = b.sessions[u[0]]
                d = data_objectiu(s, k)
                fi = t + s.durada
                if dia_bloquejat(b, s, d, t, fi):
                    d = s.data
                    if dia_bloquejat(b, s, d, t, fi):
                        pla = None
                        break
                a = s.aula if (s.aula in b.aules and not s.sense_espai) else None
                if a is None or not all(h.persones_lliures(x, d, t, fi) for x in u):
                    pla = None
                    break
                pla.append((u, d, a))
            if not pla:
                continue
            posades = []
            for u, d, a in pla:
                fi = t + b.sessions[u[0]].durada
                if not (all(h.persones_lliures(x, d, t, fi) for x in u) and h.aula_valida(u, a, d, t, fi)):
                    break
                for x in u:
                    h.mou(x, data=d, ini=t, aula=a)
                posades.append(u)
            if len(posades) == len(pla):
                log.append(f'Bloc {s0.codi} {s0.grup} ({len(bloc)} ses.): {DIES[k0]} {fmt(s0.ini)} -> {DIES[k]} '
                           f'{fmt(t)} (aula d\'avui)')
                return True
            for u in posades:
                for x in u:
                    h.treu(x)
    for _, k, t in cands:
        pla = []   # (unitat, data)
        ok = True
        for u in unitats:
            s = b.sessions[u[0]]
            d = data_objectiu(s, k)
            fi = t + s.durada
            if dia_bloquejat(b, s, d, t, fi):
                d = s.data   # setmana amb festiu: es queda al seu dia, a l'hora nova
                if dia_bloquejat(b, s, d, t, fi):
                    ok = False
                    break
            if not all(h.persones_lliures(x, d, t, fi) for x in u):
                ok = False
                break
            pla.append((u, d))
        if not ok:
            continue
        # aula: una per a tot el bloc si es pot (aula base), si no unitat a unitat
        if sense_espai:
            for u, d in pla:
                for x in u:
                    h.mou(x, data=d, ini=t, aula=h_aula_doble(b, x))
            log.append(f'Bloc {s0.codi} {s0.grup} ({len(bloc)} ses.): {DIES[k0]} {fmt(s0.ini)} -> {DIES[k]} {fmt(t)} '
                       f'(doble titulació, sense aula)')
            return True
        rep = pla[0][0]
        triada = None
        for a in ([orig] if orig else []) + h.candidates(rep, orig):
            if all(h.aula_valida(u, a, d, t, t + b.sessions[u[0]].durada) for u, d in pla):
                triada = {id(u): a for u, _ in pla}
                break
        if triada is None:
            triada = {}
            for u, d in pla:
                a = next((a for a in h.candidates(u, orig) if h.aula_valida(u, a, d, t, t + b.sessions[u[0]].durada)),
                         None)
                if a is None:
                    break
                triada[id(u)] = a
            if len(triada) < len(pla):
                continue
        # col·locar incrementalment comprovant de nou (dues unitats del bloc el mateix dia no poden xocar)
        posades = []
        for u, d in pla:
            a = triada[id(u)]
            fi = t + b.sessions[u[0]].durada
            if not (all(h.persones_lliures(x, d, t, fi) for x in u) and h.aula_valida(u, a, d, t, fi)):
                break
            for x in u:
                h.mou(x, data=d, ini=t, aula=a)
            posades.append(u)
        if len(posades) == len(pla):
            aules = sorted(set(triada.values()))
            log.append(f'Bloc {s0.codi} {s0.grup} ({len(bloc)} ses.): {DIES[k0]} {fmt(s0.ini)} -> {DIES[k]} {fmt(t)} '
                       f'a {", ".join(aules)}')
            return True
        for u in posades:
            for x in u:
                h.treu(x)
    # no hi ha cap franja comuna a totes les setmanes: cada setmana busca la seva (mateix torn, mateixa setmana)
    pendents = []
    for u in unitats:
        if not col_loca_unitat(h, u, hores, orig, sense_espai):
            pendents.append(u)
    if not pendents:
        log.append(f'Bloc {s0.codi} {s0.grup} ({len(bloc)} ses.): sense franja comuna, col·locat setmana a setmana')
        return True
    log.append(f'NO MOGUT: bloc {s0.codi} {s0.grup}: {sum(len(u) for u in pendents)} de {len(bloc)} sessions '
               f'sense cap franja lliure al seu torn')
    unitats = pendents
    # el que no s'ha pogut moure es torna a posar on era, amb una aula que encara sigui vàlida
    for u in unitats:
        s = b.sessions[u[0]]
        for x in u:
            h.mou(x, data=b.sessions[x].data, ini=b.sessions[x].ini, aula='')
        if not sense_espai:
            a = next((a for a in ([orig] if orig else []) + h.candidates(u, orig)
                      if h.aula_valida(u, a, s.data, s.ini, s.fi)), '')
            for x in u:
                h.mou(x, aula=a)
    log.append(f'NO MOGUT: bloc {s0.codi} {s0.grup} ({len(bloc)} ses.) {DIES[k0]} {fmt(s0.ini)}: cap franja lliure')
    return False


def col_loca_unitat(h: HorariT, u: list[str], hores: list[int], orig: str, sense_espai: bool) -> bool:
    """Una sola classe física (unitat) al millor forat del seu torn dins la seva setmana."""
    b = h.base
    s = b.sessions[u[0]]
    k0 = s.data.weekday()
    cands = []
    for k in range(5):
        d = data_objectiu(s, k)
        for t in hores:
            fi = t + s.durada
            if dia_bloquejat(b, s, d, t, fi) or not all(h.persones_lliures(x, d, t, fi) for x in u):
                continue
            cands.append((puntuacio(h, s, d, t, fi, k0, k), d, t))
    for _, d, t in sorted(cands):
        fi = t + s.durada
        if sense_espai:
            a = h_aula_doble(b, u[0])
        else:
            a = next((a for a in ([orig] if orig else []) + h.candidates(u, orig) if h.aula_valida(u, a, d, t, fi)),
                     None)
            if a is None:
                continue
        for x in u:
            h.mou(x, data=d, ini=t, aula=a)
        return True
    return False


def hores_torn(s) -> list[int]:
    finestres = [MATI] if s.torn == 'mati' else [TARDA] if s.torn == 'tarda' else [MATI, TARDA]
    return [t for a, z in finestres for t in range(a, z - s.durada + 1, PAS_MIN)]


def repara_residu(h: HorariT, sid: str, log: list) -> bool:
    """Una sessió que no ha trobat lloc al seu torn: busca una franja on només la bloquegin sessions no fixades,
    mou aquestes a una altra franja vàlida de la seva setmana i hi posa la sessió. Si alguna no es pot moure, es desfà."""
    b = h.base
    s = b.sessions[sid]
    u = [x for x in h.unitats[s.unitat] if x in h.pos]
    guardat = {x: list(h.pos[x]) for x in u}
    opcions = []
    for k in range(5):
        d = data_objectiu(s, k)
        for t in hores_torn(s):
            fi = t + s.durada
            if dia_bloquejat(b, s, d, t, fi):
                continue
            bloq = set()
            for x in u:
                sx = b.sessions[x]
                for oid in h.veins(sx, d):
                    o = b.sessions[oid]
                    if o.unitat == sx.unitat:
                        continue
                    oi = h.pos[oid][1]
                    if oi < fi and oi + o.durada > t and (sx.docents & o.docents or _alumnat_comparteix(sx, o) or (
                            sx.codi == o.codi and 'PLAB' in {sx.tipus, o.tipus})):
                        bloq.add(o.unitat)
            if any(b.sessions[y].fixada for un in bloq for y in h.unitats[un]):
                continue
            opcions.append((len(bloq), d, t, bloq))
    for _, d, t, bloq in sorted(opcions, key=lambda o: o[0]):
        fi = t + s.durada
        unitats_b = [[y for y in h.unitats[un] if y in h.pos] for un in sorted(bloq)]
        guard_b = {y: list(h.pos[y]) for ub in unitats_b for y in ub}
        for ub in unitats_b:
            for y in ub:
                h.treu(y)
        for x in u:
            h.treu(x)
        aula = '' if s.sense_espai else next((a for a in h.candidates(u, s.aula) if h.aula_valida(u, a, d, t, fi)), None)
        ok = aula is not None and all(h.persones_lliures(x, d, t, fi) for x in u)
        if ok:
            for x in u:
                h.pos[x] = [d, t, aula]
                h._indexa(x)
            for ub in unitats_b:
                o = b.sessions[ub[0]]
                for y in ub:   # es tornen a posar on eren per poder-los recol·locar
                    h.pos[y] = list(guard_b[y])
                    h._indexa(y)
                for y in ub:
                    h.treu(y)
                orig = guard_b[ub[0]][2]
                if not col_loca_unitat(h, ub, hores_torn(o), orig, o.sense_espai):
                    ok = False
                    break
        if ok:
            log.append(f'Reparat: {sid} ({s.codi} {s.grup}) -> {d} {fmt(t)}; recol·locades {len(unitats_b)} classes')
            return True
        # desfer
        for y in list(guard_b) + u:
            if y in h.pos:
                h.treu(y)
        for y, p in list(guard_b.items()) + list(guardat.items()):
            h.pos[y] = list(p)
            h._indexa(y)
    # estratègia 2: persones lliures però cap aula -> alliberar una aula movent-ne l'ocupant a una altra aula
    if not s.sense_espai:
        for _, d, t, bloq in sorted(opcions, key=lambda o: o[0]):
            if bloq:
                continue
            fi = t + s.durada
            if allibera_aula(h, u, d, t, fi, guardat, log):
                log.append(f'Reparat (aula alliberada): {sid} ({s.codi} {s.grup}) -> {d} {fmt(t)}')
                return True
    # estratègia 3: si un docent o grup té més hores de tarda que franges aquell dia (setmana d'un sol dia lectiu),
    # algú s'ha de quedar fora de torn: que sigui una classe amb menys files que aquesta (menys incompliments),
    # tornant-la a la seva hora d'avui
    for _, d, t, bloq in sorted(opcions, key=lambda o: o[0]):
        unitats_b = [[y for y in h.unitats[un] if y in h.pos] for un in sorted(bloq)]
        if len(unitats_b) != 1 or len(unitats_b[0]) >= len(u):
            continue
        ub = unitats_b[0]
        o = b.sessions[ub[0]]
        if not all(b.sessions[y].data == h.pos[y][0] for y in ub):
            continue   # només si torna al seu dia d'avui
        guard_b = {y: list(h.pos[y]) for y in ub}
        for y in ub + u:
            h.treu(y)
        fi = t + s.durada
        aula = '' if s.sense_espai else next((a for a in h.candidates(u, s.aula) if h.aula_valida(u, a, d, t, fi)), None)
        ok = aula is not None and all(h.persones_lliures(x, d, t, fi) for x in u)
        if ok:
            for x in u:
                h.mou(x, data=d, ini=t, aula=aula)
            # la classe desplaçada torna a la seva hora d'avui (amb aula vàlida)
            ok = all(h.persones_lliures(y, o.data, o.ini, o.fi) for y in ub)
            if ok:
                au = '' if o.sense_espai else next((a for a in ([o.aula] if o.aula else []) + h.candidates(ub, o.aula)
                                                    if h.aula_valida(ub, a, o.data, o.ini, o.fi)), None)
                ok = au is not None
                if ok:
                    for y in ub:
                        h.mou(y, data=o.data, ini=o.ini, aula=au)
        if ok:
            log.append(f'Reparat (incompliment desplaçat): {sid} ({s.codi} {s.grup}) -> {d} {fmt(t)}; '
                       f'{ub} ({o.codi} {o.grup}) torna a la seva hora d\'avui ({len(ub)} fila en lloc de {len(u)})')
            return True
        for y in ub + u:
            if y in h.pos:
                h.treu(y)
        for y, p in list(guard_b.items()) + list(guardat.items()):
            h.pos[y] = list(p)
            h._indexa(y)
    return False


def allibera_aula(h: HorariT, u: list[str], d, t: int, fi: int, guardat: dict, log: list) -> bool:
    """Busca una aula vàlida per a la unitat `u` a (d, t) on els ocupants es puguin passar a una altra aula."""
    b = h.base
    s = b.sessions[u[0]]
    alumnes = sum(b.sessions[x].alumnes for x in u if not b.sessions[x].sense_espai)
    for a in h.candidates(u, s.aula):
        if h.tancada(a, d, t, fi) or not all(_espai_ok(b, b.sessions[x], a) for x in u if not b.sessions[x].sense_espai):
            continue
        if b.aules[a].capacitat < alumnes:
            continue
        ocupants = {b.sessions[x].unitat for x, (p, q) in h.per_aula.get((a, d), {}).items() if p < fi and q > t}
        if any(b.sessions[y].fixada and b.sessions[y].aula for un in ocupants for y in h.unitats[un]):
            continue
        ocup = [[y for y in h.unitats[un] if y in h.pos] for un in sorted(ocupants)]
        guard_o = {y: list(h.pos[y]) for ub in ocup for y in ub}
        for ub in ocup:
            for y in ub:
                h.mou(y, aula='')
        for x in u:
            if x in h.pos:
                h.treu(x)
        ok = h.aula_valida(u, a, d, t, fi) and all(h.persones_lliures(x, d, t, fi) for x in u)
        if ok:
            for x in u:
                h.mou(x, data=d, ini=t, aula=a)
            for ub in ocup:
                o = b.sessions[ub[0]]
                od, oi = h.pos[ub[0]][0], h.pos[ub[0]][1]
                na = next((c for c in h.candidates(ub, guard_o[ub[0]][2])
                           if c != a and h.aula_valida(ub, c, od, oi, oi + o.durada)), None)
                if na is not None:
                    for y in ub:
                        h.mou(y, aula=na)
                    continue
                # cap altra aula a la mateixa hora: l'ocupant es mou d'hora dins la seva setmana i el seu torn
                if o.fixada:
                    ok = False
                    break
                for y in ub:
                    h.treu(y)
                if not col_loca_unitat(h, ub, hores_torn(o), guard_o[ub[0]][2], o.sense_espai):
                    ok = False
                    break
        if ok:
            return True
        for y in list(guard_o) + u:
            if y in h.pos:
                h.treu(y)
        for y, p in list(guard_o.items()) + list(guardat.items()):
            h.pos[y] = list(p)
            h._indexa(y)
    return False


def veins_consecutius(h: HorariT, sid: str) -> list[str]:
    """Classes del mateix alumnat el mateix dia, just abans o just després (fins a 1 h de forat)."""
    b = h.base
    s = b.sessions[sid]
    d, i, _ = h.pos[sid]
    fi = i + s.durada
    out = []
    for c in s.cohorts:
        for oid in sorted(h.per_coh.get((d, c), ())):
            o = b.sessions[oid]
            if o.unitat == s.unitat or not _alumnat_comparteix(s, o):
                continue
            oi = h.pos[oid][1]
            if 0 <= oi - fi <= 60 or 0 <= i - (oi + o.durada) <= 60:
                out.append(oid)
    return out


def _edifici(b, aula: str) -> str:
    """Mateixa definició que el verificador (`desplacaments_edifici`): l'edifici de l'aulari o el prefix del codi."""
    x = b.aules.get(aula)
    return x.edifici if x else aula.split('/')[0]


def _veins_edifici(h: HorariT, sid: str) -> list[str]:
    """Edificis de les classes immediatament anterior i posterior de cada grup de la sessió aquell dia."""
    b = h.base
    s = b.sessions[sid]
    data = h.pos[sid][0]
    out = []
    for coh in s.cohorts:
        cs = [x for x in h.per_data.get(data, ()) if x in h.pos and h.pos[x][2]
              and coh in b.sessions[x].cohorts and b.sessions[x].linia == s.linia]
        cs.sort(key=lambda x: h.pos[x][1])
        if sid not in cs:
            continue
        i = cs.index(sid)
        for j in (i - 1, i + 1):
            if 0 <= j < len(cs) and b.sessions[cs[j]].unitat != s.unitat:
                out.append(_edifici(b, h.pos[cs[j]][2]))
    return out


def acosta_edifici(h: HorariT, log: list) -> int:
    """Fase 5: un grup amb classes en una aula d'avui fora de l'aulari (p. ex. B3/0021) i classes consecutives a
    l'aulari (Q) ha de canviar d'edifici (`desplacaments_edifici`, que la puntuació web pesa molt: 17 -> 0 va fer
    passar el 5.2 de 70 a 73). Es mouen juntes totes les sessions no fixades del grup en aquella aula (si en mogués
    només una part, els canvis d'edifici passarien a ser entre les seves classes) a una aula ordinària de l'edifici
    dels veïns, la mateixa per a totes les dates, si n'hi ha una de vàlida a totes (tipus, aforament, lliure,
    reserva de 2 aules).
    Només si redueix els canvis d'edifici."""
    b = h.base
    per_act: dict[str, list[str]] = collections.defaultdict(list)
    for sid, (d, i, a) in h.pos.items():
        s = b.sessions[sid]
        if a and a not in b.aules and not s.fixada and s.tipus != 'PLAB':
            per_act[f"{a} {'+'.join(s.cohorts)}"].append(sid)   # tota la teoria del grup en aquella aula, junta
    moguts = 0
    for act, sids in sorted(per_act.items()):
        actual = h.pos[sids[0]][2]
        if any(h.pos[x][2] != actual for x in sids):
            continue
        ed = _edifici(b, actual)
        veins = collections.Counter(e for x in sids for e in _veins_edifici(h, x))
        abans = sum(n for e, n in veins.items() if e != ed)
        if not abans:
            continue
        desti = max((e for e in veins if e != ed), key=lambda e: veins[e])
        unitats = sorted({b.sessions[x].unitat for x in sids})
        for aula in sorted(a for a in h.ordinaries if b.aules[a].edifici == desti):
            grups = [[x for x in h.unitats[u] if x in h.pos] for u in unitats]
            if all(h.aula_valida(g, aula, h.pos[g[0]][0], h.pos[g[0]][1],
                                 h.pos[g[0]][1] + max(b.sessions[x].durada for x in g)) for g in grups):
                for g in grups:
                    for x in g:
                        h.mou(x, aula=aula)
                despres = sum(1 for x in sids for e in _veins_edifici(h, x) if e != desti)
                if despres < abans:
                    log.append(f'Edifici: {act} -> {aula} ({len(sids)} sessions; canvis d\'edifici {abans} -> {despres})')
                    moguts += len(sids)
                else:
                    for g in grups:
                        for x in g:
                            h.mou(x, aula=actual)
                break
    return moguts


def millora_aules(h: HorariT, lliures: set[str], log: list, passades: int = 8) -> int:
    """Fase 4: cada activitat amb aula triada per nosaltres (no la d'avui) prova l'aula de les classes veïnes del
    seu grup (menys desplaçaments, mateix passadís TE<->PAUL), si és vàlida a totes les seves setmanes."""
    b = h.base
    per_act = collections.defaultdict(list)
    for sid in sorted(lliures):
        if sid in h.pos and h.pos[sid][2]:
            per_act[b.sessions[sid].activitat or sid].append(sid)
    canvis = 0
    for passada in range(passades):
        items = list(per_act.items())
        for act, sids in (items if passada % 2 == 0 else items[::-1]):   # alterna el sentit: menys biaix d'ordre
            unitats = {}
            for x in sids:
                unitats.setdefault(b.sessions[x].unitat, [y for y in h.unitats[b.sessions[x].unitat] if y in h.pos])
            unitats = list(unitats.values())
            actual = collections.Counter(h.pos[u[0]][2] for u in unitats)
            vots = collections.Counter()
            for u in unitats:
                for oid in veins_consecutius(h, u[0]):
                    a = h.pos[oid][2]
                    if a in b.aules:
                        vots[a] += 1
            def encerts(a):
                return sum(1 for u in unitats for oid in veins_consecutius(h, u[0]) if h.pos[oid][2] == a)
            millor_actual = max(encerts(a) for a in actual)
            for a, _v in vots.most_common(4):
                if a in actual or encerts(a) <= millor_actual:
                    continue
                guard = {y: list(h.pos[y]) for u in unitats for y in u}
                for u in unitats:
                    for y in u:
                        h.mou(y, aula='')
                if all(h.aula_valida(u, a, h.pos[u[0]][0], h.pos[u[0]][1], h.pos[u[0]][1] + b.sessions[u[0]].durada)
                       for u in unitats):
                    for u in unitats:
                        for y in u:
                            h.mou(y, aula=a)
                    canvis += 1
                    break
                for y, p in guard.items():
                    h.mou(y, aula=p[2])
    log.append(f'Millora d\'aules: {canvis} activitats canviades a l\'aula dels seus veïns')
    return canvis


def veins_ordenats(h: HorariT, sid: str) -> list[str]:
    """Classes que el mateix alumnat té just abans i just després (les parelles que compten a l'indicador de
    desplaçaments), sense límit de forat: l'indicador mira parelles consecutives de l'agenda del grup."""
    b = h.base
    s = b.sessions[sid]
    d, i, _ = h.pos[sid]
    fi = i + s.durada
    abans, despres = [], []
    for c in s.cohorts:
        for oid in h.per_coh.get((d, c), ()):
            o = b.sessions[oid]
            if o.unitat == s.unitat or not _alumnat_comparteix(s, o) or oid not in h.pos:
                continue
            oi = h.pos[oid][1]
            if oi + o.durada <= i:
                abans.append((oi + o.durada, oid))
            elif oi >= fi:
                despres.append((oi, oid))
    out = []
    if abans:
        m = max(x for x, _ in abans)
        out += [o for x, o in abans if x == m]
    if despres:
        m = min(x for x, _ in despres)
        out += [o for x, o in despres if x == m]
    return out


def cost_parella(b, s, o, aula_s: str, aula_o: str) -> int:
    """1 per canvi d'aula entre dues classes consecutives + 1 si és TE<->PAUL i canvia de passadís."""
    if not aula_s or not aula_o or aula_s == aula_o:
        return 0
    c = 1
    if {s.tipus, o.tipus} == {'TE', 'PAUL'} and passadis(aula_s) != passadis(aula_o):
        c += 1
    return c


def optimitza_aules(h: HorariT, lliures: set[str], log: list, passades: int = 30, per_unitat: bool = False) -> int:
    """Fase 4b: cerca local sobre l'indicador real (desplaçaments d'aula + canvis TE<->PAUL fora del passadís).
    Cada activitat amb aula triada per nosaltres prova, per a totes les seves sessions alhora, les aules de les
    classes veïnes i les del seu passadís, i es queda la d'opció de menys cost que sigui vàlida. Només millores
    estrictes: acaba sempre i mai no empitjora l'indicador."""
    b = h.base
    per_act = collections.defaultdict(list)
    for sid in sorted(lliures):
        if sid in h.pos and h.pos[sid][2] and not (per_unitat and b.sessions[sid].tipus == 'TE'):
            per_act[b.sessions[sid].unitat if per_unitat else (b.sessions[sid].activitat or sid)].append(sid)
    acts = list(per_act.items())
    canvis = 0
    for passada in range(passades):
        millores = 0
        for act, sids in (acts if passada % 2 == 0 else acts[::-1]):
            sids = [x for x in sids if x in h.pos]
            unitats = {}
            for x in sids:
                unitats.setdefault(b.sessions[x].unitat, [y for y in h.unitats[b.sessions[x].unitat] if y in h.pos])
            unitats = list(unitats.values())
            propis = {y for u in unitats for y in u}
            veins = {x: [o for o in veins_ordenats(h, x) if o not in propis] for u in unitats for x in u}

            def cost(a):
                return sum(cost_parella(b, b.sessions[x], b.sessions[o], a, h.pos[o][2])
                           for u in unitats for x in u for o in veins[x])
            actual = h.pos[unitats[0][0]][2]
            if any(h.pos[u[0]][2] != actual for u in unitats):
                actual = None   # unitats en aules diferents: es mira si n'hi ha una de millor per a totes
            c_act = sum(cost_parella(b, b.sessions[x], b.sessions[o], h.pos[x][2], h.pos[o][2])
                        for u in unitats for x in u for o in veins[x])
            cands = set()
            for x, vs in veins.items():
                for o in vs:
                    a = h.pos[o][2]
                    if a in b.aules:
                        cands.add(a)
                        cands.update(z for z in b.aules if passadis(z) == passadis(a))
            if actual:
                cands.discard(actual)
            puntuats = sorted(((cost(a), b.aules[a].capacitat, a) for a in cands))
            if not puntuats or puntuats[0][0] >= c_act:
                continue
            guard = {y: list(h.pos[y]) for u in unitats for y in u}
            for u in unitats:
                for y in u:
                    h.mou(y, aula='')
            triada = None
            for c, _cap, a in puntuats:
                if c >= c_act:
                    break
                if all(h.aula_valida(u, a, h.pos[u[0]][0], h.pos[u[0]][1], h.pos[u[0]][1] + b.sessions[u[0]].durada)
                       for u in unitats):
                    triada = a
                    break
            if triada:
                for u in unitats:
                    for y in u:
                        h.mou(y, aula=triada)
                millores += 1
            else:
                for y, p in guard.items():
                    h.mou(y, aula=p[2])
        canvis += millores
        if not millores:
            break
    log.append(f"Optimització d'aules ({'per sessió' if per_unitat else 'per activitat'}): {canvis} canvis d'activitat en {passada + 1} passades")
    return canvis


# ----------------------------------------------------------------- fase 3c: tornar a col·locar els blocs moguts
def mortes_clau(h: HorariT, coh, linia, d) -> int:
    """Minuts morts d'un (cohort, línia, dia) tal com els compta l'indicador del verificador: per a cada subgrup,
    la teoria més les seves pràctiques, parelles consecutives dins el mateix torn."""
    b = h.base
    agenda = collections.defaultdict(list)
    for sid in h.per_coh.get((d, coh), ()):
        s = b.sessions[sid]
        if s.linia == linia and sid in h.pos:
            agenda[s.num_grup if s.tipus != 'TE' else '*'].append(sid)
    teoria = agenda.get('*', [])
    reals = [g for g in agenda if g != '*'] or ['*']
    total = 0
    for g in reals:
        ids = set(teoria) | (set(agenda.get(g, ())) if g != '*' else set())
        cs = sorted(((h.pos[x][1], h.pos[x][1] + b.sessions[x].durada) for x in ids))
        for (i0, f0), (i1, f1) in zip(cs, cs[1:]):
            gap = i1 - f0
            if gap > 0 and (f0 <= MATI[1]) == (i1 < MATI[1]):
                total += gap
    return total


def claus_bloc(h: HorariT, bloc: list[str]) -> set:
    b = h.base
    return {(c, b.sessions[x].linia, h.pos[x][0]) for x in bloc if x in h.pos for c in b.sessions[x].cohorts}


def replaca_blocs(h: HorariT, bls: list[list[str]], log: list, passades: int = 6, cost_canvi: float = 0.0,
                  forcats: set | None = None) -> int:
    """Quan tot és col·locat, cada bloc mogut es treu i es torna a triar la franja amb la imatge completa:
    mateix criteri que l'indicador de hores mortes (contribució marginal del bloc), només canvis estrictament
    millors i amb aula vàlida. Si no es pot col·locar, el bloc torna on era.
    `cost_canvi`: minuts d'hores mortes que val cada sessió fora de la seva hora d'avui (`canvis_franja`): un
    bloc només es mou si l'estalvi d'hores mortes supera aquest cost (0 = no es mira)."""
    b = h.base
    total = 0

    cost_aula = float(os.environ.get('TORNS_COST_AULA', 0))

    def cost(pla) -> float:
        if pla is None:
            return 0.0
        c = 0.0
        if cost_canvi:
            c += cost_canvi * sum(1 for u, d, tt in pla for x in u if (d, tt) != (b.sessions[x].data, b.sessions[x].ini))
        if cost_aula:
            # experiment: cada sessió que a la nova franja no pot fer-se a la seva aula d'avui (`canvis_aula`)
            for u, d, tt in pla:
                s = b.sessions[u[0]]
                if s.aula and s.aula in b.aules and not s.sense_espai and not (
                        h.aula_lliure(s.aula, d, tt, tt + s.durada, s.unitat)
                        and h.aula_valida(u, s.aula, d, tt, tt + s.durada)):
                    c += cost_aula * len(u)
        return c
    for passada in range(passades):
        millores = 0
        for bloc in (bls if passada % 2 == 0 else bls[::-1]):
            bloc = [x for x in bloc if x in h.pos]
            if not bloc or any(b.sessions[x].sense_espai for x in bloc):
                continue
            guard = {x: list(h.pos[x]) for x in bloc}
            s0 = min((b.sessions[x] for x in bloc), key=lambda s: s.data)
            torns = {b.sessions[x].torn for x in bloc}
            torn = s0.torn if len(torns) == 1 else None
            finestres = [MATI] if torn == 'mati' else [TARDA] if torn == 'tarda' else [MATI, TARDA]
            hores = [t for a, z in finestres for t in range(a, z - s0.durada + 1, PAS_MIN)]
            unitats = collections.defaultdict(list)
            for x in bloc:
                unitats[b.sessions[x].unitat].append(x)
            unitats = sorted(unitats.values(), key=lambda u: b.sessions[u[0]].data)
            claus_vell = claus_bloc(h, bloc)
            actual_aules = collections.Counter(h.pos[x][2] for x in bloc if h.pos[x][2])
            orig = actual_aules.most_common(1)[0][0] if actual_aules else ''
            for x in bloc:
                h.treu(x)
            sense = {}

            def sense_bloc(k):
                if k not in sense:
                    sense[k] = mortes_clau(h, *k)
                return sense[k]

            def marginal(pla):
                claus = {(c, b.sessions[x].linia, d) for u, d, _t in pla for x in u for c in b.sessions[x].cohorts}
                base0 = {k: sense_bloc(k) for k in claus}   # abans de col·locar: amb el bloc fora
                for u, d, t in pla:
                    for x in u:
                        h.mou(x, data=d, ini=t, aula='')
                val = sum(mortes_clau(h, *k) - base0[k] for k in claus)
                for x in bloc:
                    h.treu(x)
                return val
            # marginal de la posició actual
            pla0 = [(u, guard[u[0]][0], guard[u[0]][1]) for u in unitats]
            for u in unitats:
                for x in u:
                    if guard[x][1] != guard[u[0]][1] or guard[x][0] != guard[u[0]][0]:
                        pla0 = None
            if pla0 is None:   # unitats amb hores diferents dins la unitat: no es toca
                for x in bloc:
                    h.mou(x, data=guard[x][0], ini=guard[x][1], aula=guard[x][2])
                continue
            vell = marginal(pla0) + cost(pla0)
            if forcats and bloc[0] in forcats and any(
                    not h.persones_lliures(x, guard[x][0], guard[x][1], guard[x][1] + b.sessions[x].durada) for x in bloc):
                vell = float('inf')   # avui ja hi ha un solapament de persones: es mou on no n'hi hagi cap
            cands = []
            for k in range(5):
                for t in hores:
                    pla = []
                    ok = True
                    for u in unitats:
                        s = b.sessions[u[0]]
                        d = data_objectiu(s, k)
                        fi = t + s.durada
                        if dia_bloquejat(b, s, d, t, fi):
                            d = s.data
                            if dia_bloquejat(b, s, d, t, fi):
                                ok = False
                                break
                        if not all(h.persones_lliures(x, d, t, fi) for x in u):
                            ok = False
                            break
                        pla.append((u, d, t))
                    if not ok or [(d, t) for _, d, t in pla] == [(guard[u[0]][0], guard[u[0]][1]) for u in unitats]:
                        continue
                    cands.append((marginal(pla) + cost(pla), k, t, pla))
            cands.sort(key=lambda c: (c[0], c[1], c[2]))
            posat = False
            for m, k, t, pla in cands:
                if m >= vell:
                    break
                posades = []
                ok = True
                for u, d, tt in pla:
                    fi = tt + b.sessions[u[0]].durada
                    if not all(h.persones_lliures(x, d, tt, fi) for x in u):
                        ok = False
                        break
                    propia = b.sessions[u[0]].aula
                    primeres = ([propia] if os.environ.get('TORNS_PREF_AULA_AVUI') and propia in b.aules else [])
                    a = next((a for a in primeres + ([orig] if orig else []) + h.candidates(u, orig)
                              if h.aula_valida(u, a, d, tt, fi)), None)
                    if a is None:
                        ok = False
                        break
                    for x in u:
                        h.mou(x, data=d, ini=tt, aula=a)
                    posades.append(u)
                if ok:
                    posat = True
                    millores += 1
                    break
                for u in posades:
                    for x in u:
                        h.treu(x)
            if not posat:
                for x in bloc:
                    h.mou(x, data=guard[x][0], ini=guard[x][1], aula=guard[x][2])
        total += millores
        if not millores:
            break
    log.append(f'Re-col·locació de blocs (hores mortes): {total} blocs moguts en {passada + 1} passades')
    return total


def h_aula_doble(b, sid) -> str:
    """Les dobles titulacions no necessiten aula: es deixa la que portaven (el verificador no la mira)."""
    return b.sessions[sid].aula or ''


# ------------------------------------------------------------------------------------------------- main
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--partida', default=str(PAQUET / 'proposta_partida.csv'))
    ap.add_argument('--sortida', required=True)
    ap.add_argument('--relaxacions', help='CSV de relaxacions a declarar')
    ap.add_argument('--informe', help='resum en JSON')
    ap.add_argument('--paquet', default=str(PAQUET))
    ap.add_argument('--sense-cpsat', action='store_true', help="no passa la reassignació d'aules amb CP-SAT")
    a = ap.parse_args(argv)

    base = carrega_base(Path(a.paquet), semestre=2)
    b = base
    files_csv, _ = llegeix_files_csv(Path(a.partida))
    files_in = [a_fila(r, i) for i, r in enumerate(files_csv, start=2) if r['id_sessio'].strip() in base.sessions]
    h = HorariT(base, files_in)
    log: list[str] = []

    # quines sessions es mouen de franja (blocs no fixats fora de torn o de finestra)
    a_moure = [sid for sid, s in b.sessions.items() if not s.fixada and fora_de_torn(s, s.ini, s.fi)]
    # un bloc inclou totes les sessions de les seves activitats (no només les fora de torn)
    per_act = collections.defaultdict(list)
    for sid, s in b.sessions.items():
        per_act[s.activitat or sid].append(sid)
    bls = blocs(b, sorted({y for x in a_moure for y in per_act[b.sessions[x].activitat or x]}))
    bls = [bl for bl in bls if not any(b.sessions[x].fixada for x in bl)]
    mouen = {x for bl in bls for x in bl}

    # fase 1-2: sessions que no es mouen i necessiten aula (buida o no vàlida, i se'ls pot canviar)
    necessiten = []
    vistes = set()
    for sid, s in b.sessions.items():
        if sid in mouen or s.tipus == 'PLAB' or s.sense_espai or s.unitat in vistes:
            continue
        u = [x for x in h.unitats[s.unitat] if x in h.pos]
        aula = h.pos[sid][2]
        if aula and aula_ok_avui(b, u, aula):
            continue
        if s.fixada and s.aula and not a_traslladar(s.aula):
            continue   # fixada amb aula: no es toca (si no és vàlida, és heretat)
        vistes.add(s.unitat)
        for x in u:
            if h.pos[x][2]:
                h.mou(x, aula='')
        necessiten.extend(u)
    for x in mouen:   # els blocs que es mouran no ocupen la seva franja d'avui mentre es col·loca la resta
        h.treu(x)
    sense_aula = assigna_aules(h, necessiten, log)
    for x in mouen:   # es tornen a posar (sense aula) per poder-los moure en bloc
        s = b.sessions[x]
        h.mou(x, data=s.data, ini=s.ini, aula='')

    # fase 3: moure els blocs; primer els que van al matí (és el torn més just), després els grans
    ordre = sorted(bls, key=lambda bl: (b.sessions[bl[0]].torn != 'mati',
                                         all(b.sessions[x].sense_espai for x in bl),
                                         -max(b.sessions[x].alumnes for x in bl), -len(bl)))
    no_mouen = [bl for bl in ordre if not mou_bloc(h, bl, log)]
    # fase 3b: les sessions que han quedat fora de torn, una a una, alliberant-los un forat
    residus = [x for x in sorted(mouen) if x in h.pos and fora_de_torn(b.sessions[x], h.pos[x][1],
                                                                        h.pos[x][1] + b.sessions[x].durada)]
    fets = set()
    for x in residus:
        if b.sessions[x].unitat in fets:
            continue
        fets.add(b.sessions[x].unitat)
        if not repara_residu(h, x, log):
            log.append(f'NO REPARAT: {x} ({b.sessions[x].codi} {b.sessions[x].grup}) {h.pos[x][0]}')
    replaca_blocs(h, [bl for bl in bls if bl not in no_mouen], log)
    # opcional: també es poden moure activitats que ja eren al seu torn, si cada sessió moguda estalvia prou hores
    # mortes (TORNS_COST_CANVI minuts per sessió fora de la seva hora d'avui); per defecte no es fa
    cost_canvi = float(os.environ.get('TORNS_COST_CANVI', 0))
    if cost_canvi:
        ja = {x for bl in bls for x in bl}
        resta = [x for x in h.pos if x not in ja and not b.sessions[x].fixada and b.sessions[x].tipus != 'PLAB'
                 and not b.sessions[x].sense_espai]
        extra = [bl for bl in blocs(b, sorted({y for x in resta for y in per_act[b.sessions[x].activitat or x]}))
                 if not any(b.sessions[y].fixada or y in ja or y not in h.pos for y in bl)]
        replaca_blocs(h, extra + [bl for bl in bls if bl not in no_mouen], log, cost_canvi=cost_canvi)
    # opcional: resoldre solapaments de docent/alumnat/PLAB que ja hi eren a l'horari d'avui (el verificador els
    # compta com a heretats) movent el bloc no fixat a una franja del seu torn on no xoqui amb ningú
    if os.environ.get('TORNS_RESOL_SOLAP') == '1':
        ja = {x for bl in bls for x in bl}
        xoquen = {x for x, (d, i, au) in h.pos.items() if not b.sessions[x].fixada and b.sessions[x].tipus != 'PLAB'
                  and not b.sessions[x].sense_espai and not h.persones_lliures(x, d, i, i + b.sessions[x].durada)}
        cands_bl = [bl for bl in blocs(b, sorted({y for x in xoquen for y in per_act[b.sessions[x].activitat or x]}))
                    if not any(b.sessions[y].fixada or y not in h.pos for y in bl)]
        n0 = len(xoquen)
        replaca_blocs(h, cands_bl, log, passades=2, cost_canvi=cost_canvi, forcats={bl[0] for bl in cands_bl})
        n1 = sum(1 for x, (d, i, au) in h.pos.items() if not b.sessions[x].fixada and b.sessions[x].tipus != 'PLAB'
                 and not b.sessions[x].sense_espai and not h.persones_lliures(x, d, i, i + b.sessions[x].durada))
        log.append(f'Solapaments heretats: {n0} sessions no fixades amb xoc -> {n1}')
    # opcional (TORNS_PER_SETMANA=1): les sessions que ja canvien d'hora (ja compten a `canvis_franja`) es poden
    # re-col·locar setmana a setmana, cadascuna a la franja del seu torn que deixa menys hores mortes al grup
    if os.environ.get('TORNS_PER_SETMANA') == '1':
        mogudes = {x for x, (d, i, au) in h.pos.items() if (d, i) != (b.sessions[x].data, b.sessions[x].ini)
                   and not b.sessions[x].fixada and b.sessions[x].tipus != 'PLAB'
                   and fora_de_torn(b.sessions[x], b.sessions[x].ini, b.sessions[x].ini + b.sessions[x].durada)}
        per_unitat = {}
        for x in sorted(mogudes):
            u = b.sessions[x].unitat
            if u not in per_unitat:
                xs = [y for y in h.unitats[u] if y in h.pos]
                if all(y in mogudes for y in xs):
                    per_unitat[u] = xs
        replaca_blocs(h, list(per_unitat.values()), log, passades=int(os.environ.get('TORNS_PER_SETMANA_PASSADES', 3)),
                      cost_canvi=1000.0)
    # fase 4: qualitat de les aules (només les que hem triat nosaltres: les aules d'avui no es toquen)
    lliures = {x for x in h.pos if not b.sessions[x].sense_espai and b.sessions[x].tipus != 'PLAB'
               and not (b.sessions[x].aula and h.pos[x][2] == b.sessions[x].aula)
               and not (b.sessions[x].fixada and b.sessions[x].aula)}
    if os.environ.get('TORNS_AULES_AVUI_LLIURES') == '1':
        # experiment: també es poden canviar les aules d'avui (no les de sessions fixades amb aula ni els PLAB)
        lliures = {x for x in h.pos if not b.sessions[x].sense_espai and b.sessions[x].tipus != 'PLAB'
                   and not (b.sessions[x].fixada and b.sessions[x].aula)}
    millora_aules(h, lliures, log)
    optimitza_aules(h, lliures, log)
    optimitza_aules(h, lliures, log, per_unitat=True)
    if not a.sense_cpsat:
        reassigna_aules(h, lliures, log)
    acosta_edifici(h, log)

    # sortida
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
                 if r['id_sessio'].strip() in base.sessions]
    inf = avalua(base, files_out)
    rel_rows = relaxacions(base, inf)
    if a.relaxacions:
        with open(a.relaxacions, 'w', encoding='utf-8', newline='') as f:
            w = csv.writer(f)
            w.writerow(['restriccio', 'sessions', 'justificacio'])
            for r in rel_rows:
                w.writerow(r)
        inf = avalua(base, files_out, llegeix_relaxacions(Path(a.relaxacions)))
    rec = inf.recompte()
    res = {'veredicte': inf.veredicte, 'compten': {k: v['compten'] for k, v in rec.items() if v['compten']},
           'declarades': {k: v['declarades'] for k, v in rec.items() if v['declarades']},
           'objectius': inf.objectius, 'blocs': len(bls), 'blocs_no_moguts': len(no_mouen),
           'sessions_sense_aula': len(sense_aula), 'accions': log}
    print('\n'.join(x for x in log if x.startswith(('NO ', 'Sense'))))
    print(f"\nBlocs a moure: {len(bls)} · no moguts: {len(no_mouen)} · sessions sense aula: {len(sense_aula)}")
    print(f"Veredicte: {res['veredicte']}")
    print(f"Compten: {res['compten']}")
    print(f"Declarades: {res['declarades']}")
    print(f"Objectius: {res['objectius']}")
    if a.informe:
        Path(a.informe).write_text(json.dumps(res, ensure_ascii=False, indent=2, default=str) + '\n', encoding='utf-8')
    return 0 if res['veredicte'].startswith('VALIDA') else 1


def relaxacions(base, inf) -> list[list[str]]:
    """Només el que no es pot evitar, agrupat per motiu i amb la justificació."""
    b = base
    r1_fixades = sorted({v.sessions[0] for v in inf.violacions
                         if v.regla == 'R1-TORN' and v.compta and b.sessions[v.sessions[0]].fixada})
    files = []
    if r1_fixades:
        files.append(['R1-TORN', '|'.join(r1_fixades),
                      "Grups de GEI i GEET+GEST de 1r i 2n fixats per l'Escola («no es toquen», regla 1) que avui fan "
                      "classe a la tarda. No es poden moure de franja; la proposta només els assigna l'aula que no "
                      "tenien (regla 5), i per això el verificador ja no els marca com a heretats. Es mantenen al seu "
                      "torn actual tal com demana l'Escola."])
    # sessions movibles que no es poden posar al seu torn: proves de recompte (regla 11, «demostrat que no existeix»)
    residus = sorted({v.sessions[0] for v in inf.violacions
                      if v.regla == 'R1-TORN' and v.compta and not b.sessions[v.sessions[0]].fixada})
    for sid in residus:
        files.append(['R1-TORN', sid, PROVES.get(sid, (
            "No s'ha trobat cap franja del seu torn dins la seva setmana amb alumnat, docents i aula lliures; es "
            "manté a la seva hora d'avui. (Sense prova formal d'impossibilitat: «no l'hem trobat».)"))])
    return files


# Proves d'impossibilitat comprovades amb les dades (vegeu INFORME.md). Si una nova execució deixa fora de torn
# una altra sessió, rep el text genèric de «no l'hem trobat».
PROVES = {
    'S02839': (
        "Demostrat que no hi cap: el 31/5/2027 és l'únic dia lectiu de la seva setmana ISO (de l'1 al 4/6 no hi ha "
        "docència, R2-CALENDARI) i els docents D214 i D398 hi tenen 480 minuts de classes que han de ser a la tarda "
        "(102730 PAUL/321, PAUL/322, TE/320, TE/7 i la doble TE/51), mentre que la finestra de tarda en té 390. Almenys "
        "90 minuts han de quedar fora de la tarda: es deixa al seu horari d'avui la classe que costa menys incompliments "
        "(TE/7, una sola fila; la doble TE/51 en compta dues perquè és compartida)."),
    'S04511': (
        "Demostrat que no hi cap: el 9/4/2027 és l'únic dia de la seva setmana on es pot moure (del 5 al 8/4 és la "
        "setmana intrasemestral d'avaluació, R2-CALENDARI). Aquest PAUL (34 alumnes) només pot anar a les aules "
        "d'informàtica Q1/0007 o Q1/0019 (els laboratoris integrats són de 24 places), i totes dues estan ocupades de "
        "15.00 a 19.00 per grups fixats (R1). Queden 14.30-15.00 (massa curt) i 19.00-21.00, però el docent D380 hi té "
        "tres PAUL de 60 minuts (451, 452 i 453) que necessiten aquestes aules: dues hores per a tres classes."),
}


if __name__ == '__main__':
    sys.exit(main())
