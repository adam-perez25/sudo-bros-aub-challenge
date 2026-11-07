"""Level 1 analysis: how are the School's rooms used today, and does the new shift model fit?

All the calculations live here so the notebook (nivell1.ipynb) only calls them and draws charts.
Run from the project root or from this folder; the data is read from repte-horaris-escola/paquet/.

Conventions (the same as the official verifier, repte-horaris-escola/horaris/check.py):
- Semester by date: Sep-Jan = 1, Feb-Aug = 2 (the Sigma T/V field is not reliable).
- Shift (torn) is decided by the start time: before 14:30 = morning.
- A shared session (same id_compartida) is ONE physical class: counted once for room usage.
- Double-degree groups (sense_espai = 1) need no room: left out of room demand.
- PLAB labs are fixed and use department labs: left out of classroom demand.
- Hour slots ("franges") for the 2-free-rooms reserve rule: every hour from 8:30 to 20:30.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PAQUET = ROOT / 'repte-horaris-escola' / 'paquet'

DIES = ['L', 'M', 'X', 'J', 'V']
NOM_DIA = {'L': 'Mon', 'M': 'Tue', 'X': 'Wed', 'J': 'Thu', 'V': 'Fri'}
MATI_FI = 14 * 60 + 30                          # 14:30, end of the morning window
FRANGES = [8 * 60 + 30 + 60 * i for i in range(13)]   # 8:30, 9:30, ... 20:30
FRANGES_MATI = [f for f in FRANGES if f < MATI_FI]     # 6 morning slots
RESERVA = 2                                     # ordinary rooms that must stay free (rule 8)
CLASSROOM_TYPES = {'Aules docents', 'Seminaris'}
PRACTICE_TYPES = {'Laboratoris docents', 'Aules informàtiques'}


def hm(s: str) -> int:
    h, m = s.split(':')
    return int(h) * 60 + int(m)


def fmt(m: int) -> str:
    return f'{m // 60:02d}:{m % 60:02d}'


# ----------------------------------------------------------------------------------------------- loading
def carrega(paquet: Path = PAQUET) -> tuple[pd.DataFrame, pd.DataFrame]:
    """sessions and rooms, with a few helper columns added to sessions."""
    s = pd.read_csv(paquet / 'sessions.csv', dtype=str, keep_default_na=False)
    a = pd.read_csv(paquet / 'aules.csv')
    for c in ('durada_min', 'alumnes', 'capacitat_grup'):
        s[c] = pd.to_numeric(s[c], errors='coerce').fillna(0).astype(int)
    s['date'] = pd.to_datetime(s['data'])
    s['smt'] = s['date'].dt.month.map(lambda m: 1 if m >= 9 or m == 1 else 2)
    s['ini'] = s['h_ini'].map(hm)
    s['fi'] = s['ini'] + s['durada_min']
    s['unitat'] = s['id_compartida'].where(s['id_compartida'] != '', s['id_sessio'])
    s['doble'] = s['sense_espai'] == '1'
    s['torn_actual'] = s['ini'].map(lambda m: 'mati' if m < MATI_FI else 'tarda')
    s['fora_torn'] = s['torn_actual'] != s['torn_requerit']
    s['curs'] = s['titulacions_curs'].map(_curs)
    tipus_aula = dict(zip(a['aula'], a['tipus']))
    s['tipus_aula'] = s['aula_partida'].map(lambda x: tipus_aula.get(x, 'sense aula' if not x else 'fora aulari'))
    return s, a


def _curs(tc: str) -> str:
    """'GEI:3r|GEI:4t' -> '3r/4t'; the year(s) of the session."""
    cursos = sorted({x.split(':')[1] for x in tc.split('|') if ':' in x})
    return '/'.join(cursos) or '?'


def explode_cohorts(s: pd.DataFrame) -> pd.DataFrame:
    """One row per (session, cohort): a session of 'GEI:3r|GEI:4t' counts for both cohorts."""
    e = s.assign(cohort=s['titulacions_curs'].str.split('|')).explode('cohort')
    e['titulacio'] = e['cohort'].str.split(':').str[0]
    e['curs_c'] = e['cohort'].str.split(':').str[1]
    return e


def demanda_aula(s: pd.DataFrame, inclou_practiques: bool = False) -> pd.DataFrame:
    """Sessions that need a classroom (ordinary room or seminar), one row per physical class.

    Left out: PLAB (fixed department labs), double-degree groups (no room needed), sessions in rooms
    outside the building that may stay there (B3/0021, QC/1082) and, unless `inclou_practiques`, sessions
    that today are in a lab / computer room (PAUL that do everything there and can keep doing so).
    The statement's 67-70 % figure uses inclou_practiques=True."""
    d = s[(s['tipus'] != 'PLAB') & ~s['doble']]
    ok = d['tipus_aula'].isin(CLASSROOM_TYPES | {'sense aula'}) | d['aula_partida'].str.startswith('J/')
    if inclou_practiques:
        ok |= d['tipus_aula'].isin(PRACTICE_TYPES)
    return d[ok].drop_duplicates('unitat')


