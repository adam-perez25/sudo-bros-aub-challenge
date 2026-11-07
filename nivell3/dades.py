# Dades: carrega una sola vegada sessions.csv, aules.csv, calendari.csv i la proposta (horari actual) i les deixa
# preparades per consultar amb DuckDB (SQL). Només lectura.
#
# Ús des d'un altre fitxer (eines.py, agent.py...):
#
#     from dades import carrega
#     d = carrega()                    # la primera vegada llegeix els fitxers; les següents torna el mateix objecte
#     d.sql("SELECT ...")              # SQL de confiança (el nostre codi) -> taula de pandas
#     d.consulta_lectura("SELECT ...") # SQL que ve del LLM: només una SELECT, amb límit de files
#
# Taules SQL disponibles:
#     sessions   una fila per sessió (sessions.csv del paquet), amb la columna semestre (1 o 2)
#     aules      les 56 aules (aules.csv)
#     calendari  festius, aturades i setmanes d'avaluació (calendari.csv)
#     horari     L'HORARI ACTUAL: cada sessió amb data_nova, dia_nou, h_ini_nou, h_fi_nou, ini_min, fi_min,
#                aula_nova i setmana_nova segons la proposta (per defecte, el nostre 5.2)
#
# DuckDB treballa en memòria i sense accés a fitxers (enable_external_access = false, configuració bloquejada): una
# consulta no pot llegir cap fitxer del disc (ni el de les claus) ni escriure'n cap.
#
# Per provar-ho:  python nivell3/dades.py   (des de l'arrel del projecte, amb el .venv actiu)
from __future__ import annotations

import datetime as dt
import re
import sys
from pathlib import Path

import duckdb
import pandas as pd

AQUI = Path(__file__).resolve().parent          # .../hackathon2026/nivell3
ROOT = AQUI.parent                              # .../hackathon2026  (l'arrel del projecte)
sys.path.insert(0, str(ROOT / 'repte-horaris-escola'))

PAQUET = ROOT / 'repte-horaris-escola' / 'paquet'          # les dades del repte (no són a git: vegeu SETUP.md)
LLIURAMENTS = ROOT / 'lliuraments'
PROPOSTA_PER_DEFECTE = LLIURAMENTS / 'proposta-torns.csv'  # el nostre 5.2: és l'«horari actual» de l'assistent
PROPOSTA_PARTIDA = PAQUET / 'proposta_partida.csv'         # l'horari d'avui, sense canvis

DIES = ['L', 'M', 'X', 'J', 'V']
MAX_FILES = 200                                             # files màximes que torna una consulta del LLM
TAULES = ('sessions', 'aules', 'calendari', 'horari')

# paraules que una consulta del LLM no pot contenir (a més, DuckDB no té accés a fitxers)
PROHIBIDES = re.compile(r'\b(insert|update|delete|create|drop|alter|copy|attach|detach|install|load|pragma|set|'
                        r'reset|call|export|import|checkpoint|vacuum|truncate|grant|revoke|use)\b', re.I)


def llegeix_csv(path: Path) -> pd.DataFrame:
    """Llegeix un CSV del repte tal com és: tot com a text, sense convertir els buits en NaN.
    (utf-8-sig: si algú ha desat el fitxer amb Excel, porta una marca BOM al principi.)"""
    if not path.exists():
        raise FileNotFoundError(f"No trobo {path}. Les dades del repte s'han de descarregar a part (vegeu SETUP.md).")
    return pd.read_csv(path, dtype=str, keep_default_na=False, encoding='utf-8-sig')


def semestre_de(data: dt.date) -> int:
    """Com el verificador: de setembre a gener és el 1r semestre, de febrer a agost el 2n (manen les dates)."""
    return 1 if data.month >= 9 or data.month == 1 else 2


def minuts(hhmm: str) -> int:
    return int(hhmm[:2]) * 60 + int(hhmm[3:5])


def hhmm(m: int) -> str:
    return f'{m // 60:02d}:{m % 60:02d}'


class ConsultaNoPermesa(ValueError):
    """La consulta del LLM no és una SELECT de només lectura."""


