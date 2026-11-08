"""5.2 variant generator: local search (cerca_local.py) + placement of the two sessions that used to be relaxations.

Relaxations (statement §7: VALIDA beats VALIDA AMB RELAXACIONS, and fewer declared sessions rank higher):
- S02839 (TE/7, 31/5/2027): NOT a relaxation any more. TE/320, TE/51 and TE/7 share teachers D214+D398 and are taught at
  the same time in the starting timetable, so keeping TE/7 at the same time as TE/320 (or TE/51) in the afternoon only
  produces R4-DOCENT overlaps the verifier marks as inherited ("partida") and does not count.
- S04511 (PAUL/452, 9/4/2027): the only afternoon gap left is in an ordinary classroom (the two IT rooms are taken by
  fixed groups 15-19 and D380 has three 60-min PAULs for the 19-21 gap; integrated labs have 24 seats for 34 students).
  Three modes, chosen per variant:
    torn    keep it at 12:30 in Q1/0019, declare R1-TORN (1 relaxation, as before)
    tipus   move it to an ordinary classroom in the afternoon, declare R3-TIPUS (1 relaxation, rule 1 is met)
    nodecl  same placement, nothing declared: locally NO VALIDA (R3-TIPUS); a probe to see whether the web verifier
            accepts a PAUL in an ordinary classroom (the statement says every room has PCs and a projector)

usage as a script: genera.py BASE OUTDIR N SECONDS PARALLEL SEED [MODES comma list]
"""
from __future__ import annotations

import csv
import json
import os
import random
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

DATA = Path(os.environ.get('HK_ROOT', r'C:\Users\Usuario\Desktop\hackathon2026'))   # checkout that holds paquet/ and .venv
PY = str(DATA / '.venv' / 'Scripts' / 'python.exe')
HOR = DATA / 'repte-horaris-escola'
PAQ = HOR / 'paquet'
ESC = PAQ / 'escenaris' / 'contingencies'
CERCA = DATA / 'nivell2' / 'p52_torns' / 'cerca_local.py'
RELAX0 = DATA / 'lliuraments' / 'relaxacions.csv'
sys.path.insert(0, str(HOR))
from horaris.check import avalua  # noqa: E402
from horaris.model import carrega_base, llegeix_proposta, llegeix_relaxacions  # noqa: E402

JUST_TIPUS = ("Demostrat que a l'aula d'informàtica no hi cap a la tarda: el 9/4/2027 és l'únic dia de la seva setmana on "
              "es pot moure (del 5 al 8/4 és la setmana intrasemestral d'avaluació, R2-CALENDARI). Les dues aules "
              "d'informàtica (Q1/0007 i Q1/0019) estan ocupades de 15.00 a 19.00 per grups fixats de GEI 1r (R1), i de "
              "19.00 a 21.00 hi van els altres dos PAUL de 60 minuts del docent D380 (451 i 453): dues hores per a tres "
              "classes. Els laboratoris integrats són de 24 places i el grup en té 34. Per complir el torn (regla 1) es porta "
              "a una aula docent de la tarda amb aforament suficient; l'enunciat diu que totes les aules tenen PC i projector.")

