# 5.1 · Assign rooms without moving any time

Owner: _?_ · Branch: `nivell2/p51-aules` · Weight 5 % (but 5.2-5.4 reuse this engine)

**Goal:** give a room to every semester-2 session that needs one (4,541 today), keeping today's day and hour:
right type, enough seats, no two classes in a room at once, 2 ordinary rooms free in every hour slot. Also fix the
43 over-capacity sessions and the 54 PAUL sessions in Q6 labs.

**Scored on quality:** one stable home room per group, few room changes between consecutive classes, few changes
vs today's rooms. A valid assignment is known to exist.

**Suggested approach:** per `activitat_id` (same room all semester); keep today's room when valid; biggest classes
first into the smallest valid free room; then improve (theory group and its PAULs in the same corridor). OR-Tools
CP-SAT is in `requirements.txt` if needed.

**Check:** `python -m horaris check ../lliuraments/proposta-aules.csv --semestre 2 --nomes-aules` (from
`repte-horaris-escola/`). Final file: `lliuraments/proposta-aules.csv`.
