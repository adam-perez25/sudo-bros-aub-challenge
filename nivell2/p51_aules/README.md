# 5.1 · Assign rooms without moving any time

Weight 5 % · **Done: `VALIDA` with `--nomes-aules`, no relaxations** · Jury-facing explanation (Catalan):
[`INFORME.md`](INFORME.md)

## Regenerate (from the repo root, `.venv` active)

```bash
python nivell2/p51_aules/aules.py --sortida lliuraments/proposta-aules.csv --informe nivell2/p51_aules/informe-aules.json
```

Jury check (from `repte-horaris-escola/`):

```bash
python -m horaris check ../lliuraments/proposta-aules.csv --semestre 2 --nomes-aules --json ../lliuraments/informe-aules.json --violacions ../lliuraments/violacions-aules.csv
```

## How `aules.py` works

Times are frozen; only the `aula` column changes. It reuses the 5.2 engine (`nivell2/p52_torns/torns.py`):

1. Keep every valid room of today (fewer changes).
2. Sessions that need a room (empty or invalid, and changeable: not PLAB, not double degree, not fixed with a room):
   theory first, biggest first; each weekly activity tries **one room for the whole semester**, preferring today's
   room, then the group's **home room** (theory rooms already used by the same cohort + line), then the same corridor,
   then the smallest room that fits. Type, capacity, no overlaps and the 2-free-rooms reserve always respected.
3. Room-quality pass: each activity with a new room tries the room of its group's neighbouring classes, then a local search
   (`optimitza_aules` from 5.2) scores every candidate room with the same logic as the verifier's two room indicators and
   keeps only strict improvements (first per activity, then per practical session).
4. **CP-SAT pass** (`nivell2/p52_torns/aules_cpsat.py`, shared with 5.2): for each date, rooms of the units we are allowed to
   change are re-chosen at once to minimise the verifier's room indicators (consecutive-class room changes, TE↔PAUL
   outside the corridor, classes leaving today's room), with type, capacity, closures, overlaps and the 2-free-rooms
   reserve as hard constraints and theory restricted to rooms its group already uses (extra-room indicator can't grow).
5. Official verifier in `--nomes-aules` mode. The CP-SAT step is multithreaded: indicators can vary by a few units between
   runs (the committed CSV is the reference).

## Results vs the simple greedy the statement suggests

| Objective (lower is better) | Simple greedy | 5.1 |
|---|---|---|
| Extra theory rooms per group (R6) | 130 | **48** |
| TE↔PAUL changes outside the corridor (R6) | 1,675 | **343** |
| Room changes between consecutive classes | 3,636 | **1,612** |
| Room changes vs today | 132 | **97** |
