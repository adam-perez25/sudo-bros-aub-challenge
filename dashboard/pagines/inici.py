import streamlit as st

st.title("Horaris i espais de l'Escola d'Enginyeria")
st.markdown('<div class="resposta"><b>La pregunta:</b> hi cap el model nou de torns (1r i 2n al matí; 3r, 4t, '
            'dobles titulacions i màsters a la tarda; sempre dues aules ordinàries lliures)? '
            '<b>Sí</b>, amb una proposta que el verificador oficial dona per vàlida i que aguanta imprevistos i un '
            'grau nou.</div>', unsafe_allow_html=True)

TARGETES = [
    ('pagines/nivell1.py', "1 · Les dades d'avui", 'Com s\'usen les aules avui',
     "El 74 % de les sessions del 2n semestre no tenen aula, 2.008 sessions són al torn equivocat i el límit "
     "real és el pic del dimarts al matí."),
    ('pagines/nivell2.py', '2 · Els horaris nous', '5.1, 5.2, 5.3 i 5.4',
     'Totes quatre propostes són vàlides. Hores mortes −22 %, cap desplaçament d\'edifici, imprevistos resolts '
     'amb 56 canvis i el grau nou hi cap sense moure res.'),
    ('pagines/planol.py', "3 · L'edifici Q", 'Els plànols, amb l\'horari a sobre',
     'Qui hi ha a cada aula a qualsevol hora, avui i amb cada proposta. També les aules tancades del 5.3.'),
    (None, '4 · Assistent', 'Preguntes en directe',
     "La bombolla de baix a la dreta, a totes les pàgines. Respon només amb dades de les eines i cita les "
     "sessions; quan parla d'una aula, la mostra al plànol."),
]
cols = st.columns(4)
for col, (pag, titol, sub, text) in zip(cols, TARGETES):
    with col:
        st.markdown(f'<div class="targeta"><div class="etiqueta">{sub}</div><div class="gran">{titol}</div>'
                    f'<div class="peu">{text}</div></div>', unsafe_allow_html=True)
        if pag:
            st.page_link(pag, label='Obre', icon=':material/arrow_forward:')
        else:
            st.caption('Obriu-la amb el botó 💬 de baix a la dreta ↘')

st.caption("Equip sudo bros · UAB The Hack 2026 · Dades pseudonimitzades del pla docent 2026-27, només en aquest "
           "ordinador.")
