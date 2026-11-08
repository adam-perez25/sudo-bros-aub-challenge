"""Batch of local-search variants. usage: lot.py BASE_CSV RELAX_CSV PREFIX N SECONDS PARALLEL SEED0
Writes scratchpad/<PREFIX><i>/p.csv + r.csv + params.txt + check.txt; prints one line per variant (valid ones only)."""
import os
import random
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(r'C:\Users\Usuario\Desktop\hackathon2026')
PY = str(ROOT / '.venv' / 'Scripts' / 'python.exe')
S = Path(__file__).resolve().parent
base, relax, pref, n, secs, par, seed0 = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]), sys.argv[5], int(sys.argv[6]), int(sys.argv[7])
rnd = random.Random(seed0)


MODE = sys.argv[8] if len(sys.argv) > 8 else 'ampli'


def params(i):
    if MODE == 'franja':   # around the 74 recipe (B08/B12/B14): heavy franja weight, many slot moves
        return {
            '--llavor': str(seed0 * 100 + i),
            '--prob-intercanvi': os.environ.get('LOT_SWAP', '0'),
            '--temperatura': str(rnd.choice([2, 5, 10])),
            '--prob-temps': str(rnd.choice([0.7, 0.8, 0.9])),
            '--pes-mortes': str(rnd.choice([0.3, 1, 2, 4])),
            '--pes-desplac': str(rnd.choice([10, 30, 80, 200])),
            '--pes-passadis': str(rnd.choice([10, 30, 80])),
            '--pes-extra': str(rnd.choice([100, 300, 800])),
            '--pes-franja': str(rnd.choice([40, 60, 100, 200])),
            '--pes-aula': str(rnd.choice([60, 150, 300])),
            '--pes-edifici': '5000',
        }
    if MODE == 'aules':   # rooms only (almost no slot moves): cut room moves / corridor / extra / today-room changes
        return {
            '--llavor': str(seed0 * 100 + i),
            '--temperatura': str(rnd.choice([0, 2, 5])),
            '--prob-temps': str(rnd.choice([0.0, 0.05])),
            '--prob-intercanvi': str(rnd.choice([0.2, 0.4])),
            '--pes-mortes': '1',
            '--pes-desplac': str(rnd.choice([50, 100, 200])),
            '--pes-passadis': str(rnd.choice([50, 100, 200])),
            '--pes-extra': str(rnd.choice([300, 1000, 3000])),
            '--pes-franja': '500',
            '--pes-aula': str(rnd.choice([20, 60, 150])),
            '--pes-edifici': '5000',
        }
    if MODE == 'decl':   # all-declared experiment: franja near 0 is the big term; trade a little franja for idle/rooms
        return {
            '--llavor': str(seed0 * 100 + i),
            '--temperatura': str(rnd.choice([0, 2, 5])),
            '--prob-temps': str(rnd.choice([0.5, 0.8])),
            '--prob-intercanvi': str(rnd.choice([0, 0.2])),
            '--pes-mortes': str(rnd.choice([1, 2, 4])),
            '--pes-desplac': str(rnd.choice([10, 30, 80])),
            '--pes-passadis': str(rnd.choice([10, 30, 80])),
            '--pes-extra': str(rnd.choice([100, 300])),
            '--pes-franja': str(rnd.choice([10, 30, 60, 120])),
            '--pes-aula': str(rnd.choice([60, 150, 300])),
            '--pes-edifici': '5000',
        }
    if MODE == 'franjamax':   # idle is at its floor: pull time changes back toward the 2006 minimum
        return {
            '--llavor': str(seed0 * 100 + i),
            '--temperatura': str(rnd.choice([0, 0, 1])),
            '--prob-temps': str(rnd.choice([0.8, 0.95])),
            '--pes-mortes': str(rnd.choice([1, 2, 4, 8])),
            '--pes-desplac': str(rnd.choice([10, 30, 80])),
            '--pes-passadis': str(rnd.choice([10, 30, 80])),
            '--pes-extra': str(rnd.choice([300, 800])),
            '--pes-franja': str(rnd.choice([400, 800, 1500, 3000])),
            '--pes-aula': str(rnd.choice([150, 300])),
            '--pes-edifici': '5000',
        }
    if MODE == 'r6':   # keep idle/franja, push extra theory rooms and today-room changes down
        return {
            '--llavor': str(seed0 * 100 + i),
            '--temperatura': str(rnd.choice([0, 1, 2])),
            '--prob-temps': str(rnd.choice([0.3, 0.5])),
            '--pes-mortes': str(rnd.choice([2, 4])),
            '--pes-desplac': str(rnd.choice([30, 80])),
            '--pes-passadis': str(rnd.choice([30, 80])),
            '--pes-extra': str(rnd.choice([2000, 4000])),
            '--pes-franja': str(rnd.choice([200, 400])),
            '--pes-aula': str(rnd.choice([400, 800])),
            '--pes-edifici': '5000',
        }
    if MODE == 'polir':   # no worsening, heavy franja/extra weights: pull franja back toward 2006 keeping the gains
        return {
            '--llavor': str(seed0 * 100 + i),
            '--temperatura': str(rnd.choice([0, 0, 1])),
            '--prob-temps': str(rnd.choice([0.6, 0.8])),
            '--pes-mortes': str(rnd.choice([1, 2, 4])),
            '--pes-desplac': str(rnd.choice([30, 80])),
            '--pes-passadis': str(rnd.choice([30, 80])),
            '--pes-extra': str(rnd.choice([300, 800])),
            '--pes-franja': str(rnd.choice([200, 400])),
            '--pes-aula': str(rnd.choice([150, 300])),
            '--pes-edifici': '5000',
        }
    return {
        '--llavor': str(seed0 * 100 + i),
        '--temperatura': str(rnd.choice([0, 2, 5, 10, 20])),
        '--prob-temps': str(rnd.choice([0.2, 0.5, 0.8])),
        '--pes-mortes': str(rnd.choice([0.3, 1, 2, 4])),
        '--pes-desplac': str(rnd.choice([10, 30, 80, 200])),
        '--pes-passadis': str(rnd.choice([10, 30, 80, 200])),
        '--pes-extra': str(rnd.choice([100, 300, 800])),
        '--pes-franja': str(rnd.choice([0.5, 2, 10, 40])),
        '--pes-aula': str(rnd.choice([20, 60, 150, 400])),
        '--pes-edifici': '5000',
    }


