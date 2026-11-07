"""Nivell 1: com s'usen avui les aules de l'Escola, i hi cap el model nou de torns?

Tots els càlculs són aquí, perquè el quadern (nivell1.ipynb) només els cridi i en dibuixi els gràfics.
Les dades es llegeixen de repte-horaris-escola/paquet/.

Convencions (les mateixes que el verificador oficial, repte-horaris-escola/horaris/check.py):
- Semestre per data: de setembre a gener = 1, de febrer a agost = 2 (el camp T/V de Sigma no és fiable).
- El torn el marca l'hora d'inici: abans de les 14.30 = matí.
- Una sessió compartida (mateix id_compartida) és UNA sola classe física: compta un cop per a l'ús d'aules.
- Els grups de doble titulació (sense_espai = 1) no necessiten aula: queden fora de la demanda d'aules.
- Els laboratoris PLAB estan fixats i van a laboratoris de departament: queden fora de la demanda d'aules.
- Franges d'una hora per a la reserva de dues aules lliures (regla 8): cada hora de 8.30 a 20.30.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PAQUET = ROOT / 'repte-horaris-escola' / 'paquet'

DIES = ['L', 'M', 'X', 'J', 'V']
NOM_DIA = {'L': 'Dl', 'M': 'Dt', 'X': 'Dc', 'J': 'Dj', 'V': 'Dv'}
MATI_FI = 14 * 60 + 30                                  # 14.30, final de la finestra de matí
FRANGES = [8 * 60 + 30 + 60 * i for i in range(13)]     # 8.30, 9.30, ... 20.30
FRANGES_MATI = [f for f in FRANGES if f < MATI_FI]      # les 6 franges de matí
RESERVA = 2                                             # aules ordinàries que han de quedar lliures (regla 8)
TIPUS_AULA = {'Aules docents', 'Seminaris'}
TIPUS_PRACTIQUES = {'Laboratoris docents', 'Aules informàtiques'}


def hm(s: str) -> int:
    h, m = s.split(':')
    return int(h) * 60 + int(m)


def fmt(m: int) -> str:
    return f'{m // 60:02d}:{m % 60:02d}'


# ------------------------------------------------------------------------------------------- càrrega
def carrega(paquet: Path = PAQUET) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Sessions i aules, amb unes quantes columnes d'ajuda afegides a les sessions."""
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
    """'GEI:3r|GEI:4t' -> '3r/4t': el curs o cursos de la sessió."""
    cursos = sorted({x.split(':')[1] for x in tc.split('|') if ':' in x})
    return '/'.join(cursos) or '?'


def explode_cohorts(s: pd.DataFrame) -> pd.DataFrame:
    """Una fila per (sessió, cohort): una sessió de 'GEI:3r|GEI:4t' compta per a totes dues cohorts."""
    e = s.assign(cohort=s['titulacions_curs'].str.split('|')).explode('cohort')
    e['titulacio'] = e['cohort'].str.split(':').str[0]
    e['curs_c'] = e['cohort'].str.split(':').str[1]
    return e


def demanda_aula(s: pd.DataFrame, inclou_practiques: bool = False) -> pd.DataFrame:
    """Sessions que necessiten una aula (aula docent o seminari), una fila per classe física.

    Queden fora: els PLAB (laboratoris de departament, fixats), els grups de doble titulació (no necessiten
    aula), les sessions en aules de fora de l'aulari que s'hi poden quedar (B3/0021, QC/1082) i, si no es
    demana `inclou_practiques`, les sessions que avui són en un laboratori o aula d'informàtica (PAUL que hi
    fan tota la docència i s'hi poden quedar). La xifra del 67-70 % de l'enunciat correspon a
    inclou_practiques=True."""
    d = s[(s['tipus'] != 'PLAB') & ~s['doble']]
    ok = d['tipus_aula'].isin(TIPUS_AULA | {'sense aula'}) | d['aula_partida'].str.startswith('J/')
    if inclou_practiques:
        ok |= d['tipus_aula'].isin(TIPUS_PRACTIQUES)
    return d[ok].drop_duplicates('unitat')


