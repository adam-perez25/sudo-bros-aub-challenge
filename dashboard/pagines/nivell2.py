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
t51, t52, t53, t54, tcomp, trest, tprova = st.tabs(['5.1 · Aules', '5.2 · Torns nous', '5.3 · Imprevist',
                                                    '5.4 · Grau nou', 'Comparativa', 'Restriccions del model',
                                                    "Prova de l'avaluador"])

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

# ------------------------------------------------------------------------------------------- restriccions
with trest:
    st.subheader('Què ha de complir el model perquè un horari sigui vàlid')
    st.markdown("El model (cerca + CP-SAT) parteix de l'horari d'avui i només **canvia el mínim**. Les restriccions "
                "dures no es poden trencar mai; l'objectiu va per sota i es mesura amb els indicadors del verificador.")
    a, b = st.columns(2, gap='large')
    with a:
        st.markdown('#### Restriccions dures')
        st.dataframe(pd.DataFrame([
            ['R1 · Torn', '1r i 2n al matí; 3r, 4t, dobles titulacions i màsters a la tarda'],
            ['R1 · Grups fixats', "Les sessions fixades no es mouen (els grups de GEI 1r i 2n que avui són a la tarda)"],
            ['R2 · Calendari i finestres', "Dies lectius, setmanes d'avaluació i setmana ISO respectats"],
            ['R3 · Aula', "Tipus d'aula correcte, aforament suficient i aula no tancada"],
            ['R4 · Cap solapament', "Una aula, un docent o un grup d'alumnes no poden tenir dues classes alhora"],
            ['R5 · Aula assignada', 'Totes les sessions han de tenir aula'],
            ['R7 · PLAB', 'Els laboratoris fixats es queden on són'],
            ['R8 · Reserva', 'A cada franja queden lliures com a mínim 2 de les 21 aules ordinàries'],
        ], columns=['Regla', 'Què exigeix']), hide_index=True, use_container_width=True)
    with b:
        st.markdown('#### Què optimitza (menys és millor)')
        st.markdown("- **Hores mortes** de l'alumnat entre classes.\n"
                    "- **Desplaçaments** entre aules i entre edificis de les classes seguides d'un grup.\n"
                    "- **Canvis de franja** i **canvis d'aula** respecte d'avui.\n"
                    "- **Aules de teoria extra** per grup i canvis TE↔PAUL fora del passadís.")
        st.markdown('#### Com ho resolem')
        st.markdown("1. Es manté tot el que ja compleix.\n"
                    "2. Aules primer per a les sessions que no canvien d'hora.\n"
                    "3. Les activitats fora de torn es mouen **en bloc** (mateix dia i hora cada setmana).\n"
                    "4. Reparació local i cerca local sobre les hores mortes.\n"
                    "5. CP-SAT per dia per triar les aules, amb les restriccions dures com a condicions.\n"
                    "6. Verificador oficial al final: només es declara el que **s'ha demostrat** que no hi cap.")
    st.markdown('#### Excepcions declarades a la regla 1')
    st.markdown("Només **460**: 458 sessions de grups fixats i 2 que hem demostrat que no hi caben "
                "(S02839 i S04511). La resta de regles, **0 incompliments**.")

# ------------------------------------------------------------------------------------------------ prova
with tprova:
    st.subheader("Què puntua l'estimació web quan es declaren relaxacions")
    st.markdown('<div class="resposta">L&#8217;estimació gairebé no penalitza les relaxacions declarades: un horari que '
                '<b>no canvia res</b> i ho declara tot treu més punts que el que compleix les regles. '
                '<b>No és cap lliurament</b>, és un experiment (7-8 de novembre).</div>', unsafe_allow_html=True)
    c = st.columns(4)
    c[0].metric('La nostra 5.2 real', '74', '2.083 canvis de franja', delta_color='off', border=True)
    c[1].metric('Només torn i finestra declarats', '77', '0 canvis de franja', delta_color='off', border=True)
    c[2].metric("Horari d'avui, tot declarat", '80', '6.659 relaxacions', delta_color='off', border=True)
    c[3].metric('Canvis de franja que fan baixar la nota', '255 → 77', '414 → 76 · 2.000 → 74', delta_color='off',
                border=True)
    st.markdown('#### Prova de 80 contra el nostre lliurament real')
    st.dataframe(pd.DataFrame([
        ['5.1 Aules', 78, 81, '4.638'],
        ['5.2 Torns nous', 80, 74, '6.659'],
        ['5.3 Imprevistos', 80, 80, '6.669'],
        ['5.4 Grau nou', 80, 73, '6.659'],
    ], columns=['Pregunta', 'Prova (tot declarat)', 'Lliurament real', 'Relaxacions declarades a la prova']),
        hide_index=True, use_container_width=True)
    a, b = st.columns(2, gap='large')
    with a:
        st.markdown('#### Què en traiem')
        st.markdown("- A l'estimació, els **canvis de franja** pesen molt més que les **relaxacions declarades**.\n"
                    "- La cerca local millora hores mortes i aules, però la nota no passa de 77 ni de 80.\n"
                    "- Al 5.2 i al 5.4 la prova treu més que la solució real; al 5.3 empata; al 5.1 en treu menys.")
    with b:
        st.markdown('#### Per què no ho fem servir')
        st.markdown("L'enunciat diu que la validesa mira **si cada relaxació declarada està justificada**. Les 6.659 "
                    "de la prova no ho estan: les sessions es poden moure. Els lliuraments només declaren el que "
                    "no hi cap, i la prova diu obertament a les justificacions que és un experiment.")
