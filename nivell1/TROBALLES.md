# Nivell 1 · Les cinc troballes principals

**Pregunta:** com s'usen avui els espais de l'Escola, i hi cap el model nou (1r i 2n al matí; 3r, 4t, dobles
titulacions i màsters a la tarda; sempre dues aules ordinàries lliures)?

**Resposta curta:** **sí, el matí hi cap, però només si es reparteixen les hores punta.** El total setmanal no és el
problema (al voltant del 60 % de les hores-aula de matí); el problema és el dimarts i les franges de 10.30 a 13.30.
La mida de les aules no fa de coll d'ampolla, i la tarda es queda amb molta capacitat de sobres.

Totes les xifres són del **2n semestre** (el del nivell 2) si no es diu el contrari. Surten de
[`analisi.py`](analisi.py) i es dibuixen a [`nivell1.ipynb`](nivell1.ipynb), amb les mateixes convencions que el
verificador oficial: semestre per data, torn per hora d'inici (abans de les 14.30 = matí), una sessió compartida
compta un cop, els grups de doble titulació (`sense_espai = 1`) no necessiten aula i els PLAB estan fixats.
«Aules disponibles» = 21 aules ordinàries menys les 2 que han de quedar lliures = **19**. «Setmana normal» = 5 dies
lectius i cap esdeveniment a `calendari.csv` (11 de les 20 setmanes).

---

### 1. Les dades amaguen tres quartes parts de la demanda d'aules: el 74 % de les sessions no tenen aula

- **5.722 de les 7.739** sessions del 2n semestre tenen `aula_partida` buida. D'aquestes, **919 són PLAB**
  (laboratoris de departament, fixats, que assignen els departaments) i **262 són grups de doble titulació** (no
  necessiten aula): **4.541 necessiten aula de veritat.**
- Per això, al 2n semestre les aules ordinàries *semblen* ocupades un 23 % al matí i un 4 % a la tarda, davant del
  50 % i el 27 % del 1r semestre. Aules com Q2/1009 i Q2/1013 (90 places) semblen gairebé sense ús.
- **Com:** `sense_aula()` classifica les sessions sense aula per `tipus` i `sense_espai`; `ocupacio_aules()` compta,
  per a cada aula i franja, la proporció de setmanes lectives en què està ocupada (mapa de calor, apartat 1 del
  quadern).
- **Per què importa:** qualsevol conclusió del tipus «aquesta aula és lliure» treta de les aules del 2n semestre és
  falsa. La demanda real s'ha de comptar des de les sessions, no des de les aules (troballa 3).

### 2. 3.246 sessions són fora de torn; se'n poden moure 2.008, sobretot de 3r i 4t cap a la tarda

- **2.008 movibles**: 1.774 han d'anar a la tarda i 234 al matí. 248 d'aquestes són sessions de doble titulació que
  avui es fan juntament amb un grup de matí: candidates a una excepció declarada.
- Per cohort (proporció de les sessions de la cohort que són fora de torn): **GEI 3r 89 %, GEI 4t 92 %, GEST 3r 99 %,
  GEET 3r 98 %, GEQ 3r 100 %** (cap a la tarda); **GCIS 2n 100 %, GIA 1r 100 %, GIA 2n 100 %** (cap al matí).
- **1.238 són fixades** i no podran complir mai: **600 sessions de classe de GEI 1r i 2n** («no es toquen»; 573 a la
  tarda, més 27 de doble titulació al matí) i **638 laboratoris PLAB fixats** a l'altre torn (349 de GEI 3r i 4t al
  matí; 148 de GEI 1r i 2n i 94 de GIA 1r i 2n a la tarda; 47 de GEET/GEST). El verificador les marca com a heretades,
  però són excepcions reals a la regla 1 que la Junta ha de conèixer.
- **Com:** `fora_torn` = hora d'inici a l'altra banda de les 14.30 respecte de `torn_requerit`; `fora_de_torn()` ho
  reparteix per titulació i curs (una sessió compartida per dues cohorts compta per a totes dues); movible = `fixada`
  buit. El total de 2.008 coincideix amb el recompte R1-TORN del verificador.

