# Experiment: declaring the shift rule instead of meeting it (NOT a deliverable)

Made on the night of 7-8 Nov 2026 to understand the web score estimate ("fórmula v1"). Our real 5.2
(`lliuraments/proposta-torns.csv`) moves ~2,000 sessions to their shift and scores **74**. This folder shows that the
estimate scores a timetable that moves **nothing** and declares every shift violation as a relaxation **higher**.

| Submission | What | Time changes | Declared R1-TORN | Idle min | Web |
|---|---|---|---|---|---|
| #264 | Real 5.2 (delivered) | 2,083 | 2 | 49,995 | 74 |
| #310 | `proposta-test.csv` + `relaxacions-test.csv`: today's times, all 2,006 R1-TORN + 13 R2-FINESTRA declared | 0 | 2,008 | 72,930 | **77** |
| #311 | `proposta-test-cercalocal.csv`: #310 improved with `cerca_local.py` (params in `params-cercalocal.txt`) | 134 | ~1,900 | 57,900 | **77** |
| #316-#323 | more local-search variants | 25-255 | ~1,800-2,000 | 53,580-67,110 | 77 |
| #318 | same idea | 414 | | 53,580 | 76 |
| #319 | same idea, most declared sessions moved back into their shift | 1,886 | | 48,900 | 74 |

What it shows: in the estimate, the number of time changes (`canvis_franja`) weighs far more than the number of
declared relaxations. A timetable that ignores the main rule of question 5.2 (1st/2nd year in the morning, the rest in
the afternoon) and declares it scores ~3 points more than one that meets it. The ranking's 79 is very likely built
this way.

Why it is not our deliverable: the statement grades validity (35 %) by the verdict **and whether each declared
relaxation is justified**. These 2,008 declarations are not: the sessions could move (the justification says so
openly). The board summary would also make no sense.

Rebuild: `python nivell2/p52_torns/prova-relaxacions/construeix.py` writes `proposta-test.csv` (= the 5.1 file) and
`relaxacions-test.csv`; `lot.py` is the batch runner used for the local-search variants (`decl` / `aules` modes).

## 5.3 on top of the test (also not a deliverable)

`proposta-test-52-anticipat.csv` = `proposta-test-cercalocal.csv` with the 5.3 incident rooms already applied
(`imprevist.py --anticipa-52`): web **77** (#328). `proposta-test-53.csv` + `relaxacions-test-53.csv` = the 5.3 repair
built on it (1 slot + 10 rooms vs that reference): web **79** (#329, reference #328), i.e. **one point below** our real
5.3 (80, #266, built on the real 5.2). So the declared-relaxations trick does not carry over to 5.3.

## 5.4 on top of the test (also not a deliverable)

`proposta-test-54.csv` = the new 40-student degree placed by `grau_nou.py` on `proposta-test-cercalocal.csv`, checked
with `relaxacions-test.csv`: all 235 new sessions fit (margin 2 free ordinary rooms in the tightest morning slot, the
minimum, because 3rd/4th year stay in the morning here), web **77** (#330) vs **73** for our real 5.4 (#125). Like 5.2,
5.4 rewards the declared-relaxations trick; 5.3 does not (79 vs 80).

## Even more relaxations: today's timetable untouched (also not a deliverable)

`proposta-test-partida.csv` = `paquet/proposta_partida.csv` exactly as it is (nothing moved, 4,541 sessions still
without a room), with **every** violation declared in `relaxacions-test-partida.csv`: R1-TORN 2,006, R5-SENSE-AULA 4,541,
R3-TIPUS 54, R3-AFORAMENT 43, R2-FINESTRA 13 (6,659 in total). Locally "VALIDA AMB RELAXACIONS DECLARADES", all
objectives at today's values (0 time changes, 0 room changes, 544 room moves). Web: **80** (#333), above the ranking's
79 and above every real solution of ours (74).

Local search on top (`proposta-test-partida-cercalocal.csv`, 120-300 time changes, idle ~54k, room moves ~420):
#334-#336 = **80** as well. So the more relaxations are declared, the higher the estimate, and doing nothing at all
scores best: the estimate does not penalise declared relaxations in a meaningful way. The jury's validity criterion
("whether each declared relaxation is justified") is what is supposed to stop this.

## All four questions on the 80 test

| Question | Test (everything declared) | Real deliverable |
|---|---|---|
| 5.1 | 78 (#341), 4,638 declared (no room, type, capacity) | 81 |
| 5.2 | 80 (#342, incident-ready version) | 74 |
| 5.3 | 80 (#343, ref #342, 1 slot + 10 rooms) | 80 |
| 5.4 | 80 (#344, all 235 new sessions fit) | 73 |

Files: `proposta-test-partida-51/52-anticipat/53/54.csv` and `relaxacions-test-partida-51/53.csv` (5.2 and 5.4 use
`relaxacions-test-partida.csv`). Summary for the jury in `INFORME.md` (Catalan).
