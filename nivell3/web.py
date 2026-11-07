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
from agent import Agent  # noqa: E402

MAX_FONTS = 200
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


def main() -> None:
    st.set_page_config(page_title="Assistent d'horaris", page_icon='🗓️', layout='wide')
    st.title("Assistent d'horaris · Escola d'Enginyeria")
    if 'agent' not in st.session_state:
        nova_conversa()

    with st.sidebar:
        st.header('Preguntes d\'exemple')
        exemple = None
        for etiqueta, pregunta in EXEMPLES:
            if st.button(etiqueta, use_container_width=True):
                exemple = pregunta
        st.divider()
        detall = st.toggle('Mostra les eines utilitzades', value=False)
        if st.button('Nova conversa', use_container_width=True):
            nova_conversa()
            st.rerun()
        st.divider()
        st.caption("Horari consultat: la nostra proposta del 5.2 (2n semestre) i l'horari d'avui sense canvis (1r semestre).")

    falten = config.comprova()
    if falten:
        st.error(f"Falta configurar {', '.join(falten)}: copieu nivell3/.env.example com a nivell3/.env i ompliu-lo.")

    for m in st.session_state.historial:
        with st.chat_message(m['rol']):
            if m['rol'] == 'user':
                st.markdown(m['text'])
            else:
                mostra_resposta(m['r'], detall)

    pregunta = st.chat_input('Escriviu una pregunta sobre l\'horari…') or exemple
    if pregunta:
        with st.chat_message('user'):
            st.markdown(pregunta)
        st.session_state.historial.append({'rol': 'user', 'text': pregunta})
        agent = st.session_state.agent
        with st.chat_message('assistant'):
            with st.spinner('Consultant l\'horari…'):
                agent.ultim_avis = None
                r = agent.respon(pregunta)
                r['avis'] = agent.ultim_avis
            mostra_resposta(r, detall)
        st.session_state.historial.append({'rol': 'assistant', 'r': r})


main()