class Dades:
    """Totes les taules carregades (pandas) i registrades a DuckDB, i l'horari actual (sessions + proposta)."""

    def __init__(self, proposta: Path = PROPOSTA_PER_DEFECTE):
        self.proposta_path = Path(proposta)

        # --- sessions.csv: una fila per sessió de classe datada
        s = llegeix_csv(PAQUET / 'sessions.csv')
        for col in ('durada_min', 'alumnes', 'capacitat_grup'):
            s[col] = pd.to_numeric(s[col], errors='coerce').fillna(0).astype(int)
        s['data'] = pd.to_datetime(s['data']).dt.date
        s['semestre'] = s['data'].map(semestre_de)
        self.sessions = s

        # --- aules.csv: inventari de les 56 aules
        a = llegeix_csv(PAQUET / 'aules.csv')
        a['capacitat'] = a['capacitat'].astype(int)
        a['ordinaria'] = a['ordinaria'].astype(int)
        self.aules = a

        # --- calendari.csv: dates sense classe o amb aturades
        c = llegeix_csv(PAQUET / 'calendari.csv')
        c['data'] = pd.to_datetime(c['data']).dt.date
        self.calendari = c

        # --- la proposta: id_sessio, dia, h_ini, aula (i, al 5.3, una columna data per a la sessió recuperada)
        p = llegeix_csv(self.proposta_path)
        if 'data' not in p.columns:
            p['data'] = ''
        self.proposta = p[['id_sessio', 'dia', 'h_ini', 'aula', 'data']]

        self.horari = self._combina()
        self.con = self._connecta()

    # ------------------------------------------------------------------------------------------- horari
    def _combina(self) -> pd.DataFrame:
        """L'horari actual: cada sessió amb la data, l'hora i l'aula que li dona la proposta.

        La proposta només diu el dia de la setmana: la data nova és aquell dia dins la MATEIXA setmana que la data
        original (com fa el verificador). Si la proposta porta una data explícita (sessió recuperada), mana aquesta."""
        p = self.proposta.rename(columns={'dia': 'dia_nou', 'h_ini': 'h_ini_nou', 'aula': 'aula_nova',
                                          'data': 'data_explicita'})
        h = self.sessions.merge(p, on='id_sessio', how='left')

        def data_nova(fila):
            if isinstance(fila['data_explicita'], str) and fila['data_explicita']:
                return dt.date.fromisoformat(fila['data_explicita'])
            if fila['dia_nou'] not in DIES:          # la proposta no porta la sessió: es queda on era
                return fila['data']
            return fila['data'] + dt.timedelta(days=DIES.index(fila['dia_nou']) - fila['data'].weekday())

        h['data_nova'] = h.apply(data_nova, axis=1)
        h['dia_nou'] = h['data_nova'].map(lambda d: DIES[d.weekday()] if d.weekday() < 5 else '?')
        h['h_ini_nou'] = h['h_ini_nou'].where(h['h_ini_nou'].fillna('') != '', h['h_ini'])
        h['aula_nova'] = h['aula_nova'].fillna('')
        h['ini_min'] = h['h_ini_nou'].map(minuts)
        h['fi_min'] = h['ini_min'] + h['durada_min']
        h['h_fi_nou'] = h['fi_min'].map(hhmm)
        h['setmana_nova'] = h['data_nova'].map(lambda d: d.strftime('%G-W%V'))
        return h.drop(columns=['data_explicita'])

    # ---------------------------------------------------------------------------------------------- SQL
    def _connecta(self) -> duckdb.DuckDBPyConnection:
        con = duckdb.connect(config={'enable_external_access': False})
        for nom in TAULES:
            con.register(nom, getattr(self, nom))
        con.execute('SET lock_configuration = true')    # ningú no pot tornar a obrir l'accés a fitxers
        return con

    def sql(self, consulta: str, params: list | None = None) -> pd.DataFrame:
        """SQL del nostre codi (de confiança): torna una taula de pandas."""
        return self.con.execute(consulta, params or []).df()

    def consulta_lectura(self, consulta: str, max_files: int = MAX_FILES) -> dict:
        """SQL que escriu el LLM: només una SELECT (o WITH ... SELECT), sense ordres que modifiquin res.

        Torna {'columnes', 'files', 'n_files', 'truncat'}. Llança ConsultaNoPermesa si no és de només lectura."""
        q = consulta.strip().rstrip(';').strip()
        if not q or ';' in q:
            raise ConsultaNoPermesa('Només es permet una sola consulta.')
        if not re.match(r'^(select|with)\b', q, re.I):
            raise ConsultaNoPermesa('Només es permeten consultes SELECT.')
        if PROHIBIDES.search(q):
            raise ConsultaNoPermesa('La consulta conté una ordre que no és de lectura.')
        df = self.con.execute(f'SELECT * FROM ({q}) AS consulta LIMIT {max_files + 1}').df()
        truncat = len(df) > max_files
        df = df.head(max_files)
        return {'columnes': list(df.columns), 'files': df.astype(str).values.tolist(), 'n_files': len(df),
                'truncat': truncat}


_CARREGADES: dict = {}


def carrega(proposta: Path = PROPOSTA_PER_DEFECTE) -> Dades:
    """Carrega les dades una sola vegada per proposta (les crides següents tornen el mateix objecte, sense rellegir)."""
    clau = str(Path(proposta).resolve())
    if clau not in _CARREGADES:
        _CARREGADES[clau] = Dades(proposta)
    return _CARREGADES[clau]


if __name__ == '__main__':
    # Prova ràpida: les xifres han de coincidir amb les de l'enunciat i les del verificador.
    d = carrega()
    print(f"Proposta: {d.proposta_path.name}")
    print(d.sql("SELECT semestre, count(*) AS sessions FROM sessions GROUP BY semestre ORDER BY semestre"))
    print(d.sql("SELECT count(*) AS aules, sum(ordinaria) AS ordinaries FROM aules"))
    print(d.sql("""SELECT count(*) AS sense_aula FROM horari
                   WHERE semestre = 2 AND aula_nova = '' AND tipus <> 'PLAB' AND sense_espai <> '1'"""))
    print(d.consulta_lectura("SELECT id_sessio, codi, grup, data_nova, h_ini_nou, h_fi_nou, aula_nova "
                             "FROM horari WHERE semestre = 2 ORDER BY id_sessio", max_files=3))
