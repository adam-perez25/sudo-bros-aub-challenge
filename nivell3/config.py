# Configuració: llegeix de l'entorn (fitxer local de secrets, mai a git) l'adreça del LLM de l'event, el nom del
# model i la clau; i defineix les rutes a les dades (repte-horaris-escola/paquet) i a la proposta que fa d'«horari
# actual» (per defecte lliuraments/proposta-torns.csv).
#
# Cada persona crea el seu fitxer local a partir de la plantilla nivell3/.env.example (copiar-lo amb el nom «.env»
# a la mateixa carpeta i omplir-lo). Aquest fitxer no es puja mai a git (.gitignore). Les variables també es poden
# definir directament a l'entorn del sistema, i llavors manen aquestes.
from __future__ import annotations

import os
from pathlib import Path

AQUI = Path(__file__).resolve().parent
FITXER_LOCAL = AQUI / '.env'


def _llegeix_fitxer_local() -> dict:
    """Llegeix línies CLAU=valor del fitxer local (si existeix). Ignora comentaris i línies buides."""
    valors = {}
    if FITXER_LOCAL.exists():
        for linia in FITXER_LOCAL.read_text(encoding='utf-8-sig').splitlines():
            linia = linia.strip()
            if not linia or linia.startswith('#') or '=' not in linia:
                continue
            clau, valor = linia.split('=', 1)
            valors[clau.strip()] = valor.strip().strip('"').strip("'")
    return valors


_LOCAL = _llegeix_fitxer_local()


def valor(nom: str, per_defecte: str = '') -> str:
    return os.environ.get(nom) or _LOCAL.get(nom) or per_defecte


LLM_URL = valor('LLM_URL').rstrip('/')        # adreça base compatible amb l'API d'OpenAI (acaba en /v1, normalment)
LLM_MODEL = valor('LLM_MODEL')
LLM_API_KEY = valor('LLM_API_KEY')
LLM_TIMEOUT = int(valor('LLM_TIMEOUT', '90'))  # segons


def comprova() -> list[str]:
    """Què falta per poder parlar amb el LLM (llista buida si tot hi és). No mostra mai la clau."""
    falten = [n for n, v in (('LLM_URL', LLM_URL), ('LLM_MODEL', LLM_MODEL), ('LLM_API_KEY', LLM_API_KEY)) if not v]
    return falten
