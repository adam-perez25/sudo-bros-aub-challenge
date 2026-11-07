# Setup — do this once on your computer

You need **Python 3.11 or newer** (check with `python --version`; on Windows you can also use `py --version`).
If you don't have it, install it from https://www.python.org/downloads/ (on Windows tick **"Add Python to PATH"**).

## 1. Get the code

```bash
git clone https://github.com/adam-perez25/sudo-bros-aub-challenge.git
cd sudo-bros-aub-challenge
```

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