### 3. Sobre el paper el matí hi cap: el model nou necessita ~60 % de les hores-aula de matí

- A les setmanes normals, 1r i 2n necessiten el **59-64 % de les hores-aula de matí** de les 19 aules disponibles
  (19 aules × 6 h × 5 dies = 570 hores-aula per setmana), quan avui, només amb les classes que ja són al matí, és el
  47-52 %. Amb la definició de l'enunciat (comptant també les classes que es fan en aules d'informàtica) és el
  64-70 %, en línia amb el 67-70 % que s'hi cita.
- Això són **12,2 classes alhora de mitjana** davant del límit de 19 (setmana 2027-W06).
- Cada subgrup d'alumnes té **com a molt 20 h** de classe a la setmana davant de les 30 hores de matí: els horaris
  dels alumnes tampoc no són el límit.
- La tarda (3r, 4t i màsters) es queda al **35-40 %**: molt d'espai de sobres.
- **Com:** `hores_aula_setmana()` suma les durades de les classes que necessiten aula (una per classe física; sense
  PLAB, sense dobles titulacions i sense les que es poden quedar en un laboratori o aula d'informàtica) per setmana,
  i les divideix per l'oferta.

### 4. El límit real és el pic: el dimarts i la franja de 10.30 a 13.30 ja són a 15 de 19

- Amb les hores d'avui, les classes de 1r i 2n que ja són al matí arriben a **15 alhora** (dimarts a les 10.30).
  Mantenint els dies d'avui, el dimarts faria de mitjana **14,5 classes alhora** durant tot el matí, davant de les
  10,8 del dimecres.
- Fins i tot l'horari d'avui (tots els torns) necessita **més de 19 aules en 23 de les 894** franges del 2n semestre
  (fins a 21, dimarts a les 10.30 i a les 16.30): els grups petits ja han d'anar a seminaris.
- **Implicació per al 5.2:** les classes que passen al matí han d'anar als dies i les hores més tranquils (dimecres,
  divendres, 8.30), no a les franges que agafarien de manera natural.
- **Com:** `simultanies()` compta, per a cada data i franja, les classes que necessiten aula alhora (amb la regla de
  solapament del verificador) i en pren el màxim per franja.

### 5. La mida de les aules no és un coll d'ampolla; avui només hi ha 2 grups movibles per sobre de l'aforament

- Comprovació de recompte en una setmana normal: per a cada mida d'aula N, les classes de matí que necessiten com a
  mínim N places fan servir com a molt el **33 %** de les hores-aula de les aules amb N places o més (les 2 de reserva,
  preses de les més petites). Les classes de més de 117 alumnes necessiten 2 hores-aula a la setmana de les 90 que
  ofereixen les tres aules de 130-160 places.
- **101 sessions (6 grups)** tenen més alumnes que places a l'aula d'avui, però **58 són de grups PAUL fixats** de GEI
  que només passen d'1 o 2 alumnes una aula de 48-50 places (heretades). Les **43 movibles** són de dos grups, tots
  dos fàcils de resoldre:
  - **Física TE/21 (GEQ 1r): 125 alumnes a Q4/0011 (117 places)** → Q1/1011 (160), Q3/1007 o Q3/1011 (130).
  - **Sistemes i Tecnologies Web TE/450 (GEI 3r i 4t): 103 a Q3/0003 (100)** → qualsevol aula de 117 places o més.
- **Com:** `mida_mati()` (demanda i oferta per mida) i `sobre_aforament()` (alumnes d'una classe física sumats i
  comparats amb la capacitat d'`aules.csv`; els 43 i 58 coincideixen amb els recomptes R3-AFORAMENT del verificador).

---

**No fet:** la comparació «pla contra realitat» amb `validacio/`: el CSV d'ocupació real no és al paquet que hem
rebut (només n'hi ha el LLEGIU-ME).
