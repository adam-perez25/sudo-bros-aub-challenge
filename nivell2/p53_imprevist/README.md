# 5.3 · Incidents: what do we propose?

Owner: Claude (with Adam) · Branch: `nivell2/p53-imprevist` · Weight 10 % · **Tool ready; final run waits for 5.2**

**Four things at once** (`paquet/escenaris/contingencies/`): Q3/0013 closed 15-19 March 2027 · Transmissió de
Calor i Termotècnia TE/21 (GEQ 2n) grows to 130 students and no longer fits Q4/0011 · Q1/1003 broken on 10 March ·
session S11527 (8 March) cancelled and recovered by 19 March (extra column `data`). The goal is to fix all four
changing **as little as possible** vs our 5.2 proposal.

## The tool: `imprevist.py`

It repairs **any** proposal, so it was built and tested before 5.2 existed. From the repo root, with `.venv` active:

```bash
python nivell2/p53_imprevist/imprevist.py lliuraments/proposta-torns.csv --sortida lliuraments/proposta-imprevist.csv --relaxacions lliuraments/relaxacions-imprevist.csv --informe nivell2/p53_imprevist/informe-reparacio.json
```

What it does, in this order:

1. **Closed rooms:** every class in Q3/0013 (15-19/3) or Q1/1003 (10/3) keeps its day and time and only changes
   room: a free room of the right type, big enough, preferably in the same corridor (spine + floor), respecting the
   2-free-rooms reserve.
2. **Group that grows:** all TE/21 sessions that no longer fit move to **one** room with 130+ seats that is free at
   all their times (a stable home room). Only if none exists does it go session by session, and any session left
   without a room is declared as an R3-AFORAMENT relaxation (split group).
3. **Cancelled session:** S11527 goes to the first valid slot after 8/3 and up to 19/3: students, teachers and a
   130+ room free, no holiday/stoppage (18/3 has no teaching, 17/3 13-15h stoppage), right shift and window.
   It prefers the original start time and the group's room. The row gets the `data` column.
4. **Self-check with the official verifier:** incident errors before/after and **any new error the repair
   introduced**. Exit code 0 only if all incidents are fixed and nothing new broke.

### Unavoidable relaxations (written to `relaxacions-imprevist.csv`)

8 fixed GEI sessions (R1) and 2 fixed master's labs (R7, PLAB) are in Q3/0013/Q1/1003 on those dates. A closed
room can't be relaxed (R3-TANCADA is not relaxable), so they must change room, which the verifier counts as R1-FIXADA
/ R7-PLAB. The tool keeps their day and time, moves only the room, and declares them with a justification. Fixed
sessions never move in 5.2 either, so **the final run will need these same 10 declarations** (every team will).

## Final delivery (when `lliuraments/proposta-torns.csv` exists)

1. Run the command above.
2. Check exactly as the jury will (from `repte-horaris-escola/`):
   ```bash
   python -m horaris check ../lliuraments/proposta-imprevist.csv --semestre 2 --escenari paquet/escenaris/contingencies --referencia ../lliuraments/proposta-torns.csv --relaxacions ../lliuraments/relaxacions-imprevist.csv --json ../lliuraments/informe-imprevist.json --violacions ../lliuraments/violacions-imprevist.csv
   ```
3. Put the final numbers in [`INFORME.md`](INFORME.md) (Catalan, for the jury).

**If 5.2 already has relaxations** (`lliuraments/relaxacions.csv`), the 5.3 check also needs them: append the rows
of `relaxacions-imprevist.csv` to a copy of 5.2's file and pass that combined file to `--relaxacions`.

## Tests done (before 5.2 exists)

| Input | Incident errors | New errors | Changes vs input | Official verifier |
|---|---|---|---|---|
| `proposta_partida.csv` (today) | 42 → 0 | 0 | 1 slot, 41 rooms | R3-TANCADA 14→0, R5-RECUPERACIO 1→0, R1-FIXADA 8 + R7-PLAB 2 declared, every other rule unchanged |
| dense stand-in (every room filled, `VALIDA` with `--nomes-aules`) | 57 → 0 | 0 | 1 slot, 56 rooms | R3-TANCADA 25→0, R3-AFORAMENT 31→0, R5-RECUPERACIO 1→0, 10 declared |

In both cases the number of changes is the minimum possible: every changed room belongs to a session that was in
a closed room or no longer fitted, plus the one recovered session.
