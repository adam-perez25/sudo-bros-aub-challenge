# 5.4 · A new 40-student degree: does it fit?

Owner: Claude (with Adam) · Branch: `nivell2/p54-grau-nou` · Weight 10 % · **Done: final files in `lliuraments/` (see INFORME.md)**

The fictional degree (`paquet/escenaris/grau-nou-40/`) has 235 semester-2 sessions, all in the morning, no room:
54 theory classes (TE/91, 40 students) and 181 PAUL (14-20 students). Its teachers (N…) and cohort (`GNOU:1r`) are
new, so it only competes with the rest for **rooms** (and the 2-free-rooms reserve).

## The tool: `grau_nou.py`

Places the new degree on top of **any** proposal without touching a single existing session. From the repo root:

```bash
python nivell2/p54_grau_nou/grau_nou.py nivell2/p54_grau_nou/base-52.csv --sortida lliuraments/proposta-grau-nou.csv --informe nivell2/p54_grau_nou/informe-encaix.json
```

(add `--relaxacions lliuraments/relaxacions.csv` if 5.2 has relaxations, so the self-check uses them)

1. Each weekly activity keeps the day and hour it comes with and gets **one room for the whole semester** if
   possible: the smallest that fits; PAULs next to their theory room (same corridor).
2. If there is no free room at its hour, the session moves to another **morning** slot of the same ISO week with
   students, teacher and a room free (calendar and reserve respected).
3. If even that fails it says so (`NO HI CAP`: which session, which date and hour).
4. **Room quality (CP-SAT, from 5.2):** only the new degree's sessions get their rooms re-chosen date by date with the
   verifier's indicators (room and corridor changes between consecutive classes, theory rooms per group). Room moves
   added by the degree drop from 85 to 9 and corridor changes from 13 to 0 (`GRAU_NOU_CPSAT=0` skips it). The web
   score stays at 73, like 5.2: room quality barely moves it.
5. **Self-check with the official verifier:** errors of the new sessions, and any new error in the rest of the
   proposal. It also reports the **margin**: free ordinary rooms in the tightest morning slot after placing the
   degree. Exit code 0 only if everything fits and nothing broke.

It reuses the timetable engine of 5.3 (`nivell2/p53_imprevist/imprevist.py`), so this branch is stacked on 5.3.

## Why it fits, whatever 5.2 looks like

- The new degree never needs **more than 2 rooms at the same time**, and **at most 1 theory class** (there is one
  theory group).
- Its theory (40) needs one of the 20 ordinary rooms with 40+ seats. Its PAULs (≤ 20) can also use **14
  non-ordinary spaces** (6 seminars, 6 integrated labs, the 2 computer rooms), which don't count for the reserve rule.
- So it fits on any 5.2 where, in each week, its 4 weekly theory slots (Tue 10:30, Tue 12:30, Thu 12:30,
  Fri 12:30, 2 h each) — or any other morning slot of that week — have **3 ordinary rooms free** (1 for the theory,
  2 reserve). Level 1 found the new model needs ~12 of the 19 usable rooms on average in the morning, so this holds
  with room to spare; the tool checks it for real on the final 5.2.

## Final delivery (when `lliuraments/proposta-torns.csv` exists)

1. Run the command above.
2. Check exactly as the jury will (from `repte-horaris-escola/`):
   ```bash
   python -m horaris check ../lliuraments/proposta-grau-nou.csv --semestre 2 --escenari paquet/escenaris/grau-nou-40 --relaxacions ../lliuraments/relaxacions.csv --json ../lliuraments/informe-grau-nou.json --violacions ../lliuraments/violacions-grau-nou.csv
   ```
   (`--relaxacions` only if 5.2 has one: the new degree itself needs none)
3. Put the final numbers in [`INFORME.md`](INFORME.md) (Catalan, for the jury).

## Tests done (before 5.2 exists)

| Input | Placed | Moved | New-session errors | New errors elsewhere | Free ordinary rooms, worst morning slot |
|---|---|---|---|---|---|
| `proposta_partida.csv` (today; the statement's fallback) | 235/235 | 0 | 0 | 0 | 12 (rooms mostly unassigned) |
| dense stand-in (every room filled, today's hours) | 235/235 | 0 | 0 | 0 | 4 before → 3 after (rule needs 2) |

Official verifier on both outputs (`--escenari grau-nou-40`): R5-FALTA 235 → 0, R5-SENSE-AULA unchanged, R8 OK,
every other rule identical to the input.

**Stress test** (dense stand-in, k copies of the degree with separate cohorts and teachers): up to **10 copies**
(2,350 sessions) are placed with 0 errors (343 moved within their week); at 11 copies the first session doesn't fit.
This is a greedy method, so 10 is a lower bound on what fits, not a proven maximum.

## Base timetable: `base-52.csv`

5.4 is built on `base-52.csv`, the 5.2 timetable **before** it was adapted to the 5.3 incidents
(`imprevist.py --anticipa-52`). That adaptation lifts 5.3 from 73 to 79 on the web, but 5.4 built on it scores 72
instead of 73, so 5.4 keeps the earlier 5.2 (same shifts and times; only some room choices differ). Both are valid.
