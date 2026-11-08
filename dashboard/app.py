# Tauler per a la presentació: nivell 1 (les dades d'avui), nivell 2 (els horaris nous) i el plànol de l'edifici Q, en
# aquest ordre (menú de dalt). L'assistent del nivell 3 és una bombolla flotant a baix a la dreta, a totes les pàgines, i una pàgina pròpia («Assistent») per a converses llargues.
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

import bombolla  # noqa: E402
import comu  # noqa: E402

st.set_page_config(page_title="Horaris · Escola d'Enginyeria", page_icon='🗓️', layout='wide')
st.markdown(f'<style>{(AQUI / "estil.css").read_text(encoding="utf-8")}</style>', unsafe_allow_html=True)

falten = comu.dades_ok()
if falten:
    st.error('Falten les dades del repte (no són a git, vegeu SETUP.md): ' + ', '.join(falten))
    st.stop()

PAGINES = AQUI / 'pagines'
pagina_xat = st.Page(PAGINES / 'assistent.py', title='Assistent', icon=':material/forum:', url_path=bombolla.PAGINA_GRAN)
pg = st.navigation([
    st.Page(PAGINES / 'inici.py', title='Inici', icon=':material/home:', default=True),
    st.Page(PAGINES / 'nivell1.py', title="1 · Les dades d'avui", icon=':material/query_stats:'),
    st.Page(PAGINES / 'nivell2.py', title='2 · Els horaris nous', icon=':material/calendar_month:'),
    st.Page(PAGINES / 'planol.py', title="3 · L'edifici Q", icon=':material/map:'),
    pagina_xat,
], position='top')
bombolla.munta(pagina_xat)      # abans de pg.run(): una pàgina que fa st.stop() no pot amagar la bombolla
pg.run()
