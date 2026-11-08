# Gràfics del tauler (Altair), tots amb la mateixa paleta i el mateix estil: marques primes, quadrícula discreta,
# text en tinta (mai del color de la sèrie) i tooltip a cada marca. Paleta de referència de la skill dataviz.
from __future__ import annotations

import altair as alt
import pandas as pd

SERIE = ['#2a78d6', '#eb6834', '#1baf7a']           # categòrica, en aquest ordre fix
BLAUS = ['#cde2fb', '#9ec5f4', '#6da7ec', '#3987e5', '#256abf', '#184f95', '#0d366b']   # seqüencial
GRIS = '#c0c9c3'
CRITIC = '#d03b3b'
TINTA, TINTA2, APAGAT, QUADRICULA = '#12201a', '#46544d', '#7f8a84', '#dde3df'
DIES = ['L', 'M', 'X', 'J', 'V']
NOM_DIA = {'L': 'Dl', 'M': 'Dt', 'X': 'Dc', 'J': 'Dj', 'V': 'Dv'}


def estil(c: alt.Chart, alcada: int = 300) -> alt.Chart:
    return (c.properties(height=alcada)
            .configure(background='#ffffff', font='Segoe UI')
            .configure_view(strokeWidth=0)
            .configure_axis(labelColor=TINTA2, titleColor=TINTA2, gridColor=QUADRICULA, domainColor=GRIS,
                            tickColor=GRIS, labelFontSize=13, titleFontSize=13, titleFontWeight='normal')
            .configure_legend(labelColor=TINTA2, titleColor=TINTA2, labelFontSize=13, titleFontSize=13,
                              orient='top')
            .configure_title(color=TINTA, fontSize=15, anchor='start'))


def barres_h(df: pd.DataFrame, cat: str, val: str, titol_val: str, color: str = SERIE[0],
             tooltip: list | None = None, alcada: int | None = None) -> alt.Chart:
    """Barres horitzontals d'una sola sèrie, ordenades de més a menys, amb el valor escrit al final."""
    base = alt.Chart(df).encode(y=alt.Y(f'{cat}:N', sort='-x', title=None, axis=alt.Axis(labelLimit=320, labelOverlap=False)),
                                x=alt.X(f'{val}:Q', title=titol_val))
    barres = base.mark_bar(color=color, cornerRadiusEnd=4, height={'band': 0.7}).encode(
        tooltip=tooltip or [cat, val])
    text = base.mark_text(align='left', dx=4, color=TINTA2, fontSize=12).encode(text=alt.Text(f'{val}:Q', format=',.0f'))
    return estil(barres + text, alcada or max(170, 36 * len(df)))


def mapa_calor(df: pd.DataFrame, valor: str, titol: str, limit: float | None = None, domini: tuple | None = None,
               format_: str = '.0f', tooltip_extra: list | None = None) -> alt.Chart:
    """Dia (columnes) x franja (files), color seqüencial blau i el valor escrit a cada casella. Les caselles per
    sobre de `limit` porten una vora vermella (crític)."""
    d = df.copy()
    d['nom_dia'] = d['dia'].map(NOM_DIA)
    escala = alt.Scale(range=BLAUS, domain=list(domini) if domini else alt.Undefined)
    base = alt.Chart(d).encode(x=alt.X('nom_dia:N', sort=[NOM_DIA[x] for x in DIES], title=None,
                                       axis=alt.Axis(orient='top', labelAngle=0, domain=False, ticks=False)),
                               y=alt.Y('franja:O', title=None, axis=alt.Axis(domain=False, ticks=False)))
    tt = [alt.Tooltip('nom_dia:N', title='Dia'), alt.Tooltip('franja:O', title='Franja'),
          alt.Tooltip(f'{valor}:Q', title=titol, format=format_)] + (tooltip_extra or [])
    caselles = base.mark_rect(cornerRadius=3, stroke='#ffffff', strokeWidth=2).encode(
        color=alt.Color(f'{valor}:Q', scale=escala, title=titol, legend=alt.Legend(orient='right', gradientLength=180)),
        tooltip=tt)
    capes = [caselles]
    if limit is not None:
        capes.append(base.transform_filter(alt.datum[valor] > limit).mark_rect(
            filled=False, stroke=CRITIC, strokeWidth=3, cornerRadius=3).encode(tooltip=tt))
    llindar = (sum(domini) / 2) if domini else d[valor].max() * 0.55
    capes.append(base.mark_text(fontSize=13).encode(
        text=alt.Text(f'{valor}:Q', format=format_),
        color=alt.condition(alt.datum[valor] > llindar, alt.value('#ffffff'), alt.value(TINTA)), tooltip=tt))
    return estil(alt.layer(*capes), 34 * d['franja'].nunique())


