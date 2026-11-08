"""5.2 · Cerca local sobre una proposta ja vàlida (no substitueix `torns.py`: el millora després).

    python nivell2/p52_torns/cerca_local.py lliuraments/proposta-torns.csv --sortida /tmp/52-cl.csv \
        [--segons 300] [--llavor 1] [--pes-mortes 1 --pes-desplac 30 ...]

Parteix d'un horari vàlid i fa moviments petits, sessió (unitat) a sessió:
  * canviar l'aula d'una unitat;
  * moure una unitat a una altra franja del seu torn, el mateix dia o un altre dia de la mateixa setmana ISO.
Un moviment només s'aplica si no trenca cap regla dura (les mateixes comprovacions que `torns.py`: torn i finestra,
calendari, docent/alumnat/PLAB lliures, tipus, aforament, aula tancada, aula lliure i reserva de 2 aules) i si baixa
un objectiu ponderat amb els indicadors del verificador (hores mortes, desplaçaments d'aula i d'edifici, canvis TE<->PAUL
fora del passadís, canvis de franja i d'aula respecte d'avui, aules de teoria de més per grup). Accepta també alguns
empitjoraments petits al principi (recuit simulat) per sortir de mínims locals.

No toca sessions fixades, PLAB, dobles titulacions sense aula ni cap sessió que no tingui totes les seves companyes
(sessions compartides) movibles. Les relaxacions de la proposta d'entrada es copien tal qual.
"""
from __future__ import annotations

import argparse
import collections
import csv
import math
import random
import sys
import time
from pathlib import Path

AQUI = Path(__file__).resolve().parent
ROOT = AQUI.parents[1]
sys.path.insert(0, str(ROOT / 'repte-horaris-escola'))
sys.path.insert(0, str(ROOT / 'nivell2' / 'p53_imprevist'))
sys.path.insert(0, str(AQUI))

from horaris.check import passadis  # noqa: E402
from horaris.model import DIES, MATI, TARDA, a_traslladar, carrega_base, fmt  # noqa: E402
from imprevist import a_fila, llegeix_files_csv  # noqa: E402
from torns import HorariT, data_objectiu, dia_bloquejat, fora_de_torn  # noqa: E402

PAQUET = ROOT / 'repte-horaris-escola' / 'paquet'
PAS_MIN = 30


def edifici(b, aula: str) -> str:
    x = b.aules.get(aula)
    return x.edifici if x else aula.split('/')[0]


