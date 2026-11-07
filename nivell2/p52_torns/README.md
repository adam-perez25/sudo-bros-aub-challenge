# 5.2 · New shifts: 1st/2nd year morning, 3rd/4th afternoon

Owner: _?_ · Branch: `nivell2/p52-torns` · Weight 25 % · Starts from 5.1

**Goal:** move day, hour and room of the movable sessions so every rule passes (`--semestre 2`), with the fewest
idle gaps and changes. Starting point: R1-TORN 2,008, R2-FINESTRA 13, R3-AFORAMENT 43, R3-TIPUS 54,
R5-SENSE-AULA 4,541. Rules we really can't meet go to `lliuraments/relaxacions.csv` with a justification
(candidate: 248 double-degree sessions taught with a morning group).

**Also deliver:** a one-page summary for the Junta Permanent (in Catalan): peak simultaneous classes morning and
afternoon vs available rooms, missing/spare rooms by size, sessions moved by degree and year, the exceptions to
rule 1 we ask for and why.

**Hints from level 1** (`nivell1/TROBALLES.md`): the morning fits in total (~60 % of room-hours) but Tuesday and
10:30-13:30 are already at 15 of 19: put the classes that move to the morning on quiet days and hours. Room size
is not a bottleneck. Day can change but not the ISO week; avoid holidays (`calendari.csv`).

**Check:** `python -m horaris check ../lliuraments/proposta-torns.csv --semestre 2`.

Run the check from inside `repte-horaris-escola/` with the `.venv` active.
