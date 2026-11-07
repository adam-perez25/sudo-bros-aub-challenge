# Xat web de l'assistent de nivell 3 (Streamlit). Aquest fitxer només munta la pantalla; cada cosa és al seu lloc:
#   xat/vistes.py      tot el que es dibuixa
#   xat/estils.css     l'estil (CSS)
#   xat/estat.py       l'estat de la conversa i les converses anteriors (st.session_state)
#   xat/agent_web.py   l'agent (el mateix que al terminal, amb un afegit pels avisos)
#   xat/exemples.py    les preguntes d'exemple
#   historial.py       desa/llegeix les converses (fitxers JSON a nivell3/xats/)
#   agent.py, eines.py, dades.py   la lògica de l'assistent (la mateixa que al terminal)
#
#   streamlit run nivell3/web.py        (des de l'arrel del projecte, amb el .venv actiu)
#
# Sota cada resposta hi ha una taula plegable «Fonts» amb les files reals de cada id_sessio citat. Si hi ha un
# imprevist, també es mostren els esborranys d'avís i el registre de canvis, marcats com a «no enviat».
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import streamlit as st  # noqa: E402

import config  # noqa: E402
from xat import estat, vistes  # noqa: E402


def respon(pregunta: str, detall: bool) -> None:
    vistes.missatge_usuari(pregunta)
    st.session_state.historial.append({'rol': 'user', 'text': pregunta})
    agent = st.session_state.agent
    with st.chat_message('assistant', avatar=vistes.AVATAR['assistant']):
        with st.spinner("Consultant l'horari…"):
            agent.ultim_avis = None
            r = agent.respon(pregunta)
            r['avis'] = agent.ultim_avis
        vistes.mostra_resposta(r, detall)
    st.session_state.historial.append({'rol': 'assistant', 'r': r})
    estat.desa_conversa(pregunta)


def main() -> None:
    st.set_page_config(page_title="Assistent d'horaris", page_icon='🗓️', layout='centered')
    vistes.carrega_estils()
    vistes.capcalera()
    estat.inicia()
    detall = vistes.barra_lateral()
    vistes.avis_pendent()

    falten = config.comprova()
    if falten:
        st.error(f"Falta configurar {', '.join(falten)}: copieu nivell3/.env.example com a nivell3/.env i ompliu-lo.")

    exemple = None if st.session_state.historial else vistes.pantalla_inicial()
    vistes.historial_xat(detall)
    pregunta = st.chat_input("Escriviu una pregunta sobre l'horari…") or exemple
    if pregunta:
        respon(pregunta, detall)


main()