# ---------------------------------------------------------------------------------------- 1. occupancy
def ocupacio_aules(s: pd.DataFrame, a: pd.DataFrame, smt: int) -> pd.DataFrame:
    """Share of teaching weeks in which each room is busy, per weekday and hour slot (0-1).

    Rows = rooms of the building (sorted by type and capacity), columns = (day, slot)."""
    x = s[(s['smt'] == smt) & (s['aula_partida'] != '')]
    files = []
    for r in x.itertuples():
        for f0 in FRANGES:
            if r.ini < f0 + 60 and r.fi > f0:
                files.append((r.aula_partida, r.data, r.dia, f0))
    occ = pd.DataFrame(files, columns=['aula', 'data', 'dia', 'franja']).drop_duplicates()
    # how many dates with classes each weekday has (the denominator)
    dates = s[s['smt'] == smt].groupby('dia')['data'].nunique()
    t = occ.groupby(['aula', 'dia', 'franja']).size().unstack(['dia', 'franja'], fill_value=0)
    cols = pd.MultiIndex.from_product([DIES, FRANGES], names=['dia', 'franja'])
    t = t.reindex(columns=cols, fill_value=0)
    t = t.div([dates.get(d, 1) for d, _ in t.columns], axis=1)
    ordre = a.sort_values(['tipus', 'capacitat'], ascending=[True, False])['aula']
    return t.reindex([x for x in ordre if x in t.index] + [x for x in t.index if x not in set(ordre)]).fillna(0)


def resum_aules(s: pd.DataFrame, a: pd.DataFrame, smt: int) -> pd.DataFrame:
    """Per room: average occupancy over the whole week (morning, afternoon, total) and capacity."""
    o = ocupacio_aules(s, a, smt)
    mati = o.loc[:, [c for c in o.columns if c[1] < MATI_FI]].mean(axis=1)
    tarda = o.loc[:, [c for c in o.columns if c[1] >= MATI_FI]].mean(axis=1)
    r = pd.DataFrame({'ocup_mati': mati, 'ocup_tarda': tarda, 'ocup_total': o.mean(axis=1)})
    return r.join(a.set_index('aula')[['tipus', 'capacitat']], how='left').sort_values('ocup_total', ascending=False)


# ------------------------------------------------------------------------------- 2. sessions without room
def sense_aula(s: pd.DataFrame, smt: int) -> pd.Series:
    """Why sessions have no room: PLAB (department labs), double degree (no room needed) or really missing."""
    x = s[(s['smt'] == smt) & (s['aula_partida'] == '')]
    motiu = pd.Series('needs a room', index=x.index)
    motiu[x['doble'] & (x['tipus'] != 'PLAB')] = 'double degree (no room needed)'
    motiu[x['tipus'] == 'PLAB'] = 'PLAB (department lab, fixed)'
    return motiu.value_counts()


def simultanies(s: pd.DataFrame, smt: int, filtre=None) -> pd.DataFrame:
    """Number of classes needing a classroom at the same time, per date and hour slot.

    Returns one row per (date, slot) with: total, with_room, without_room."""
    d = demanda_aula(s[s['smt'] == smt])
    if filtre is not None:
        d = d[filtre(d)]
    files = []
    for r in d.itertuples():
        for f0 in FRANGES:
            if r.ini < f0 + 60 and r.fi > f0:
                files.append((r.data, r.dia, f0, r.aula_partida != ''))
    x = pd.DataFrame(files, columns=['data', 'dia', 'franja', 'amb_aula'])
    g = x.groupby(['data', 'dia', 'franja'])['amb_aula'].agg(total='size', amb_aula='sum').reset_index()
    g['sense_aula'] = g['total'] - g['amb_aula']
    return g


# ------------------------------------------------------------------------------------- 3. wrong shift
def fora_de_torn(s: pd.DataFrame, smt: int) -> pd.DataFrame:
    """Sessions today in the shift that the new model does NOT give them, per degree and year.

    A session of two cohorts counts once for each. 'movable' excludes fixed groups (R1 GEI/GEET 1r-2n and
    PLAB), which cannot be moved and so are not the proposal's fault."""
    e = explode_cohorts(s[s['smt'] == smt])
    e['fora_torn_movible'] = e['fora_torn'] & (e['fixada'] == '')
    g = e.groupby(['titulacio', 'curs_c']).agg(
        sessions=('id_sessio', 'size'),
        fora_torn=('fora_torn', 'sum'),
        fora_torn_movibles=('fora_torn_movible', 'sum'),
        torn_requerit=('torn_requerit', lambda v: '/'.join(sorted(set(v)))))
    g['pct_fora_torn'] = (100 * g['fora_torn'] / g['sessions']).round(1)
    return g.reset_index().sort_values('fora_torn', ascending=False)


