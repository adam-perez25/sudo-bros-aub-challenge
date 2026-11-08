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
