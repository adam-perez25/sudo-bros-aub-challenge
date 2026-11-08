# Web loop for 5.2 (automated submissions)

1. Stop any other server on port 8765, then run from this folder:
   `..\..\..\.venv\Scripts\python.exe servidor.py`
2. Open https://uabthehack.cat/participants/xaman signed in, press F12, Console, paste `consola.js`, Enter.
3. It runs 6 rounds. Each round the server generates ~10 valid variants from the best-scoring file so far (the deliverable
   in round 1), the browser submits each one, and every score is appended to `resultats.jsonl` (also printed in the console).

Env vars for the server: VARIANTS (10), SECONDS (240, search time per variant), PARALLEL (10).
Chrome may ask to allow access to local network devices: allow it. The `rondaNN/` folders hold challenge-derived data:
they are git-ignored and must never be uploaded anywhere except the official evaluator.
