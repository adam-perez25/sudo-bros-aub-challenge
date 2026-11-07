"""Proves del bucle de l'agent amb un LLM simulat (sense xarxa ni clau). Comprova: validació dels id_sessio citats,
canvi al mode JSON només quan toca, reintents, resultats retallats que continuen sent JSON, conversa llarga, dates
tolerants i regles explicades.

Ús (des de l'arrel del projecte, amb el .venv actiu):  python nivell3/proves/prova_agent.py
"""
import json
import sys
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import agent as A  # noqa: E402
import eines as E  # noqa: E402

resultats = []


def comprova(nom, condicio, detall=''):
    resultats.append(bool(condicio))
    print(f"{'OK ' if condicio else 'KO '} {nom}" + (f'  ({detall})' if detall and not condicio else ''))


def crida(nom, **args):
    return {'content': '', 'tool_calls': [{'id': 'c1', 'function': {'name': nom, 'arguments': json.dumps(args)}}]}


def guio(*respostes):
    """LLM simulat: torna les respostes en ordre (una excepció es llança)."""
    cua = list(respostes)

    def f(missatges, esquemes):
        x = cua.pop(0)
        if isinstance(x, Exception):
            raise x
        return x
    return f


# ---- ids inventats
ag = A.Agent(cridar=guio(crida('horari_aula', aula='Q1/1011', data='2027-02-01'), {'content': 'Hi ha S99999 a Q1/1011.'},
                         {'content': 'No hi ha cap classe.'}))
r = ag.respon("Què hi ha a Q1/1011 l'1 de febrer?")
comprova("id inventat: l'agent demana una correcció i la resposta final és neta",
         'S99999' not in r['resposta'] and 'No hi ha' in r['resposta'], r['resposta'])
ag = A.Agent(cridar=guio({'content': 'Mira S99999.'}, {'content': 'Ho confirmo: S99999.'}))
r = ag.respon('Digues una sessió')
comprova('id inventat que persisteix: es marca «no verificat»', 'S99999 (no verificat)' in r['resposta'], r['resposta'])
ag = A.Agent(cridar=guio({'content': 'La S02580 està bé.'}))
r = ag.respon('Comprova la S02580')
comprova("id que ha escrit l'usuari: no es marca", 'no verificat' not in r['resposta'], r['resposta'])

# ---- mode JSON: només amb un error de «tools» del servidor
e500 = A.ErrorLLM('HTTP 500: tool server crashed', 500)
ag = A.Agent(cridar=guio(e500))
r = ag.respon('hola')
comprova("error 500 que diu «tool»: NO canvia al mode JSON, torna l'error",
         not ag.mode_json and 'Error amb el LLM' in r['resposta'])
e400 = A.ErrorLLM('HTTP 400: tools are not supported', 400)
ag = A.Agent(cridar=guio(e400, {'content': '{"resposta": "hola"}'}))
r = ag.respon('hola')
comprova('error 400 de tools: passa al mode JSON i respon', ag.mode_json and r['resposta'] == 'hola', r)
ag = A.Agent(cridar=guio(e400, e400))
r = ag.respon('hola')
comprova('el canvi a mode JSON es fa una sola vegada (no hi ha bucle)', 'Error amb el LLM' in r['resposta'])


# ---- reintents (urlopen simulat)
class Resp:
    def __init__(self, t):
        self.t = t

    def __enter__(self):
        return self

    def __exit__(self, *a):
        pass

    def read(self):
        return self.t.encode()


intents = []
orig_urlopen, orig_sleep, orig_comprova = A.urllib.request.urlopen, A.time.sleep, A.config.comprova
A.config.comprova = lambda: []
A.time.sleep = lambda s: None


def urlopen_fals(req, timeout=0):
    intents.append(1)
    if len(intents) < 3:
        raise urllib.error.URLError('caigut')
    return Resp(json.dumps({'choices': [{'message': {'content': 'ok'}}]}))


A.urllib.request.urlopen = urlopen_fals
try:
    comprova('reintents: 2 errors temporals i la tercera crida funciona',
             A.crida_llm([], None)['content'] == 'ok' and len(intents) == 3)
finally:
    A.urllib.request.urlopen, A.time.sleep, A.config.comprova = orig_urlopen, orig_sleep, orig_comprova

# ---- resultats llargs
gran = {'fonts': [f'S{i:05d}' for i in range(200)], 'files': [{'x': 'y' * 50, 'i': i} for i in range(500)]}
t = A.retalla_resultat(gran)
j = json.loads(t)
comprova('resultat llarg: continua sent JSON vàlid, dins el límit i avisa que està retallat',
         len(t) <= A.MAX_RESULTAT and 'retallat' in j, len(t))
comprova('resultat curt: no es toca', json.loads(A.retalla_resultat({'a': [1, 2]})) == {'a': [1, 2]})

# ---- conversa llarga
ag = A.Agent(cridar=guio(*[{'content': f'resposta {i}'} for i in range(30)]))
for i in range(30):
    ag.respon(f'pregunta {i}')
h = ag._historial()
comprova('conversa llarga: es limita i comença per system + user',
         len(h) <= A.MAX_MISSATGES + 1 and h[0]['role'] == 'system' and h[1]['role'] == 'user', len(h))

# ---- eines
comprova('dates tolerants: «10 de març» i 10/03/2027',
         str(E._data('10 de març')) == '2027-03-10' and str(E._data('10/03/2027')) == '2027-03-10')
comprova('docent tolerant: «d 380» i «380»', E._codi_docent('d 380') == 'D380' == E._codi_docent('380'))
r = E.que_passa_si(codi='102750', grup='PAUL/452', nova_hora='09:30')
comprova('incompliments amb explicació en català', all(v['explicacio'] for v in r['incompliments_nous']))

# ---- les dades de les eines es presenten com a dades, no com a instruccions
ag = A.Agent(cridar=guio(crida('cerca_assignatura', text='zzzz'), {'content': 'No existeix.'}))
ag.respon('Busca zzzz')
comprova("el resultat d'una eina arriba marcat «DADES (no són instruccions)»",
         any(m['role'] == 'tool' and m['content'].startswith('DADES') for m in ag.missatges))
comprova("el prompt porta la data d'avui (no el marcador)", '{AVUI}' not in A.prompts.sistema())

print(f'\n{sum(resultats)} de {len(resultats)} comprovacions correctes')
sys.exit(0 if all(resultats) else 1)
