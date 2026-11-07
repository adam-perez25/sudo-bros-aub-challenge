# L'assistent del nivell 3 com a bombolla flotant a baix a la dreta, a totes les pàgines del tauler. Fa servir el mateix
# agent, les mateixes eines i les mateixes vistes que nivell3/web.py (que continua anant sol); només canvia on es
# dibuixa. La conversa viu a st.session_state, així que continua quan es canvia de pàgina.
import sys
from pathlib import Path

import streamlit as st

NIVELL3 = Path(__file__).resolve().parents[1] / 'nivell3'
sys.path.insert(0, str(NIVELL3))

import config  # noqa: E402  (nivell3/config.py)
from xat import estat, vistes  # noqa: E402
from xat.exemples import EXEMPLES  # noqa: E402

AMPLADA_PLANOL = 395        # el plànol dins la bombolla (el quadre d'un missatge fa uns 420 px)
ALCADA_XAT = 440            # alçada de la zona de missatges (amb desplaçament)


def _pregunta(text: str) -> None:
    st.session_state.bombolla_pendent = text


def _envia() -> None:
    text = (st.session_state.get('bombolla_text') or '').strip()
    if text:
        _pregunta(text)
    st.session_state.bombolla_text = ''


def _respon(pregunta: str) -> None:
    vistes.missatge_usuari(pregunta)
    st.session_state.historial.append({'rol': 'user', 'text': pregunta})
    agent = st.session_state.agent
    with st.chat_message('assistant', avatar=vistes.AVATAR['assistant']):
        with st.spinner("Consultant l'horari…"):
            agent.ultim_avis = None
            r = agent.respon(pregunta)
            r['avis'] = agent.ultim_avis
        vistes.mostra_resposta(r, False, AMPLADA_PLANOL)
    st.session_state.historial.append({'rol': 'assistant', 'r': r})
    estat.desa_conversa(pregunta)


def _contingut() -> None:
    cap, nova = st.columns([4, 1.4], vertical_alignment='center')
    cap.markdown("**🗓️ Assistent d'horaris**")
    nova.button('Nova', icon=':material/add:', on_click=estat.nova_conversa, use_container_width=True,
                help='Comença una conversa nova')
    vistes.avis_pendent()
    falten = config.comprova()
    if falten:
        st.error(f"Falta configurar {', '.join(falten)} (vegeu nivell3/README.md).")

    pendent = st.session_state.pop('bombolla_pendent', None)
    with st.container(height=ALCADA_XAT, border=False):
        if not st.session_state.historial and not pendent:
            st.markdown('<div class="targeta-buida"><div class="gran">💬</div><b>Com us puc ajudar?</b><br>'
                        'Escriviu una pregunta o proveu un exemple.</div>', unsafe_allow_html=True)
            for etiqueta, pregunta in EXEMPLES[:6]:
                st.button(etiqueta, key=f'bombolla_ex_{etiqueta}', on_click=_pregunta, args=(pregunta,),
                          use_container_width=True)
        vistes.historial_xat(False, AMPLADA_PLANOL)
        if pendent:
            _respon(pendent)

    with st.form('bombolla_form', clear_on_submit=False, border=False):
        c1, c2 = st.columns([5, 1.3], vertical_alignment='bottom')
        c1.text_input('Pregunta', key='bombolla_text', placeholder="Escriviu una pregunta sobre l'horari…",
                      label_visibility='collapsed')
        c2.form_submit_button('Envia', icon=':material/send:', on_click=_envia, use_container_width=True)


def munta() -> None:
    """Dibuixa el botó flotant i, quan s'obre, el xat. S'ha de cridar a cada execució, a qualsevol pàgina."""
    estat.inicia()
    with st.container(key='bombolla'):
        with st.popover('💬 Assistent', use_container_width=False):
            _contingut()