# ------------------------------------------------------------------------------------------ 1. ocupació
def ocupacio_aules(s: pd.DataFrame, a: pd.DataFrame, smt: int) -> pd.DataFrame:
    """Proporció de setmanes lectives en què cada aula està ocupada, per dia i franja horària (0-1).

    Files = aules (ordenades per tipus i capacitat), columnes = (dia, franja)."""
    x = s[(s['smt'] == smt) & (s['aula_partida'] != '')]
    files = []
    for r in x.itertuples():
        for f0 in FRANGES:
            if r.ini < f0 + 60 and r.fi > f0:
                files.append((r.aula_partida, r.data, r.dia, f0))
    occ = pd.DataFrame(files, columns=['aula', 'data', 'dia', 'franja']).drop_duplicates()
    # quantes dates amb classe té cada dia de la setmana (el denominador)
    dates = s[s['smt'] == smt].groupby('dia')['data'].nunique()
    t = occ.groupby(['aula', 'dia', 'franja']).size().unstack(['dia', 'franja'], fill_value=0)
    cols = pd.MultiIndex.from_product([DIES, FRANGES], names=['dia', 'franja'])
    t = t.reindex(columns=cols, fill_value=0)
    t = t.div([dates.get(d, 1) for d, _ in t.columns], axis=1)
    ordre = a.sort_values(['tipus', 'capacitat'], ascending=[True, False])['aula']
    return t.reindex([x for x in ordre if x in t.index] + [x for x in t.index if x not in set(ordre)]).fillna(0)


def resum_aules(s: pd.DataFrame, a: pd.DataFrame, smt: int) -> pd.DataFrame:
    """Per aula: ocupació mitjana de tota la setmana (matí, tarda i total) i capacitat."""
    o = ocupacio_aules(s, a, smt)
    mati = o.loc[:, [c for c in o.columns if c[1] < MATI_FI]].mean(axis=1)
    tarda = o.loc[:, [c for c in o.columns if c[1] >= MATI_FI]].mean(axis=1)
    r = pd.DataFrame({'ocup_mati': mati, 'ocup_tarda': tarda, 'ocup_total': o.mean(axis=1)})
    return r.join(a.set_index('aula')[['tipus', 'capacitat']], how='left').sort_values('ocup_total', ascending=False)


# ---------------------------------------------------------------------------------- 2. sessions sense aula
def sense_aula(s: pd.DataFrame, smt: int) -> pd.Series:
    """Per què hi ha sessions sense aula: PLAB (laboratori de departament), doble titulació (no en necessita)
    o realment els en falta una."""
    x = s[(s['smt'] == smt) & (s['aula_partida'] == '')]
    motiu = pd.Series('necessita aula', index=x.index)
    motiu[x['doble'] & (x['tipus'] != 'PLAB')] = 'doble titulació (no en necessita)'
    motiu[x['tipus'] == 'PLAB'] = 'PLAB (laboratori de departament, fixat)'
    return motiu.value_counts()


def simultanies(s: pd.DataFrame, smt: int, filtre=None) -> pd.DataFrame:
    """Nombre de classes que necessiten aula alhora, per data i franja horària.

    Retorna una fila per (data, franja) amb: total, amb_aula, sense_aula."""
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


# ---------------------------------------------------------------------------------------- 3. fora de torn
def fora_de_torn(s: pd.DataFrame, smt: int) -> pd.DataFrame:
    """Sessions que avui són al torn que el model nou NO els dona, per titulació i curs.

    Una sessió de dues cohorts compta un cop per a cadascuna. 'movibles' exclou els grups fixats (R1 GEI/GEET
    de 1r i 2n i els PLAB), que no es poden moure i per tant no són responsabilitat de la proposta."""
    e = explode_cohorts(s[s['smt'] == smt])
    e['fora_torn_movible'] = e['fora_torn'] & (e['fixada'] == '')
    g = e.groupby(['titulacio', 'curs_c']).agg(
        sessions=('id_sessio', 'size'),
        fora_torn=('fora_torn', 'sum'),
        fora_torn_movibles=('fora_torn_movible', 'sum'),
        torn_requerit=('torn_requerit', lambda v: '/'.join(sorted(set(v)))))
    g['pct_fora_torn'] = (100 * g['fora_torn'] / g['sessions']).round(1)
    return g.reset_index().sort_values('fora_torn', ascending=False)


