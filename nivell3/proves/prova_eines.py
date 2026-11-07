"""Comprova les eines del nivell 3 amb les respostes de proves/README.md (calculades a part). Sense LLM.

Ús (des de l'arrel del projecte, amb el .venv actiu):  python nivell3/proves/prova_eines.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import dades as D  # noqa: E402
import eines as E  # noqa: E402

resultats = []


def comprova(nom, condicio, detall=''):
    resultats.append(bool(condicio))
    print(f"{'OK ' if condicio else 'KO '} {nom}" + (f'  ({detall})' if detall and not condicio else ''))


r = E.horari_grup(grup='81', dia='M', semestre=2)
comprova('1. grup 81 dimarts: 115 sessions', r['sessions'] == 115, r.get('sessions'))
comprova('1. inclou 104346 TE/81 a Q4/1013 a les 8.30',
         any(p['codi'] == '104346' and p['aula'] == 'Q4/1013' and p['h_ini'] == '08:30' for p in r['setmanal']))

r = E.aules_lliures(hora_inici='10:00', durada_min=60, dia='J', places_min=60, semestre=2)
comprova('2. aules lliures dijous 10.00 (60+)', [a['aula'] for a in r['aules_lliures']] ==
         ['Q2/1009', 'Q4/0003', 'Q3/1011'], [a['aula'] for a in r['aules_lliures']])
comprova('2. 17 dijous comprovats', r['dates_comprovades'] == 17, r['dates_comprovades'])

r = E.consulta_sql('SELECT count(*) AS n FROM sessions WHERE semestre = 2')
comprova('3. 7.739 sessions al 2n semestre', r['files'] == [['7739']], r.get('files'))

r = E.verifica('partida')
comprova('4. partida: 4.541 sense aula', r['compten'].get('R5-SENSE-AULA') == 4541, r['compten'])

r = E.verifica('torns')
comprova('5. 5.2 vàlida amb 460 relaxacions', r['veredicte'] == 'VALIDA AMB RELAXACIONS DECLARADES'
         and not r['compten'] and r['declarades'] == {'R1-TORN': 460}, (r['veredicte'], r['compten']))

r = E.que_passa_si(codi='102750', grup='PAUL/452', nova_hora='09:30')
regles = {v['regla'] for v in r['incompliments_nous']}
comprova('6. moure PAUL/452 a les 9.30 trenca R1-TORN i R4-PLAB',
         r['n_incompliments_nous'] == 26 and regles == {'R1-TORN', 'R4-PLAB'}, (r['n_incompliments_nous'], regles))

r = E.resol_imprevist('aula_tancada', aula='Q1/1003', data_ini='2027-03-10')
noves = {c['id_sessio']: c['despres']['aula'] for c in r['canvis']}
comprova("7. avaria Q1/1003: canvis només d'aula (mateix dia i hora), verificats, cap a Q1/1003",
         r['verificacio']['correcte'] and r['n_canvis'] > 0 and 'Q1/1003' not in noves.values()
         and all(c['abans']['h_ini'] == c['despres']['h_ini'] and c['abans']['data'] == c['despres']['data']
                 for c in r['canvis']), noves)
comprova('7. relaxacions R1-FIXADA per a S06630 i S06644',
         sorted(x['id_sessio'] for x in r['relaxacions_necessaries']) == ['S06630', 'S06644'])

a = E.esborrany_avis(r['canvis'], 'avaria del projector de Q1/1003')
comprova('8. avisos redactats i no enviats, una fila de registre per canvi', a['enviat'] is False and len(a['registre']) == r['n_canvis'] > 0)

r = E.horari_grup(codi='102750', data='2027-04-09')
d380 = sorted((s['id_sessio'], s['h_ini']) for s in r.get('sessions_del_dia', []) if 'D380' in s['docents'])
comprova('9. D380 el 9/4: 12.30, 19.00 i 20.00 a Q1/0019', d380 == [('S04496', '20:00'), ('S04511', '12:30'),
                                                                       ('S04526', '19:00')], d380)

r = E.consulta_sql("SELECT capacitat FROM aules WHERE aula = 'Q4/0011'")
comprova('10. Q4/0011 té 117 places', r['files'] == [['117']], r.get('files'))

r = E.horari_aula('Q1/1011', data='2027-02-01')
comprova('11. Q1/1011 l\'1/2: cap classe', r['sessions'] == 0 and 'avis' in r, r.get('sessions'))

r = E.aules_lliures(aula='-2')
comprova("12. aula inexistent: ho diu sense demanar l'hora", r.get('trobat') is False and 'No hi ha cap aula' in r['avis'])
r = E.aules_lliures(aula='Q2-1009')
comprova('12. proposa el codi semblant Q2/1009', r.get('aules_semblants', [''])[0] == 'Q2/1009', r.get('aules_semblants'))
r = E.aules_lliures(aula='Q1/1003', hora_inici='10:30', data='2027-02-02')
comprova('13. Q1/1003 el 2/2 a les 10.30 ocupada per S09923', r['n_lliures'] == 0 and r['fonts'] == ['S09923'], r['fonts'])

# --- eines d'ús quotidià (comparades amb pandas directament, sense el codi de les eines)
import agent as A  # noqa: E402

h2 = E.d.horari[E.d.horari['semestre'] == 2]
x = h2[(h2['data_nova'].astype(str) == '2027-02-02') & (h2['ini_min'] < 720) & (h2['fi_min'] > 660)]
r = E.ocupacio('11:00', data='2027-02-02')
comprova('14. ocupacio dimarts 2/2 a les 11: mateix nombre de sessions que pandas', r['sessions'] == len(x) > 0, r.get('sessions'))
r = E.ocupacio('11:00', data='2026-08-10')
comprova('14. ocupacio fora del curs: ho diu', r['trobat'] is False and 'fora del període lectiu' in r['avis'])
r = E.ocupacio('11:00', dia='M', tipus_sessio='PLAB')
comprova('14. ocupacio per dia de la setmana: patró setmanal', r['trobat'] and 'setmanal' in r)

r = E.horari_docent('D380', data='2027-04-09')
comprova('15. docent D380 el 9/4: 3 classes', r['sessions'] == 3 and r['fonts'] == ['S04496', 'S04511', 'S04526'], r.get('fonts'))
comprova('15. docent inexistent: ho diu', E.horari_docent('D99999')['trobat'] is False)

r = E.cerca_assignatura('Grafs')
comprova('16. cerca assignatura: Grafs -> 104349', r['trobat'] and r['assignatures'][0]['codi'] == '104349')
comprova('16. assignatura inexistent: ho diu', E.cerca_assignatura('Quimica quantica')['trobat'] is False)

r = E.info_aules(places_min=150)
comprova('17. aules de 150+ places: només Q1/1011', [a['aula'] for a in r['aules']] == ['Q1/1011'], r.get('aules'))

r = E.reserva_aules(semestre=2)
comprova('18. reserva de 2 aules: es compleix tot el semestre', r['compleix_regla_8'] and r['dates_comprovades'] == 83, r)

r = E.sessions_canviades(cohort='GEI:3r')
canv = h2[h2['titulacions_curs'].str.contains('GEI:3r', regex=False) & ((h2['dia'] != h2['dia_nou']) | (h2['h_ini'] != h2['h_ini_nou']))]
comprova('19. sessions canviades de GEI:3r: mateix nombre que pandas', r['canviades'] == len(canv) > 0, (r.get('canviades'), len(canv)))

r = E.calendari_info('2027-03-26')
comprova('20. calendari: 26/3 és festiu (Divendres Sant)', 'Divendres Sant' in r['consulta']['avis'], r['consulta'])

r = E.aturada('2027-03-09', '11:00')
y = h2[(h2['data_nova'].astype(str) == '2027-03-09') & (h2['ini_min'] >= 660) & (h2['sense_espai'] != '1')]
comprova('21. aturada 9/3 des de les 11: sessions que comencen a partir de les 11', r['sessions_afectades'] == len(y) > 0,
         r.get('sessions_afectades'))
comprova('21. aturada fora del curs: error clar', 'fora del període lectiu' in E.aturada('2026-08-10', '11:00')['error'])
a = E.esborrany_avis(r['canvis'], 'aturada general')
comprova("21. avís d'aturada: esborrany no enviat, diu «cancel·lada»",
         a['enviat'] is False and len(a['registre']) == r['sessions_afectades'] and 'cancel·lada' in a['registre'][0]['a'])

ag = A.Agent(cridar=lambda m, e: {'content': ''})
res = ag.executa('aturada', {'data': '2027-03-09', 'h_ini': '11:00'})
comprova("22. l'agent no reenvia al LLM la llista completa de l'aturada, però la guarda per a l'avís",
         'canvis' not in res and ag.ultim_imprevist and len(ag.ultim_imprevist['canvis']) == r['sessions_afectades'])
comprova('22. eina inexistent: error net (no cau)', 'error' in ag.executa('envia_correu', {'a': 'x'}))
comprova("23. ajuda: diu què no pot fer (enviar, canviar l'horari oficial)",
         any('Enviar' in t for t in E.ajuda()['no_pot_fer']) and any('oficial' in t for t in E.ajuda()['no_pot_fer']))
comprova('23. el prompt inclou la regla de «cap eina encaixa»', 'CAP EINA NO ENCAIXA' in A.prompts.SISTEMA)


# ---- 1r semestre (l'horari d'avui, que el 5.2 no canvia): respostes calculades a part amb pandas
h1 = D.carrega().horari
h1 = h1[h1['semestre'] == 1]
r = E.horari_grup(grup='81', dia='M', semestre=1)
y = h1[h1['grup'].str.match(r'^[A-Z]+/81\d*$') & (h1['dia_nou'] == 'M')]
comprova('S1-1. grup 81 dimarts al 1r semestre: mateix nombre que pandas', r['sessions'] == len(y) > 0, (r['sessions'], len(y)))
r = E.horari_grup(grup='81', dia='M')
comprova('S1-2. grup 81 dimarts sense semestre: surten els dos semestres, etiquetats',
         {p['semestre'] for p in r['setmanal']} == {1, 2})
r = E.ocupacio('11:00', data='2026-10-13')
x = h1[(h1['data_nova'].astype(str) == '2026-10-13') & (h1['ini_min'] < 720) & (h1['fi_min'] > 660) & (h1['sense_espai'] != '1')]
comprova('S1-3. ocupació dimarts 13/10/2026 a les 11: mateix nombre que pandas', r['sessions'] == len(x) > 0, r.get('sessions'))
r = E.aules_lliures(hora_inici='10:00', data='2026-10-15', places_min=60)
ocup = set(h1[(h1['data_nova'].astype(str) == '2026-10-15') & (h1['ini_min'] < 660) & (h1['fi_min'] > 600)]['aula_nova'])
comprova("S1-4. aules lliures 15/10/2026 a les 10: cap té classe a l'horari", r['aules_lliures'] and
         not {a['aula'] for a in r['aules_lliures']} & ocup, [a['aula'] for a in r['aules_lliures']])
r = E.aules_lliures(hora_inici='10:00', dia='J', places_min=60)
comprova('S1-5. aules lliures un dia de la setmana sense semestre: es donen per separat', set(r['per_semestre']) == {'semestre_1', 'semestre_2'})
r = E.calendari_info('2026-12-08')
comprova('S1-6. calendari: 8/12 és festiu del 1r semestre', r['consulta']['semestre'] == 1 and 'Immaculada' in r['consulta']['avis'], r['consulta'])
r = E.verifica('torns', 1)
comprova("S1-7. verificador del 1r semestre: NO VALIDA (l'horari d'avui, 9.287 sessions) amb R1-TORN",
         r['veredicte'] == 'NO VALIDA' and r['compten'].get('R1-TORN', 0) > 0, (r['veredicte'], r['compten']))
comprova('S1-8. proposta del nivell 2 al 1r semestre: error clar', 'error' in E.verifica('aules', 1))
sid = h1['id_sessio'].iloc[0]
r = E.que_passa_si(id_sessio=sid, nova_hora='19:30')
comprova('S1-9. què passa si en una sessió del 1r semestre: usa el semestre 1', r.get('semestre') == 1 and 'error' not in r, r)
r = E.resol_imprevist('aula_tancada', aula='Q1/1003', data_ini='2026-10-15')
comprova("S1-10. imprevist al 1r semestre: tria el semestre 1 i canvia només sessions d'aquell dia",
         r.get('semestre') == 1 and r['n_canvis'] > 0 and all(c['abans']['data'] == '2026-10-15' for c in r['canvis']), r.get('error'))
r = E.aturada('2026-10-15', '11:00')
y = h1[(h1['data_nova'].astype(str) == '2026-10-15') & (h1['ini_min'] >= 660) & (h1['sense_espai'] != '1')]
comprova('S1-11. aturada al 1r semestre: sessions que comencen a partir de les 11', r['sessions_afectades'] == len(y) > 0)
r = E.cerca_assignatura('Càlcul')
comprova("S1-12. cerca d'assignatura: diu els semestres", all('semestres' in a for a in r['assignatures']) and
         any(a['semestres'] == [1] for a in r['assignatures']))
comprova('S1-13. data en català: 13 d octubre de 2026', str(E._data("13 d'octubre de 2026")) == '2026-10-13')

# ---- dates: el codi calcula els dies de la setmana, i un cap de setmana no té classes
import datetime as _dt  # noqa: E402
demà = _dt.date.today() + _dt.timedelta(days=1)
comprova('dates relatives: «demà» i «avui»', E._data('demà') == demà and E._data('avui') == _dt.date.today())
r = E.aules_lliures(hora_inici='11:00', data='2026-11-08')
comprova('diumenge: no es dona cap llista d\'aules lliures i diu «diumenge»',
         r['trobat'] is False and 'diumenge' in r['avis'] and 'aules_lliures' not in r, r)
r = E.aules_lliures(hora_inici='11:00', data='2026-11-09')
comprova('dilluns 9/11: surt el dia de la setmana calculat pel codi', r['dia_consultat'] == 'dilluns 2026-11-09', r.get('dia_consultat'))
comprova('ocupació en cap de setmana: avís', 'cap de setmana' in E.ocupacio('11:00', data='2026-11-07')['avis'])
comprova('horari d\'un grup en cap de setmana: avís', 'cap de setmana' in E.horari_grup(grup='81', data='2026-11-08')['avis'])
p = A.prompts.sistema()
comprova('el prompt porta avui amb el dia de la setmana i els propers 15 dies',
         f'{A.prompts.NOMS_DIA[_dt.date.today().weekday()]} {_dt.date.today().isoformat()}' in p
         and f'{A.prompts.NOMS_DIA[demà.weekday()]} {demà.isoformat()}' in p and '{PROPERS}' not in p)

comprova('SQL: no deixa modificar dades', 'error' in E.consulta_sql('DELETE FROM aules'))
comprova('SQL: no deixa llegir fitxers', 'error' in E.consulta_sql("SELECT * FROM read_csv('requirements.txt')"))

print(f'\n{sum(resultats)} de {len(resultats)} comprovacions correctes')
sys.exit(0 if all(resultats) else 1)
