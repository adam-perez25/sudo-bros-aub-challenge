"""Interactive 5.2 loop: generate a round of variants, you upload them by hand, type the web scores, next round.

usage (from this folder):  ..\\..\\..\\.venv\\Scripts\\python.exe bucle.py [--variants 10] [--segons 240] [--paralel 10]
(the venv lives in the main checkout: C:\\Users\\Usuario\\Desktop\\hackathon2026\\.venv\\Scripts\\python.exe)

Each round writes rondaNN/vXX/proposta.csv + relaxacions.csv (upload BOTH, question 5.2 "torns"), prints a table,
then asks the score of each variant (Enter = not submitted, q = quit). Results go to resultats.jsonl. The next round
starts from the best-scoring variant so far (ties: fewer declared relaxations, then the smaller local objectives).
Round 1 mixes the three S04511 modes (see genera.py); later rounds drop a mode whose best score is 3+ points behind.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import time
from pathlib import Path

import genera

HERE = Path(__file__).resolve().parent
LOG = HERE / 'resultats.jsonl'
MODES = ['tipus', 'nodecl', 'torn']


def resultats() -> list[dict]:
    if not LOG.exists():
        return []
    return [json.loads(l) for l in LOG.read_text(encoding='utf-8').splitlines() if l.strip()]


def clau(r: dict):
    o = r.get('obj') or {}
    cost = (o.get('idle') or 0) / 60 + (o.get('franja') or 0) + (o.get('moves') or 0) + 3 * (o.get('aula') or 0)
    return (r['score'], -r.get('declarades_web', 9), -cost)


def millor(rs):
    s = [r for r in rs if isinstance(r.get('score'), int)]
    return max(s, key=clau) if s else None


def modes_ronda(rs, n) -> list[str]:
    s = [r for r in rs if isinstance(r.get('score'), int)]
    if not s:
        return ['tipus', 'nodecl', 'torn', 'tipus', 'tipus', 'torn', 'tipus', 'tipus', 'tipus', 'tipus'][:n] or ['tipus']
    top = max(r['score'] for r in s)
    best = {}
    for r in s:
        best[r['mode']] = max(best.get(r['mode'], -1), r['score'])
    vius = [m for m in MODES if m in best and best[m] >= top - 2]
    lead = max(vius, key=lambda m: best[m])
    others = [m for m in vius if m != lead]
    plan = [lead] * n
    for k, m in enumerate(others[:max(0, n // 5)]):     # keep a little exploration of close modes
        plan[-1 - k] = m
    return plan


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--variants', type=int, default=10)
    ap.add_argument('--segons', default='240')
    ap.add_argument('--paralel', type=int, default=10)
    a = ap.parse_args()
    while True:
        rs = resultats()
        r = 1 + max([int(p.name[5:]) for p in HERE.glob('ronda[0-9][0-9]')] or [0])
        b = millor(rs)
        base_csv = Path(b['dir']) / 'pre.csv' if b else genera.DATA / 'lliuraments' / 'proposta-torns.csv'
        modes = modes_ronda(rs, a.variants)
        print(f'\n=== Round {r}: base {base_csv} ({"score " + str(b["score"]) if b else "deliverable"}), '
              f'modes {",".join(modes)}')
        print(f'Generating {a.variants} variants, {a.segons} s of search each (about {int(a.segons) // 60 + 2} min)...')
        t0 = time.time()
        out = HERE / f'ronda{r:02d}'
        vs = genera.genera(str(base_csv), out, a.variants, a.segons, a.paralel, r * 1000 + random.randrange(1000), modes)
        print(f'Done in {int(time.time() - t0)} s. Upload each folder\'s proposta.csv + relaxacions.csv (5.2 torns):\n')
        print(f'{"var":4} {"mode":7} {"decl":4} {"valid":5} {"idle":>6} {"moves":>5} {"franja":>6} {"aula":>4}  S04511')
        for v in vs:
            o = v['obj']
            print(f'{Path(v["dir"]).name:4} {v["mode"]:7} {v["declarades_web"]:4} {"yes" if v["valida_local"] else "NO":5} '
                  f'{o["idle"]:>6} {o["moves"]:>5} {o["franja"]:>6} {o["aula"]:>4}  {v["S04511"]}')
        print(f'\nFolders: {out}')
        try:
            os.startfile(out)
        except OSError:
            pass
        quit_ = False
        for v in vs:
            s = input(f'Score for {Path(v["dir"]).name} [{v["mode"]}] (Enter = skip, q = quit): ').strip().lower()
            if s == 'q':
                quit_ = True
                break
            if s.isdigit():
                v['score'] = int(s)
                v['round'] = r
                with open(LOG, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(v, ensure_ascii=False) + '\n')
        b = millor(resultats())
        if b:
            print(f'Best so far: {b["dir"]}  score {b["score"]}  mode {b["mode"]}  declared {b["declarades_web"]}')
        if quit_ or input('Next round? (Enter = yes, q = quit): ').strip().lower() == 'q':
            break


if __name__ == '__main__':
    main()
