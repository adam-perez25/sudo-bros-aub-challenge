# 5.3 · Un imprevist: què proposem?

**Principi:** resoldre els quatre imprevistos **canviant el mínim** respecte de la nostra proposta del 5.2. Cap
sessió canvia de dia o d'hora si no és imprescindible, i cap reparació no pot trencar res que ja funcionés.

Ho fa l'eina [`imprevist.py`](imprevist.py), que repara qualsevol proposta i després es comprova amb el verificador
oficial: compta els imprevistos abans i després i els incompliments nous que la reparació hagi pogut introduir.

## Què fem amb cada imprevist

| Imprevist | Què fem | Per què així |
|---|---|---|
| **Sala reservada:** Q3/0013, del 15 al 19 de març | Cada classe que hi havia es queda el mateix dia i a la mateixa hora i canvia només d'aula: una de lliure, del tipus que toca, prou gran i, si pot ser, del mateix passadís (espina i planta) | Ni alumnes ni docents no han de canviar d'horari; només de porta |
| **Grup que creix:** Transmissió de Calor i Termotècnia, TE/21 (GEQ 2n), de 91 a 130 alumnes | Totes les seves sessions passen a **una sola** aula de 130 places o més que estigui lliure a totes les seves hores | Una aula base estable per al grup (regla 6), sense desdoblar-lo ni declarar cap relaxació d'aforament |
| **Avaria:** projector i ordinador de Q1/1003, dimecres 10 de març | Com la sala reservada: mateix dia i hora, una altra aula lliure i prou gran | És una avaria d'un sol dia: només canvien les classes d'aquell dia |
| **Sessió cancel·lada:** S11527 (TE/21, dilluns 8 de març) | Es recupera al primer forat vàlid fins al 19 de març: alumnat, docents i una aula de 130 places lliures, dins del torn de matí, fora de festius i aturades (el 18 de març no hi ha docència i el 17 hi ha aturada de 13 a 15 h). Es prefereix la mateixa hora i l'aula nova del grup | S11527 és una sessió del mateix grup que creix: la recuperació també necessita una aula de 130 places |

## Relaxacions que declarem (i per què no es poden evitar)

Aquella setmana, a Q3/0013 i a Q1/1003 hi ha **8 sessions fixades** de GEI de 1r i 2n i **2 laboratoris PLAB** del
màster RICSE, que les regles diuen que no es toquen. Però una aula tancada no es pot relaxar (R3-TANCADA), així que
aquestes 10 sessions s'han de canviar d'aula per força. Les declarem com a relaxació de R1-FIXADA (8) i R7-PLAB (2),
amb la justificació, i **només en canviem l'aula**: el dia i l'hora es mantenen.

## Resultat sobre la nostra proposta del 5.2

Fitxers: `lliuraments/proposta-imprevist.csv`, `relaxacions-imprevist.csv` (les del 5.2 + les 10 d'aquest
apartat), `informe-imprevist.json` i `violacions-imprevist.csv`. Comprovat amb l'ordre del jurat (`--escenari
contingencies --referencia proposta-torns.csv`):

| | |
|---|---|
| **Veredicte** | **VALIDA AMB RELAXACIONS DECLARADES**, cap incompliment que compti |
| Imprevistos (R3-TANCADA, R3-AFORAMENT del grup, R5-RECUPERACIO) | 58 → **0** |
| Incompliments nous introduïts per la reparació | **0** |
| Canvis respecte del 5.2 | **1 franja** (la sessió recuperada) i **57 aules** |
| Relaxacions noves d'aquest apartat | 10: R1-FIXADA (8) i R7-PLAB (2), les sessions fixades que eren a les aules tancades |

Què ha passat amb cada imprevist:

- **Q3/0013 (15-19/3) i Q1/1003 (10/3):** 26 classes canvien d'aula al mateix dia i hora, a una aula lliure del tipus i la mida
  que toca, del mateix passadís quan n'hi ha cap de lliure (Q1/1007, Q1/1011, Q3/0003, Q3/0009, Q3/0011, Q4/1005, QC/0019, QC/3115.2, QC/3115.4).
- **TE/21 de Transmissió de Calor (130 alumnes):** les seves 31 sessions passen totes de Q4/0007 (117 places) a
  **Q3/1011** (130), sempre la mateixa aula.
- **S11527:** es recupera el **dimarts 9 de març de 10.30 a 12.30 a Q3/1007** (130 places), l'endemà de la
  cancel·lació, amb l'alumnat i els docents lliures.

El nombre de canvis és el mínim possible: cada canvi d'aula és d'una sessió que era en una aula tancada o on el grup
ja no hi cabia, i l'únic canvi de franja és la sessió cancel·lada, que s'havia de recuperar.

Abans de tenir el 5.2, l'eina es va provar sobre l'horari d'avui (42 → 0 imprevistos, 0 incompliments nous) i sobre
un horari amb totes les aules plenes (57 → 0, 0 nous).
