"""Local server for the web loop. usage: servidor.py   (port 8765, keep running while the browser script loops)
GET  /<file>        serves files from this folder (CORS open)
GET  /next          generates a new round of variants from the best base so far and returns the manifest
POST /log           appends one result line to resultats.jsonl
Config by env: VARIANTS (10), SECONDS (240), PARALLEL (10)"""
import http.server, json, os, subprocess, threading
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PY = str(ROOT / '.venv' / 'Scripts' / 'python.exe')
LOG = HERE / 'resultats.jsonl'
N, SECS, PAR = os.environ.get('VARIANTS', '10'), os.environ.get('SECONDS', '240'), os.environ.get('PARALLEL', '10')
os.chdir(HERE)
lock = threading.Lock()
state = {'round': 0}


def results():
    return [json.loads(l) for l in LOG.read_text(encoding='utf-8').splitlines() if l.strip()] if LOG.exists() else []


def best_base():
    scored = [r for r in results() if isinstance(r.get('score'), int)]
    if not scored:
        return str(ROOT / 'lliuraments' / 'proposta-torns.csv')
    b = max(scored, key=lambda r: (r['score'], -((r.get('obj') or {}).get('idle') or 10**9)))
    print('base for next round:', b['dir'], b['score'], flush=True)
    return str(HERE / b['dir'] / 'p.csv')


class H(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Private-Network', 'true')
        self.send_header('Access-Control-Allow-Headers', '*')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()

    def do_GET(self):
        if self.path.startswith('/next'):
            with lock:
                state['round'] += 1
                r = state['round']
                out = HERE / f'ronda{r:02d}'
                p = subprocess.run([PY, str(HERE / 'genera.py'), best_base(), str(out), N, SECS, PAR, str(r)],
                                   stdin=subprocess.DEVNULL, capture_output=True, text=True)
                items = json.loads(p.stdout.strip().splitlines()[-1]) if p.stdout.strip() else []
                for it in items:
                    it['dir'] = f'ronda{r:02d}/' + it['dir']
            body = json.dumps({'round': r, 'variants': items}).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(body)
        else:
            super().do_GET()

    def do_POST(self):
        data = self.rfile.read(int(self.headers.get('Content-Length', 0))).decode('utf-8')
        with open(LOG, 'a', encoding='utf-8') as f:
            f.write(data.replace('\n', ' ') + '\n')
        self.send_response(204)
        self.end_headers()

    def log_message(self, *a):
        pass


print('listening on 127.0.0.1:8765', flush=True)
http.server.ThreadingHTTPServer(('127.0.0.1', 8765), H).serve_forever()
