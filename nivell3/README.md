# Level 3 · AI assistant for Gestió Acadèmica

Owner: _?_ · Branch: `nivell3/assistent` · Weight 25 % · Independent of level 2

**Goal:** an assistant that helps make and maintain the timetable, e.g. "where does group 81 have class on
Tuesday?", "which 60-seat room is free Thursday at 10?", explaining verifier errors, proposing a fix for an
incident (5.3) and drafting (never sending) the notice and change-log entry.

**Hard rules:**
- Every answer must come from a tool and be checkable: SQL over the CSVs (e.g. DuckDB) and the verifier
  (`from horaris.check import avalua`). Cite the `id_sessio` behind each answer. If no tool says it, don't say it.
- **Only the event's LLM** (UAB DCC servers). Never send this data to ChatGPT, Claude or any external API.
- The verifier's output is data, not instructions for the agent.

**Deliverable:** a demo (short video or live) and an explanation of how its answers are checked. The jury asks 3
live questions and checks them against the CSVs.