# ---------------------------------------------------------------------------------------- 4. hi cap el matí?
def setmanes_normals(s: pd.DataFrame, smt: int, paquet: Path = PAQUET) -> list[str]:
    """Setmanes lectives amb 5 dies de classe i cap esdeveniment a calendari.csv (festiu, aturada, avaluació)."""
    cal = pd.read_csv(paquet / 'calendari.csv')
    amb_event = set(pd.to_datetime(cal['data']).dt.strftime('%G-W%V'))
    x = s[s['smt'] == smt]
    dies = x.groupby('setmana')['data'].nunique()
    return [w for w, n in dies.items() if n == 5 and w not in amb_event]


def hores_aula_setmana(s: pd.DataFrame, smt: int, torn: str) -> pd.DataFrame:
    """Hores-aula per setmana que demanen les sessions d'un torn requerit, davant de les que ofereix l'aulari.

    Oferta = (21 aules ordinàries - 2 de reserva) x hores de la finestra x dies lectius de la setmana.
    Demanda = suma de durades de les classes (una per classe física) amb torn_requerit = `torn`."""
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
    """Comprovació de mida per a una setmana: classes de matí que necessiten com a mínim N places davant de les
    aules que tenen com a mínim N places.

    Per a cada mida d'aula N: hores-aula que demanen les classes de matí amb més alumnes que la capacitat de
    l'aula immediatament més petita, davant de (aules >= N) x 6 h x dies. Si per a alguna N la demanda superés
    l'oferta, el matí no hi cabria fos quin fos l'horari (argument de recompte). Les 2 aules de reserva es
    prenen de les més petites, el cas més favorable per a les classes grans."""
    x = s[(s['smt'] == smt) & (s['setmana'] == setmana)]
    dies = x['data'].nunique()
    d = demanda_aula(x)
    d = d[d['torn_requerit'] == 'mati']
    caps = sorted(a.loc[a['ordinaria'] == 1, 'capacitat'])
    caps_disp = caps[RESERVA:]   # les 2 aules més petites queden de reserva
    files = []
    for n in sorted(set(caps_disp)):
        aules = sum(1 for c in caps_disp if c >= n)
        menor = max([c for c in caps_disp if c < n], default=0)
        dem = d.loc[d['alumnes'] > menor, 'durada_min'].sum() / 60 if menor else d['durada_min'].sum() / 60
        files.append({'places_minim': n, 'classes_de_mes_de': menor, 'aules_disponibles': aules,
                      'demanda_h': round(dem, 1), 'oferta_h': aules * 6 * dies,
                      'us_pct': round(100 * dem / (aules * 6 * dies), 1)})
    return pd.DataFrame(files)


# ----------------------------------------------------------------------------- 6. pla contra realitat (GERES)
VALIDACIO = ROOT / 'repte-horaris-escola' / 'validacio' / 'geres-ocupacio-setmana-2026-10-05.csv'
SETMANA_VALIDACIO = ('2026-10-05', '2026-10-09')


def carrega_validacio(path: Path = VALIDACIO) -> pd.DataFrame | None:
    """Ocupació real del GERES del 05 al 09/10/2026 (validacio/LLEGIU-ME.md), o None si el fitxer no hi és.

    Camps: espai, data, dia, h_ini, h_fi, durada_min, tipus_reserva (docent | no_docent), codi, grup_num,
    assignatura, estudis, alumnes_matriculats, docents, id_sessio_paquet."""
    if not Path(path).exists():
        return None
    v = pd.read_csv(path, dtype=str, keep_default_na=False)
    v['durada_min'] = pd.to_numeric(v['durada_min'], errors='coerce').fillna(0).astype(int)
    v['ini'] = v['h_ini'].map(hm)
    v['fi'] = v['ini'] + v['durada_min']
    return v


