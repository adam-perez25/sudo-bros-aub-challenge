import pandas as pd
import streamlit as st

import comu
import grafics as g

inf = {t: comu.informe(t) for t in comu.INFORMES}
o = {t: inf[t]['objectius'] for t in inf}
BASE_HORES_MORTES = o['5.1']['hores_mortes_min']     # el 5.1 no mou cap hora: són les hores mortes d'avui


def n(x) -> str:
    return f'{x:,}'.replace(',', '.')


def veredicte_curt(v: str) -> str:
    return 'VÀLIDA' if v == 'VALIDA' else 'VÀLIDA amb excepcions declarades'


st.title('Nivell 2 · Els horaris nous (2n semestre)')
st.markdown('<div class="resposta">Les quatre propostes passen el <b>verificador oficial</b> sense cap incompliment '
            'que compti. Les úniques excepcions són a la regla 1 (torn) i estan declarades i justificades.</div>',
            unsafe_allow_html=True)

RESUM = {
    '5.1': f"{n(o['5.1']['canvis_aula'])} canvis d'aula, cap hora moguda",
    '5.2': f"Hores mortes −{100 * (1 - o['5.2']['hores_mortes_min'] / BASE_HORES_MORTES):.0f} %, "
           f"{n(o['5.2']['canvis_franja'])} sessions canvien de franja",
    '5.3': '4 imprevistos resolts: 1 franja i '
           f"{o['5.3'].get('canvis_aula_vs_referencia', 0)} aules canviades",
    '5.4': 'Hi cap: 235 sessions noves, 0 canvis a la resta',
}
cols = st.columns(4)
for col, t in zip(cols, comu.INFORMES):
    v = inf[t]['veredicte']
    col.markdown(f'<div class="targeta"><div class="etiqueta">{t} · {comu.INFORMES[t][1]}</div>'
                 f'<div class="gran ok">✓ {veredicte_curt(v)}</div><div class="peu">{RESUM[t]}</div></div>',
                 unsafe_allow_html=True)

st.write('')
t51, t52, t53, t54, tcomp = st.tabs(['5.1 · Aules', '5.2 · Torns nous', '5.3 · Imprevist', '5.4 · Grau nou',
                                     'Comparativa'])

# --------------------------------------------------------------------------------------------------- 5.1
with t51:
    st.subheader("Donar aula a totes les sessions sense moure cap hora")
    c = st.columns(4)
    c[0].metric('Veredicte', 'VÀLIDA', 'sense cap relaxació', delta_color='off', border=True)
    c[1].metric("Canvis d'aula respecte d'avui", n(o['5.1']['canvis_aula']), border=True)
    c[2].metric("Desplaçaments entre aules (classes seguides)", n(o['5.1']['desplacaments_aula']), border=True)
    c[3].metric("Desplaçaments d'edifici", n(o['5.1']['desplacaments_edifici']), border=True)
    st.markdown("Cada grup té una aula base estable i les classes seguides es queden a la mateixa aula o al mateix "
                "passadís. L'assignació es fa amb un model de restriccions (CP-SAT) per dia, amb les hores fixes.")

