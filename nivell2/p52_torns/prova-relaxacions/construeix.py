"""Experiment (NOT a deliverable): today's times as a 5.2 proposal, with every shift violation declared as a relaxation.

    python nivell2/p52_torns/prova-relaxacions/construeix.py

Takes the 5.1 deliverable (today's day and time for every session, rooms already fixed), runs the verifier in 5.2 mode,
and writes relaxacions-test.csv = the real relaxations + one row per rule with every counted violation
(R1-TORN 2,006, R2-FINESTRA 13), with a justification that says plainly it is a test and not an impossibility.
"""
import csv
import collections
import subprocess
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
ROOT = AQUI.parents[2]
PY = sys.executable
prop = AQUI / 'proposta-test.csv'
prop.write_bytes((ROOT / 'lliuraments' / 'proposta-aules.csv').read_bytes())
viol = AQUI / '_violacions.csv'
subprocess.run([PY, '-m', 'horaris', 'check', str(prop), '--semestre', '2', '--relaxacions',
                str(ROOT / 'lliuraments' / 'relaxacions.csv'), '--violacions', str(viol)],
               cwd=ROOT / 'repte-horaris-escola', stdin=subprocess.DEVNULL, capture_output=True)
per = collections.defaultdict(set)
for r in csv.DictReader(open(viol, encoding='utf-8')):
    if r['compta'] == '1':
        per[r['regla']].update(r['sessions'].split('|'))
viol.unlink()
rel = list(csv.reader(open(ROOT / 'lliuraments' / 'relaxacions.csv', encoding='utf-8')))
for regla, sids in sorted(per.items()):
    rel.append([regla, '|'.join(sorted(sids)),
                "Prova: horari d'avui sense passar aquestes sessions al seu torn. No és una impossibilitat: es mantenen a "
                "la seva franja d'avui per no canviar cap horari."])
with open(AQUI / 'relaxacions-test.csv', 'w', encoding='utf-8', newline='') as f:
    csv.writer(f).writerows(rel)
print({k: len(v) for k, v in per.items()})
