# Dades del tauler: carrega una vegada (st.cache_data) el paquet, els lliuraments i els càlculs del nivell 1.
# Tot és local: llegeix repte-horaris-escola/paquet/ i lliuraments/, no envia res enlloc.
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

AQUI = Path(__file__).resolve().parent
ROOT = AQUI.parent
PAQUET = ROOT / 'repte-horaris-escola' / 'paquet'
LLIURAMENTS = ROOT / 'lliuraments'
sys.path.insert(0, str(ROOT / 'nivell1'))

import analisi  # noqa: E402  (nivell1/analisi.py)

DIES = ['L', 'M', 'X', 'J', 'V']
NOM_DIA = {'L': 'Dilluns', 'M': 'Dimarts', 'X': 'Dimecres', 'J': 'Dijous', 'V': 'Divendres'}
FRANGES = [8 * 60 + 30 + 60 * i for i in range(12)]          # 8.30 ... 19.30 (inici de cada franja d'1 h)

# Els horaris que es poden mirar al tauler: nom -> (proposta, sessions extra de l'escenari, proposta de referència)
HORARIS = {
    "Avui (horari de partida)": ('proposta_partida', None, None),
    '5.1 · Aules sense moure hores': ('proposta-aules', None, None),
    '5.2 · Torns nous': ('proposta-torns', None, None),
    '5.3 · Imprevist': ('proposta-imprevist', None, 'proposta-torns'),
    '5.4 · Grau nou de 40 places': ('proposta-grau-nou', 'grau-nou-40', None),
}
INFORMES = {
    '5.1': ('informe-aules.json', 'Assignar aules sense moure cap hora'),
    '5.2': ('informe-torns.json', 'Torns nous: 1r i 2n al matí, la resta a la tarda'),
    '5.3': ('informe-imprevist.json', 'Imprevistos: aula tancada, grup que creix, avaria, sessió cancel·lada'),
    '5.4': ('informe-grau-nou.json', 'Un grau nou de 40 places'),
}
ESCENARI_IMPREVIST = PAQUET / 'escenaris' / 'contingencies' / 'escenari.json'


def hm(m: int) -> str:
    return f'{m // 60:02d}:{m % 60:02d}'


def dades_ok() -> list[str]:
    """Fitxers que falten per fer anar el tauler (el paquet no és a git)."""
    cal = [PAQUET / 'sessions.csv', PAQUET / 'aules.csv', LLIURAMENTS / 'proposta-torns.csv']
    return [str(p.relative_to(ROOT)) for p in cal if not p.exists()]


# ----------------------------------------------------------------------------------------------- paquet
@st.cache_data(show_spinner=False)
def paquet() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Sessions i aules, amb les columnes d'ajuda del nivell 1 (smt, ini, fi, unitat, doble, curs...)."""
    return analisi.carrega()


@st.cache_data(show_spinner=False)
def aules() -> pd.DataFrame:
    return pd.read_csv(PAQUET / 'aules.csv')


@st.cache_data(show_spinner=False)
def informe(tasca: str) -> dict:
    return json.loads((LLIURAMENTS / INFORMES[tasca][0]).read_text(encoding='utf-8'))


@st.cache_data(show_spinner=False)
def escenari_imprevist() -> dict:
    return json.loads(ESCENARI_IMPREVIST.read_text(encoding='utf-8'))


