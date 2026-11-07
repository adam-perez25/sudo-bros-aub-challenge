# 5.2 · Torns nous: 1r i 2n al matí, 3r i 4t a la tarda

**Resultat: VALIDA AMB RELAXACIONS DECLARADES**, amb **cap incompliment que compti** a cap regla. Les 460
excepcions declarades són totes de la regla 1: 458 sessions de grups fixats que l'Escola no vol tocar i 2 sessions
on hem **demostrat** que no hi caben. Resum per a la Junta Permanent: [`RESUM-JUNTA.md`](RESUM-JUNTA.md).

Fitxers (a `lliuraments/`): `proposta-torns.csv`, `relaxacions.csv`, `informe-torns.json`, `violacions-torns.csv` i
la graella setmanal per aula (`graella-setmanal.md` i `.csv`). Es regeneren amb [`torns.py`](torns.py),
[`resum_junta.py`](resum_junta.py) i [`graella.py`](graella.py).

## Com ho hem fet

Partim de l'horari d'avui i **canviem el mínim**:

1. **Es manté** tot el que ja compleix: les sessions al seu torn i les aules d'avui que són vàlides.
2. **Aula, primer, per a les sessions que no canvien d'hora** (són les menys flexibles): una aula per activitat
   setmanal si es pot (aula base), l'aula d'avui si és vàlida, després la del mateix passadís i la més petita on hi
   càpiga, sempre amb tipus, aforament, cap solapament i la reserva de 2 aules ordinàries.
3. **Cada activitat fora de torn es mou en bloc** (160 activitats, 2.008 sessions): mateix dia de la setmana i mateixa
   hora totes les setmanes, les sessions compartides juntes. Es tria la franja lliure per a alumnat, docents i una
   aula que deixi menys hores mortes (enganxada a les altres classes del grup aquell dia), que eviti les hores punta
   que vam trobar al nivell 1 i que, si pot, mantingui el dia. Calendari, finestres i setmana ISO respectats.
4. **Reparació local** del que queda: si una sessió no troba lloc, s'alliberen forats movent altres classes no
   fixades a una altra franja o aula vàlida, i es desfà tot si alguna no es pot moure.
5. **Millora de la qualitat de les aules**: cada activitat amb aula triada per nosaltres prova l'aula de les classes
   veïnes del seu grup (menys desplaçaments i canvis TE↔PAUL dins del mateix passadís).
6. **Verificador oficial** al final, i declaració només del que no es pot complir.

## Resultats (objectius de la regla 9, com més baix millor)

| | Avui | Proposta 5.2 |
|---|---|---|
| Incompliments que compten | R1-TORN 2.008, R2-FINESTRA 13, R3 97, R5-SENSE-AULA 4.541 | **0** |
| Hores mortes (minuts) | 72.930 | **62.640** (−14 %) |
| Sessions que canvien de franja / d'aula | — | 2.006 / 289 |
| Solapaments de docent heretats (no compten) | 752 | 418 |

Els desplaçaments entre aules (2.209) i els canvis TE↔PAUL fora del passadís (560) no són comparables amb avui:
avui el 74 % de les sessions del 2n semestre no tenen aula i no hi compten. La millora d'aules (veïns + cerca local
sobre l'indicador real, `optimitza_aules`) els va reduir de 4.373 a 2.209 i de 1.825 a 560; les aules de teoria
extra per grup baixen de 79 a 76.

## Excepcions declarades (i per què)

1. **458 sessions de grups fixats de GEI de 1r i 2n que avui són a la tarda.** No es poden moure (R1-FIXADA). Avui no
   tenen aula i el verificador les considera heretades; en donar-los l'aula que els falta (obligatori, regla 5)
   deixen de ser-ho. Qualsevol proposta vàlida ha de declarar-les.
2. **2 sessions on està demostrat que no hi caben** (regla 11, «hem demostrat que no existeix»):
   - **S02839** (102730 TE/7): el 31/5/2027 és l'únic dia lectiu de la seva setmana i els docents D214 i D398 hi tenen
     480 minuts de classes que han de ser a la tarda, que només en té 390. Algú s'ha de quedar fora de la tarda: és
     aquesta classe, que compta una sola fila (la doble TE/51 en comptaria dues).
   - **S04511** (102750 PAUL/452): el 9/4/2027 és l'únic dia on es pot moure (del 5 al 8/4 és la setmana
     d'avaluació). Necessita una aula d'informàtica (34 alumnes), i totes dues estan ocupades de 15.00 a 19.00 per
     grups fixats; el docent D380 té tres PAUL d'una hora per a les dues hores que queden (19.00-21.00).

Les 248 sessions de doble titulació que avui es fan amb un grup de matí s'han pogut passar totes a la tarda: no cal
cap excepció per a elles.
