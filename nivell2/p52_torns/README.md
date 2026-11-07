# 5.2 · New shifts: 1st/2nd year morning, 3rd/4th afternoon

Owner: Adam (+ Claude) · Weight 25 % · **Done: `VALIDA AMB RELAXACIONS DECLARADES`, 0 counted violations**

Jury-facing explanation (Catalan): [`INFORME.md`](INFORME.md) · one-page board summary: [`RESUM-JUNTA.md`](RESUM-JUNTA.md).

## Regenerate everything (from the repo root, `.venv` active)

```bash
python nivell2/p52_torns/torns.py --sortida lliuraments/proposta-torns.csv --relaxacions lliuraments/relaxacions.csv --informe nivell2/p52_torns/informe-torns.json
python nivell2/p52_torns/resum_junta.py
python nivell2/p52_torns/graella.py
```

The scheduler is deterministic and takes a couple of seconds. Then 5.3 and 5.4 are rebuilt on top of it (commands in
their READMEs), and the jury check is:

```bash
cd repte-horaris-escola
python -m horaris check ../lliuraments/proposta-torns.csv --semestre 2 --relaxacions ../lliuraments/relaxacions.csv --json ../lliuraments/informe-torns.json --violacions ../lliuraments/violacions-torns.csv
```

## How `torns.py` works

1. Keep every session already in its shift, and every valid room of today.
2. Rooms first for the sessions that don't change time (least flexible): one room per weekly activity when possible.
3. Move each wrong-shift activity **as a block** (same weekday and hour every week, shared sessions together) to the
   free slot of its shift with the fewest idle gaps for its group, avoiding the peak slots and, if possible, keeping
   the weekday.
4. Local repair for leftovers (free a slot or a room by moving non-fixed classes; undo if anything fails).
5. Room-quality pass: activities whose room we chose try the room of their group's neighbouring classes.
6. Official verifier + relaxations file with the justification of each exception.

It reuses the timetable engine of 5.3 (`nivell2/p53_imprevist/imprevist.py`) with extra per-person indexes.

## Results

| | Today | 5.2 |
|---|---|---|
| Counted violations | R1-TORN 2,008 · R2 13 · R3 97 · R5 4,541 | **0** |
| Idle gap minutes | 72,930 | **62,640** (−14 %) |
| Sessions moved (slot / room) | — | 2,006 / 291 |

Declared (460, all R1-TORN): 458 fixed GEI 1st/2nd-year sessions that are in the afternoon today (unavoidable: they
can't move, and giving them the room they lack makes the verifier stop calling them inherited), plus **2 sessions
proven impossible** by counting (31/5 and 9/4, weeks with a single possible day). Details in `INFORME.md` and in the
justification column of `lliuraments/relaxacions.csv`.

## Ideas to improve further (if there is time)

- Fewer room changes between consecutive classes (2,977) and TE↔PAUL changes outside the corridor (1,397): a smarter
  room assignment (e.g. CP-SAT per day) instead of the greedy + neighbour pass.
- Fewer idle gaps: let blocks that already moved be re-optimised once everything is placed.
