# 5.2 rounds with manual upload

Run from this folder (the venv is the main checkout's):

    C:\Users\Usuario\Desktop\hackathon2026\.venv\Scripts\python.exe bucle.py

Each round generates ~10 variants (local search from the best-scoring file so far, then the two ex-relaxation sessions
are placed, see `genera.py`), opens the round folder and prints a table. Upload `vXX/proposta.csv` + `vXX/relaxacions.csv`
for 5.2 (torns), then type each score in the terminal. `resultats.jsonl` keeps every score; the next round starts from the
best one. Options: `--variants 10 --segons 240 --paralel 10`.

Relaxations: S02839 is placed (inherited teacher overlap with TE/320), so it is no longer declared. S04511 has three
modes: `torn` (declare R1-TORN), `tipus` (afternoon in an ordinary room, declare R3-TIPUS) and `nodecl` (same room, nothing
declared: a probe of the web verifier; locally it is NO VALIDA). Round 1 mixes them; later rounds keep the best.

`rondaNN/` and `resultats.jsonl` hold challenge-derived data: git-ignored, never upload them anywhere except the
official evaluator.