def run(i):
    d = S / f'{pref}{i:02d}'
    d.mkdir(exist_ok=True)
    p = params(i)
    args = [PY, str(ROOT / 'nivell2' / 'p52_torns' / 'cerca_local.py'), base, '--sortida', str(d / 'p.csv'), '--segons', secs]
    for k, v in p.items():
        args += [k, v]
    import os
    args += os.environ.get('LOT_EXTRA', '').split()
    (d / 'params.txt').write_text(' '.join(f'{k} {v}' for k, v in p.items()) + f' base={base}\n', encoding='utf-8')
    subprocess.run(args, stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding='utf-8', errors='replace')
    (d / 'r.csv').write_bytes(Path(relax).read_bytes())
    chk = subprocess.run([PY, '-m', 'horaris', 'check', str(d / 'p.csv'), '--semestre', '2', '--relaxacions', str(d / 'r.csv')],
                         cwd=str(ROOT / 'repte-horaris-escola'), stdin=subprocess.DEVNULL, capture_output=True, text=True,
                         encoding='utf-8', errors='replace')
    (d / 'check.txt').write_text(chk.stdout, encoding='utf-8')
    out = chk.stdout
    ok = 'Veredicte: VALIDA' in out
    vals = {}
    for line in out.splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1].isdigit():
            vals[parts[0]] = int(parts[1])
    short = ' '.join(f"{lab}={vals.get(k)}" for lab, k in
                     (('idle', 'hores_mortes_min'), ('moves', 'desplacaments_aula'), ('bldg', 'desplacaments_edifici'),
                      ('franja', 'canvis_franja'), ('aula', 'canvis_aula'), ('extra', 'r6_aules_te_extra_per_grup'),
                      ('corr', 'r6_canvis_te_paul_fora_passadis')))
    return f"{d.name} {'VALID' if ok else 'INVALID'} {short}"


with ThreadPoolExecutor(par) as ex:
    for line in ex.map(run, range(1, n + 1)):
        print(line, flush=True)