class Cost:
    """Objectiu ponderat amb càlcul incremental per (cohort, línia, data), com l'agenda del verificador."""

    def __init__(self, h: HorariT, pesos: dict):
        self.h = h
        self.b = h.base
        self.p = pesos
        # aules de teoria per (cohort, línia) -> Counter(aula)
        self.te: dict[tuple, collections.Counter] = collections.defaultdict(collections.Counter)
        for sid, (d, i, a) in h.pos.items():
            s = self.b.sessions[sid]
            if s.tipus == 'TE' and a:
                for c in s.cohorts:
                    self.te[(c, s.linia)][a] += 1

    # ---- termes per sessió
    def franja(self, sid) -> int:
        s = self.b.sessions[sid]
        d, i, a = self.h.pos[sid]
        return int((d, i) != (s.data, s.ini))

    def canvi_aula(self, sid) -> int:
        s = self.b.sessions[sid]
        return int(bool(s.aula) and not a_traslladar(s.aula) and not s.sense_espai and self.h.pos[sid][2] != s.aula)

    # ---- termes per clau (cohort, línia, data): hores mortes, desplaçaments, edifici, passadís
    def clau(self, coh, linia, d) -> tuple[int, int, int, int]:
        h, b = self.h, self.b
        agenda = collections.defaultdict(list)
        for sid in h.per_coh.get((d, coh), ()):
            s = b.sessions[sid]
            if s.linia == linia and sid in h.pos:
                agenda[s.num_grup if s.tipus != 'TE' else '*'].append(sid)
        teoria = agenda.get('*', [])
        reals = [g for g in agenda if g != '*'] or ['*']
        mortes = desplac = edif = pas = 0
        for g in reals:
            ids = set(teoria) | (set(agenda.get(g, ())) if g != '*' else set())
            cs = sorted(ids, key=lambda x: h.pos[x][1])
            for x, y in zip(cs, cs[1:]):
                sx, sy = b.sessions[x], b.sessions[y]
                fx = h.pos[x][1] + sx.durada
                iy = h.pos[y][1]
                gap = iy - fx
                if gap > 0 and (fx <= MATI[1]) == (iy < MATI[1]):
                    mortes += gap
                ax, ay = h.pos[x][2], h.pos[y][2]
                if ax and ay and ax != ay:
                    desplac += 1
                    if edifici(b, ax) != edifici(b, ay):
                        edif += 1
                if {sx.tipus, sy.tipus} == {'TE', 'PAUL'} and ax and ay and passadis(ax) != passadis(ay):
                    pas += 1
        return mortes, desplac, edif, pas

    def valor_claus(self, claus) -> float:
        p = self.p
        t = 0.0
        for k in claus:
            m, dsp, e, ps = self.clau(*k)
            t += p['mortes'] * m + p['desplac'] * dsp + p['edifici'] * e + p['passadis'] * ps
        return t

    def claus(self, sids) -> set:
        b = self.b
        return {(c, b.sessions[x].linia, self.h.pos[x][0]) for x in sids for c in b.sessions[x].cohorts}

    def extra_te(self, keys) -> int:
        return sum(max(0, len([a for a, n in self.te[k].items() if n > 0]) - 1) for k in keys)

    def te_claus(self, sids) -> set:
        b = self.b
        return {(c, b.sessions[x].linia) for x in sids if b.sessions[x].tipus == 'TE' for c in b.sessions[x].cohorts}

    def te_actualitza(self, sids, signe: int) -> None:
        for x in sids:
            s = self.b.sessions[x]
            a = self.h.pos[x][2]
            if s.tipus == 'TE' and a:
                for c in s.cohorts:
                    self.te[(c, s.linia)][a] += signe

    def local(self, sids, claus, te_keys) -> float:
        p = self.p
        return (self.valor_claus(claus) + p['franja'] * sum(self.franja(x) for x in sids)
                + p['aula'] * sum(self.canvi_aula(x) for x in sids) + p['extra'] * self.extra_te(te_keys))


def unitats_movibles(h: HorariT) -> list[list[str]]:
    b = h.base
    out = []
    for u, xs in h.unitats.items():
        xs = [x for x in xs if x in h.pos]
        if not xs:
            continue
        if any(b.sessions[x].fixada or b.sessions[x].tipus == 'PLAB' or b.sessions[x].sense_espai for x in xs):
            continue
        out.append(xs)
    return out


def finestres(s):
    return [MATI] if s.torn == 'mati' else [TARDA] if s.torn == 'tarda' else [MATI, TARDA]