# ------------------------------------------------------------------------------------------- horaris
@st.cache_data(show_spinner='Carregant l\'horari…')
def horari(nom: str) -> pd.DataFrame:
    """Una fila per sessió del 2n semestre amb la data, l'hora i l'aula que li dona l'horari `nom` (de HORARIS).

    Com el verificador: la proposta diu el dia de la setmana i la data nova és aquell dia dins la mateixa setmana;
    si porta una columna `data` (sessió recuperada del 5.3), mana aquesta."""
    fitxer, extra, _ = HORARIS[nom]
    s = pd.read_csv(PAQUET / 'sessions.csv', dtype=str, keep_default_na=False)
    if extra:
        x = pd.read_csv(PAQUET / 'escenaris' / extra / 'sessions_extra.csv', dtype=str, keep_default_na=False)
        s = pd.concat([s, x], ignore_index=True).fillna('')
    path = PAQUET / f'{fitxer}.csv' if fitxer == 'proposta_partida' else LLIURAMENTS / f'{fitxer}.csv'
    p = pd.read_csv(path, dtype=str, keep_default_na=False)
    if 'data' not in p.columns:
        p['data'] = ''
    p = p.rename(columns={'dia': 'dia_p', 'h_ini': 'h_ini_p', 'aula': 'aula_p', 'data': 'data_p'})
    h = s.merge(p[['id_sessio', 'dia_p', 'h_ini_p', 'aula_p', 'data_p']], on='id_sessio', how='left').fillna('')
    data0 = pd.to_datetime(h['data'])
    h = h[(data0.dt.month >= 2) & (data0.dt.month <= 8)].copy()         # 2n semestre (com el verificador)
    data0 = pd.to_datetime(h['data'])
    desp = h['dia_p'].map(lambda d: DIES.index(d) if d in DIES else -1)
    nova = data0 + pd.to_timedelta(desp.where(desp >= 0, data0.dt.weekday) - data0.dt.weekday, unit='D')
    explicita = pd.to_datetime(h['data_p'].where(h['data_p'] != '', None))
    h['data_n'] = explicita.fillna(nova).dt.date
    h['dia_n'] = h['data_n'].map(lambda d: DIES[d.weekday()] if d.weekday() < 5 else '?')
    h['h_ini_n'] = h['h_ini_p'].where(h['h_ini_p'] != '', h['h_ini'])
    h['aula_n'] = h['aula_p']
    h['durada_min'] = pd.to_numeric(h['durada_min'], errors='coerce').fillna(0).astype(int)
    h['alumnes'] = pd.to_numeric(h['alumnes'], errors='coerce').fillna(0).astype(int)
    h['ini'] = h['h_ini_n'].map(lambda t: int(t[:2]) * 60 + int(t[3:5]))
    h['fi'] = h['ini'] + h['durada_min']
    h['unitat'] = h['id_compartida'].where(h['id_compartida'] != '', h['id_sessio'])
    return h[['id_sessio', 'unitat', 'codi', 'assignatura', 'tipus', 'grup', 'titulacions_curs', 'alumnes',
              'data', 'h_ini', 'aula_partida', 'data_n', 'dia_n', 'h_ini_n', 'ini', 'fi', 'aula_n']]


def ocupacio_moment(nom: str, data: dt.date, minut: int) -> pd.DataFrame:
    """Qui hi ha a cada aula el dia `data` al minut `minut`. Una fila per aula ocupada."""
    h = horari(nom)
    x = h[(h['data_n'] == data) & (h['ini'] <= minut) & (h['fi'] > minut) & (h['aula_n'] != '')]
    if x.empty:
        return pd.DataFrame(columns=['aula', 'classe', 'alumnes', 'hora', 'ids'])
    # una classe física (id_compartida) compta un cop; els alumnes de les sessions compartides se sumen
    g = x.groupby(['aula_n', 'unitat']).agg(codi=('codi', 'first'), assignatura=('assignatura', 'first'),
                                            grup=('grup', 'first'), alumnes=('alumnes', 'sum'),
                                            ini=('ini', 'first'), fi=('fi', 'first'),
                                            ids=('id_sessio', lambda v: ', '.join(v))).reset_index()
    g['classe'] = g['assignatura'].str.slice(0, 34) + ' · ' + g['grup']
    g['hora'] = g['ini'].map(hm) + '–' + g['fi'].map(hm)
    return g.rename(columns={'aula_n': 'aula'}).drop_duplicates('aula')[['aula', 'classe', 'alumnes', 'hora', 'ids']]


@st.cache_data(show_spinner='Calculant l\'ocupació…')
def ocupacio_mitjana(nom: str, dia: str, franja: int) -> pd.DataFrame:
    """Per aula: proporció de les dates lectives d'aquell dia de la setmana (2n semestre) en què l'aula està
    ocupada en algun moment de la franja d'una hora que comença a `franja`."""
    h = horari(nom)
    x = h[(h['dia_n'] == dia) & (h['aula_n'] != '')]
    dates = h.loc[h['dia_n'] == dia, 'data_n'].nunique() or 1
    y = x[(x['ini'] < franja + 60) & (x['fi'] > franja)]
    r = (y.groupby('aula_n')['data_n'].nunique() / dates).rename('ocupacio').reset_index()
    return r.rename(columns={'aula_n': 'aula'}).assign(dates=dates)


