# Xat web de l'assistent de nivell 3 (Streamlit). Només és la pantalla: la lògica és la mateixa que al terminal
# (agent.Agent, eines i dades).
#
#   streamlit run nivell3/web.py        (des de l'arrel del projecte, amb el .venv actiu)
#
# Sota cada resposta hi ha una taula plegable «Fonts» amb les files reals de cada id_sessio citat. Si hi ha un
# imprevist, també es mostren els esborranys d'avís i el registre de canvis, marcats com a «no enviat».
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

import config  # noqa: E402
import dades  # noqa: E402
import historial  # noqa: E402
from agent import Agent  # noqa: E402

MAX_FONTS = 200

# Estil: amaga l'animació esportiva de Streamlit (el ninot que corre/pedala/neda mentre l'script s'executa),
# el menú i el peu, i dona un aspecte més net al xat.
CSS = """
<style>
[data-testid="stStatusWidget"], [data-testid="stAppDeployButton"], #MainMenu, footer, [data-testid="stDecoration"] { display: none !important; }
.block-container { max-width: 980px; padding-top: 2rem; }
h1 { font-size: 1.7rem !important; font-weight: 700; letter-spacing: -0.01em; }
.subtitol { color: #5b6675; margin: -0.6rem 0 1.2rem 0; font-size: 0.98rem; }
[data-testid="stChatMessage"] { border-radius: 14px; padding: 0.9rem 1.1rem; margin-bottom: 0.6rem;
    border: 1px solid #e3e9f2; }
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) { background: #eef4ff; border-color: #d4e3ff; }
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) { background: #ffffff; }
[data-testid="stSidebar"] .stButton > button { text-align: left; justify-content: flex-start; border-radius: 10px; }
.stButton > button { border-radius: 10px; }
[data-testid="stChatInput"] { border-radius: 14px; }
.targeta-buida { text-align: center; padding: 1.5rem 0 0.5rem 0; color: #5b6675; }
.targeta-buida .gran { font-size: 2.4rem; }
</style>
"""
EXEMPLES = [
    ('On té classe el grup 81 dimarts?', 'On té classe el grup 81 dimarts?'),
    ('Aula de 60+ lliure dijous a les 10', 'Quina aula de 60 places o més està lliure dijous a les 10?'),
    ('Moure el PAUL/452 a les 9.30', 'Què passa si moc el PAUL/452 de 102750 a les 9.30?'),
    ('Projector de Q1/1003 espatllat', 'El projector de Q1/1003 no funciona el 10 de març. Què fem?'),
    ("Prepara l'avís", "I prepara l'avís"),
    ('Què hi ha dimarts a les 11?', 'Quines classes hi ha dimarts a les 11:00?'),
    ('Aturada general el 9 de març', "Es cancel·la tota l'activitat el 9 de març de 2027 a partir de les 11. Prepara l'avís."),
    ('Què pots fer?', 'Què pots fer?'),
]


class AgentWeb(Agent):
    """Igual que Agent, però recorda l'últim esborrany d'avís per poder-lo mostrar a la pantalla."""

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.ultim_avis: dict | None = None

    def executa(self, nom, arguments):
        r = super().executa(nom, arguments)
        if nom == 'esborrany_avis' and isinstance(r, dict) and 'avisos' in r:
            self.ultim_avis = r
        return r


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


def nova_conversa() -> None:
    st.session_state.agent = AgentWeb()
    st.session_state.historial = []
    st.session_state.xat_id = None   # no es desa fins a la primera pregunta


def obre_conversa(id_: str) -> None:
    d = historial.carrega(id_)
    if d is None:
        st.session_state.avis_xat = "No s'ha pogut obrir aquesta conversa (fitxer trencat o esborrat)."
        return
    a = AgentWeb()
    est = d.get('agent', {})
    a.mode_json = bool(est.get('mode_json'))
    a.missatges = est.get('missatges') or a.missatges
    a.missatges[0] = {'role': 'system', 'content': a._sistema()}   # el prompt de sistema sempre és l'actual
    a.ultim_imprevist = est.get('ultim_imprevist')
    a.ids_vistos = set(est.get('ids_vistos', []))
    st.session_state.agent = a
    st.session_state.historial = d.get('historial', [])
    st.session_state.xat_id = id_


