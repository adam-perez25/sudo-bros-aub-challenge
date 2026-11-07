# Setup — do this once on your computer

You need **Python 3.11 or newer** (check with `python --version`; on Windows you can also use `py --version`).
If you don't have it, install it from https://www.python.org/downloads/ (on Windows tick **"Add Python to PATH"**).

## 1. Get the code

```bash
git clone https://github.com/adam-perez25/sudo-bros-aub-challenge.git
cd sudo-bros-aub-challenge
```

## 1b. Get the data (NOT in GitHub)

The challenge data is pseudonymised and only for the hackathon: it must **not** be published or uploaded
anywhere (GitHub included), so it is in `.gitignore` and you have to add it yourself:

1. Download the material from the organisers' SharePoint folder (link in the event message): the data zip, the
   floor plans (`planols`) and the PDFs.
2. Unzip it and copy the **`paquet`** folder into `repte-horaris-escola/`, so you end up with
   `repte-horaris-escola/paquet/sessions.csv`, `aules.csv`, …
3. Optional: put `planols/` and the PDFs in the project root (they are ignored by git too).
4. Optional (level 1, section 6): if you have the real-occupancy file `geres-ocupacio-setmana-2026-10-05.csv`, put it
   in `repte-horaris-escola/validacio/`. Without it, that section of the notebook just says the file is missing.

Never `git add -f` these files, and never paste the data into external AI tools: for level 3 use the event's LLM.

## 2. Create the virtual environment (only the first time)

A virtual environment is a private folder (`.venv`) with the libraries for this project, so they don't mix
with anything else on your computer. It is **not** uploaded to GitHub: everyone creates their own.

Windows (PowerShell):
```powershell
py -m venv .venv
```

macOS / Linux:
```bash
python3 -m venv .venv
```

## 3. Activate it (every time you open a new terminal)

Windows (PowerShell):
```powershell
.venv\Scripts\Activate.ps1
```
If PowerShell says scripts are disabled, run this once and try again:
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

Windows (cmd):
```
.venv\Scripts\activate.bat
```

macOS / Linux:
```bash
source .venv/bin/activate
```

When it works, the prompt starts with `(.venv)`.

## 4. Install the libraries (first time, and whenever requirements.txt changes)

```bash
python -m pip install -r requirements.txt
```

## 5. Check that everything works

```bash
cd repte-horaris-escola
python -m horaris check paquet/proposta_partida.csv --semestre 2
```

It must print `Veredicte: NO VALIDA` with `R5-SENSE-AULA 4541`: that is today's timetable, our starting point.
On Windows, if you see strange characters, first run `$env:PYTHONUTF8=1` (PowerShell) or `set PYTHONUTF8=1` (cmd).

## Rules for the team

- Always activate `.venv` before running anything.
- Need a new library? `python -m pip install <name>`, then add it **with its version** to `requirements.txt`
  (`python -m pip show <name>` tells you the version) and commit that file, so everyone gets it.
- Never commit the `.venv` folder (it is already in `.gitignore`).
- In VS Code: `Ctrl+Shift+P` → "Python: Select Interpreter" → choose the one inside `.venv`.
