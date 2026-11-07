import altair as alt
import pandas as pd
import streamlit as st

import comu
import grafics as g
import planol

r = comu.nivell1()

st.title("Nivell 1 · Com s'usen avui les aules?")
st.markdown('<div class="resposta"><b>Sí, el matí hi cap, però només si es reparteixen les hores punta.</b> El total '
            'setmanal no és el problema (unes 60 % de les hores-aula de matí); el problema és el dimarts i les '
            'franges de 10.30 a 13.30.</div>', unsafe_allow_html=True)

pct_sense = 100 * r['n_sense_aula'] / r['sessions']
pic = r['pic']
mx = pic.loc[pic['total'].idxmax()]
normals = r['hores'][(r['hores']['torn'] == 'Matí') & r['hores']['normal']]
c1, c2, c3, c4 = st.columns(4)
c1.metric('Sessions sense aula (2n sem.)', f'{pct_sense:.0f} %', help=f"{r['n_sense_aula']:,} de "
          f"{r['sessions']:,}".replace(',', '.'), border=True)
c2.metric('Fora de torn i movibles', f"{r['n_movibles']:,}".replace(',', '.'),
          f"de {r['n_fora_torn']:,} fora de torn".replace(',', '.'), delta_color='off', border=True)
c3.metric('Hores-aula de matí necessàries', f"{normals['ocupacio_pct'].min():.0f}-"
          f"{normals['ocupacio_pct'].max():.0f} %", 'setmanes normals', delta_color='off', border=True)
c4.metric('Pic de classes alhora (19 aules)', f"{int(mx['total'])}",
          f"{g.NOM_DIA[mx['dia']]} {mx['franja']}", delta_color='off', border=True)

st.divider()

# ----------------------------------------------------------------------------- 1. sessions sense aula
a, b = st.columns([1, 1], gap='large')
with a:
    st.subheader('1 · Les dades amaguen tres quartes parts de la demanda')
    sa = r['sense_aula'].copy()
    sa.loc[len(sa)] = ['amb aula', r['sessions'] - r['n_sense_aula']]
    sa['motiu'] = sa['motiu'].str.replace(' (laboratori de departament, fixat)', ' (lab. de departament)', regex=False).str.replace(' (no en necessita)', '', regex=False)
    st.altair_chart(g.barres_h(sa, 'motiu', 'sessions', 'Sessions del 2n semestre'), use_container_width=True)
    st.markdown('<div class="nota">Les aules <i>semblen</i> buides al 2n semestre perquè la majoria de sessions '
                'encara no en tenen. La demanda s\'ha de comptar des de les sessions, no des de les aules.</div>',
                unsafe_allow_html=True)
with b:
    st.subheader('Al plànol: el que sembla lliure no ho és')
    if planol.disponible():
        oc = r['ocup_aules'][['aula', 'ocup_mati', 'capacitat']].copy()
        oc['pct'] = (100 * oc['ocup_mati']).round(0)
        oc['etiq'] = oc['pct'].map(lambda v: f'{v:.0f} %')
        color = alt.Color('pct:Q', scale=alt.Scale(range=g.BLAUS, domain=[0, 100]), title='% matí ocupat',
                          legend=alt.Legend(orient='bottom', gradientLength=160))
        tt = [alt.Tooltip('aula:N', title='Aula'), alt.Tooltip('pct:Q', title='% del matí ocupat (avui)'),
              alt.Tooltip('capacitat:Q', title='Places')]
        planta = st.segmented_control('Planta', ['1', '0'], default='1', format_func=lambda p: planol.SALES[
            'plantes'][p]['nom'], label_visibility='collapsed') or '1'
        planol.mostra(planol.grafic(planta, oc, color, tt, amplada=560, etiqueta='etiq',
                                    titol="Ocupació de matí amb l'horari d'avui"))
    else:
        st.info('Els plànols (carpeta planols/) no hi són: es poden posar a l\'arrel del projecte (vegeu SETUP.md).')

st.divider()

# ---------------------------------------------------------------------------------- 2. fora de torn
a, b = st.columns([1, 1], gap='large')
with a:
    st.subheader('2 · 3.246 sessions són fora de torn; se\'n poden moure 2.008')
    ft = r['fora_torn']
    ft = ft[ft['fora_torn'] > 0].head(12).copy()
    ft['cohort'] = ft['titulacio'] + ' ' + ft['curs_c']
    llarg = pd.concat([
        ft.assign(tipus='Es pot moure', n=ft['fora_torn_movibles']),
        ft.assign(tipus='Fixada (no es toca)', n=ft['fora_torn'] - ft['fora_torn_movibles'])])
    st.altair_chart(g.barres_apilades(llarg, 'cohort', 'n', 'tipus', ['Es pot moure', 'Fixada (no es toca)'],
                                      'Sessions fora de torn'), use_container_width=True)
    st.markdown('<div class="nota">3r i 4t han de passar a la tarda (GEI 3r 89 %, GEST 3r 99 %); GCIS 2n i GIA 1r i '
                '2n, al matí. Les fixades (GEI 1r i 2n, laboratoris PLAB) no es poden moure: són excepcions que la '
                'Junta ha de conèixer.</div>', unsafe_allow_html=True)

# ------------------------------------------------------------------------------- 3. hores-aula per setmana
with b:
    st.subheader('3 · Sobre el paper, el matí hi cap')
    h = r['hores'].copy()
    h['setmana'] = h['setmana'].str.slice(5)
    st.altair_chart(g.linies(h, 'setmana', 'ocupacio_pct', 'torn', '% de les hores-aula del torn', regla=100,
                             etiqueta_regla='100 % = 19 aules plenes tot el torn', x_titol='Setmana (2n semestre)'),
                    use_container_width=True)
    st.markdown('<div class="nota">Si totes les classes de 1r i 2n fossin al matí, ocuparien el 59-64 % de les '
                'hores-aula de les setmanes normals. La tarda es queda al 35-40 %.</div>', unsafe_allow_html=True)

st.divider()

# -------------------------------------------------------------------------------------------- 4. el pic
a, b = st.columns([1, 1], gap='large')
with a:
    st.subheader('4 · El límit real és el pic')
    st.altair_chart(g.mapa_calor(pic, 'total', 'Classes alhora (màxim)', limit=19, domini=(0, 22),
                                 tooltip_extra=[]), use_container_width=True)
with b:
    st.markdown('#### Màxim de classes que necessiten aula alhora, avui')
    st.markdown(f"Les caselles amb vora vermella passen de les **19 aules disponibles** (21 ordinàries menys les 2 "
                f"de reserva). Amb l'horari d'avui passa en {int((pic['total'] > 19).sum())} franges, i el pic és "
                f"**{int(mx['total'])} classes** el {comu.NOM_DIA[mx['dia']].lower()} a les {mx['franja']}.")
    st.markdown('**Implicació per al 5.2:** les classes que passen al matí han d\'anar als dies i les hores més '
                'tranquils (dimecres, divendres, 8.30), no a les franges que agafarien de manera natural.')
    st.markdown('#### 5 · La mida de les aules no és un coll d\'ampolla')
    st.markdown('Les classes de matí que necessiten N places o més fan servir com a molt el **33 %** de les '
                'hores-aula de les aules de N places o més. Només 2 grups movibles passen de l\'aforament, i tots '
                'dos tenen aules més grans lliures.')
