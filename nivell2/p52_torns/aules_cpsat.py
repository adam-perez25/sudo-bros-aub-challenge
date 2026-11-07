"""Reassignació d'aules amb CP-SAT, dia a dia, sense tocar cap dia ni hora.

Parteix d'un horari ja col·locat (`HorariT`) i, per a cada data, tria l'aula de les unitats «lliures» (les que hem
triat nosaltres: les aules d'avui i les fixades amb aula no es toquen) minimitzant l'indicador real del verificador:

* canvis d'aula entre dues classes consecutives del mateix grup (`desplacaments_aula`),
* +1 si és TE<->PAUL i canvia de passadís (`r6_canvis_te_paul_fora_passadis`),
* classes que deixen l'aula d'avui (`canvis_aula`),
* un petit cost per a la teoria fora de l'aula base del grup (`r6_aules_te_extra_per_grup`, que lliga les dates).

Restriccions dures (mateixes que `HorariT.aula_valida`): tipus, aforament, aules tancades, cap solapament d'aula i
reserva de 2 aules ordinàries lliures a cada franja (regla 8). L'aula actual de cada unitat és sempre una solució
factible i s'hi parteix com a pista, de manera que l'indicador mai no empitjora.
"""
from __future__ import annotations

import collections
import datetime as dt

from ortools.sat.python import cp_model

from horaris.check import FRANGES, RESERVA_MIN, _espai_ok, passadis
from horaris.model import MATI, a_traslladar

PES_PARELLA = 10      # un canvi d'aula (o de passadís) entre classes consecutives
PES_ORIGEN = 10       # una classe que deixa l'aula d'avui
PES_TE_BASE = 3
RESTRINGEIX_TE = True   # la teoria només usa aules que el seu grup ja usa: l'indicador d'aules extra no pot créixer


def _parelles_dia(h, data: dt.date) -> dict[tuple[str, str], int]:
    """Parelles consecutives (sessió, sessió) de les agendes dels grups aquell dia, amb la seva multiplicitat."""
    b = h.base
    agenda: dict[tuple, list[str]] = collections.defaultdict(list)
    for sid in h.per_data.get(data, ()):
        s = b.sessions[sid]
        for coh in s.cohorts:
            agenda[(coh, s.linia, s.num_grup if s.tipus != 'TE' else '*')].append(sid)
    linies: dict[tuple, set] = collections.defaultdict(set)
    for (coh, lin, sg) in agenda:
        linies[(coh, lin)].add(sg)
    out: dict[tuple[str, str], int] = collections.Counter()
    for (coh, lin), sgs in linies.items():
        teoria = agenda.get((coh, lin, '*'), [])
        reals = [x for x in sgs if x != '*'] or ['*']
        for sg in reals:
            ids = set(teoria) | (set(agenda.get((coh, lin, sg), ())) if sg != '*' else set())
            cs = sorted(ids, key=lambda x: h.pos[x][1])
            for x, y in zip(cs, cs[1:]):
                if b.sessions[x].unitat != b.sessions[y].unitat:
                    out[(x, y)] += 1
    return out


def reassigna_aules(h, lliures: set[str], log: list, temps_dia: float = 10.0, rondes: int = 2,
                    workers: int = 8) -> int:
    b = h.base
    ordinaries = set(h.ordinaries)
    canvis_tot = 0
    # unitats lliures: totes les seves sessions són lliures i tenen aula triada
    unitat_lliure = {}
    for u, sids in h.unitats.items():
        sids = [x for x in sids if x in h.pos]
        if sids and all(x in lliures and h.pos[x][2] for x in sids):
            unitat_lliure[u] = sids
    dates = sorted({h.pos[sids[0]][0] for sids in unitat_lliure.values()})
    per_data_unitats: dict[dt.date, list[str]] = collections.defaultdict(list)
    for u, sids in unitat_lliure.items():
        per_data_unitats[h.pos[sids[0]][0]].append(u)

    for ronda in range(rondes):
        # aula base de la teoria per (cohort, línia): la més usada ara
        usos: dict[tuple, collections.Counter] = collections.defaultdict(collections.Counter)
        for sid, (d, i, a) in h.pos.items():
            s = b.sessions[sid]
            if s.tipus == 'TE' and a:
                for coh in s.cohorts:
                    usos[(coh, s.linia)][a] += 1
        base_te = {k: c.most_common(1)[0][0] for k, c in usos.items()}
        sets_te = {k: set(c) for k, c in usos.items()}
        canvis_ronda = 0
        for data in dates:
            canvis_ronda += _resol_dia(h, data, per_data_unitats[data], unitat_lliure, ordinaries, base_te, sets_te,
                                       temps_dia, workers)
        log.append(f'CP-SAT d\'aules, ronda {ronda + 1}: {canvis_ronda} unitats canvien d\'aula')
        canvis_tot += canvis_ronda
        if not canvis_ronda:
            break
    return canvis_tot