def linies(df: pd.DataFrame, x: str, y: str, serie: str, titol_y: str, regla: float | None = None,
           etiqueta_regla: str = '', x_titol: str | None = None) -> alt.Chart:
    """Línies de 2 px (com a molt 3 sèries, llegenda a dalt) amb una línia de referència opcional."""
    sel = alt.selection_point(fields=[x], nearest=True, on='pointerover', empty=False)
    dom = list(dict.fromkeys(df[serie]))
    color = alt.Color(f'{serie}:N', scale=alt.Scale(domain=dom, range=SERIE[:len(dom)]), title=None)
    base = alt.Chart(df).encode(x=alt.X(f'{x}:O', title=x_titol, axis=alt.Axis(labelAngle=-45)),
                                y=alt.Y(f'{y}:Q', title=titol_y), color=color)
    linia = base.mark_line(strokeWidth=2)
    punts = base.mark_point(size=70, filled=True).encode(
        opacity=alt.condition(sel, alt.value(1), alt.value(0)), tooltip=[x, serie, alt.Tooltip(f'{y}:Q', format='.1f')]
    ).add_params(sel)
    regle = alt.Chart(df).mark_rule(color=APAGAT, strokeDash=[4, 4]).encode(x=f'{x}:O', opacity=alt.condition(
        sel, alt.value(0.6), alt.value(0))).transform_filter(sel)
    capes = [linia, punts, regle]
    if regla is not None:
        r = pd.DataFrame({'y': [regla], 't': [etiqueta_regla]})
        capes.append(alt.Chart(r).mark_rule(color=TINTA2, strokeDash=[6, 4]).encode(y='y:Q'))
        capes.append(alt.Chart(r).mark_text(align='left', dy=-8, x=4, color=TINTA2, fontSize=12).encode(
            y='y:Q', text='t:N'))
    return estil(alt.layer(*capes), 300)


def barres_apilades(df: pd.DataFrame, cat: str, val: str, serie: str, ordre_series: list[str], titol_val: str,
                    alcada: int | None = None) -> alt.Chart:
    """Barres horitzontals apilades (2-3 sèries), amb 2 px de separació entre segments."""
    cats = df.groupby(cat)[val].sum().sort_values(ascending=False).index.tolist()
    d = df.assign(_o=df[serie].map({s: i for i, s in enumerate(ordre_series)}))
    c = alt.Chart(d).mark_bar(stroke='#ffffff', strokeWidth=2, height={'band': 0.72}).encode(
        y=alt.Y(f'{cat}:N', sort=cats, title=None, axis=alt.Axis(labelLimit=320, labelOverlap=False)),
        x=alt.X(f'{val}:Q', title=titol_val, stack='zero'),
        color=alt.Color(f'{serie}:N', scale=alt.Scale(domain=ordre_series, range=SERIE[:len(ordre_series)]),
                        title=None),
        order=alt.Order('_o:Q'),
        tooltip=[cat, serie, alt.Tooltip(f'{val}:Q', format=',.0f')])
    return estil(c, alcada or max(170, 32 * len(cats)))
