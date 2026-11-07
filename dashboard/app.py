# Tauler per a la presentació: nivell 1 (les dades d'avui), nivell 2 (els horaris nous), el plànol de l'edifici Q i
# l'assistent del nivell 3, en aquest ordre (menú de dalt).
#
#   streamlit run dashboard/app.py        (des de l'arrel del projecte, amb el .venv actiu)
#
# Tot és local (vegeu .streamlit/config.toml): llegeix el paquet i lliuraments/, i només l'assistent parla amb el
# LLM de l'event.
import sys
from pathlib import Path

import streamlit as st

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))

import comu  # noqa: E402

st.set_page_config(page_title="Horaris · Escola d'Enginyeria", page_icon='🗓️', layout='wide')
st.markdown(f'<style>{(AQUI / "estil.css").read_text(encoding="utf-8")}</style>', unsafe_allow_html=True)

falten = comu.dades_ok()
if falten:
    st.error('Falten les dades del repte (no són a git, vegeu SETUP.md): ' + ', '.join(falten))
    st.stop()

PAGINES = AQUI / 'pagines'
pg = st.navigation([
    st.Page(PAGINES / 'inici.py', title='Inici', icon=':material/home:', default=True),
    st.Page(PAGINES / 'nivell1.py', title="1 · Les dades d'avui", icon=':material/query_stats:'),
    st.Page(PAGINES / 'nivell2.py', title='2 · Els horaris nous', icon=':material/calendar_month:'),
    st.Page(PAGINES / 'planol.py', title="3 · L'edifici Q", icon=':material/map:'),
    st.Page(PAGINES / 'assistent.py', title='4 · Assistent', icon=':material/chat:'),
], position='top')
pg.run()
