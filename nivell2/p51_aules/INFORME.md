# 5.1 · Distribuir els grups del semestre a les aules

**Resultat: VALIDA** (mode `--nomes-aules`), **sense cap relaxació**. Cap sessió no canvia de dia ni d'hora.

Fitxers: `lliuraments/proposta-aules.csv`, `informe-aules.json` i `violacions-aules.csv`. Es regenera amb
[`aules.py`](aules.py).

## Què demanava l'enunciat

Amb l'horari d'avui, donar aula a les **4.541 sessions** que no en tenen, i arreglar les **43** que tenen més alumnes
que places i els **54 PAUL** que són en un laboratori de Q6: que hi càpiguen, del tipus que toca, sense dues classes
alhora a la mateixa aula i amb dues aules ordinàries lliures a cada franja. Una assignació vàlida existeix; el que
es valora és que sigui **bona**.

## Com l'hem fet bona

1. **Pocs canvis respecte d'avui:** tota aula d'avui que sigui vàlida es manté. Només canvien les que no ho són.
2. **Aula base per grup:** primer es col·loquen les teories (de més a menys alumnes) i les d'un mateix grup (cohort i
   línia) proven la mateixa aula. Cada activitat setmanal té la mateixa aula tot el semestre sempre que es pot.
3. **Pocs desplaçaments:** els PAUL i seminaris proven l'aula de la teoria del seu grup i, si no, el mateix passadís
   (espina i planta), i només després la més petita on hi càpiguen.
4. **Passada de millora:** cada activitat amb aula nova prova l'aula de les classes just abans o just després del seu
   grup, si és vàlida a totes les setmanes.

## Resultat (objectius de la regla 9, com més baix millor)

Comparat amb el mètode senzill que proposa l'enunciat (sessions d'una en una, de més a menys alumnes, a l'aula més
petita lliure), també vàlid:

| | Mètode senzill | **La nostra proposta** |
|---|---|---|
| Aules de teoria de més per grup (aula base, R6) | 130 | **55** (−58 %) |
| Canvis TE↔PAUL fora del passadís (R6) | 1.675 | **457** (−73 %) |
| Canvis d'aula entre classes seguides | 3.636 | **2.377** (−35 %) |
| Canvis d'aula respecte d'avui | 132 | **97** |

Els 97 canvis respecte d'avui són les sessions que tenien una aula no vàlida (PAUL en laboratoris de Q6, grups que no
hi cabien) i les que hem mogut a l'aula del seu grup.

**Una decisió:** les 35 sessions del 2n semestre que avui es fan a B3/0021 (fora de l'aulari) s'hi queden, tal com
permet l'Escola. Això deixa 17 canvis d'edifici entre classes seguides; portar-les a l'aulari els eliminaria, però
afegiria fins a 35 canvis d'aula respecte d'avui.