C = random.choice
WEIGHTS = {
    'franja': lambda: dict(temperatura=C([2, 5, 10]), prob_temps=C([.7, .8, .9]), pes_mortes=C([.3, 1, 2, 4]), pes_desplac=C([10, 30, 80, 200]),
                           pes_passadis=C([10, 30, 80]), pes_extra=C([100, 300, 800]), pes_franja=C([40, 60, 100, 200]), pes_aula=C([60, 150, 300])),
    'franjamax': lambda: dict(temperatura=C([0, 0, 1]), prob_temps=C([.8, .95]), pes_mortes=C([1, 2, 4, 8]), pes_desplac=C([10, 30, 80]),
                              pes_passadis=C([10, 30, 80]), pes_extra=C([300, 800]), pes_franja=C([400, 800, 1500, 3000]), pes_aula=C([150, 300])),
    'polir': lambda: dict(temperatura=C([0, 0, 1]), prob_temps=C([.6, .8]), pes_mortes=C([1, 2, 4]), pes_desplac=C([30, 80]),
                          pes_passadis=C([30, 80]), pes_extra=C([300, 800]), pes_franja=C([200, 400]), pes_aula=C([150, 300])),
    'r6': lambda: dict(temperatura=C([0, 1, 2]), prob_temps=C([.3, .5]), pes_mortes=C([2, 4]), pes_desplac=C([30, 80]),
                       pes_passadis=C([30, 80]), pes_extra=C([2000, 4000]), pes_franja=C([200, 400]), pes_aula=C([400, 800])),
    'ampli': lambda: dict(temperatura=C([0, 2, 5, 10, 20]), prob_temps=C([.2, .5, .8]), pes_mortes=C([.3, 1, 2, 4]), pes_desplac=C([10, 30, 80, 200]),
                          pes_passadis=C([10, 30, 80, 200]), pes_extra=C([100, 300, 800]), pes_franja=C([.5, 2, 10, 40]), pes_aula=C([20, 60, 150, 400])),
}
W_ORDER = ['franja', 'polir', 'franjamax', 'r6', 'franja', 'polir', 'ampli', 'franjamax', 'r6', 'polir']
KEYS = [('idle', 'hores_mortes_min'), ('moves', 'desplacaments_aula'), ('bldg', 'desplacaments_edifici'), ('franja', 'canvis_franja'),
        ('aula', 'canvis_aula'), ('extra', 'r6_aules_te_extra_per_grup'), ('corr', 'r6_canvis_te_paul_fora_passadis')]

_base = None


def base():
    global _base
    if _base is None:
        _base = carrega_base(PAQ, semestre=2)
    return _base


def llegeix(p: Path) -> list[list[str]]:
    with open(p, encoding='utf-8', newline='') as f:
        return list(csv.reader(f))


def escriu(p: Path, rows) -> None:
    with open(p, 'w', encoding='utf-8', newline='') as f:
        csv.writer(f).writerows(rows)


def relaxacions(s02839_placed: bool, mode: str) -> list[list[str]]:
    rows = llegeix(RELAX0)
    out = [rows[0]]
    for r in rows[1:]:
        ses = r[1].split('|')
        if ses == ['S02839']:
            if not s02839_placed:
                out.append(r)
        elif ses == ['S04511']:
            if mode == 'torn':
                out.append(r)
        else:
            out.append(r)                       # the fixed GEI / GEET+GEST groups row (inherited on the web verifier)
    if mode == 'tipus':
        out.append(['R3-TIPUS', 'S04511', JUST_TIPUS])
    return out


def avalua_fitxers(prop: Path, rel: Path):
    b = base()
    return avalua(b, [f for f in llegeix_proposta(prop) if f.id in b.sessions], llegeix_relaxacions(rel))


def compten(inf) -> set:
    return {(v.regla, v.sessions) for v in inf.violacions if not v.declarada and not v.heretada}


def col_loca(rows, sid, cands, d: Path, rel: Path, permeses: set):
    """Try (dia, hora, aula) candidates for `sid`; keep the first one whose counted violations are within `permeses`."""
    i = next(k for k, r in enumerate(rows) if r[0] == sid)
    orig = rows[i]
    tmp = d / 'prova.csv'
    for dia, h, aula in cands:
        rows[i] = [sid, dia, h, aula]
        escriu(tmp, rows)
        if compten(avalua_fitxers(tmp, rel)) <= permeses:
            tmp.unlink()
            return rows[i]
    rows[i] = orig
    tmp.unlink(missing_ok=True)
    return None


def aules(filtre) -> list[str]:
    b = base()
    return [k for k, a in sorted(b.aules.items(), key=lambda kv: (kv[1].capacitat, kv[0])) if filtre(a)]