def _resol_dia(h, data, unitats: list[str], unitat_lliure, ordinaries, base_te, sets_te, temps, workers) -> int:
    b = h.base
    lliures_ids = {x for u in unitats for x in unitat_lliure[u]}
    info = {}   # unitat -> (ini, fi, alumnes, sessions)
    for u in unitats:
        sids = unitat_lliure[u]
        s0 = b.sessions[sids[0]]
        ini = h.pos[sids[0]][1]
        info[u] = (ini, ini + s0.durada, sum(b.sessions[x].alumnes for x in sids if not b.sessions[x].sense_espai),
                   sids)

    # ocupació fixa d'aquell dia (sessions no lliures amb aula de l'aulari)
    ocupat: dict[str, list[tuple[int, int]]] = collections.defaultdict(list)
    for sid in h.per_data.get(data, ()):
        if sid in lliures_ids:
            continue
        s = b.sessions[sid]
        a = h.pos[sid][2]
        if a in b.aules and not s.sense_espai:
            ocupat[a].append((h.pos[sid][1], h.pos[sid][1] + s.durada))

    perm: dict[str, list[str]] = {}
    for u, (ini, fi, alumnes, sids) in info.items():
        ses = [b.sessions[x] for x in sids if not b.sessions[x].sense_espai]
        actual = h.pos[sids[0]][2]
        ok = []
        for a, x in b.aules.items():
            if a != actual:
                if x.capacitat < alumnes or not all(_espai_ok(b, s, a) for s in ses):
                    continue
                if h.tancada(a, data, ini, fi) or any(p < fi and q > ini for p, q in ocupat.get(a, ())):
                    continue
            if RESTRINGEIX_TE and a != actual:
                # la teoria no pot obrir una aula nova per a un grup: l'indicador d'aules extra no creix
                if any(a not in sets_te.get((coh, s.linia), ()) for s in ses if s.tipus == 'TE' for coh in s.cohorts):
                    continue
            ok.append(a)
        perm[u] = ok if actual in ok else ok + [actual]

    m = cp_model.CpModel()
    x = {(u, a): m.NewBoolVar(f'x_{u}_{a}') for u in info for a in perm[u]}
    for u in info:
        m.AddExactlyOne(x[u, a] for a in perm[u])

    # solapaments entre unitats lliures
    ordenades = sorted(info, key=lambda u: info[u][0])
    for i, u in enumerate(ordenades):
        for v in ordenades[i + 1:]:
            if info[v][0] >= info[u][1]:
                break
            for a in set(perm[u]) & set(perm[v]):
                m.AddBoolOr([x[u, a].Not(), x[v, a].Not()])

    # reserva: >= RESERVA_MIN aules ordinàries lliures a cada franja
    if len(ordinaries) >= RESERVA_MIN:
        for f0 in FRANGES:
            tocades = [u for u in info if info[u][0] < f0 + 60 and info[u][1] > f0]
            if not tocades:
                continue
            fixes = {a for a in ordinaries for p, q in ocupat.get(a, ()) if p < f0 + 60 and q > f0}
            o = {}
            for u in tocades:
                for a in perm[u]:
                    if a in ordinaries and a not in fixes:
                        if a not in o:
                            o[a] = m.NewBoolVar(f'o_{a}_{f0}')
                        m.AddImplication(x[u, a], o[a])
            if o:
                m.Add(sum(o.values()) <= len(ordinaries) - RESERVA_MIN - len(fixes))

    # objectiu
    termes = []
    unitat_de = {sid: u for u in info for sid in info[u][3]}

    def igual(u, v):
        """Variable 1 si les dues unitats lliures acaben a la mateixa aula."""
        y = []
        for a in set(perm[u]) & set(perm[v]):
            z = m.NewBoolVar(f'z_{u}_{v}_{a}')
            m.AddImplication(z, x[u, a])
            m.AddImplication(z, x[v, a])
            y.append(z)
        return sum(y) if y else 0

    def mateix_passadis(u, v):
        ps = collections.defaultdict(list)
        for a in perm[u]:
            ps[passadis(a)].append(x[u, a])
        qs = collections.defaultdict(list)
        for a in perm[v]:
            qs[passadis(a)].append(x[v, a])
        y = []
        for p in set(ps) & set(qs):
            z = m.NewBoolVar(f'p_{u}_{v}_{p}')
            m.Add(z <= sum(ps[p]))
            m.Add(z <= sum(qs[p]))
            y.append(z)
        return sum(y) if y else 0

    for (sx, sy), mult in _parelles_dia(h, data).items():
        ux, uy = unitat_de.get(sx), unitat_de.get(sy)
        if ux is None and uy is None:
            continue
        tx, ty = b.sessions[sx].tipus, b.sessions[sy].tipus
        te_paul = {tx, ty} == {'TE', 'PAUL'}
        ax, ay = h.pos[sx][2], h.pos[sy][2]
        if ux and uy:
            termes.append(PES_PARELLA * mult * (1 - igual(ux, uy)))
            if te_paul:
                termes.append(PES_PARELLA * mult * (1 - mateix_passadis(ux, uy)))
        else:
            lliure, fixa_aula = (ux, ay) if ux else (uy, ax)
            if not fixa_aula or fixa_aula not in b.aules or b.sessions[sx if ux else sy].sense_espai:
                continue
            if b.sessions[sy if ux else sx].sense_espai:
                continue
            xs = x.get((lliure, fixa_aula))
            termes.append(PES_PARELLA * mult * (1 - xs if xs is not None else 1))
            if te_paul:
                mateix = [x[lliure, a] for a in perm[lliure] if passadis(a) == passadis(fixa_aula)]
                termes.append(PES_PARELLA * mult * (1 - sum(mateix) if mateix else 1))

    for u, (ini, fi, alumnes, sids) in info.items():
        # classes que deixen l'aula d'avui
        for sid in sids:
            s = b.sessions[sid]
            if s.aula and not a_traslladar(s.aula) and not s.sense_espai:
                v = x.get((u, s.aula))
                termes.append(PES_ORIGEN * (1 - v if v is not None else 1))
        # teoria fora de l'aula base del grup
        for sid in sids:
            s = b.sessions[sid]
            if s.tipus == 'TE':
                for coh in s.cohorts:
                    base = base_te.get((coh, s.linia))
                    v = x.get((u, base))
                    termes.append(PES_TE_BASE * (1 - v if v is not None else 1))

    m.Minimize(sum(termes))
    for u in info:
        actual = h.pos[info[u][3][0]][2]
        for a in perm[u]:
            m.AddHint(x[u, a], 1 if a == actual else 0)

    sol = cp_model.CpSolver()
    sol.parameters.max_time_in_seconds = temps   # cerca en paral·lel: el resultat varia unes unitats entre execucions
    sol.parameters.num_workers = workers
    sol.parameters.random_seed = 1
    st = sol.Solve(m)
    if st not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return 0
    canvis = 0
    for u in info:
        nova = next(a for a in perm[u] if sol.BooleanValue(x[u, a]))
        for sid in info[u][3]:
            if h.pos[sid][2] != nova:
                canvis += 1 if sid == info[u][3][0] else 0
                h.mou(sid, aula=nova)
    return canvis
