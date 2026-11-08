# 5.2 · New shifts: 1st/2nd year morning, 3rd/4th afternoon

Owner: Adam (+ Claude) · Weight 25 % · **Done: `VALIDA AMB RELAXACIONS DECLARADES`, 0 counted violations**

Jury-facing explanation (Catalan): [`INFORME.md`](INFORME.md) · one-page board summary: [`RESUM-JUNTA.md`](RESUM-JUNTA.md).

## Regenerate everything (from the repo root, `.venv` active)

```bash
python nivell2/p52_torns/torns.py --sortida lliuraments/proposta-torns.csv --relaxacions lliuraments/relaxacions.csv --informe nivell2/p52_torns/informe-torns.json
python nivell2/p52_torns/resum_junta.py
python nivell2/p52_torns/graella.py
```

Then apply the 5.3 incident rooms to it with `imprevist.py --anticipa-52` (see `nivell2/p53_imprevist/README.md`):
this is what the delivered `proposta-torns.csv` is.

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
6. Building pass (`acosta_edifici`): a group whose classes sit in a room outside the aulari (GED 4t in B3/0021)
   next to its labs in Q has all those sessions moved to one free ordinary room in Q (Q3/0011), so building moves
   go 17 -> 0. The web score weighs this heavily (70 -> 73); room and idle-gap tuning moved it by only 1-2 points.
7. Official verifier + relaxations file with the justification of each exception.

It reuses the timetable engine of 5.3 (`nivell2/p53_imprevist/imprevist.py`) with extra per-person indexes.

## Results

| | Today | 5.2 |
|---|---|---|
| Counted violations | R1-TORN 2,008 · R2 13 · R3 97 · R5 4,541 | **0** |
| Idle gap minutes | 72,930 | **56,790** (−22 %) |
| Sessions moved (slot / room) | — | 2,006 / 222 |
| Room changes between consecutive classes | 2,977 before the local search | **1,504** |
| TE↔PAUL changes outside the corridor | 1,397 before the local search | **339** |
| Extra theory rooms per group (R6) | 79 | **47** |

Declared (460, all R1-TORN): 458 fixed GEI 1st/2nd-year sessions that are in the afternoon today (unavoidable: they
can't move, and giving them the room they lack makes the verifier stop calling them inherited), plus **2 sessions
proven impossible** by counting (31/5 and 9/4, weeks with a single possible day). Details in `INFORME.md` and in the
justification column of `lliuraments/relaxacions.csv`.

## Room quality: the CP-SAT pass

After the greedy + local search, `aules_cpsat.py` (`reassigna_aules`) re-chooses, **date by date**, the room of every unit
we are allowed to change (today's valid rooms and fixed sessions with a room are never touched), with all times frozen.
Objective: the verifier's own indicators (room changes between consecutive classes of a group, +1 if TE↔PAUL changes
corridor, classes leaving today's room, a small penalty for theory outside the group's base room). Hard constraints:
type, capacity, closures, no overlap, reserve of 2 free ordinary rooms per slot, and theory may only use rooms its
(cohort, line) already uses, so the extra-room indicator cannot grow. The current room is the starting hint, so it never
makes a date worse. 2 rounds, ~1 minute in total; `--sense-cpsat` skips it. It is multithreaded, so indicators can vary
by a few units between runs (the committed CSV is the reference). 5.1 reuses it.

Effect: room changes 2,110 → 1,504, TE↔PAUL outside corridor 512 → 339, changes vs today 291 → 222, extra theory rooms
77 → 47.

## Tried and not kept

- Simulated annealing over the block re-placement (`replaca_blocs` accepting small worsenings, up to 300 iterations,
  T0 up to 600): idle minutes only 56,790 → 56,490 (−0.5 %), for +1 min runtime. Idle gaps are bounded by the sessions that
  can't move, so it was dropped.

## Local search on top (`cerca_local.py`, web 74; the 5.3 built on it, web 80)

`torns.py` is unchanged and still produces the 73 version. The delivered `proposta-torns.csv` now comes from a second,
separate step: `cerca_local.py` takes a valid 5.2 and improves it with simulated annealing over single units (change a
unit's room, or move it to another slot of its shift in the same ISO week), accepting only moves that pass the same
hard-rule checks as `torns.py` and lower a weighted mix of the verifier's indicators. With `--escenari
paquet/escenaris/contingencies` it never puts a class in a room the 5.3 incidents close, or in a room too small for the
group that grows, and keeps the cancelled session where it is: the result stays ready for 5.3 (1 slot + 10 rooms).

What the web score taught us: time changes do cost points (variants with 2,500-3,700 time changes stayed at 73);
the 74s keep time changes near the minimum (2,083 here vs 2,006) while cutting idle minutes (56,790 -> 49,995) and room
moves (1,505 -> 1,089).

Delivered run (not bit-for-bit reproducible: the search is time-limited and random, so the committed CSV is the reference):

```bash
python nivell2/p52_torns/torns.py --sortida /tmp/52.csv --relaxacions lliuraments/relaxacions.csv
python nivell2/p53_imprevist/imprevist.py /tmp/52.csv --sortida /tmp/x.csv --anticipa-52 /tmp/52a.csv
python nivell2/p52_torns/cerca_local.py /tmp/52a.csv --sortida lliuraments/proposta-torns.csv --segons 300 \
    --escenari repte-horaris-escola/paquet/escenaris/contingencies --llavor 5007 --temperatura 1 --prob-temps 0.8 \
    --pes-mortes 2 --pes-desplac 30 --pes-passadis 80 --pes-extra 800 --pes-franja 200 --pes-aula 300
```

(the delivered file went through two earlier local-search rounds from the 74 versions before this one; see the commit log)
