# 5.3 · Incidents: what do we propose?

Owner: _?_ · Branch: `nivell2/p53-imprevist` · Weight 10 % · Final version starts from 5.2

**Four things at once** (`paquet/escenaris/contingencies/`): Q3/0013 closed 15-19 March 2027 ·
Transmissió de Calor i Termotècnia TE/21 (GEQ 2n) grows to 130 students and no longer fits Q4/0011 · Q1/1003
broken on 10 March · session S11527 (8 March) cancelled and recovered by 19 March (extra column `data`).

**Goal:** fix all four changing **as little as possible** vs our 5.2 proposal (`canvis_franja_vs_referencia`,
`canvis_aula_vs_referencia`: lower is better). Can be prototyped now on `proposta_partida.csv`.

**Check:** `python -m horaris check ../lliuraments/proposta-imprevist.csv --semestre 2 --escenari
paquet/escenaris/contingencies --referencia ../lliuraments/proposta-torns.csv`.

Run the check from inside `repte-horaris-escola/` with the `.venv` active.
