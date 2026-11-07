# Level 1 · The five key findings

**Question:** how are the School's rooms used today, and does the new model fit
(1st/2nd year in the morning; 3rd, 4th, double degrees and master's in the afternoon; 2 ordinary rooms always free)?

**Short answer:** **yes, the morning fits, but only if the peak hours are spread out.** The weekly total is not the
problem (about 60 % of the morning room-hours); the problem is Tuesday and the 10:30-13:30 slots. Room size is not a
bottleneck, and the afternoon is left with a lot of spare capacity.

All figures are for **semester 2** (the one level 2 works on) unless stated otherwise. They come from
[`analisi.py`](analisi.py) and are drawn in [`nivell1.ipynb`](nivell1.ipynb), with the same conventions as the
official verifier: semester by date, shift by start time (before 14:30 = morning), a shared session counted once,
double-degree groups (`sense_espai = 1`) need no room, PLAB labs are fixed. "Usable rooms" = 21 ordinary classrooms
minus the 2 that must stay free = **19**. "Normal week" = 5 teaching days and nothing in `calendari.csv`
(11 of the 20 weeks).

---

### 1. The data hides three quarters of the room demand: 74 % of sessions have no room

- **5,722 of 7,739** semester-2 sessions have an empty `aula_partida`. Of those, **919 are PLAB** (department labs,
  fixed, assigned by departments) and **262 are double-degree groups** (no room needed): **4,541 really need a room.**
- Because of this, the ordinary classrooms *look* 23 % busy in the morning and 4 % in the afternoon in semester 2,
  against 50 % and 27 % in semester 1. Rooms like Q2/1009 and Q2/1013 (90 seats) look almost unused.
- **How:** `sense_aula()` classifies the empty-room sessions by `tipus` and `sense_espai`; `ocupacio_aules()` counts,
  for each room and hour slot, the share of teaching weeks it is busy (heatmap, section 1 of the notebook).
- **Why it matters:** any "this room is free" conclusion drawn from semester-2 room data is wrong. Real demand must be
  counted from the sessions, not from the rooms (finding 3).

### 2. 3,246 sessions are in the wrong shift; 2,008 can be moved, mainly 3rd and 4th year to the afternoon

- **2,008 movable**: 1,774 must go to the afternoon, 234 to the morning. 248 of them are double-degree sessions taught
  today together with a morning group: candidates for a declared exception.
- By cohort (share of that cohort's sessions in the wrong shift): **GEI 3r 89 %, GEI 4t 92 %, GEST 3r 99 %,
  GEET 3r 98 %, GEQ 3r 100 %** (to the afternoon); **GCIS 2n 100 %, GIA 1r 100 %, GIA 2n 100 %** (to the morning).
- **1,238 are fixed** and can never comply: **600 GEI 1r/2n class sessions** ("not touched"; 573 of them in the
  afternoon, plus 27 double-degree sessions in the morning) and **638 fixed PLAB labs** in the other shift
  (349 GEI 3r/4t labs in the morning; 148 GEI 1r/2n and 94 GIA 1r/2n labs in the afternoon; 47 GEET/GEST).
  The verifier calls them inherited, but they are real exceptions to rule 1 that the Junta should know about.
- **How:** `fora_torn` = start time on the wrong side of 14:30 compared with `torn_requerit`; `fora_de_torn()` splits it
  per degree and year (a session shared by two cohorts counts for both); movable = `fixada` empty. The 2,008 total
  matches the verifier's R1-TORN count.

### 3. The morning fits on paper: the new model needs ~60 % of the morning room-hours

- In normal weeks, 1st and 2nd year need **59-64 % of the morning room-hours** of the 19 usable rooms
  (19 rooms x 6 h x 5 days = 570 room-hours/week), up from 47-52 % with only the classes already in the morning.
  With the statement's definition (also counting classes in computer rooms) it is 64-70 %, matching the 67-70 % quoted.
- That is **12.2 classes at once on average** against the limit of 19 (week 2027-W06).
- Each student subgroup has **at most 20 h** of class a week against the 30 morning hours: the student timetables
  are not the limit either.
- The afternoon (3rd, 4th, master's) is left at **35-40 %**: plenty of spare room.
- **How:** `hores_aula_setmana()` adds up the durations of the classes that need a classroom (one per physical class;
  no PLAB, no double degrees, not the ones that can stay in a lab or computer room) per week, and divides by the offer.

### 4. The real limit is the peak: Tuesday and 10:30-13:30 are already at 15 of 19

- With today's hours, the 1st/2nd-year classes already in the morning reach **15 at once** (Tuesday 10:30). Keeping
  today's weekdays, Tuesday would average **14.5 classes at once** over the whole morning, against 10.8 on Wednesday.
- Even today's timetable (all shifts) needs **more than 19 classrooms in 23 of 894** semester-2 hour slots (up to 21,
  at Tue 10:30 and 16:30): small groups already have to go to seminars.
- **Implication for 5.2:** the classes that come to the morning must go to the quiet days and hours (Wednesday,
  Friday, 8:30), not to the slots they would naturally take.
- **How:** `simultanies()` counts, for each date and hour slot, the classes that need a classroom at the same time
  (with the verifier's overlap rule), then takes the maximum per slot.

### 5. Room size is not a bottleneck; only 2 movable groups are over capacity today

- Counting check for a normal week: for every room size N, the morning classes that need at least N seats use at most
  **33 %** of the room-hours of the rooms with at least N seats (2 reserve rooms taken from the smallest). Classes of
  more than 117 students need 2 room-hours a week out of the 90 offered by the three 130-160 rooms.
- **101 sessions (6 groups)** have more students than seats in today's room, but **58 are fixed** GEI PAUL groups only
  1-2 students over a 48-50 seat room (inherited). The **43 movable** ones are two groups, both easy to fix:
  - **Física TE/21 (GEQ 1r): 125 students in Q4/0011 (117 seats)** -> Q1/1011 (160), Q3/1007 or Q3/1011 (130).
  - **Sistemes i Tecnologies Web TE/450 (GEI 3r/4t): 103 in Q3/0003 (100)** -> any 117+ room.
- **How:** `mida_mati()` (demand vs offer by size class) and `sobre_aforament()` (students of a physical class summed
  and compared with the capacity in `aules.csv`; the 43 and 58 match the verifier's R3-AFORAMENT counts).

---

**Not done:** the "plan vs reality" comparison with `validacio/`: the real-occupancy CSV is not in the package we
received (only its README).
