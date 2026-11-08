# L'edifici Q: els plànols amb l'horari a sobre. Qui hi ha a cada aula en un moment concret, o com d'ocupada està de
# mitjana una franja al llarg del semestre; per a l'horari d'avui i per a cada proposta. Al 5.3 es veuen les aules
# tancades i les que reben classes canviades.
import datetime as dt

import altair as alt
import pandas as pd
import streamlit as st

import comu
import grafics as g
import planol

st.title("L'edifici Q · L'horari damunt dels plànols")
if not planol.disponible():
    st.error("Falten els plànols: poseu la carpeta planols/ (els 5 PDF de l'edifici Q) a l'arrel del projecte. "
             "No són a git perquè són dades de l'Escola.")
    st.stop()

# Moments preparats per a la presentació: (etiqueta, horari, data, hora, horari per comparar)
PRESETS = {
    'Dimarts 10.30: avui vs 5.2': ('Avui (horari de partida)', dt.date(2027, 2, 9), '10:30', '5.2 · Torns nous'),
    'Dilluns 15/3: Q3/0013 tancada (5.3)': ('5.3 · Imprevist', dt.date(2027, 3, 15), '12:30', None),
    'Dimecres 10/3: avaria a Q1/1003 (5.3)': ('5.3 · Imprevist', dt.date(2027, 3, 10), '10:30', None),
    'Dimarts 10.30: grau nou (5.4)': ('5.4 · Grau nou de 40 places', dt.date(2027, 2, 9), '10:30', None),
    'Divendres 9/4: per què S04511 no hi cap': ('5.2 · Torns nous', dt.date(2027, 4, 9), '16:00', None),
}
DIA_S04511 = dt.date(2027, 4, 9)
HORES = [comu.hm(8 * 60 + 30 + 30 * i) for i in range(24)]          # 8.30 ... 20.00 cada mitja hora
NOMS = list(comu.HORARIS)

if 'pl_horari' not in st.session_state:
    st.session_state.update(pl_horari='5.2 · Torns nous', pl_data=dt.date(2027, 2, 9), pl_hora='10:30',
                            pl_compara=False, pl_horari2='Avui (horari de partida)',
                            pl_mode='Un moment concret')


def aplica(p: str) -> None:
    h, d, hora, comp = PRESETS[p]
    st.session_state.update(pl_horari=h, pl_data=d, pl_hora=hora, pl_mode='Un moment concret',
                            pl_compara=comp is not None)
    if comp:
        st.session_state.update(pl_horari=comp, pl_horari2=h)


st.markdown('**Moments preparats:**')
bc = st.columns(len(PRESETS))
for c, p in zip(bc, PRESETS):
    c.button(p, on_click=aplica, args=(p,), use_container_width=True)

f1, f2, f3, f4 = st.columns([2.2, 1.6, 1.4, 1.2])
nom = f1.selectbox('Horari', NOMS, key='pl_horari')
mode = f2.segmented_control('Què es mostra', ['Un moment concret', 'Mitjana del semestre'], key='pl_mode') or 'Un moment concret'
if mode == 'Un moment concret':
    data = f3.date_input('Dia', key='pl_data', min_value=dt.date(2027, 2, 1), max_value=dt.date(2027, 6, 30),
                         format='DD/MM/YYYY')
    hora = f4.selectbox('Hora', HORES, key='pl_hora')
else:
    dia = f3.selectbox('Dia de la setmana', comu.DIES, format_func=comu.NOM_DIA.get, index=1, key='pl_dia')
    franja = f4.selectbox('Franja', [comu.hm(f) for f in comu.FRANGES], index=2, key='pl_franja')
compara = st.toggle('Compara amb un altre horari', key='pl_compara')
nom2 = st.selectbox('Horari per comparar', NOMS, key='pl_horari2') if compara else None


def estat_moment(nom_h: str) -> tuple[pd.DataFrame, alt.Color, list, str]:
    minut = int(hora[:2]) * 60 + int(hora[3:])
    oc = comu.ocupacio_moment(nom_h, data, minut)
    v = pd.DataFrame({'aula': sorted(planol.aules_al_planol())}).merge(oc, on='aula', how='left')
    v['estat'] = v['classe'].notna().map({True: 'Ocupada', False: 'Lliure'})
    # 5.3: aules tancades aquell dia i aules que reben una classe canviada respecte del 5.2
    ref = comu.HORARIS[nom_h][2]
    if ref:
        esc = comu.escenari_imprevist()
        tanc = {t['aula'] for t in esc['aules_tancades'] if t['data_ini'] <= str(data) <= t['data_fi']}
        ch = comu.canvis_aula(nom_h, next(k for k, x in comu.HORARIS.items() if x[0] == ref))
        ch = ch[(ch['data_n'] == data) & (ch['ini'] <= minut) & (ch['fi'] > minut)]
        v.loc[v['aula'].isin(set(ch['aula_n'])), 'estat'] = "Canvi d'aula"
        v.loc[v['aula'].isin(tanc), 'estat'] = 'Tancada'
        v.loc[v['aula'].isin(tanc), 'classe'] = 'Tancada (imprevist)'
    cap = comu.aules().set_index('aula')['capacitat']
    v['places'] = v['aula'].map(cap)
    v['etiq'] = v.apply(lambda r: f"{int(r['alumnes'])}/{int(r['places'])}" if pd.notna(r['alumnes']) else '', axis=1)
    v = v.fillna({'classe': 'Lliure', 'hora': '', 'ids': ''})
    dom = [e for e in ['Ocupada', "Canvi d'aula", 'Tancada', 'Lliure'] if e in set(v['estat']) or e in
           ('Ocupada', 'Lliure')]
    color = alt.Color('estat:N', title=None, scale=alt.Scale(domain=dom, range=[planol.ESTATS[e] for e in dom]),
                      legend=alt.Legend(orient='bottom'))
    tt = [alt.Tooltip('aula:N', title='Aula'), alt.Tooltip('classe:N', title='Classe'),
          alt.Tooltip('hora:N', title='Hora'), alt.Tooltip('etiq:N', title='Alumnes / places'),
          alt.Tooltip('ids:N', title='Sessions')]
    ocup = (v['estat'] != 'Lliure') & (v['estat'] != 'Tancada')
    resum = f"{int(ocup.sum())} de {len(v)} aules ocupades"
    return v, color, tt, resum