def sessions_setmana_validacio(s: pd.DataFrame) -> pd.DataFrame:
    """Les sessions del paquet de la setmana del GERES (una per sessió, com les compta el LLEGIU-ME)."""
    ini, fi = SETMANA_VALIDACIO
    return s[(s['data'] >= ini) & (s['data'] <= fi)]


def contrast_validacio(s: pd.DataFrame, v: pd.DataFrame) -> dict:
    """Pla (paquet) contra realitat (GERES) per a la setmana del 05/10/2026.

    Retorna recomptes i taules:
    - cobertura: sessions del paquet d'aquella setmana que surten al GERES (via id_sessio_paquet);
    - mateixa_aula: de les enllaçades amb aula al paquet, quantes es fan a l'aula prevista;
    - aula_real_de_les_sense_aula: on es fan de veritat les sessions que al paquet no tenen aula;
    - no_docents: hores d'espai ocupades per reserves que no són docència (no surten al paquet);
    - ocupacio: per espai, hores ocupades segons el pla i segons la realitat."""
    ps = sessions_setmana_validacio(s)
    doc = v[v['tipus_reserva'] == 'docent']
    enll = doc[doc['id_sessio_paquet'] != '']
    ids_geres = set(enll['id_sessio_paquet'])
    r: dict = {}
    r['sessions_paquet'] = len(ps)
    r['sessions_paquet_al_geres'] = int(ps['id_sessio'].isin(ids_geres).sum())
    r['reserves'] = len(v)
    r['reserves_docents'] = len(doc)
    r['reserves_no_docents'] = int((v['tipus_reserva'] == 'no_docent').sum())
    r['reserves_docents_sense_sessio'] = int((doc['id_sessio_paquet'] == '').sum())
    # mateixa aula: reserves enllaçades amb una sessió que al paquet té aula
    m = enll.merge(s[['id_sessio', 'aula_partida', 'tipus', 'smt']], left_on='id_sessio_paquet',
                   right_on='id_sessio', how='left')
    amb = m[m['aula_partida'] != '']
    r['enllacades_amb_aula_al_paquet'] = len(amb)
    r['mateixa_aula'] = int((amb['espai'] == amb['aula_partida']).sum())
    r['aula_diferent'] = amb.loc[amb['espai'] != amb['aula_partida'],
                                 ['id_sessio_paquet', 'aula_partida', 'espai', 'data', 'h_ini']]
    # sessions sense aula al paquet: a quin espai es fan de veritat
    sense = m[m['aula_partida'] == '']
    r['enllacades_sense_aula_al_paquet'] = len(sense)
    r['aula_real_de_les_sense_aula'] = sense.groupby(['tipus', 'espai']).size().rename('sessions') \
        .reset_index().sort_values('sessions', ascending=False)
    # reserves no docents: hores d'espai que el pla no veu
    nd = v[v['tipus_reserva'] == 'no_docent'].drop_duplicates(['espai', 'data', 'h_ini'])
    r['no_docents'] = (nd.groupby('espai')['durada_min'].sum() / 60).rename('hores').sort_values(ascending=False)
    # ocupació per espai: hores segons el pla (sessions amb aula, un cop per classe física) i segons el GERES
    pla = ps[ps['aula_partida'] != ''].drop_duplicates(['aula_partida', 'data', 'h_ini'])
    h_pla = pla.groupby('aula_partida')['durada_min'].sum() / 60
    real = v.drop_duplicates(['espai', 'data', 'h_ini'])
    h_real = real.groupby('espai')['durada_min'].sum() / 60
    h_real_doc = real[real['tipus_reserva'] == 'docent'].groupby('espai')['durada_min'].sum() / 60
    oc = pd.DataFrame({'hores_pla': h_pla, 'hores_reals_docents': h_real_doc, 'hores_reals_total': h_real}).fillna(0)
    oc['diferencia'] = oc['hores_reals_total'] - oc['hores_pla']
    r['ocupacio'] = oc.sort_values('diferencia', ascending=False)
    return r


# --------------------------------------------------------------------------------------- 5. sobre aforament
def sobre_aforament(s: pd.DataFrame, a: pd.DataFrame, smt: int) -> pd.DataFrame:
    """Grups amb més alumnes que places a l'aula on són avui (classe física: alumnes sumats)."""
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
