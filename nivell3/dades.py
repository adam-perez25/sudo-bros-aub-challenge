# Dades: carrega una sola vegada sessions.csv, aules.csv, calendari.csv i la proposta (horari actual) i les deixa
# preparades per consultar (per exemple, taules de DuckDB). Només lectura.
#
# Ús des d'un altre fitxer (eines.py, agent.py...):
#
#     from dades import carrega
#     d = carrega()          # la primera vegada llegeix els fitxers; les següents torna el mateix objecte
#     d.sessions             # una fila per sessió (sessions.csv del paquet)
#     d.aules                # les 56 aules (aules.csv)
#     d.calendari            # festius, aturades i setmanes d'avaluació (calendari.csv)
#     d.horari               # L'HORARI ACTUAL: cada sessió amb la data, l'hora i l'aula de la proposta
#
# Per provar-ho:  python nivell3/dades.py   (des de l'arrel del projecte, amb el .venv actiu)
import datetime as dt
import sys
from pathlib import Path

import pandas as pd

AQUI = Path(__file__).resolve().parent          # .../hackathon2026/nivell3
ROOT = AQUI.parent                              # .../hackathon2026  (l'arrel del projecte)
sys.path.insert(0, str(ROOT / 'repte-horaris-escola'))

PAQUET = ROOT / 'repte-horaris-escola' / 'paquet'          # les dades del repte (no són a git: vegeu SETUP.md)
LLIURAMENTS = ROOT / 'lliuraments'
PROPOSTA_PER_DEFECTE = LLIURAMENTS / 'proposta-torns.csv'  # el nostre 5.2: és l'«horari actual» de l'assistent
PROPOSTA_PARTIDA = PAQUET / 'proposta_partida.csv'         # l'horari d'avui, sense canvis

DIES = ['L', 'M', 'X', 'J', 'V']


def llegeix_csv(path: Path) -> pd.DataFrame:
    """Llegeix un CSV del repte tal com és: tot com a text, sense convertir els buits en NaN.
    (utf-8-sig: si algú ha desat el fitxer amb Excel, porta una marca BOM al principi.)"""
    if not path.exists():
        raise FileNotFoundError(f"No trobo {path}. Les dades del repte s'han de descarregar a part (vegeu SETUP.md).")
    return pd.read_csv(path, dtype=str, keep_default_na=False, encoding='utf-8-sig')


def semestre_de(data: dt.date) -> int:
    """Com el verificador: de setembre a gener és el 1r semestre, de febrer a agost el 2n (manen les dates)."""
    return 1 if data.month >= 9 or data.month == 1 else 2


class Dades:
    """Totes les taules carregades, i l'horari actual (sessions + proposta) ja combinat."""

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

    def _combina(self) -> pd.DataFrame:
        """L'horari actual: cada sessió amb la data, l'hora i l'aula que li dona la proposta.

        La proposta només diu el dia de la setmana: la data nova és aquell dia dins la MATEIXA setmana que la data
        original (com fa el verificador). Si la proposta porta una data explícita (sessió recuperada), mana aquesta."""
        p = self.proposta.rename(columns={'dia': 'dia_nou', 'h_ini': 'h_ini_nou', 'aula': 'aula_nova',
                                          'data': 'data_explicita'})
        h = self.sessions.merge(p, on='id_sessio', how='left')

        def data_nova(fila):
            if fila['data_explicita']:
                return dt.date.fromisoformat(fila['data_explicita'])
            if fila['dia_nou'] not in DIES:          # la proposta no porta la sessió: es queda on era
                return fila['data']
            return fila['data'] + dt.timedelta(days=DIES.index(fila['dia_nou']) - fila['data'].weekday())

        h['data_nova'] = h.apply(data_nova, axis=1)
        h['dia_nou'] = h['data_nova'].map(lambda d: DIES[d.weekday()] if d.weekday() < 5 else '?')
        h['h_ini_nou'] = h['h_ini_nou'].where(h['h_ini_nou'].fillna('') != '', h['h_ini'])
        h['aula_nova'] = h['aula_nova'].fillna('')
        minuts = h['h_ini_nou'].map(lambda x: int(x[:2]) * 60 + int(x[3:5]))
        h['h_fi_nou'] = (minuts + h['durada_min']).map(lambda m: f'{m // 60:02d}:{m % 60:02d}')
        h['setmana_nova'] = h['data_nova'].map(lambda d: d.strftime('%G-W%V'))
        return h


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
    print(f"Sessions: {len(d.sessions)} (1r semestre {(d.sessions['semestre'] == 1).sum()}, "
          f"2n semestre {(d.sessions['semestre'] == 2).sum()})")
    print(f"Aules: {len(d.aules)} · dies al calendari: {len(d.calendari)}")
    h2 = d.horari[d.horari['semestre'] == 2]
    sense = h2[(h2['aula_nova'] == '') & (h2['tipus'] != 'PLAB') & (h2['sense_espai'] != '1')]
    print(f"Horari actual, 2n semestre: {len(h2)} sessions; sense aula (sense comptar PLAB ni dobles): {len(sense)}")
    print(h2[['id_sessio', 'codi', 'grup', 'data_nova', 'dia_nou', 'h_ini_nou', 'h_fi_nou', 'aula_nova']].head())
