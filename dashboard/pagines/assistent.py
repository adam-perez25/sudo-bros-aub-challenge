# L'assistent del nivell 3, tal com és a nivell3/web.py (la mateixa pantalla, el mateix agent i les mateixes eines).
import runpy
from pathlib import Path

WEB = Path(__file__).resolve().parents[2] / 'nivell3' / 'web.py'
runpy.run_path(str(WEB), run_name='__assistent__')
