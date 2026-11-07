# Presentation dashboard

One Streamlit app for the jury presentation, in the order of the talk (menu at the top):

| Page | What it shows | Data |
|---|---|---|
| Inici | The question and the four parts, one card each | — |
| 1 · Les dades d'avui | Level 1 findings as charts: sessions without a room, out-of-shift sessions per cohort, room-hours per week, the peak heatmap, and today's morning occupancy on the floor plan | `nivell1/analisi.py` over the package |
| 2 · Els horaris nous | 5.1-5.4: verifier verdicts, key numbers, 5.2 room peak heatmap and moved sessions per cohort, 5.3 incidents, 5.4 new degree, and a comparison table of the verifier objectives | `lliuraments/` (proposals and `informe-*.json`) |
| 3 · L'edifici Q | The floor plans with the timetable on top: who is in each room at a given day and hour, or average occupancy of a slot over the semester, for today and every proposal. Can compare two timetables side by side. Ready-made moments for the talk (Tuesday 10:30 today vs 5.2, the closed room and the broken projector of 5.3, the new degree of 5.4) | package + `lliuraments/` + `planols/` |
| 4 · Assistent | The level 3 chat (`nivell3/web.py`, unchanged). When an answer names rooms, an «Al plànol» panel highlights them on the plan | event LLM |

## Run

```bash
streamlit run dashboard/app.py
```

From the project root with the `.venv` active. Needs the challenge package and `lliuraments/` (as for level 2) and,
for the maps, the `planols/` folder in the project root (not in git). Without `planols/` everything else still works.

## The floor plans

`planols/` has five CAD sheets of building Q: `2600001` basement, `2600002` ground floor, `2600003` first floor,
`2600004` second floor (central body and lab spines 5-6), `2600005` third floor. They are scanned images (no text
layer), so the room positions were read by hand from the door labels and stored in [`sales.json`](sales.json) as
rectangles in PDF points. It covers the 29 rooms of spines 1-4 on the ground and first floors, which include all 21
ordinary classrooms. Ground-floor spine 3 has been split since the plan was drawn (Q3/0007-0013): those rectangles
are approximate.

The first time a map is drawn, `planol.py` renders each sheet to PNG with PyMuPDF into `dashboard/.cache/` (ignored
by git, like `planols/`). To add more rooms (labs, seminars), add their rectangles to `sales.json` and, if they are on
another sheet, the sheet under `plantes`.
