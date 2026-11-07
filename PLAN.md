# Team plan — UAB THE HACK! 2026 · Escola d'Enginyeria challenge

The full statement is the PDF in the SharePoint folder (`ENUNCIAT`). This file says **what we deliver, who does it,
where it lives in the repo and how we work without stepping on each other**. Keep it up to date: change the
status and owner columns when you start or finish something.

First time here? Do [SETUP.md](SETUP.md) first (clone, data from SharePoint, `.venv`).

## 1. The tasks

| # | Task | Weight | Folder | Status | Owner |
|---|---|---:|---|---|---|
| L1 | Data analysis: how rooms are used, does the new model fit? | 25 % | `nivell1/` | ✅ Done | Adam |
| 5.1 | Assign rooms without moving any time | 5 % | `nivell2/p51_aules/` | ✅ Done: VALIDA, no relaxations | Adam (+ Claude) |
| 5.2 | New shifts (1st/2nd morning, 3rd/4th afternoon) + board summary | 25 % | `nivell2/p52_torns/` | ✅ Done: VALIDA AMB RELAXACIONS (460, all justified) | Adam (+ Claude) |
| 5.3 | Incidents: closed room, bigger group, broken projector, cancelled session | 10 % | `nivell2/p53_imprevist/` | ✅ Done: 1 slot + 57 rooms changed vs 5.2 | Adam (+ Claude) |
| 5.4 | New 40-student degree: does it fit? | 10 % | `nivell2/p54_grau_nou/` | ✅ Done: it fits, 0 changes, 0 new relaxations | Adam (+ Claude) |
| L3 | AI assistant whose answers can be checked | 25 % | `nivell3/` | ⬜ To do | _?_ |
| — | Weekly grid per room (one, from the most advanced proposal) | in 5.x | `lliuraments/` | ✅ Done (from 5.2) | Adam (+ Claude) |
| — | Presentation / demo | — | — | ⬜ To do | _?_ |

Status: ⬜ to do · 🟡 in progress · ✅ done. Level 2 is always **semester 2** only.

### What "done" means for each task

- **L1** (done): notebook `nivell1/nivell1.ipynb` + five findings in `nivell1/TROBALLES.md`. Section 6 (plan vs
  reality) is ready but waits for the GERES file, which is not in the organisers' zip.
- **5.1**: `proposta-aules.csv` (`id_sessio,dia,h_ini,aula`, one row per session) that is `VALIDA` with
  `--semestre 2 --nomes-aules`, plus `informe.json` and `violacions.csv`. Validity is assumed; the score is the
  **quality**: one stable home room per group, few room changes between consecutive classes, few changes vs today.
- **5.2**: `proposta-torns.csv` as `VALIDA` as possible with `--semestre 2` (any rule we can't meet goes in
  `relaxacions.csv`, each with a solid justification), the fewest idle gaps and changes, plus a **one-page summary
  for the Junta Permanent**: peak simultaneous classes morning/afternoon vs rooms, missing/spare rooms by size,
  sessions moved by degree and year, the exceptions to rule 1 we ask for and why.
- **5.3**: `proposta-imprevist.csv` starting from our 5.2 and changing as little as possible, checked with
  `--escenari paquet/escenaris/contingencies --referencia proposta-torns.csv`. Session S11527 needs an extra
  `data` column with its recovery date.
- **5.4**: `proposta-grau-nou.csv` on top of our 5.2, checked with `--escenari paquet/escenaris/grau-nou-40`. If it
  doesn't fit: which rule, where, and the smallest change that would fix it. Any "it doesn't fit" must be
  **proven** (a counting argument or a solver INFEASIBLE that relaxes nothing silently).
- **L3**: a demo (short video or live) of an assistant that answers questions about the timetable **only from
  tools** (SQL over the CSVs + the verifier) and cites the `id_sessio` behind each answer. **Only the event's LLM**,
  never an external API with this data. The jury asks 3 live questions and checks the answers against the CSVs.

Every level 2 delivery includes the verifier output. Run it from inside `repte-horaris-escola/`:

```
python -m horaris check ../lliuraments/<proposta>.csv --semestre 2 --json ../lliuraments/informe.json --violacions ../lliuraments/violacions.csv
```

## 2. Who can start now (dependencies)

