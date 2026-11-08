# Prova: què puntua l'estimació web quan es declaren relaxacions

**No és cap lliurament.** És un experiment fet la nit del 7 al 8 de novembre de 2026 per entendre la puntuació orientativa
del verificador web («fórmula v1», que no és pública). Els lliuraments de veritat són a `lliuraments/`.

## Resum

L'estimació gairebé no penalitza les relaxacions declarades. Un horari que **no canvia res** i declara totes les
regles que incompleix treu més punts que una solució que les compleix:

| Enviament | Proposta (pregunta 5.2) | Relaxacions declarades | Canvis de franja | Puntuació web |
|---|---|---|---|---|
| #264 | **La nostra 5.2 real** (`lliuraments/`): 1r i 2n al matí, la resta a la tarda | 2 (justificades) | 2.083 | **74** |
| #310 | Hores d'avui, totes les infraccions de torn i de finestra declarades | 2.008 | 0 | **77** |
| #333 | **L'horari d'avui sense tocar**, totes les infraccions declarades | 6.659 | 0 | **80** |
| #334-#336 | #333 millorat amb cerca local (hores mortes ~54.000, desplaçaments ~420) | ~6.500 | 120-300 | 80 |

El mateix passa al 5.4 (grau nou sobre la prova de 77: **77**, davant del 73 de la nostra 5.4 real). Al 5.3 no
(**79**, davant del nostre 80).

## Com s'ha fet

1. `proposta-test.csv` = el lliurament del 5.1 (cada sessió al seu dia i hora d'avui, amb aula). Passat pel verificador
   en mode 5.2, incompleix R1-TORN (2.006 sessions) i R2-FINESTRA (13). `construeix.py` les declara totes a
   `relaxacions-test.csv`. Resultat: «vàlida amb relaxacions declarades», 0 canvis de franja, **77**.
2. `proposta-test-partida.csv` = `paquet/proposta_partida.csv` tal com és. Incompleix R1-TORN (2.006), R5-SENSE-AULA
   (4.541), R3-TIPUS (54), R3-AFORAMENT (43) i R2-FINESTRA (13): 6.659 en total, totes declarades a
   `relaxacions-test-partida.csv`. Tots els objectius queden com avui. Resultat: **80**.
3. La cerca local (`cerca_local.py`, `lot.py`) sobre aquestes proves millora hores mortes i aules, però la puntuació no
   passa de 77 ni de 80. El que la fa moure és el nombre de canvis de franja: fins a ~255, 77; 414, 76; ~2.000, 74.

Totes les justificacions d'aquestes relaxacions diuen obertament que són una prova i que no són impossibilitats.

## Què en traiem

- A l'estimació, els **canvis de franja** pesen molt més que les **relaxacions declarades**. Com més regles es declaren
  en lloc de complir-les, més puja la xifra. No fer res i declarar-ho tot és el que puntua més.
- Per això creiem que el 79 que es veia al rànquing del 5.2 s'havia fet així.
- L'enunciat diu que la validesa (35 % de la nota) mira el veredicte **i si cada relaxació declarada està justificada**.
  Aquestes 6.659 no ho estan: les sessions es poden moure. Per això els nostres lliuraments no fan servir aquest truc i
  només declaren el que no hi cap: les 2 sessions demostrades (S02839 i S04511) i els grups fixats de GEI.

## Fitxers

| Fitxer | Què és | Web |
|---|---|---|
| `proposta-test.csv`, `relaxacions-test.csv` | Hores d'avui, torn i finestra declarats | 77 (#310) |
| `proposta-test-cercalocal.csv` | L'anterior amb cerca local (`params-cercalocal.txt`) | 77 (#311) |
| `proposta-test-52-anticipat.csv` | L'anterior preparat per als imprevistos del 5.3 | 77 (#328) |
| `proposta-test-53.csv`, `relaxacions-test-53.csv` | 5.3 sobre la prova (1 franja + 10 aules) | 79 (#329) |
| `proposta-test-54.csv` | 5.4 sobre la prova | 77 (#330) |
| `proposta-test-partida.csv`, `relaxacions-test-partida.csv` | Horari d'avui sense tocar, tot declarat | 80 (#333) |
| `proposta-test-partida-cercalocal.csv` | L'anterior amb cerca local | 80 (#334) |
| `construeix.py`, `lot.py` | Generen la primera prova i les variants de cerca local | |

Detall tècnic en anglès a `README.md`.
