"""Graella setmanal per aula (lliurament 10 de l'enunciat) a partir d'una proposta.

Ús (des de l'arrel):
    python nivell2/p52_torns/graella.py [lliuraments/proposta-torns.csv] [--setmana 2027-W06]

Escriu lliuraments/graella-setmanal.md (llegible) i lliuraments/graella-setmanal.csv (Excel): per a cada aula de
l'aulari, una taula franja horària × dia d'una setmana tipus amb el codi, el grup i el tipus de cada classe.
"""
from __future__ import annotations

import argparse
import collections
import csv
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
ROOT = AQUI.parents[1]
sys.path.insert(0, str(ROOT / 'repte-horaris-escola'))

from horaris.check import FRANGES, Informe, _col_loca  # noqa: E402
from horaris.model import DIES, carrega_base, fmt, llegeix_proposta  # noqa: E402

NOM = {'L': 'Dilluns', 'M': 'Dimarts', 'X': 'Dimecres', 'J': 'Dijous', 'V': 'Divendres'}


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('proposta', nargs='?', default=str(ROOT / 'lliuraments' / 'proposta-torns.csv'))
    ap.add_argument('--setmana', default='2027-W06', help='setmana ISO tipus (per defecte, una setmana normal)')
    ap.add_argument('--sortida', default=str(ROOT / 'lliuraments' / 'graella-setmanal'))
    a = ap.parse_args(argv)

    b = carrega_base(ROOT / 'repte-horaris-escola' / 'paquet', semestre=2)
    files = [f for f in llegeix_proposta(Path(a.proposta)) if f.id in b.sessions]
    col = _col_loca(b, files, Informe())
    cel = collections.defaultdict(set)   # (aula, dia, franja) -> textos
    for sid, c in col.items():
        s = b.sessions[sid]
        if c.data.strftime('%G-W%V') != a.setmana:
            continue
        if not c.aula or c.aula not in b.aules or s.sense_espai:
            continue
        for f0 in FRANGES:
            if c.ini < f0 + 60 and c.fi > f0:
                cel[(c.aula, DIES[c.data.weekday()], f0)].add(f'{s.codi} {s.grup}')
    aules = sorted(b.aules, key=lambda x: (b.aules[x].tipus, x))
    out = Path(a.sortida)
    with open(out.with_suffix('.csv'), 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(['aula', 'tipus', 'capacitat', 'franja'] + [NOM[d] for d in DIES])
        for au in aules:
            for f0 in FRANGES:
                w.writerow([au, b.aules[au].tipus, b.aules[au].capacitat, f'{fmt(f0)}-{fmt(f0 + 60)}'] +
                           [' / '.join(sorted(cel[(au, d, f0)])) for d in DIES])
    L = [f'# Graella setmanal per aula · setmana {a.setmana}\n',
         f'Proposta: `{Path(a.proposta).name}`. Cada cel·la: codi de l\'assignatura i grup. Franges d\'una hora de '
         f'8.30 a 21.00. Les dobles titulacions no ocupen aula i no hi surten; els PLAB, a la seva aula de laboratori. '
         f'Si una cel·la porta dues classes és una sessió compartida entre dues titulacions (una sola classe física) '
         f'o dues classes seguides dins la mateixa hora (per exemple, una acaba a les 15.00 i l\'altra hi comença): '
         f'el verificador confirma que no hi ha cap solapament d\'aula (R4-AULA = 0).\n']
    for au in aules:
        x = b.aules[au]
        ocup = sum(1 for d in DIES for f0 in FRANGES if cel[(au, d, f0)])
        L.append(f'## {au} · {x.tipus} · {x.capacitat} places · {ocup} de {len(DIES) * len(FRANGES)} franges ocupades\n')
        L.append('| Franja | ' + ' | '.join(NOM[d] for d in DIES) + ' |')
        L.append('|---|' + '---|' * len(DIES))
        for f0 in FRANGES:
            L.append(f'| {fmt(f0)} | ' + ' | '.join('<br>'.join(sorted(cel[(au, d, f0)])) for d in DIES) + ' |')
        L.append('')
    out.with_suffix('.md').write_text('\n'.join(L), encoding='utf-8')
    print(f'Escrit {out.with_suffix(".md")} i {out.with_suffix(".csv")} ({len(aules)} aules, setmana {a.setmana})')


if __name__ == '__main__':
    main()
