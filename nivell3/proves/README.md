# Proves

Preguntes com les del jurat, cada una amb la resposta correcta **calculada a part** (amb el verificador oficial i
pandas, sense el codi de l'assistent) i els id_sessio que la demostren. Serveixen per comparar el que diu
l'assistent. Horari: `lliuraments/proposta-torns.csv` (la proposta del 5.2 al 2n semestre; l'horari d'avui, sense canvis, al 1r).

Comprovació automàtica de les eines (sense LLM): `python nivell3/proves/prova_eines.py` (ha de sortir tot «OK»; 63 comprovacions, 13 del 1r semestre) i del bucle de l'agent amb un LLM simulat: `python nivell3/proves/prova_agent.py` (16).

| # | Pregunta | Resposta esperada | Fonts / com es comprova |
|---|---|---|---|
| 1 | On té classe el grup 81 dimarts? | Sense dir semestre, els dos: 123 sessions al 1r i 121 al 2n (línia 81, diverses assignatures i titulacions). Al 2n, entre altres: 104346 TE/81 8.30-10.30 a Q4/1013 | S09767, S09923, S10138, S10250, S10263, S10527, S10635 |
| 2 | Quina aula de 60 places o més està lliure dijous a les 10? | Comprovats els 17 dijous del semestre, de 10.00 a 11.00: **cap** (el 5.2 actual té classe algun dijous a les 10 a totes les aules de 60 places o més) | Cap sessió de l'horari en aquestes aules a aquesta hora cap dijous; la reserva de 2 aules es manté |
| 3 | Quantes sessions té el 2n semestre? | 7.739 | `SELECT count(*) FROM sessions WHERE semestre = 2` |
| 4 | Quantes sessions del 2n semestre no tenen aula a l'horari d'avui? | 4.541 (sense comptar PLAB ni dobles titulacions) | verifica('partida'): R5-SENSE-AULA 4.541 |
| 5 | La proposta del 5.2 és vàlida? | VALIDA AMB RELAXACIONS DECLARADES: cap incompliment que compti; 460 relaxacions de la regla 1 declarades i justificades | verifica('torns') |
| 6 | Què passa si moc el PAUL/452 de 102750 a les 9.30? | No es pot: 26 incompliments nous, de R1-TORN (és de 3r/4t i ha de ser a la tarda) i R4-AULA (la seva aula ja és ocupada a aquella hora algun dia) | que_passa_si(codi='102750', grup='PAUL/452', nova_hora='09:30') |
| 7 | El projector de Q1/1003 no funciona el 10 de març. Què fem? | 7 classes canvien només d'aula, al mateix dia i hora, cap queda a Q1/1003 (S02580, S02845, S05520, S06630, S15034 a Q1/1007; S03071 i S06644 a Q1/1011). Verificat: cap aula tancada ni cap incompliment nou; S06630 i S06644 són de grups fixats i cal declarar-les (R1-FIXADA) | resol_imprevist('aula_tancada', aula='Q1/1003', data_ini='2027-03-10') |
| 8 | I prepara l'avís | Esborranys per a cada docent, cada cohort i Gestió Acadèmica, i una fila del registre per cada canvi (8). **No s'envia res** | esborrany_avis(motiu=...) |
| 9 | Quines classes té el docent D380 el 9 d'abril? | Tres PAUL de 102750 a Q1/0019: PAUL/452 a les 12.30, PAUL/453 a les 19.00 i PAUL/451 a les 20.00 | S04511, S04526, S04496 |
| 10 | Quina capacitat té Q4/0011? Quantes aules ordinàries hi ha? | 117 places; 21 aules ordinàries | aules.csv |
| 11 | Quines classes hi ha a Q1/1011 el dilluns 8 de febrer? | Dues classes de TE/21 (GEQ 2n): S11519 Transmissió de Calor i Termotècnia 11.30-13.30 i S11610 Circulació de Fluids 13.30-14.30 | horari_aula('Q1/1011', data='2027-02-08') |
| 12 | La classe -2 està lliure? | «No hi ha cap aula -2 a l'aulari.» Directe, sense mostrar consultes ni demanar l'hora | aules_lliures(aula='-2') |
| 13 | L'aula Q1/1003 està lliure el 2 de febrer a les 10.30? | No: hi ha 102769 PAUL/432 (Informació i Seguretat) de 10.30 a 11.30 | S06254 |
| 14 | Quines classes hi ha dimarts 13 d'octubre del 2026 a les 11? | 30 sessions (1r semestre) | ocupacio('11:00', data='2026-10-13'), comprovat amb pandas |
| 15 | El 8 de desembre hi ha classe? | No: és festiu (La Immaculada) | calendari_info('2026-12-08'); el 1r semestre va del 7/9/2026 al 29/1/2027 |
| 16 | L'horari del 1r semestre és vàlid? | No: NO VALIDA (és l'horari d'avui, que el 5.2 no toca): R1-TORN 2.069, R3-AULA 217... | verifica('torns', semestre=1) |
