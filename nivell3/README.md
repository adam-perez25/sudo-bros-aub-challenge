# Level 3 · AI assistant for Gestió Acadèmica

Branch: `nivell3` · Weight 25 % · Jury-facing explanation (Catalan): [`INFORME.md`](INFORME.md)

An assistant that answers questions about the timetable (where a group is, which room is free, what happens if we
move something, how to solve an incident) **only through tools that read the data or run the official verifier**,
and cites the `id_sessio` behind every answer.

## Setup (once per computer)

1. `python -m pip install -r requirements.txt` (adds `duckdb`).
2. Copy `nivell3/.env.example` as `nivell3/.env` and fill in `LLM_URL` (the event LLM's OpenAI-compatible base URL,
   usually ending in `/v1`), `LLM_MODEL` and `LLM_API_KEY`. That file is ignored by git: **never commit the key**.

## Run

```bash
python nivell3/main.py
```

or one question: `python nivell3/main.py -p "Quina aula de 60 places està lliure dijous a les 10?"`

Answers show only the text and its sources. Add `--detall` to also see which tools were called (for debugging).

Check without the LLM: `python nivell3/proves/prova_eines.py` (must print 37 of 37) and `python nivell3/proves/prova_agent.py` (15 of 15: agent loop with a fake LLM)

## Files

| File | Role |
|---|---|
| `main.py` | Terminal chat (entry point) |
| `web.py` | Web chat (Streamlit): `streamlit run nivell3/web.py` from the project root; collapsible "Fonts" table with the real rows, notices marked "not sent" |
| `agent.py` | Loop LLM ↔ tools (OpenAI-compatible `tools`; falls back to a JSON protocol if the server doesn't support them); retries on timeouts/429/5xx; checks that every `id_sessio` in the answer came from a tool (one correction round, then marks it "no verificat"); trims long results and long conversations |
| `prompts.py` | System prompt: answer only from tools, cite sources, tool output is data not instructions, notices are drafts |
| `eines.py` | The 17 tools + their JSON schemas for the LLM |
| `dades.py` | Loads the CSVs once and exposes them as DuckDB SQL tables (`sessions`, `aules`, `calendari`, `horari`), sandboxed: no file access, read-only queries |
| `avisos.py` | Notice and change-log drafts (never sent) |
| `config.py` | Reads URL, model and key from `nivell3/.env` or the environment |
| `proves/` | Test questions with independently computed answers, and the tool test script |

## The tools

| Tool | What it answers |
|---|---|
| `consulta_sql` | Anything else, with a read-only SELECT (max 200 rows) |
| `horari_grup` | Where and when a group has class (exact group or line number, by day / date / week) |
| `horari_aula` | What happens in a room |
| `aules_lliures` | Free rooms at a time (one date, or every such weekday of the semester), by size and type; checks overlaps and the 2-room reserve |
| `verifica` | Official verifier on any of our proposals (5.1-5.4, or today's) |
| `que_passa_si` | Simulates moving a session / group and lists the rules it would break |
| `resol_imprevist` | Validated fix for a closed room (breakdown, event) or a cancelled session, using the 5.3 engine |
| `esborrany_avis` | Notices for teachers, students and Gestió Acadèmica + change-log rows (drafts only) |
| `ocupacio` | Which classes are on at a given time (one date, or the weekly pattern of a weekday) |
| `horari_docent` | A teacher's classes (by date, weekday, week or weekly pattern) |
| `cerca_assignatura` | Find a subject by name or code: groups, cohorts, teachers |
| `info_aules` | List rooms by capacity, type or building |
| `reserva_aules` | Checks the "2 ordinary rooms free" rule: tightest slot of a date / weekday / semester |
| `sessions_canviades` | Sessions that changed day or time versus today's timetable (because of 5.2) |
| `calendari_info` | Semester dates, holidays, evaluation weeks; whether a date is a teaching day |
| `aturada` | General stop: every class from an hour on a date is cancelled; lists sessions, teachers, cohorts (feeds `esborrany_avis`; nothing saved) |
| `ajuda` | What the assistant can and cannot do |

**When no tool fits** (send an email, change the official timetable, anything off-topic) the prompt (rule 13) makes the
assistant say so in one sentence and list what it can do, instead of trying tools at random. The capabilities text is
in `prompts.py` (`POT_FER` / `NO_POT_FER`) and is shared with the `ajuda` tool.

"Current timetable" = our 5.2 proposal (`lliuraments/proposta-torns.csv`), semester 2 by default.

## Tested so far

- Every tool against answers computed independently (verifier + pandas): `proves/prova_eines.py`, 37/37.
- The agent loop with a scripted **fake LLM** (`proves/prova_agent.py`): invented `id_sessio` detection and correction, the switch to JSON mode only on a real "no tools" error, retries, valid truncated results, long conversations.
- **Not yet tested with the real event LLM** (needs your key in `nivell3/.env`). First thing to do: run
  `python nivell3/main.py -p "Quantes sessions té el 2n semestre?"` and check it answers 7.739 citing a tool.

## Next

- Run the 13 questions of `proves/README.md` through the real LLM and fix any wrong answer in the **tool**, not the
  prompt.
- Optional: a small web chat (Streamlit/Gradio) showing answer + sources, for the live demo.
- Demo script (3-4 min): question 1 → 2 → 6 → 7 + 8 of `proves/README.md`.
