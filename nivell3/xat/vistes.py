# Vistes del xat web: tot el que es dibuixa (capçalera, barra lateral, pantalla inicial, respostes). Sense lògica
# de l'assistent ni de l'estat: això és a agent.py i xat/estat.py.
from pathlib import Path

import pandas as pd
import streamlit as st

import dades
import historial
from xat import estat
from xat.exemples import EXEMPLES

MAX_FONTS = 200
MAX_CONVERSES = 30
AVATAR = {'user': '🧑‍🎓', 'assistant': '🗓️'}
ESTILS = Path(__file__).resolve().parent / 'estils.css'


def carrega_estils() -> None:
    st.markdown(f'<style>{ESTILS.read_text(encoding="utf-8")}</style>', unsafe_allow_html=True)


def capcalera() -> None:
    st.title("🗓️ Assistent d'horaris · Escola d'Enginyeria")
    st.markdown('<div class="subtitol">Pregunteu per aules, grups, franges lliures o imprevistos. '
                'Només redacta esborranys: no envia res a ningú.</div>', unsafe_allow_html=True)


def avis_pendent() -> None:
    if 'avis_xat' in st.session_state:
        st.warning(st.session_state.pop('avis_xat'))


def barra_lateral() -> bool:
    """Dibuixa la barra lateral i torna si l'usuari vol veure les eines utilitzades."""
    with st.sidebar:
        st.button('➕ Nova conversa', use_container_width=True, type='primary', on_click=estat.nova_conversa)
        st.subheader('Converses anteriors')
        desades = historial.llista()
        if not desades:
            st.caption("Encara no n'hi ha cap: es desen soles a mesura que preguntes.")
        for c in desades[:MAX_CONVERSES]:
            actual = c['id'] == st.session_state.xat_id
            col1, col2 = st.columns([6, 1])
            col1.button(c['titol'], key=f"obre_{c['id']}", use_container_width=True, help=c['data'].replace('T', ' '),
                        type='primary' if actual else 'secondary', on_click=estat.obre_conversa, args=(c['id'],))
            col2.button('', icon=':material/delete:', key=f"del_{c['id']}", help='Esborra aquesta conversa',
                        on_click=estat.esborra_conversa, args=(c['id'],))
        if len(desades) > MAX_CONVERSES:
            st.caption(f'Es mostren les {MAX_CONVERSES} més recents de {len(desades)}.')
        st.divider()
        detall = st.toggle('Mostra les eines utilitzades', value=False)
        st.caption("Les converses es desen només en aquest ordinador (nivell3/xats/).")
        st.caption("Horari consultat: la nostra proposta del 5.2 (2n semestre) i l'horari d'avui sense canvis (1r semestre).")
    return detall


def pantalla_inicial() -> str | None:
    """Benvinguda amb les preguntes d'exemple (només amb el xat buit). Torna la pregunta triada, si n'hi ha."""
    st.markdown('<div class="targeta-buida"><div class="gran">💬</div>'
                '<b>Com us puc ajudar?</b><br>Escriviu una pregunta o proveu un exemple.</div>',
                unsafe_allow_html=True)
    triada = None
    cols = st.columns(2)
    for i, (etiqueta, pregunta) in enumerate(EXEMPLES[:6]):
        if cols[i % 2].button(etiqueta, use_container_width=True, key=f'main_{etiqueta}'):
            triada = pregunta
    return triada


def missatge_usuari(text: str) -> None:
    with st.chat_message('user', avatar=AVATAR['user']):
        st.markdown(text)


def taula_fonts(ids: list[str]) -> pd.DataFrame:
    h = dades.carrega().horari
    f = h[h.id_sessio.isin(ids)].copy()
    f['_ordre'] = f.id_sessio.map({x: i for i, x in enumerate(ids)})
    f = f.sort_values('_ordre')
    return pd.DataFrame({'Sessió': f.id_sessio, 'Assignatura': f.assignatura, 'Grup': f.grup,
                         'Data': f.data_nova, 'Hora': f.h_ini_nou + '–' + f.h_fi_nou, 'Aula': f.aula_nova.fillna('')})


def mostra_resposta(r: dict, detall: bool) -> None:
    st.markdown(r['resposta'])
    if r.get('fonts'):
        ids = r['fonts']
        with st.expander(f'Fonts ({len(ids)} sessions)'):
            st.dataframe(taula_fonts(ids[:MAX_FONTS]), hide_index=True, use_container_width=True)
            if len(ids) > MAX_FONTS:
                st.caption(f'Es mostren les primeres {MAX_FONTS} de {len(ids)}.')
    av = r.get('avis')
    if av:
        with st.expander("Esborranys d'avís (esborrany, no enviat)", expanded=True):
            st.warning("Esborrany, no enviat: l'assistent només redacta, no envia res a ningú.")
            for a in av['avisos']:
                st.markdown(f"**{a['per_a']}**")
                st.text(a['text'])
            st.markdown('**Registre de canvis** (esborrany, no enviat)')
            st.dataframe(pd.DataFrame(av['registre']), hide_index=True, use_container_width=True)
    if detall and r.get('eines'):
        st.caption('Eines: ' + '; '.join(f"{e['eina']}({e['arguments']})" for e in r['eines']))


def missatge_assistent(r: dict, detall: bool) -> None:
    with st.chat_message('assistant', avatar=AVATAR['assistant']):
        mostra_resposta(r, detall)


def historial_xat(detall: bool) -> None:
    for m in st.session_state.historial:
        if m['rol'] == 'user':
            missatge_usuari(m['text'])
        else:
            missatge_assistent(m['r'], detall)