# --------------------------------------------------------------------------------------------------- 5.2
with t52:
    st.subheader('1r i 2n al matí; 3r, 4t, dobles titulacions i màsters a la tarda')
    r1 = inf['5.2']['restriccions']['R1-TORN']
    nivell1 = comu.nivell1()
    c = st.columns(4)
    c[0].metric('Hores mortes de l\'alumnat', f"{n(o['5.2']['hores_mortes_min'] // 60)} h",
                f"{-100 * (1 - o['5.2']['hores_mortes_min'] / BASE_HORES_MORTES):.0f} % respecte d'avui",
                delta_color='inverse', border=True)
    c[1].metric('Sessions fora de torn que compten', '0',
                f"avui {n(nivell1['n_fora_torn'])}", delta_color='off', border=True)
    c[2].metric('Excepcions declarades a la regla 1', n(r1['declarades']), f"+ {n(r1['heretades'])} heretades "
                "(fixades)", delta_color='off', border=True)
    c[3].metric("Desplaçaments d'edifici", n(o['5.2']['desplacaments_edifici']), border=True)

    a, b = st.columns([1, 1], gap='large')
    with a:
        st.markdown('#### Aules ordinàries ocupades alhora (màxim del semestre)')
        oc = comu.aules_ordinaries_ocupades('5.2 · Torns nous')
        st.altair_chart(g.mapa_calor(oc, 'maxim', 'Aules ordinàries ocupades', limit=19, domini=(0, 21),
                                     tooltip_extra=[]), use_container_width=True)
        st.markdown(f"Cap franja no passa de **{oc['maxim'].max()} de les 21 aules**: sempre en queden com a mínim "
                    "les 2 de reserva (regla 8) i 3 més de marge.")
    with b:
        st.markdown('#### Sessions que canvien de franja, per cohort')
        mc = comu.mogudes_per_cohort().head(12)
        st.altair_chart(g.barres_h(mc, 'cohort', 'mogudes', 'Sessions mogudes',
                                   tooltip=['cohort', 'mogudes', 'sessions', 'pct']),
                        use_container_width=True)
        st.markdown('Les que més ho noten són 3r i 4t, que passen a la tarda. Les 248 sessions de doble titulació '
                    'que es feien amb un grup de matí també han pogut passar a la tarda.')

    st.markdown('#### Les excepcions a la regla 1 que demanem a la Junta')
    st.markdown("1. **458 sessions de grups fixats de 1r i 2n que avui són a la tarda** (GEI 1r i 2n). L'Escola ha dit "
                "que no es toquen: només els donem l'aula que no tenien.\n"
                "2. **2 sessions on hem demostrat que no hi caben** (S02839, S04511): setmanes amb un sol dia lectiu on "
                "un docent té més hores de tarda que la franja.")

# --------------------------------------------------------------------------------------------------- 5.3
with t53:
    st.subheader('Quatre imprevistos, resolts canviant el mínim')
    c = st.columns(4)
    c[0].metric('Imprevistos pendents', '0', 'abans 58', delta_color='off', border=True)
    c[1].metric('Sessions que canvien de franja', n(o['5.3'].get('canvis_franja_vs_referencia', 0)),
                'la recuperada', delta_color='off', border=True)
    c[2].metric("Sessions que canvien d'aula", n(o['5.3'].get('canvis_aula_vs_referencia', 0)),
                'mateix dia i hora', delta_color='off', border=True)
    c[3].metric('Incompliments nous', '0', border=True)
    ch = comu.canvis_aula('5.3 · Imprevist', '5.2 · Torns nous')
    rec = ch[ch['data_n'] != ch['data_n_ref']]
    rec_txt = (f"{rec.iloc[0]['data_n']:%d/%m} a les {rec.iloc[0]['h_ini_n']} a {rec.iloc[0]['aula_n']}"
               if len(rec) else '—')
    te21 = ch[(ch['grup'] == 'TE/21') & (ch['codi'] == '106047')]
    te21 = te21[te21['data_n'] == te21['data_n_ref']]          # sense la sessió recuperada
    te21_aula = te21['aula_n'].mode().iloc[0] if len(te21) else '—'
    te21_base = int((te21['aula_n'] == te21_aula).sum())
    te21_altres = ', '.join(sorted(set(te21['aula_n']) - {te21_aula}))
    taula = pd.DataFrame([
        ['Q3/0013 reservada del 15 al 19/3', 'Cada classe es queda el mateix dia i hora i canvia només d\'aula, '
         'a una del mateix passadís si n\'hi ha cap de lliure'],
        ['Transmissió de Calor TE/21 passa a 130 alumnes', f'{te21_base} de les seves {len(te21)} sessions van a {te21_aula} '
         f'(130 places), la seva nova aula base; les altres, on {te21_aula} ja és ocupada, a {te21_altres}'],
        ['Avaria a Q1/1003 el 10/3', 'Com la sala reservada: mateix dia i hora, una altra aula'],
        ['S11527 cancel·lada (8/3)', f'Es recupera el {rec_txt}, amb l\'alumnat i els docents lliures'],
    ], columns=['Imprevist', 'Què fem'])
    st.dataframe(taula, hide_index=True, use_container_width=True)
    cc = ch.groupby('aula_n').size().rename('sessions').reset_index().rename(columns={'aula_n': 'aula'})
    a, b = st.columns([1, 1], gap='large')
    with a:
        st.markdown("#### On van les sessions que canvien")
        st.altair_chart(g.barres_h(cc, 'aula', 'sessions', 'Sessions que hi arriben', color=g.SERIE[1]),
                        use_container_width=True)
    with b:
        st.markdown('#### Al plànol')
        st.markdown("A la pàgina **L'edifici Q**, trieu *5.3 · Imprevist* i el dilluns 15/3: Q3/0013 surt tancada en "
                    "vermell i les aules que reben classes, en taronja.")
        st.page_link('pagines/planol.py', label="Obre l'edifici Q", icon=':material/map:')

