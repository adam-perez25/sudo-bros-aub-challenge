"""Generate N valid 5.2 local-search variants from a base CSV. usage: genera.py BASE OUTDIR N SECONDS PARALLEL SEED
Writes OUTDIR/vNN/{p.csv,r.csv,params.txt,check.txt}; prints a JSON list of the VALID variants (with objectives)."""
import json, random, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PY = str(ROOT / '.venv' / 'Scripts' / 'python.exe')
RELAX = ROOT / 'lliuraments' / 'relaxacions.csv'
ESC = ROOT / 'repte-horaris-escola' / 'paquet' / 'escenaris' / 'contingencies'
base, out, n, secs, par, seed = sys.argv[1], Path(sys.argv[2]), int(sys.argv[3]), sys.argv[4], int(sys.argv[5]), int(sys.argv[6])
base, out = str(Path(base).resolve()), out.resolve()
rnd = random.Random(seed)
C = rnd.choice
MODES = {
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
ORDER = ['franja', 'franjamax', 'polir', 'r6', 'franja', 'polir', 'franjamax', 'ampli', 'r6', 'franja']
KEYS = [('idle', 'hores_mortes_min'), ('moves', 'desplacaments_aula'), ('bldg', 'desplacaments_edifici'), ('franja', 'canvis_franja'),
        ('aula', 'canvis_aula'), ('extra', 'r6_aules_te_extra_per_grup'), ('corr', 'r6_canvis_te_paul_fora_passadis')]
plans = [(i, ORDER[(i - 1) % len(ORDER)]) for i in range(1, n + 1)]
params = {i: MODES[m]() for i, m in plans}


def run(item):
    i, mode = item
    d = out / f'v{i:02d}'
    d.mkdir(parents=True, exist_ok=True)
    p = params[i]
    args = [PY, str(ROOT / 'nivell2' / 'p52_torns' / 'cerca_local.py'), base, '--sortida', str(d / 'p.csv'), '--segons', secs,
            '--llavor', str(seed * 100 + i), '--pes-edifici', '5000', '--escenari', str(ESC)]
    for k, v in p.items():
        args += ['--' + k.replace('_', '-'), str(v)]
    (d / 'params.txt').write_text(mode + ' ' + ' '.join(f'{k}={v}' for k, v in p.items()), encoding='utf-8')
    subprocess.run(args, stdin=subprocess.DEVNULL, capture_output=True)
    (d / 'r.csv').write_bytes(RELAX.read_bytes())
    if not (d / 'p.csv').exists():
        return None
    chk = subprocess.run([PY, '-m', 'horaris', 'check', str(d / 'p.csv'), '--semestre', '2', '--relaxacions', str(d / 'r.csv')],
                         cwd=str(ROOT / 'repte-horaris-escola'), stdin=subprocess.DEVNULL, capture_output=True, text=True,
                         encoding='utf-8', errors='replace')
    (d / 'check.txt').write_text(chk.stdout, encoding='utf-8')
    if 'Veredicte: VALIDA' not in chk.stdout:   # also matches "VALIDA AMB RELAXACIONS DECLARADES"
        return None
    vals = {l.split()[0]: int(l.split()[1]) for l in chk.stdout.splitlines() if len(l.split()) == 2 and l.split()[1].isdigit()}
    return {'dir': d.name, 'mode': mode, 'obj': {lab: vals.get(k) for lab, k in KEYS}}


with ThreadPoolExecutor(par) as ex:
    res = [r for r in ex.map(run, plans) if r]
print(json.dumps(res))