def esborra_conversa(id_: str) -> None:
    historial.esborra(id_)
    if st.session_state.get('xat_id') == id_:
        nova_conversa()


def desa_conversa(primera_pregunta: str) -> None:
    if st.session_state.xat_id is None:
        st.session_state.xat_id = historial.nou_id()
        st.session_state.xat_titol = historial.titol_de(primera_pregunta)
    titol = st.session_state.get('xat_titol') or historial.titol_de(primera_pregunta)
    try:
        historial.desa(st.session_state.xat_id, titol, st.session_state.historial, st.session_state.agent)
    except OSError as e:
        st.session_state.avis_xat = f"No s'ha pogut desar la conversa: {e}"


def main() -> None:
    st.set_page_config(page_title="Assistent d'horaris", page_icon='🗓️', layout='centered')
    st.markdown(CSS, unsafe_allow_html=True)
    st.title("🗓️ Assistent d'horaris · Escola d'Enginyeria")
    st.markdown('<div class="subtitol">Pregunteu per aules, grups, franges lliures o imprevistos. '
                'Només redacta esborranys: no envia res a ningú.</div>', unsafe_allow_html=True)
    if 'agent' not in st.session_state:
        nova_conversa()

    with st.sidebar:
        st.button('➕ Nova conversa', use_container_width=True, type='primary', on_click=nova_conversa)
        st.subheader('Converses anteriors')
        desades = historial.llista()
        if not desades:
            st.caption("Encara no n'hi ha cap: es desen soles a mesura que preguntes.")
        for c in desades[:30]:
            actual = c['id'] == st.session_state.xat_id
            col1, col2 = st.columns([6, 1])
            col1.button(c['titol'], key=f"obre_{c['id']}", use_container_width=True, help=c['data'].replace('T', ' '),
                        type='primary' if actual else 'secondary',
                        on_click=obre_conversa, args=(c['id'],))
            col2.button('', icon=':material/delete:', key=f"del_{c['id']}", help='Esborra aquesta conversa',
                        on_click=esborra_conversa, args=(c['id'],))
        if len(desades) > 30:
            st.caption(f'Es mostren les 30 més recents de {len(desades)}.')
        st.divider()
        detall = st.toggle('Mostra les eines utilitzades', value=False)
        st.caption("Les converses es desen només en aquest ordinador (nivell3/xats/).")
        st.caption("Horari consultat: la nostra proposta del 5.2 (2n semestre) i l'horari d'avui sense canvis (1r semestre).")

    exemple = None
    if 'avis_xat' in st.session_state:
        st.warning(st.session_state.pop('avis_xat'))

    falten = config.comprova()
    if falten:
        st.error(f"Falta configurar {', '.join(falten)}: copieu nivell3/.env.example com a nivell3/.env i ompliu-lo.")

    if not st.session_state.historial:
        st.markdown('<div class="targeta-buida"><div class="gran">💬</div>'
                    '<b>Com us puc ajudar?</b><br>Escriviu una pregunta o proveu un exemple.</div>',
                    unsafe_allow_html=True)
        cols = st.columns(2)
        for i, (etiqueta, pregunta) in enumerate(EXEMPLES[:6]):
            if cols[i % 2].button(etiqueta, use_container_width=True, key=f'main_{etiqueta}'):
                exemple = pregunta

    for m in st.session_state.historial:
        with st.chat_message(m['rol'], avatar='🧑‍🎓' if m['rol'] == 'user' else '🗓️'):
            if m['rol'] == 'user':
                st.markdown(m['text'])
            else:
                mostra_resposta(m['r'], detall)

    pregunta = st.chat_input('Escriviu una pregunta sobre l\'horari…') or exemple
    if pregunta:
        with st.chat_message('user', avatar='🧑‍🎓'):
            st.markdown(pregunta)
        st.session_state.historial.append({'rol': 'user', 'text': pregunta})
        agent = st.session_state.agent
        with st.chat_message('assistant', avatar='🗓️'):
            with st.spinner('Consultant l\'horari…'):
                agent.ultim_avis = None
                r = agent.respon(pregunta)
                r['avis'] = agent.ultim_avis
            mostra_resposta(r, detall)
        st.session_state.historial.append({'rol': 'assistant', 'r': r})
        desa_conversa(pregunta)


main()
