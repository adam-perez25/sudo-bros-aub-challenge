# L'assistent del nivell 3 com a bombolla flotant a baix a la dreta, a totes les pàgines del tauler. Fa servir el mateix
# agent, les mateixes eines i les mateixes vistes que nivell3/web.py (que continua anant sol); només canvia on es
# dibuixa. La conversa viu a st.session_state, així que continua quan es canvia de pàgina.
import sys
from pathlib import Path

import streamlit as st

NIVELL3 = Path(__file__).resolve().parents[1] / 'nivell3'
sys.path.insert(0, str(NIVELL3))

import config  # noqa: E402  (nivell3/config.py)
import historial  # noqa: E402  (nivell3/historial.py: les converses desades)
from xat import estat, vistes  # noqa: E402
from xat.exemples import EXEMPLES  # noqa: E402

AMPLADA_PLANOL = 395        # el plànol dins la bombolla (el quadre d'un missatge fa uns 420 px)
ALCADA_XAT = 440            # alçada de la zona de missatges (amb desplaçament)
MAX_CONVERSES = 40          # converses anteriors que es mostren (les més recents)


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


def _vista(v: str) -> None:
    st.session_state.bombolla_vista = v


def _nova() -> None:
    estat.nova_conversa()
    _vista('xat')


def _obre(id_: str) -> None:
    estat.obre_conversa(id_)
    _vista('xat')


def _converses() -> None:
    """Llista de converses anteriors: obrir-ne una (torna al xat) o esborrar-la."""
    desades = historial.llista()
    with st.container(height=ALCADA_XAT + 62, border=False):
        if not desades:
            st.caption("Encara no n'hi ha cap: es desen soles a mesura que preguntes.")
        for c in desades[:MAX_CONVERSES]:
            actual = c['id'] == st.session_state.get('xat_id')
            titol, data, esborra = st.columns([6, 2.4, 1], vertical_alignment='center')
            titol.button(c['titol'], key=f"bombolla_obre_{c['id']}", use_container_width=True,
                         type='primary' if actual else 'secondary', on_click=_obre, args=(c['id'],),
                         help='Obre aquesta conversa')
            d = c['data']
            data.caption(f'{d[8:10]}/{d[5:7]} {d[11:16]}' if len(d) >= 16 else '')
            esborra.button('', icon=':material/delete:', key=f"bombolla_del_{c['id']}", help='Esborra aquesta conversa',
                           on_click=estat.esborra_conversa, args=(c['id'],))
        if len(desades) > MAX_CONVERSES:
            st.caption(f'Es mostren les {MAX_CONVERSES} més recents de {len(desades)}.')


@st.fragment
def _contingut() -> None:
    """Fragment: canviar de vista (xat/converses), enviar o esborrar només re-executa la bombolla, no tota la
    pàgina; així no hi ha el parpelleig de contingut vell i nou barrejats mentre la pàgina es recalcula."""
    en_converses = st.session_state.get('bombolla_vista') == 'converses'
    cap, hist, nova = st.columns([2.6, 2.1, 1.5], vertical_alignment='center')
    cap.markdown("**🗓️ Assistent**")
    if en_converses:
        hist.button('Al xat', icon=':material/chat:', on_click=_vista, args=('xat',), use_container_width=True,
                    help='Torna a la conversa actual')
    else:
        hist.button('Converses', icon=':material/history:', on_click=_vista, args=('converses',),
                    use_container_width=True, help='Converses anteriors')
    nova.button('Nova', icon=':material/add:', on_click=_nova, use_container_width=True,
                help='Comença una conversa nova')
    vistes.avis_pendent()
    falten = config.comprova()
    if falten:
        st.error(f"Falta configurar {', '.join(falten)} (vegeu nivell3/README.md).")

    if en_converses:
        _converses()
        return

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