@st.cache_data(show_spinner=False)
def aules_ordinaries_ocupades(nom: str) -> pd.DataFrame:
    """Màxim, sobre les dates del 2n semestre, d'aules ordinàries ocupades alhora per dia i franja."""
    h = horari(nom)
    a = aules()
    ordin = set(a.loc[a['ordinaria'] == 1, 'aula'])
    x = h[h['aula_n'].isin(ordin)]
    files = []
    for f in FRANGES:
        y = x[(x['ini'] < f + 60) & (x['fi'] > f)]
        n = y.groupby(['data_n', 'dia_n'])['aula_n'].nunique().reset_index()
        m = n.groupby('dia_n')['aula_n'].agg(['max', 'mean']).reset_index()
        for r in m.itertuples():
            files.append({'dia': r.dia_n, 'franja': hm(f), 'maxim': int(r[2]), 'mitjana': round(r[3], 1)})
    return pd.DataFrame(files)


@st.cache_data(show_spinner=False)
def mogudes_per_cohort(nom: str = '5.2 · Torns nous') -> pd.DataFrame:
    """Sessions que canvien de dia o d'hora respecte d'avui, per cohort (una sessió de dues cohorts compta a totes
    dues), com a la taula 3 del resum per a la Junta."""
    h = horari(nom)
    canvi = (h['data_n'].astype(str) != h['data']) | (h['h_ini_n'] != h['h_ini'])
    e = h.assign(canvi=canvi, cohort=h['titulacions_curs'].str.split('|')).explode('cohort')
    g = e.groupby('cohort').agg(sessions=('id_sessio', 'size'), mogudes=('canvi', 'sum')).reset_index()
    g = g[g['mogudes'] > 0].sort_values('mogudes', ascending=False)
    g['pct'] = (100 * g['mogudes'] / g['sessions']).round(0)
    return g


def canvis_aula(nom: str, referencia: str) -> pd.DataFrame:
    """Sessions que tenen una altra aula (o una altra data/hora) que a l'horari de referència."""
    a, b = horari(nom), horari(referencia)
    m = a.merge(b[['id_sessio', 'aula_n', 'data_n', 'h_ini_n']], on='id_sessio', suffixes=('', '_ref'))
    return m[(m['aula_n'] != m['aula_n_ref']) | (m['data_n'] != m['data_n_ref']) | (m['h_ini_n'] != m['h_ini_n_ref'])]


# --------------------------------------------------------------------------------------------- nivell 1
@st.cache_data(show_spinner='Calculant el nivell 1…')
def nivell1() -> dict:
    s, a = paquet()
    r: dict = {}
    s2 = s[s['smt'] == 2]
    r['sessions'] = len(s2)
    r['sense_aula'] = analisi.sense_aula(s, 2).rename_axis('motiu').reset_index(name='sessions')
    r['n_sense_aula'] = int((s2['aula_partida'] == '').sum())
    sim = analisi.simultanies(s, 2)
    p = sim.groupby(['dia', 'franja'])['total'].max().reset_index()
    p['franja'] = p['franja'].map(hm)
    r['pic'] = p
    ft = analisi.fora_de_torn(s, 2)
    r['fora_torn'] = ft
    e = s2
    r['n_fora_torn'] = int(e['fora_torn'].sum())
    r['n_movibles'] = int((e['fora_torn'] & (e['fixada'] == '')).sum())
    hs = analisi.hores_aula_setmana(s, 2, 'mati').reset_index()
    ht = analisi.hores_aula_setmana(s, 2, 'tarda').reset_index()
    r['hores'] = pd.concat([hs.assign(torn='Matí'), ht.assign(torn='Tarda')], ignore_index=True)
    r['ocup_aules'] = analisi.resum_aules(s, a, 2).rename_axis('aula').reset_index()
    return r