def proposa_temps(h: HorariT, u: list[str], rnd: random.Random):
    """Una franja nova vàlida per a la unitat (mateixa setmana ISO), o None."""
    b = h.base
    s = b.sessions[u[0]]
    a, z = rnd.choice(finestres(s))
    hores = list(range(a, z - s.durada + 1, PAS_MIN))
    if not hores:
        return None
    t = rnd.choice(hores)
    k = rnd.randrange(5)
    d = data_objectiu(s, k)
    fi = t + s.durada
    if (d, t) == tuple(h.pos[u[0]][:2]):
        return None
    if dia_bloquejat(b, s, d, t, fi) or any(fora_de_torn(b.sessions[x], t, fi) for x in u):
        return None
    if not all(h.persones_lliures(x, d, t, fi) for x in u):
        return None
    return d, t


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('proposta', help='proposta 5.2 vàlida (CSV id_sessio,dia,h_ini,aula)')
    ap.add_argument('--sortida', required=True)
    ap.add_argument('--paquet', default=str(PAQUET))
    ap.add_argument('--escenari', help="carrega també aquest escenari (p. ex. paquet/escenaris/contingencies): cap "
                    "moviment no posa una classe en una aula tancada ni en una aula massa petita per al grup que creix, "
                    "així el 5.2 que en surt continua preparat per als imprevistos del 5.3")
    ap.add_argument('--segons', type=float, default=300)
    ap.add_argument('--llavor', type=int, default=1)
    ap.add_argument('--temperatura', type=float, default=30.0, help='temperatura inicial del recuit (unitats de cost)')
    ap.add_argument('--prob-temps', type=float, default=0.5, help='probabilitat de proposar un canvi de franja')
    for nom, defecte in (('mortes', 1.0), ('desplac', 30.0), ('edifici', 2000.0), ('passadis', 30.0),
                         ('franja', 20.0), ('aula', 60.0), ('extra', 150.0)):
        ap.add_argument(f'--pes-{nom}', type=float, default=defecte)
    a = ap.parse_args(argv)
    pesos = {k: getattr(a, f'pes_{k}') for k in ('mortes', 'desplac', 'edifici', 'passadis', 'franja', 'aula', 'extra')}

    base = carrega_base(Path(a.paquet), semestre=2, escenari=Path(a.escenari) if a.escenari else None)
    b = base
    files_csv, _ = llegeix_files_csv(Path(a.proposta))
    files_in = [a_fila(r, i) for i, r in enumerate(files_csv, start=2) if r['id_sessio'].strip() in base.sessions]
    h = HorariT(base, files_in)
    if a.escenari and base.cancellades:
        # al 5.2 la sessió que l'escenari cancel·la encara existeix al seu lloc: s'hi deixa, fixa, com a obstacle
        base0 = carrega_base(Path(a.paquet), semestre=2)
        h0 = HorariT(base0, [f for f in files_in if f.id in base.cancellades])
        for sid in base.cancellades:
            if sid not in h.pos and sid in h0.pos:
                h.mou(sid, data=h0.pos[sid][0], ini=h0.pos[sid][1], aula=h0.pos[sid][2])
    cost = Cost(h, pesos)
    unitats = [u for u in unitats_movibles(h) if not any(x in base.cancellades for x in u)]
    rnd = random.Random(a.llavor)
    t0 = time.time()
    prova = accepta = millora_t = millora_a = 0
    total_delta = 0.0

    while time.time() - t0 < a.segons:
        prova += 1
        u = rnd.choice(unitats)
        s = b.sessions[u[0]]
        vell = {x: list(h.pos[x]) for x in u}
        d0, t0_, a0 = vell[u[0]]
        if rnd.random() < a.prob_temps:
            nou = proposa_temps(h, u, rnd)
            if nou is None:
                continue
            d1, t1 = nou
            fi = t1 + s.durada
            # aula: la mateixa si encara és vàlida allà, si no la primera candidata vàlida
            aules = ([a0] if a0 else []) + ([s.aula] if s.aula in b.aules else []) + h.candidates(u, a0)[:12]
            a1 = next((x for x in aules if h.aula_valida(u, x, d1, t1, fi)), None)
            if a1 is None:
                continue
            tipus = 't'
        else:
            if not a0:
                continue
            cands = [x for x in ([s.aula] if s.aula in b.aules else []) + h.candidates(u, a0)[:15] if x != a0]
            if not cands:
                continue
            a1 = rnd.choice(cands)
            d1, t1 = d0, t0_
            if not h.aula_valida(u, a1, d1, t1, t1 + s.durada):
                continue
            tipus = 'a'
        claus = cost.claus(u) | {(c, b.sessions[x].linia, d1) for x in u for c in b.sessions[x].cohorts}
        te_keys = cost.te_claus(u)
        abans = cost.local(u, claus, te_keys)
        cost.te_actualitza(u, -1)
        for x in u:
            h.mou(x, data=d1, ini=t1, aula=a1)
        cost.te_actualitza(u, +1)
        despres = cost.local(u, claus, te_keys)
        delta = despres - abans
        temp = a.temperatura * max(0.0, 1 - (time.time() - t0) / a.segons)
        if delta < 0 or (temp > 0 and rnd.random() < math.exp(-delta / temp)):
            accepta += 1
            total_delta += delta
            if delta < 0:
                if tipus == 't':
                    millora_t += 1
                else:
                    millora_a += 1
        else:
            cost.te_actualitza(u, -1)
            for x in u:
                h.mou(x, data=vell[x][0], ini=vell[x][1], aula=vell[x][2])
            cost.te_actualitza(u, +1)

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
    print(f'Cerca local: {prova} proves, {accepta} acceptades ({millora_t} millores de franja, {millora_a} d\'aula), '
          f'canvi total de l\'objectiu {total_delta:.0f}, {len(unitats)} unitats movibles, {time.time() - t0:.0f} s')
    return 0


if __name__ == '__main__':
    sys.exit(main())
