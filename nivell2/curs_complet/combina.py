"""Full-course deliverable: semester-1 rows from one proposal, semester-2 rows from another, relaxations concatenated.

usage: combina.py S1_PROPOSTA S1_RELAX S2_PROPOSTA S2_RELAX SORTIDA_PROPOSTA SORTIDA_RELAX [--paquet DIR]
The semester of each session is taken from its date (statement 8.3), as the verifier does. Rows keep the order of
proposta_partida.csv. Check the result with (from repte-horaris-escola/):
    python -m horaris check ../lliuraments/proposta-completa.csv --relaxacions ../lliuraments/relaxacions-completa.csv
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def files(p: Path) -> tuple[list[str], dict[str, list[str]]]:
    with open(p, encoding='utf-8-sig', newline='') as f:
        rows = list(csv.reader(f))
    return rows[0], {r[0].strip(): r for r in rows[1:] if r}


def main() -> None:
    ap = argparse.ArgumentParser()
    for k in ('s1', 'r1', 's2', 'r2', 'sortida', 'sortida_rel'):
        ap.add_argument(k, type=Path)
    ap.add_argument('--paquet', type=Path, default=ROOT / 'repte-horaris-escola' / 'paquet')
    a = ap.parse_args()
    with open(a.paquet / 'sessions.csv', encoding='utf-8-sig', newline='') as f:
        sem = {r['id_sessio']: 1 if dt.date.fromisoformat(r['data']).month >= 9 or dt.date.fromisoformat(r['data']).month == 1
               else 2 for r in csv.DictReader(f)}
    _, ordre = files(a.paquet / 'proposta_partida.csv')
    cap1, p1 = files(a.s1)
    cap2, p2 = files(a.s2)
    n = {1: 0, 2: 0}
    with open(a.sortida, 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(['id_sessio', 'dia', 'h_ini', 'aula'])
        for sid in ordre:
            s = sem[sid]
            row = (p1 if s == 1 else p2)[sid]
            w.writerow(row[:4])
            n[s] += 1
    with open(a.sortida_rel, 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(['restriccio', 'sessions', 'justificacio'])
        k = 0
        for p in (a.r1, a.r2):
            with open(p, encoding='utf-8-sig', newline='') as g:
                for r in list(csv.reader(g))[1:]:
                    if r:
                        w.writerow(r)
                        k += 1
    print(f'{a.sortida}: {n[1]} rows of semester 1 + {n[2]} of semester 2; {a.sortida_rel}: {k} relaxation rows')


if __name__ == '__main__':
    main()
