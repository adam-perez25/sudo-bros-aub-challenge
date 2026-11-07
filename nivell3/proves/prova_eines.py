"""Comprova les eines del nivell 3 amb les respostes de proves/README.md (calculades a part). Sense LLM.

Ús (des de l'arrel del projecte, amb el .venv actiu):  python nivell3/proves/prova_eines.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import eines as E  # noqa: E402

resultats = []


def comprova(nom, condicio, detall=''):
    resultats.append(bool(condicio))
    print(f"{'OK ' if condicio else 'KO '} {nom}" + (f'  ({detall})' if detall and not condicio else ''))


r = E.horari_grup(grup='81', dia='M')
comprova('1. grup 81 dimarts: 115 sessions', r['sessions'] == 115, r.get('sessions'))
comprova('1. inclou 104346 TE/81 a Q4/1013 a les 8.30',
         any(p['codi'] == '104346' and p['aula'] == 'Q4/1013' and p['h_ini'] == '08:30' for p in r['setmanal']))

r = E.aules_lliures(hora_inici='10:00', durada_min=60, dia='J', places_min=60)
comprova('2. aules lliures dijous 10.00 (60+)', [a['aula'] for a in r['aules_lliures']] ==
         ['Q2/1009', 'Q4/0003', 'Q3/1011', 'Q1/1011'], [a['aula'] for a in r['aules_lliures']])
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
comprova('7. avaria Q1/1003: 5 canvis només d\'aula, verificats', r['verificacio']['correcte'] and noves == {
    'S02580': 'Q1/1007', 'S02845': 'Q1/1007', 'S03071': 'Q1/1011', 'S06630': 'Q1/1011', 'S06644': 'Q1/1011'}
    and all(c['abans']['h_ini'] == c['despres']['h_ini'] and c['abans']['data'] == c['despres']['data']
            for c in r['canvis']), noves)
comprova('7. relaxacions R1-FIXADA per a S06630 i S06644',
         sorted(x['id_sessio'] for x in r['relaxacions_necessaries']) == ['S06630', 'S06644'])

a = E.esborrany_avis(r['canvis'], 'avaria del projector de Q1/1003')
comprova('8. avisos redactats i no enviats, 5 files de registre', a['enviat'] is False and len(a['registre']) == 5)

r = E.horari_grup(codi='102750', data='2027-04-09')
d380 = sorted((s['id_sessio'], s['h_ini']) for s in r.get('sessions_del_dia', []) if 'D380' in s['docents'])
comprova('9. D380 el 9/4: 12.30, 19.00 i 20.00 a Q1/0019', d380 == [('S04496', '20:00'), ('S04511', '12:30'),
                                                                       ('S04526', '19:00')], d380)

r = E.consulta_sql("SELECT capacitat FROM aules WHERE aula = 'Q4/0011'")
comprova('10. Q4/0011 té 117 places', r['files'] == [['117']], r.get('files'))

r = E.horari_aula('Q1/1011', data='2027-02-01')
comprova('11. Q1/1011 l\'1/2: cap classe', r['sessions'] == 0 and 'avis' in r, r.get('sessions'))

comprova('SQL: no deixa modificar dades', 'error' in E.consulta_sql('DELETE FROM aules'))
comprova('SQL: no deixa llegir fitxers', 'error' in E.consulta_sql("SELECT * FROM read_csv('requirements.txt')"))

print(f'\n{sum(resultats)} de {len(resultats)} comprovacions correctes')
sys.exit(0 if all(resultats) else 1)
