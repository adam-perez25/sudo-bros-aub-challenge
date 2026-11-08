# UAB The Hack 2026 · Repte d'horaris i espais de l'Escola d'Enginyeria

> Equip: **sudo bros**

Pregunta del repte: hi cap el model nou de torns (1r i 2n al matí; 3r, 4t, dobles titulacions i màsters a la tarda;
sempre dues aules ordinàries lliures)? Aquest repositori conté el nostre anàlisi, les propostes d'horari, l'assistent
d'IA i el quadre de comandament amb què ho presentem.

![](/assets/claude.png)

## Què hi ha a cada carpeta

| Carpeta | Contingut |
|---|---|
| `nivell1/` | Nivell 1, anàlisi de dades: quadern `nivell1.ipynb` i les cinc troballes a `TROBALLES.md` |
| `nivell2/` | Nivell 2, les quatre preguntes: `p51_aules`, `p52_torns` (amb el resum per a la Junta), `p53_imprevist`, `p54_grau_nou`. Cada carpeta té el seu `README.md` i `INFORME.md` |
| `nivell3/` | Nivell 3, assistent d'IA que només respon amb eines (SQL sobre els CSV i el verificador) i cita les sessions. Vegeu `nivell3/README.md` i `INFORME.md` |
| `dashboard/` | Quadre de comandament de la presentació (dades, propostes, plànols de l'edifici Q i l'assistent) |
| `lliuraments/` | Lliuraments finals: propostes CSV, relaxacions, informes del verificador i graella setmanal |
| `repte-horaris-escola/` | Material de l'organització: verificador `horaris` i paquet de dades (el paquet no és a git) |

## Resultat segons el verificador

| Pregunta | Proposta | Veredicte |
|---|---|---|
| 5.1 Aules | `lliuraments/proposta-aules.csv` | VALIDA (`--nomes-aules`) |
| 5.2 Torns nous | `lliuraments/proposta-torns.csv` | VALIDA AMB RELAXACIONS DECLARADES (460, totes de la regla 1, justificades) |
| 5.3 Imprevist | `lliuraments/proposta-imprevist.csv` | VALIDA AMB RELAXACIONS DECLARADES (470) |
| 5.4 Grau nou | `lliuraments/proposta-grau-nou.csv` | VALIDA AMB RELAXACIONS DECLARADES (460, cap de nova) |

Les ordres exactes per tornar-ho a comprovar són a [`lliuraments/README.md`](lliuraments/README.md).

## Com executar-ho

Primera vegada: seguiu [`SETUP.md`](SETUP.md) (clonar, posar el paquet de dades i crear el `.venv`). Les dades són
pseudonimitzades i **no** van a git.

```bash
streamlit run dashboard/app.py
```

És el quadre de comandament de la presentació. Cal executar-lo des de l'arrel del projecte amb el `.venv` actiu.

```bash
python nivell3/main.py
```

Xat de l'assistent al terminal. Necessita la configuració local del LLM de l'event, que no és a git (vegeu
`nivell3/README.md`). Comprovació sense LLM: `python nivell3/proves/prova_eines.py` (ha de sortir 63 de 63).
