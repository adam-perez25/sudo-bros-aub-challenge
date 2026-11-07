# Nivell 3 · Assistent per a Gestió Acadèmica

## Què fa

Un assistent conversacional per fer i mantenir l'horari del 2n semestre. Respon preguntes com:

- «On té classe el grup 81 dimarts?»
- «Quina aula de 60 places està lliure dijous a les 10?»
- «Què passa si moc aquesta assignatura a les 9.30?»
- «El projector de Q1/1003 no funciona el 10 de març: què fem? Prepara l'avís.»

Fa servir el LLM de l'event (servidors del DCC de la UAB) i **només les dades del paquet**: res no surt a serveis
externs, i els avisos es redacten però **no s'envien** a ningú.

## Per què no es pot inventar res

El LLM no respon de memòria: **només tria una eina i n'explica el resultat**. Les eines són codi normal, sense IA,
que llegeix les dades o crida el verificador oficial:

| Eina | Què fa | Com es comprova |
|---|---|---|
| `horari_grup`, `horari_aula` | On i quan té classe un grup / què hi ha en una aula | Torna els `id_sessio`: es busquen al CSV |
| `aules_lliures` | Aules lliures a una hora (una data, o tots els dies d'aquell dia de la setmana), amb capacitat i tipus | Comprova solapaments i la reserva de 2 aules (regla 8); diu quines sessions ocupen les aules no lliures |
| `consulta_sql` | Qualsevol altra consulta, en SQL de només lectura (DuckDB) | La consulta es mostra i es pot tornar a executar |
| `verifica` | Passa el verificador oficial a una proposta | És el mateix verificador del jurat |
| `que_passa_si` | Simula un canvi i diu quines regles trencaria | Verificador abans i després |
| `resol_imprevist` | Proposa la solució mínima per a una aula tancada (avaria, acte) o una sessió cancel·lada (motor del 5.3) | Verificador: cap imprevist pendent ni cap incompliment nou; diu quines relaxacions caldrien |
| `esborrany_avis` | Redacta l'avís al docent, a l'alumnat i a Gestió Acadèmica, i l'entrada del registre de canvis (sessió, d'on a on, motiu, a qui afecta, data de l'avís) | Cada línia porta l'`id_sessio` |

A més:

- Cada resposta mostra les **fonts** (els `id_sessio` o les aules) i les eines que s'han cridat.
- El missatge de sistema obliga a dir «no ho puc comprovar» quan cap eina no ho diu, i tracta la sortida de les eines
  (noms d'assignatures, missatges del verificador) com a **dades, mai com a instruccions**.
- La consulta SQL no pot modificar res ni llegir cap fitxer del disc: DuckDB treballa en memòria, amb l'accés a
  fitxers desactivat i la configuració bloquejada.

## Com l'hem provat

- **Eines:** 13 preguntes com les del jurat, amb la resposta calculada a part (verificador oficial + pandas, sense el
  codi de l'assistent): totes les eines hi coincideixen (`proves/prova_eines.py`, 19 de 19 comprovacions). Les
  preguntes i les respostes són a `proves/README.md`.
- **Agent:** el bucle amb un LLM simulat: crides a eines, l'imprevist en dos passos (solució i avís), el mode de
  reserva quan el servidor no accepta eines, i errors d'arguments retornats al LLM perquè es corregeixi.

## Exemple

> **Pregunta:** El projector de Q1/1003 no funciona el 10 de març. Què fem?
>
> **Eina:** `resol_imprevist(tipus='aula_tancada', aula='Q1/1003', data_ini='2027-03-10')`
>
> **Resposta:** 5 classes canvien només d'aula, al mateix dia i hora: S02580 i S02845 a Q1/1007; S03071, S06630 i
> S06644 a Q1/1011. Verificat: cap aula tancada ni cap incompliment nou. S06630 i S06644 són de grups fixats i cal
> declarar-ho com a relaxació (R1-FIXADA).
