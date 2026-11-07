# Converses anteriors del xat web: un fitxer JSON per conversa a nivell3/xats/ (només en aquest ordinador, no es
# puja al repositori). Es desa el que es veu a la pantalla (historial) i l'estat de l'agent, perquè es pugui
# continuar una conversa antiga amb el context de les preguntes anteriors.
import json
import re
import uuid
from datetime import datetime
from pathlib import Path

DIR = Path(__file__).resolve().parent / 'xats'
ID_VALID = re.compile(r'^[0-9]{8}-[0-9]{6}-[0-9a-f]{6}$')


def nou_id() -> str:
    return datetime.now().strftime('%Y%m%d-%H%M%S-') + uuid.uuid4().hex[:6]


def _cami(id_: str) -> Path:
    if not ID_VALID.match(id_):   # l'id acaba en un nom de fitxer: només s'accepta el format que generem nosaltres
        raise ValueError(f'Identificador de conversa no vàlid: {id_!r}')
    return DIR / f'{id_}.json'


def titol_de(pregunta: str, n: int = 45) -> str:
    t = ' '.join(pregunta.split())
    return t if len(t) <= n else t[:n - 1] + '…'


def desa(id_: str, titol: str, historial: list[dict], agent) -> None:
    DIR.mkdir(exist_ok=True)
    dades = {'id': id_, 'titol': titol, 'data': datetime.now().isoformat(timespec='seconds'),
             'historial': historial,
             'agent': {'missatges': agent.missatges, 'mode_json': agent.mode_json,
                       'ultim_imprevist': agent.ultim_imprevist, 'ids_vistos': sorted(agent.ids_vistos)}}
    cami = _cami(id_)
    tmp = cami.with_suffix('.tmp')
    tmp.write_text(json.dumps(dades, ensure_ascii=False, default=str), encoding='utf-8')
    tmp.replace(cami)   # escriptura atòmica: un tall a mig desat no deixa un fitxer trencat


def carrega(id_: str) -> dict | None:
    try:
        return json.loads(_cami(id_).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None


def llista() -> list[dict]:
    """Les converses desades, la darrera modificada primer: [{'id', 'titol', 'data'}]."""
    if not DIR.exists():
        return []
    out = []
    for f in DIR.glob('*.json'):
        if not ID_VALID.match(f.stem):
            continue
        try:
            d = json.loads(f.read_text(encoding='utf-8'))
            out.append({'id': d['id'], 'titol': d.get('titol') or '(sense títol)', 'data': d.get('data', '')})
        except (OSError, ValueError, KeyError):
            continue   # fitxer trencat: s'ignora
    return sorted(out, key=lambda x: x['data'], reverse=True)


def esborra(id_: str) -> None:
    _cami(id_).unlink(missing_ok=True)