```
L1 ✅
5.1 ──► 5.2 ──► 5.3
           └──► 5.4
L3 (independent: needs only the data and the verifier)
```

The tasks are independent enough for **3-4 people in parallel**:

| Person | Starts with | Then | Needs from others |
|---|---|---|---|
| **A · Solver** | 5.1 (room assignment engine) | 5.2 times + rooms | nothing |
| **B · Scenarios** | 5.4 counting proof (does the new degree fit at all? peak slots vs rooms) and 5.3 repair script, both prototyped on `proposta_partida.csv` | rerun both on A's 5.2 | A's `proposta-torns.csv` at the end |
| **C · AI** | L3 assistant: SQL tool + verifier tool + citations | 5.3 "incident agent" demo | nothing (later, A's proposals to talk about) |
| **D · Board & demo** | Board summary template for 5.2, weekly room grid generator, slides | fill them with A's results | A's proposals |

With 3 people, B and D merge into one role.

## 3. How we work in git without breaking each other's work

**Golden rules**

1. **Never commit on `main`.** One branch per task: `nivell2/p51-aules`, `nivell3/assistent`, `docs/...`.
2. **Work only inside your folder** (table above). Shared files (`PLAN.md`, `SETUP.md`, `requirements.txt`,
   `.gitignore`) are changed in small separate commits, and you say so in the group chat.
3. **Never commit the data** (`paquet/`, `planols/`, PDFs, exported HTML). `.gitignore` already blocks them; never use
   `git add -f`.
4. **Pull `main` often** so your branch doesn't drift.
5. New library? Add it **with its version** to `requirements.txt` in its own commit and tell the team to reinstall.

**Day-to-day commands**

Start a task (once):
```bash
git checkout main
git pull
git checkout -b nivell2/p51-aules
```

Save your work (as often as you like):
```bash
git add nivell2/p51_aules
git commit -m "5.1: greedy room assignment, valid with --nomes-aules"
git push -u origin nivell2/p51-aules
```

Bring in what others merged:
```bash
git pull origin main
```

When the task is ready: open a **Pull Request** on GitHub (branch → `main`), ask someone to look at it, and merge it.
After merging, delete the branch and start the next task from an updated `main`.

**Repo access:** the repo is private. Each teammate needs an invitation: GitHub → repo → Settings → Collaborators →
Add people.

## 4. Shared conventions

- **Run everything from the repo root** with the `.venv` active.
- **Calling the verifier from Python** (faster than the command line when iterating):
  ```python
  import sys; sys.path.insert(0, 'repte-horaris-escola')
  from horaris.model import carrega_base, llegeix_proposta
  from horaris.check import avalua
  base = carrega_base('repte-horaris-escola/paquet', semestre=2)
  # keep only semester-2 rows: the command line does this for you, avalua() does not
  # (otherwise every semester-1 row counts as an R0-FORMAT error)
  files = [f for f in llegeix_proposta('lliuraments/proposta-aules.csv') if f.id in base.sessions]
  inf = avalua(base, files, nomes_aules=True)
  print(inf.veredicte, inf.recompte())
  ```
- **Reuse `nivell1/analisi.py`** for loading data and counting (shared sessions once, double degrees without room,
  morning/afternoon by start time…): same conventions as the verifier.
- **Plan by activity, not by session**: the 1,930 `activitat_id` repeat every week at the same day and hour. Decide
  per activity, then expand to its sessions. Shared sessions (`id_compartida`) always move together.
- **Final files** go to `lliuraments/` with the names the statement uses (`proposta-aules.csv`,
  `proposta-torns.csv`, `proposta-imprevist.csv`, `proposta-grau-nou.csv`, `relaxacions.csv`) plus each one's
  `informe-*.json` and `violacions-*.csv`.
- Jury-facing text (notebooks, findings, board summary) in **Catalan**; internal docs like this one can be in English.
- **Data rules:** pseudonymised data, hackathon only. Don't publish it, don't upload it to external services or
  AIs; for L3 use the event's LLM.

## 5. Ideas for later (only if there is time)

- 2D map of the 21 classrooms (4 spines × 2 floors, from the table on page 5 of the statement) coloured by
  occupancy or group: useful for the board summary and the L3 demo. A 3D model from `planols/` is not worth it.
- Section 6 of L1 as soon as the organisers share the GERES file.
- Translate `SETUP.md` / this plan to Catalan if the team prefers.