def postprocessa(pre: Path, d: Path, mode: str) -> dict:
    rows = llegeix(pre)
    rel = d / 'relaxacions.csv'
    info = {'mode': mode}
    # S02839 next to TE/320 (S02811) or TE/51 (S02825): inherited teacher overlap
    escriu(rel, relaxacions(True, 'torn'))       # S04511 still declared while we place S02839
    pos = {r[0]: r for r in rows[1:]}
    hores = [pos[s][2] for s in ('S02811', 'S02825') if s in pos and pos[s][1] == 'L']
    sales = ['QC/3115.4'] + aules(lambda a: a.tipus in ('Seminaris', 'Aules docents'))
    got = col_loca(rows, 'S02839', [('L', h, a) for h in hores for a in sales], d, rel, set())
    info['S02839'] = ' '.join(got) if got else 'relaxacio'
    # S04511 according to the mode
    if mode in ('tipus', 'nodecl'):
        escriu(rel, relaxacions(bool(got), mode))
        perm = {('R3-TIPUS', ('S04511',))} if mode == 'nodecl' else set()
        hs = [f'{m // 60:02d}:{m % 60:02d}' for m in range(14 * 60 + 30, 20 * 60 + 1, 30)]
        sales = aules(lambda a: a.tipus == 'Aules docents' and a.capacitat >= 34)
        sales.sort(key=lambda a: (not a.startswith('Q1/'), a))
        g2 = col_loca(rows, 'S04511', [('V', h, a) for h in hs for a in sales], d, rel, perm)
        if not g2:
            mode = info['mode'] = 'torn'
        info['S04511'] = ' '.join(g2) if g2 else 'R1-TORN (no lloc a la tarda)'
    else:
        info['S04511'] = 'R1-TORN'
    escriu(rel, relaxacions(bool(got), mode))
    escriu(d / 'proposta.csv', rows)
    inf = avalua_fitxers(d / 'proposta.csv', rel)
    bad = compten(inf)
    info['valida_local'] = not bad
    info['compten'] = sorted(f'{r}:{"|".join(s)}' for r, s in bad)
    info['declarades_web'] = (0 if got else 1) + (1 if mode in ('torn', 'tipus') else 0)
    info['obj'] = {lab: inf.objectius.get(k) for lab, k in KEYS}
    return info


def genera(base_csv: str, out: Path, n: int, secs: str, par: int, seed: int, modes: list[str]) -> list[dict]:
    random.seed(seed)
    out.mkdir(parents=True, exist_ok=True)
    plans = []
    for i in range(1, n + 1):
        w = W_ORDER[(i - 1) % len(W_ORDER)]
        plans.append((i, w, WEIGHTS[w](), modes[(i - 1) % len(modes)]))

    def cerca(p):
        i, w, pesos, _ = p
        d = out / f'v{i:02d}'
        d.mkdir(exist_ok=True)
        args = [PY, str(CERCA), str(base_csv), '--sortida', str(d / 'pre.csv'), '--segons', secs, '--llavor', str(seed * 100 + i),
                '--paquet', str(PAQ), '--pes-edifici', '5000', '--escenari', str(ESC)]
        for k, v in pesos.items():
            args += ['--' + k.replace('_', '-'), str(v)]
        subprocess.run(args, stdin=subprocess.DEVNULL, capture_output=True)

    with ThreadPoolExecutor(par) as ex:
        list(ex.map(cerca, plans))
    res = []
    for i, w, pesos, mode in plans:
        d = out / f'v{i:02d}'
        if not (d / 'pre.csv').exists():
            continue
        info = postprocessa(d / 'pre.csv', d, mode)
        info.update(dir=str(d), pesos=w, params=pesos)
        (d / 'info.json').write_text(json.dumps(info, ensure_ascii=False, indent=1), encoding='utf-8')
        if info['valida_local'] or mode == 'nodecl':
            res.append(info)
    return res


if __name__ == '__main__':
    a = sys.argv
    ms = a[7].split(',') if len(a) > 7 else ['tipus']
    print(json.dumps(genera(a[1], Path(a[2]).resolve(), int(a[3]), a[4], int(a[5]), int(a[6]), ms), ensure_ascii=False))
