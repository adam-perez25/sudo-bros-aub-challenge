# Plànols de l'edifici Q amb les aules pintades a sobre (gràfic Altair amb el plànol de fons i un rectangle per aula).
#
# Els plànols (planols/*.pdf) no són a git: són dades de l'Escola. La primera vegada es converteixen a PNG
# (dashboard/.cache/, també fora de git) amb PyMuPDF. Si els PDF no hi són, disponible() torna False i les pàgines ho
# diuen en lloc de petar.
#
# Les posicions de les aules són a sales.json (punts PDF de la pàgina), llegides a mà de les etiquetes de porta.
from __future__ import annotations

import base64
import json
from pathlib import Path

import altair as alt
import pandas as pd

AQUI = Path(__file__).resolve().parent
ROOT = AQUI.parent
PLANOLS = ROOT / 'planols'
CACHE = AQUI / '.cache'
SALES = json.loads((AQUI / 'sales.json').read_text(encoding='utf-8'))
ESCALA = 2.0            # resolució del PNG respecte dels punts PDF (més = més nítid, més pes)

# Colors per estat (paleta de referència de la skill dataviz: sèrie 1, sèrie 2, crític i gris neutre)
ESTATS = {
    'Ocupada': '#2a78d6',
    'Canvi d\'aula': '#eb6834',
    'Tancada': '#d03b3b',
    'Lliure': '#ecebe6',
    'Destacada': '#eb6834',
}


def disponible() -> bool:
    return all((PLANOLS / p['fitxer']).exists() for p in SALES['plantes'].values())


def aules_al_planol() -> set[str]:
    return set(SALES['aules'])


def planta_de(aula: str) -> str | None:
    a = SALES['aules'].get(aula)
    return a['planta'] if a else None


def _retall(planta: str) -> tuple[float, float, float, float]:
    """Zona de la pàgina que es mostra (les 4 espines), en punts PDF."""
    import pymupdf
    p = SALES['plantes'][planta]
    with pymupdf.open(PLANOLS / p['fitxer']) as d:
        w, h = d[0].rect.width, d[0].rect.height
    fx0, fy0, fx1, fy1 = p['retall']
    return fx0 * w, fy0 * h, fx1 * w, fy1 * h


def imatge(planta: str) -> tuple[str, tuple[float, float, float, float]]:
    """PNG de la planta (com a data URL) i la zona que cobreix, en punts PDF."""
    CACHE.mkdir(exist_ok=True)
    png = CACHE / f'planta_{planta}.png'
    zona = _retall(planta)
    if not png.exists():
        import pymupdf
        with pymupdf.open(PLANOLS / SALES['plantes'][planta]['fitxer']) as d:
            pix = d[0].get_pixmap(matrix=pymupdf.Matrix(ESCALA, ESCALA), clip=pymupdf.Rect(*zona))
            pix.save(png)
    url = 'data:image/png;base64,' + base64.b64encode(png.read_bytes()).decode('ascii')
    return url, zona


def geometria(planta: str) -> pd.DataFrame:
    files = [{'aula': k, 'x0': v['rect'][0], 'y0': v['rect'][1], 'x1': v['rect'][2], 'y1': v['rect'][3]}
             for k, v in SALES['aules'].items() if v['planta'] == planta]
    g = pd.DataFrame(files)
    g['xc'] = (g['x0'] + g['x1']) / 2
    g['yc'] = (g['y0'] + g['y1']) / 2
    return g


def grafic(planta: str, valors: pd.DataFrame, color: alt.Color, tooltip: list, amplada: int = 760,
           etiqueta: str | None = None, titol: str | None = None) -> alt.LayerChart:
    """Plànol de la planta amb un rectangle per aula pintat segons `color`.

    `valors` porta una fila per aula (columna `aula`) amb les columnes que fan servir `color`, `tooltip` i
    `etiqueta` (text que surt a sota del codi de l'aula). Les aules del plànol que no hi són surten en gris."""
    url, (zx0, zy0, zx1, zy1) = imatge(planta)
    alcada = int(amplada * (zy1 - zy0) / (zx1 - zx0))
    g = geometria(planta).merge(valors, on='aula', how='left')
    if etiqueta:
        g[etiqueta] = g[etiqueta].fillna('')
    x = alt.Scale(domain=[zx0, zx1], nice=False, zero=False)
    y = alt.Scale(domain=[zy0, zy1], nice=False, zero=False, reverse=True)
    fons = alt.Chart(pd.DataFrame({'url': [url], 'x': [zx0], 'y': [zy0]})).mark_image(
        width=amplada, height=alcada, align='left', baseline='top', opacity=0.85).encode(
        x=alt.X('x:Q', scale=x, axis=None), y=alt.Y('y:Q', scale=y, axis=None), url='url:N')
    base = alt.Chart(g).encode(x=alt.X('x0:Q', scale=x, axis=None), y=alt.Y('y0:Q', scale=y, axis=None))
    rect = base.mark_rect(opacity=0.62, stroke='#0b0b0b', strokeWidth=1, cornerRadius=3).encode(
        x2='x1:Q', y2='y1:Q', color=color, tooltip=tooltip)
    codi = base.mark_text(fontSize=12, fontWeight='bold', color='#0b0b0b', dy=-7).encode(
        x='xc:Q', y='yc:Q', text='aula:N', tooltip=tooltip)
    capes = [fons, rect, codi]
    if etiqueta:
        capes.append(base.mark_text(fontSize=11, color='#0b0b0b', dy=8).encode(
            x='xc:Q', y='yc:Q', text=f'{etiqueta}:N', tooltip=tooltip))
    nom = SALES['plantes'][planta]['nom']
    # autosize 'pad': la zona de dibuix fa exactament amplada x alcada, com la imatge (amb 'fit' s'encongiria i les
    # aules quedarien desplaçades respecte del plànol)
    return alt.layer(*capes).properties(width=amplada, height=alcada, title=titol or nom,
                                        autosize=alt.AutoSizeParams(type='pad')).configure_view(strokeWidth=0)


def mostra(c: alt.LayerChart) -> None:
    """Dibuixa un plànol a Streamlit a la seva mida (sense el tema de Streamlit, que en canvia l'alçada)."""
    import streamlit as st
    st.altair_chart(c, theme=None, width='content', height='content')


def destaca(aules: list[str], amplada: int = 620) -> list[tuple[str, alt.LayerChart]]:
    """Plànols (un per planta implicada) amb les aules donades ressaltades. Per al xat."""
    aules = [a for a in dict.fromkeys(aules) if a in SALES['aules']]
    out = []
    for planta in sorted({planta_de(a) for a in aules}):
        tots = geometria(planta)['aula']
        v = pd.DataFrame({'aula': tots, 'estat': ['Destacada' if a in aules else 'Altres' for a in tots]})
        color = alt.Color('estat:N', legend=None,
                          scale=alt.Scale(domain=['Destacada', 'Altres'], range=[ESTATS['Destacada'], '#ffffff']))
        out.append((planta, grafic(planta, v, color, [alt.Tooltip('aula:N', title='Aula')], amplada=amplada)))
    return out
