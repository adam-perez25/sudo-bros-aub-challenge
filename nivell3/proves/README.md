# Proves

Preguntes com les del jurat, cada una amb la resposta correcta **calculada a part** (amb el verificador oficial i
pandas, sense el codi de l'assistent) i els id_sessio que la demostren. Serveixen per comparar el que diu
l'assistent. Horari: la proposta del 5.2 (`lliuraments/proposta-torns.csv`), 2n semestre.

Comprovació automàtica de les eines (sense LLM): `python nivell3/proves/prova_eines.py` (ha de sortir tot «OK»).

| # | Pregunta | Resposta esperada | Fonts / com es comprova |
|---|---|---|---|
| 1 | On té classe el grup 81 dimarts? | 115 sessions de la línia 81 (diverses assignatures i titulacions). Entre altres: 104346 TE/81 8.30-10.30 a Q4/1013; 104349 TE/81 10.30-12.30 a Q1/1003; 104353 TE/81 12.30-14.30 a Q4/0007; 104356 TE/81 10.30-12.30 a Q4/1013; 104357 TE/81 17.00-19.00 a Q2/1003; PAUL/81 de 104365 i 104368 a les 15.00 (QC/0036.B, QC/3115.1); Teoria de Jocs (104375) a B3/0021 a la tarda. L'assistent ha d'avisar que «81» és una línia amb diversos grups | S09767, S09923, S10138, S10250, S10263, S10527, S10635, S10785 |
| 2 | Quina aula de 60 places o més està lliure dijous a les 10? | Comprovats els 17 dijous del semestre, de 10.00 a 11.00: **Q2/1009 (90), Q4/0003 (90), Q3/1011 (130), Q1/1011 (160)** | Cap sessió de l'horari en aquestes aules a aquesta hora cap dijous; la reserva de 2 aules es manté |
| 3 | Quantes sessions té el 2n semestre? | 7.739 | `SELECT count(*) FROM sessions WHERE semestre = 2` |
| 4 | Quantes sessions del 2n semestre no tenen aula a l'horari d'avui? | 4.541 (sense comptar PLAB ni dobles titulacions) | verifica('partida'): R5-SENSE-AULA 4.541 |
| 5 | La proposta del 5.2 és vàlida? | VALIDA AMB RELAXACIONS DECLARADES: cap incompliment que compti; 460 relaxacions de la regla 1 declarades i justificades | verifica('torns') |
| 6 | Què passa si moc el PAUL/452 de 102750 a les 9.30? | No es pot: 26 incompliments nous, de R1-TORN (és de 3r/4t i ha de ser a la tarda) i R4-PLAB (coincidiria amb un laboratori de la mateixa assignatura) | que_passa_si(codi='102750', grup='PAUL/452', nova_hora='09:30') |
| 7 | El projector de Q1/1003 no funciona el 10 de març. Què fem? | 5 classes canvien només d'aula, al mateix dia i hora: S02580 i S02845 a Q1/1007; S03071, S06630 i S06644 a Q1/1011. Verificat: cap aula tancada ni cap incompliment nou; S06630 i S06644 són de grups fixats i cal declarar-les (R1-FIXADA) | resol_imprevist('aula_tancada', aula='Q1/1003', data_ini='2027-03-10') |
| 8 | I prepara l'avís | Esborranys per a cada docent, cada cohort i Gestió Acadèmica, i 5 files del registre de canvis. **No s'envia res** | esborrany_avis(motiu=...) |
| 9 | Quines classes té el docent D380 el 9 d'abril? | Tres PAUL de 102750 a Q1/0019: PAUL/452 a les 12.30, PAUL/453 a les 19.00 i PAUL/451 a les 20.00 | S04511, S04526, S04496 |
| 10 | Quina capacitat té Q4/0011? Quantes aules ordinàries hi ha? | 117 places; 21 aules ordinàries | aules.csv |
| 11 | Quines classes hi ha a Q1/1011 el dilluns 1 de febrer? | Cap. L'assistent ha de dir que no n'hi ha, no inventar-ne | horari_aula('Q1/1011', data='2027-02-01') |
