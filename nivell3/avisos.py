# Avisos: plantilles per redactar (no enviar) l'avís al docent, als estudiants i a Gestió Acadèmica, i l'entrada del
# registre de canvis: sessió, d'on a on, motiu, a qui afecta i data de l'avís.
#
# Només es redacta: no hi ha adreces al paquet i res no s'envia a ningú. Cada text porta l'id_sessio perquè es pugui
# comprovar al CSV.
from __future__ import annotations

import collections
import datetime as dt

NOM_DIA = {'L': 'dilluns', 'M': 'dimarts', 'X': 'dimecres', 'J': 'dijous', 'V': 'divendres'}


def _franja(c: dict) -> str:
    """'dimarts 09/03/2027 de 10:30 a 12:30 a Q3/1007'"""
    d = dt.date.fromisoformat(c['data'])
    dia = NOM_DIA.get('LMXJV'[d.weekday()] if d.weekday() < 5 else '', '')
    return f"{dia} {d.strftime('%d/%m/%Y')} de {c['h_ini']} a {c['h_fi']} a {c['aula'] or '(sense aula)'}"


def redacta(canvis: list[dict], motiu: str, data_avis: dt.date | None = None) -> dict:
    """canvis: llista de {id_sessio, codi, assignatura, grup, docents, cohorts, abans: {data, h_ini, h_fi, aula},
    despres: {data, h_ini, h_fi, aula}}. Torna els esborranys (per docent, per cohort i per a Gestió Acadèmica) i
    les files del registre de canvis. Res no s'envia."""
    data_avis = data_avis or dt.date.today()
    per_docent = collections.defaultdict(list)
    per_cohort = collections.defaultdict(list)
    registre = []
    for c in canvis:
        linia = (f"- {c['codi']} {c['assignatura']} ({c['grup']}), sessió {c['id_sessio']}: abans {_franja(c['abans'])}; "
                 f"ara {_franja(c['despres'])}.")
        for doc in c.get('docents') or ['(docent sense identificar)']:
            per_docent[doc].append(linia)
        for coh in c.get('cohorts') or ['(cohort desconeguda)']:
            per_cohort[coh].append(linia)
        registre.append({'sessio': c['id_sessio'], 'de': _franja(c['abans']), 'a': _franja(c['despres']),
                         'motiu': motiu, 'afecta': ', '.join((c.get('docents') or []) + (c.get('cohorts') or [])),
                         'data_avis': data_avis.isoformat()})
    avisos = []
    for doc, linies in sorted(per_docent.items()):
        avisos.append({'per_a': f'Docent {doc}', 'text': (
            f"Benvolgut/da {doc},\n\nPer {motiu}, hi ha canvis en sessions que impartiu:\n" + '\n'.join(linies) +
            "\n\nLa resta de l'horari no canvia. Gestió Acadèmica")})
    for coh, linies in sorted(per_cohort.items()):
        avisos.append({'per_a': f'Estudiants de {coh}', 'text': (
            f"Avís per a l'alumnat de {coh}:\n\nPer {motiu}, canvien aquestes sessions:\n" + '\n'.join(linies) +
            "\n\nLa resta de l'horari no canvia. Gestió Acadèmica")})
    avisos.append({'per_a': 'Gestió Acadèmica', 'text': (
        f"Resum de canvis ({motiu}), {len(canvis)} sessions. Registre adjunt; comprovat amb el verificador abans de "
        f"proposar-lo.")})
    return {'enviat': False, 'nota': 'Esborranys: no s\'ha enviat res a ningú.', 'avisos': avisos, 'registre': registre}