# --------------------------------------------------------------------------------- 4. does the morning fit?
def setmanes_normals(s: pd.DataFrame, smt: int, paquet: Path = PAQUET) -> list[str]:
    """Teaching weeks with 5 days of classes and no event in calendari.csv (holiday, stoppage, assessment)."""
    cal = pd.read_csv(paquet / 'calendari.csv')
    amb_event = set(pd.to_datetime(cal['data']).dt.strftime('%G-W%V'))
    x = s[s['smt'] == smt]
    dies = x.groupby('setmana')['data'].nunique()
    return [w for w, n in dies.items() if n == 5 and w not in amb_event]



def hores_aula_setmana(s: pd.DataFrame, smt: int, torn: str) -> pd.DataFrame:
    """Room-hours per week that the sessions of a required shift ask for, against what the building offers.

    Offer = (21 ordinary rooms - 2 reserve) x hours of the window x teaching days of that week.
    Demand = sum of durations of the classes (one per physical class) whose torn_requerit is `torn`."""
    x = s[s['smt'] == smt]
    dies_lectius = x.groupby('setmana')['data'].nunique()
    d = demanda_aula(x)
    d = d[d['torn_requerit'] == torn]
    dem = d.groupby('setmana')['durada_min'].sum() / 60
    dem_ara = d[d['torn_actual'] == torn].groupby('setmana')['durada_min'].sum() / 60
    hores = 6 if torn == 'mati' else 6.5
    oferta = dies_lectius * (21 - RESERVA) * hores
    t = pd.DataFrame({'dies_lectius': dies_lectius, 'demanda_h': dem, 'demanda_ja_al_torn_h': dem_ara,
                      'oferta_h': oferta}).fillna(0)
    t['normal'] = t.index.isin(setmanes_normals(s, smt))
    t['ocupacio_pct'] = (100 * t['demanda_h'] / t['oferta_h']).round(1)
    t['ocupacio_ja_al_torn_pct'] = (100 * t['demanda_ja_al_torn_h'] / t['oferta_h']).round(1)
    return t


def mida_mati(s: pd.DataFrame, a: pd.DataFrame, smt: int, setmana: str) -> pd.DataFrame:
    """Size check for one week: morning classes that need at least N seats vs rooms with at least N seats.

    For each room size N: room-hours demanded by morning-required classes with more than the next smaller
    room's capacity, against (rooms >= N) x 6 h x days. If demand > offer for some N, the morning cannot fit
    whatever the timetable (a counting argument). The 2 reserve rooms are taken from the smallest ones,
    the most favourable case for big classes."""
    x = s[(s['smt'] == smt) & (s['setmana'] == setmana)]
    dies = x['data'].nunique()
    d = demanda_aula(x)
    d = d[d['torn_requerit'] == 'mati']
    caps = sorted(a.loc[a['ordinaria'] == 1, 'capacitat'])
    caps_disp = caps[RESERVA:]   # the 2 smallest rooms kept as reserve
    files = []
    for n in sorted(set(caps_disp)):
        aules = sum(1 for c in caps_disp if c >= n)
        menor = max([c for c in caps_disp if c < n], default=0)
        dem = d.loc[d['alumnes'] > menor, 'durada_min'].sum() / 60 if menor else d['durada_min'].sum() / 60
        files.append({'seats_at_least': n, 'classes_with_more_than': menor, 'rooms_available': aules,
                      'demand_h': round(dem, 1), 'offer_h': aules * 6 * dies,
                      'use_pct': round(100 * dem / (aules * 6 * dies), 1)})
    return pd.DataFrame(files)


# ------------------------------------------------------------------------------------- 5. over capacity
def sobre_aforament(s: pd.DataFrame, a: pd.DataFrame, smt: int) -> pd.DataFrame:
    """Groups with more students than seats in today's room (one physical class: students summed)."""
    cap = dict(zip(a['aula'], a['capacitat']))
    x = s[(s['smt'] == smt) & (s['aula_partida'].isin(cap)) & ~s['doble']]
    g = x.groupby(['unitat', 'aula_partida']).agg(
        alumnes=('alumnes', 'sum'), codi=('codi', 'first'), assignatura=('assignatura', 'first'),
        grup=('grup', 'first'), tipus=('tipus', 'first'), fixada=('fixada', 'first'),
        titulacions=('titulacions_curs', 'first'), dia=('dia', 'first'), h_ini=('h_ini', 'first')).reset_index()
    g['capacitat'] = g['aula_partida'].map(cap)
    g = g[g['alumnes'] > g['capacitat']]
    g['excés'] = g['alumnes'] - g['capacitat']
    return g.groupby(['codi', 'assignatura', 'grup', 'tipus', 'aula_partida', 'fixada', 'titulacions']).agg(
        sessions=('unitat', 'size'), alumnes=('alumnes', 'max'), capacitat=('capacitat', 'first'),
        excés=('excés', 'max')).reset_index().sort_values('excés', ascending=False)