def estat_mitjana(nom_h: str) -> tuple[pd.DataFrame, alt.Color, list, str]:
    f = int(franja[:2]) * 60 + int(franja[3:])
    oc = comu.ocupacio_mitjana(nom_h, dia, f)
    v = pd.DataFrame({'aula': sorted(planol.aules_al_planol())}).merge(oc, on='aula', how='left').fillna(
        {'ocupacio': 0})
    v['pct'] = (100 * v['ocupacio']).round(0)
    v['etiq'] = v['pct'].map(lambda x: f'{x:.0f} %')
    color = alt.Color('pct:Q', title='% dels dies ocupada', scale=alt.Scale(range=g.BLAUS, domain=[0, 100]),
                      legend=alt.Legend(orient='bottom', gradientLength=200))
    tt = [alt.Tooltip('aula:N', title='Aula'), alt.Tooltip('pct:Q', title='% dels dies ocupada')]
    return v, color, tt, f"Ocupació mitjana {v['pct'].mean():.0f} %"


def fora_del_planol(nom_h: str) -> None:
    if mode != 'Un moment concret':
        return
    oc = comu.ocupacio_moment(nom_h, data, int(hora[:2]) * 60 + int(hora[3:]))
    fora = oc[~oc['aula'].isin(planol.aules_al_planol())]
    if len(fora):
        st.caption(f"A més, {len(fora)} classes en laboratoris i seminaris d'altres plantes: "
                   + ', '.join(sorted(fora['aula'])))


def estat(nom_h: str):
    return (estat_moment if mode == 'Un moment concret' else estat_mitjana)(nom_h)


AMPLADA = 620
if mode == 'Un moment concret':
    st.markdown(f"**{comu.NOM_DIA[comu.DIES[data.weekday()]] if data.weekday() < 5 else 'Cap de setmana'} "
                f"{data:%d/%m/%Y}, {hora}.** Passeu el ratolí per sobre d'una aula per veure qui hi ha.")
    if data == DIA_S04511 and nom.startswith('5.2'):
        st.info("**L'única relaxació demostrada: S04511** (Sistemes i Tecnologies Web, PAUL/452, 34 alumnes, docent "
                "D380). El 9/4 és l'únic dia de la seva setmana on es pot moure (del 5 al 8/4 és setmana "
                "d'avaluació) i, com que és a la tarda, ha d'anar a una aula d'informàtica de 34 places o més: només "
                "**Q1/0007** i **Q1/0019**.\n\n"
                "- **15.00-17.00** i **17.00-19.00**: totes dues ocupades per grups fixats de Programació 2 "
                "(S15066, S15095, S15124, S15153), que no es poden moure (regla 1).\n"
                "- **14.30-15.00**: mitja hora, massa curt.\n"
                "- **19.00-21.00**: Q1/0007 queda lliure, però el docent D380 hi fa la PAUL/453 (S04526, 19 h) i la "
                "PAUL/451 (S04496, 20 h): són **dues hores per a tres classes seves**.\n\n"
                "Proveu les hores 16:00, 17:30, 19:00 i 20:00. No hi ha cap franja possible: per això es declara, "
                "en lloc de dir que no l'hem trobada.")
if compara and nom2:
    # dos horaris de costat, una planta
    planta = st.segmented_control('Planta', ['1', '0'], default='1', key='pl_planta',
                                  format_func=lambda p: planol.SALES['plantes'][p]['nom']) or '1'
    cols = st.columns(2, gap='medium')
    for col, nom_h in zip(cols, [nom2, nom]):
        with col:
            v, color, tt, resum = estat(nom_h)
            st.markdown(f'#### {nom_h}')
            st.caption(resum)
            planol.mostra(planol.grafic(planta, v, color, tt, amplada=AMPLADA, etiqueta='etiq'))
            fora_del_planol(nom_h)
else:
    # un horari, les dues plantes de costat
    v, color, tt, resum = estat(nom)
    st.markdown(f'#### {nom}')
    st.caption(resum)
    cols = st.columns(2, gap='medium')
    for col, planta in zip(cols, ['1', '0']):
        with col:
            planol.mostra(planol.grafic(planta, v, color, tt, amplada=AMPLADA, etiqueta='etiq'))
    fora_del_planol(nom)

st.caption("Plànols de l'edifici Q (planta baixa i primera, espines 1 a 4), on són les 21 aules ordinàries. Les "
           "aules de l'espina 3 de la planta baixa estan dividides respecte del plànol original: la divisió és "
           "aproximada.")