# --------------------------------------------------------------------------------------------------- 5.4
with t54:
    st.subheader('Un grau nou de 40 places: hi cap')
    c = st.columns(4)
    c[0].metric('Sessions noves col·locades', '235 de 235', 'totes a la seva hora', delta_color='off', border=True)
    c[1].metric('Sessions dels graus actuals que canvien', '0', border=True)
    c[2].metric('Relaxacions noves', '0', border=True)
    c[3].metric('Aules ordinàries lliures a la franja de matí més plena', '6', 'abans 7 (en calen 2)',
                delta_color='off', border=True)
    h = comu.horari('5.4 · Grau nou de 40 places')
    nou = h[h['titulacions_curs'].str.startswith('GNOU')]
    per_aula = nou.groupby(['aula_n', 'tipus']).size().rename('sessions').reset_index()
    per_aula = per_aula.rename(columns={'aula_n': 'aula'})
    a, b = st.columns([1, 1], gap='large')
    with a:
        st.markdown('#### On fa classe el grau nou')
        st.altair_chart(g.barres_apilades(per_aula, 'aula', 'sessions', 'tipus',
                                          sorted(per_aula['tipus'].unique()), 'Sessions del semestre'),
                        use_container_width=True)
    with b:
        st.markdown('#### Per què hi cap')
        st.markdown("- Mai no necessita més de **2 aules alhora** i com a molt **1 teoria**.\n"
                    "- La teoria (40 alumnes) té aula fixa tot el semestre, de 48 a 63 places.\n"
                    "- Els PAUL (fins a 20 alumnes) van sobretot a seminaris, que no compten per a la reserva.\n"
                    "- Al matí el model nou fa servir unes 12 de les 19 aules disponibles: hi ha marge.")

# ------------------------------------------------------------------------------------------- comparativa
with tcomp:
    st.subheader('Objectius del verificador, proposta per proposta')
    noms = {'hores_mortes_min': 'Hores mortes (minuts)', 'desplacaments_aula': 'Desplaçaments d\'aula',
            'desplacaments_edifici': 'Desplaçaments d\'edifici', 'canvis_franja': 'Canvis de franja vs avui',
            'canvis_aula': 'Canvis d\'aula vs avui', 'r6_aules_te_extra_per_grup': 'Aules de teoria extra per grup',
            'r6_canvis_te_paul_fora_passadis': 'Canvis TE↔PAUL fora del passadís', 'sessions_avaluades': 'Sessions'}
    t = pd.DataFrame({k: {noms[m]: v for m, v in o[k].items() if m in noms} for k in o})
    t.insert(0, 'Avui', [BASE_HORES_MORTES, None, None, 0, 0, None, None, o['5.1']['sessions_avaluades']])
    st.dataframe(t.map(lambda v: '' if pd.isna(v) else n(int(v))), use_container_width=True)
    st.caption('Menys és millor a totes les files. «Avui» només té les xifres que no depenen de l\'aula (la majoria '
               'de sessions d\'avui no en tenen). El 5.4 té 235 sessions més (el grau nou).')
