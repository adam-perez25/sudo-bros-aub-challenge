# 5.4 · A new 40-student degree: does it fit?

Owner: _?_ · Branch: `nivell2/p54-grau-nou` · Weight 10 % · Final version starts from 5.2

**Goal:** place the 235 semester-2 sessions of the fictional degree (`paquet/escenaris/grau-nou-40/`, morning,
no room yet) on top of our 5.2 without breaking anything. If it fits: with which changes. If not: which rule, where,
and the smallest change that would make it fit (how many rooms of which size, or which rule to relax).

**Any "it doesn't fit" must be proven** (counting argument: demand in a slot > rooms; or a solver INFEASIBLE that
relaxes nothing), otherwise it counts as "we didn't find one". The counting part can start now.

**Check:** `python -m horaris check ../lliuraments/proposta-grau-nou.csv --semestre 2 --escenari
paquet/escenaris/grau-nou-40`.

Run the check from inside `repte-horaris-escola/` with the `.venv` active.
