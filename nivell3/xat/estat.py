# Estat del xat a st.session_state: conversa actual, obrir/esborrar/desar converses anteriors.
# Aquí no es dibuixa res: només es canvia l'estat. Les converses es guarden amb historial.py.
import streamlit as st

import historial
from xat.agent_web import AgentWeb


def inicia() -> None:
    if 'agent' not in st.session_state:
        nova_conversa()


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
