# 5.4 · Un grau nou de 40 places el curs vinent: com ho fem?

**Resposta: sí, hi cap.** A les proves, sense moure cap sessió dels graus actuals; i el grau nou no necessita cap
relaxació de les regles.

## Com el col·loquem

Ho fa l'eina [`grau_nou.py`](grau_nou.py), sobre la nostra proposta del 5.2 i sense tocar cap sessió existent:

1. Cada activitat setmanal del grau nou es queda al dia i a l'hora que porta (l'estructura de 1r de GED) i rep **una
   sola aula per a tot el semestre** si pot ser: la més petita on hi càpiga, i els PAUL al mateix passadís que la
   teoria del grup (regla 6).
2. Si a la seva hora no hi ha cap aula lliure, la sessió es mou a una altra franja de matí de la mateixa setmana on
   l'alumnat, el docent i una aula estiguin lliures.
3. Al final, el verificador oficial comprova que les sessions noves no incompleixen res i que la resta de la
   proposta no té cap incompliment nou.

## Per què hi cap (i per què no depèn dels detalls del 5.2)

- El grau nou **mai no necessita més de 2 aules alhora**, i **com a molt 1 teoria** (només té un grup de teoria).
- La teoria (40 alumnes) necessita una de les 20 aules ordinàries de 40 places o més. Els PAUL (fins a 20 alumnes)
  poden anar també a **14 espais que no són aules ordinàries** (6 seminaris, 6 laboratoris integrats i les 2 aules
  d'informàtica), que no compten per a la reserva de la regla 8.
- Per tant, hi cap en qualsevol proposta on, cada setmana, a les franges de la seva teoria (dimarts 10.30 i 12.30,
  dijous 12.30, divendres 12.30) o a qualsevol altra franja de matí d'aquella setmana, quedin **3 aules ordinàries
  lliures** (1 per a la teoria i les 2 de reserva). Al nivell 1 hem vist que el model nou ocupa de mitjana unes 12
  de les 19 aules disponibles al matí: el marge hi és.

## Resultat sobre la nostra proposta del 5.2

Fitxers: `lliuraments/proposta-grau-nou.csv`, `informe-grau-nou.json` i `violacions-grau-nou.csv`. Comprovat amb
l'ordre del jurat (`--escenari grau-nou-40`, amb les relaxacions del 5.2):

| | |
|---|---|
| **Veredicte** | **VALIDA AMB RELAXACIONS DECLARADES**: les mateixes 460 del 5.2, **cap de nova** per al grau nou |
| Sessions del grau nou col·locades | **235 de 235**, totes al dia i a l'hora que porten (0 mogudes) |
| Sessions dels graus actuals que canvien | **0** |
| Incompliments de les sessions noves / nous a la resta | **0 / 0** |
| Aules ordinàries lliures a la franja de matí més plena | 7 abans → **6 després** (la regla 8 en demana 2) |

Cada una de les 4 teories setmanals (40 alumnes) té la seva aula fixa tot el semestre, de 48 a 63 places (Q3/0009,
Q2/1005, Q4/1003 i Q4/1005), i els PAUL van sobretot a seminaris (QC/3115.x) i aules petites. Per això, a la franja
de matí més plena el grau nou només ocupa una aula ordinària més.

Abans de tenir el 5.2, l'eina es va provar sobre l'horari d'avui (235 de 235, 0 incompliments) i sobre un horari amb
totes les aules plenes (235 de 235, 0 incompliments, 3 aules ordinàries lliures a la pitjor franja).

**Quant n'hi cabria?** Prova d'estrès sobre l'horari amb totes les aules assignades, afegint-hi còpies del grau nou
(cohorts i docents diferents): **hi caben fins a 10 graus com aquest** (2.350 sessions) sense cap incompliment; amb
11, la primera sessió ja no troba lloc. És un mètode voraç, així que 10 és el mínim que sabem que hi cap, no un màxim
demostrat. En qualsevol cas, un grau de 40 places queda molt lluny del límit de l'edifici.
