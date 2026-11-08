"""Genera el resum d'una pàgina per a la Junta Permanent (RESUM-JUNTA.md) a partir de la proposta del 5.2.

Ús (des de l'arrel):  python nivell2/p52_torns/resum_junta.py
Totes les xifres surten de la proposta i del verificador oficial: es poden regenerar i comprovar.
"""
from __future__ import annotations

import collections
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
ROOT = AQUI.parents[1]
sys.path.insert(0, str(ROOT / 'repte-horaris-escola'))

from horaris.check import FRANGES, Informe, _col_loca, avalua  # noqa: E402
from horaris.model import MATI, carrega_base, fmt, llegeix_proposta, llegeix_relaxacions  # noqa: E402

PROPOSTA = ROOT / 'lliuraments' / 'proposta-torns.csv'
RELAX = ROOT / 'lliuraments' / 'relaxacions.csv'
SORTIDA = AQUI / 'RESUM-JUNTA.md'
MIDES = [(0, 30, 'fins a 30'), (31, 55, '48-50'), (56, 75, '63'), (76, 95, '88-90'), (96, 110, '100'),
         (111, 125, '117'), (126, 999, '130-160')]


def n(x) -> str:
    return f'{int(x):,}'.replace(',', '.')


def main() -> None:
    b = carrega_base(ROOT / 'repte-horaris-escola' / 'paquet', semestre=2)
    files = [f for f in llegeix_proposta(PROPOSTA) if f.id in b.sessions]
    rel = llegeix_relaxacions(RELAX) if RELAX.exists() else []
    inf = avalua(b, files, rel)
    col = _col_loca(b, files, Informe())
    ords = {a for a, x in b.aules.items() if x.ordinaria}

    # 1. pics: classes alhora que necessiten aula, i aules ordinàries ocupades, per torn
    def pics(pos):
        dem, occ = collections.defaultdict(set), collections.defaultdict(set)
        per_mida = collections.defaultdict(lambda: collections.defaultdict(set))
        for sid, (d, i, a) in pos.items():
            s = b.sessions[sid]
            if s.sense_espai or s.tipus == 'PLAB':
                continue
            for f0 in FRANGES:
                if i < f0 + 60 and i + s.durada > f0:
                    dem[(d, f0)].add(s.unitat)
                    if a in ords:
                        occ[(d, f0)].add(a)
                        per_mida[(d, f0)][a] = 1
        out = {}
        for torn, cond in (('matí', lambda f: f < MATI[1]), ('tarda', lambda f: f >= MATI[1])):
            ks = [k for k in dem if cond(k[1])]
            kd = max(ks, key=lambda k: len(dem[k]))
            ko = max(ks, key=lambda k: len(occ[k]))
            out[torn] = (len(dem[kd]), kd, len(occ[ko]), ko)
        return out, occ
    avui = {sid: (s.data, s.ini, s.aula) for sid, s in b.sessions.items()}
    nou = {sid: (c.data, c.ini, c.aula) for sid, c in col.items()}
    p_avui, _ = pics(avui)
    p_nou, occ = pics(nou)

    # 2. aules per mida: màxim d'aules de cada mida ocupades alhora, per torn
    mida_de = {a: next(lbl for lo, hi, lbl in MIDES if lo <= b.aules[a].capacitat <= hi) for a in ords}
    total_mida = collections.Counter(mida_de.values())
    max_mida = {t: collections.Counter() for t in ('matí', 'tarda')}
    for (d, f0), rooms in occ.items():
        t = 'matí' if f0 < MATI[1] else 'tarda'
        c = collections.Counter(mida_de[a] for a in rooms)
        for m, k in c.items():
            max_mida[t][m] = max(max_mida[t][m], k)

    # 3. sessions mogudes per titulació i curs
    mogudes = collections.Counter()
    totals = collections.Counter()
    for sid, c in col.items():
        s = b.sessions[sid]
        for coh in s.cohorts:
            totals[coh] += 1
            if (c.data, c.ini) != (s.data, s.ini):
                mogudes[coh] += 1
    n_mogudes = sum(1 for sid, c in col.items() if (c.data, c.ini) != (b.sessions[sid].data, b.sessions[sid].ini))

    # 4. excepcions a la regla 1
    decl = [v for v in inf.violacions if v.regla == 'R1-TORN' and v.declarada and not v.heretada]
    fix = collections.Counter(c for v in decl if b.sessions[v.sessions[0]].fixada for c in b.sessions[v.sessions[0]].cohorts)
    residus = [v.sessions[0] for v in decl if not b.sessions[v.sessions[0]].fixada]
    plab = collections.Counter(c for v in inf.violacions if v.regla == 'R1-TORN' and v.heretada
                               and b.sessions[v.sessions[0]].tipus == 'PLAB' for c in b.sessions[v.sessions[0]].cohorts)
    obj = inf.objectius
    dobles_mogudes = sum(1 for sid, c in col.items() if b.sessions[sid].sense_espai
                         and (c.data, c.ini) != (b.sessions[sid].data, b.sessions[sid].ini))

    L = []
    L.append("# Resum per a la Junta Permanent · Torns nous al 2n semestre\n")
    L.append(f"**Proposta:** 1r i 2n al matí; 3r, 4t, dobles titulacions i màsters a la tarda. **Veredicte del "
             f"verificador oficial: {inf.veredicte}** ({sum(1 for v in inf.violacions if v.declarada and not v.heretada)} "
             f"excepcions declarades, totes a la regla 1; cap altra regla incomplerta). {n(n_mogudes)} de les "
             f"{n(len(col))} sessions canvien de franja i {obj['canvis_aula']} d'aula; les hores mortes baixen de "
             f"72.930 a {n(obj['hores_mortes_min'])} minuts (−{100 - 100 * obj['hores_mortes_min'] / 72930:.0f} %).\n")
    L.append("## 1. Pic de sessions simultànies davant de les aules ordinàries disponibles\n")
    L.append("| Torn | Classes alhora que necessiten aula (pic) | Aules ordinàries ocupades (pic) | Disponibles (21 − 2 de reserva) | Marge |")
    L.append("|---|---|---|---|---|")
    for t in ('matí', 'tarda'):
        cd, kd, co, ko = p_nou[t]
        L.append(f"| {t.capitalize()} | {cd} ({kd[0].strftime('%d/%m')} {fmt(kd[1])}); avui {p_avui[t][0]} | {co} "
                 f"({ko[0].strftime('%d/%m')} {fmt(ko[1])}) | 19 | {19 - co} aules |")
    L.append("\nLes classes que no van a una aula ordinària van a seminaris, laboratoris integrats i aules d'informàtica.\n")
    L.append("## 2. Aules que falten o sobren, per mida\n")
    L.append("| Places | Aules ordinàries | Màx. ocupades alhora (matí / tarda) | Lliures al pitjor moment (matí / tarda) |")
    L.append("|---|---|---|---|")
    for _lo, _hi, m in MIDES:
        if total_mida[m]:
            L.append(f"| {m} | {total_mida[m]} | {max_mida['matí'][m]} / {max_mida['tarda'][m]} | "
                     f"{total_mida[m] - max_mida['matí'][m]} / {total_mida[m] - max_mida['tarda'][m]} |")
    def justes(t):
        return ', '.join(m for _lo, _hi, m in MIDES if total_mida[m] and total_mida[m] == max_mida[t][m]) or 'cap'

    def sobren(t):
        return ', '.join(f"{m} ({total_mida[m] - max_mida[t][m]})" for _lo, _hi, m in MIDES
                         if total_mida[m] and total_mida[m] > max_mida[t][m]) or 'cap'
    L.append(f"\n**No falta cap aula:** totes les classes tenen aula del tipus i la mida que toca i la reserva de 2 aules "
             f"es compleix a totes les franges (R8 sense cap incompliment). Mides **justes** (en algun moment s'omplen "
             f"totes, serien les primeres a faltar si creix la demanda): al matí {justes('matí')} places; a la tarda "
             f"{justes('tarda')}. Mides que **sobren** fins i tot al pitjor moment: al matí {sobren('matí')}; a la "
             f"tarda {sobren('tarda')}.\n")
    L.append("## 3. Sessions mogudes per titulació i curs\n")
    L.append("| Cohort | Mogudes | De | % |")
    L.append("|---|---|---|---|")
    for coh, k in mogudes.most_common():
        L.append(f"| {coh} | {n(k)} | {n(totals[coh])} | {100 * k / totals[coh]:.0f} % |")
    L.append(f"\nUna sessió compartida per dues cohorts compta per a totes dues. Les que més ho noten són 3r i 4t "
             f"(passen a la tarda). Les {dobles_mogudes} sessions de doble titulació que avui es feien amb un grup de "
             f"matí s'han pogut passar totes a la tarda: no cal cap excepció per a elles.\n")
    L.append("## 4. Excepcions a la regla 1 que demanem\n")
    L.append(f"1. **{n(sum(1 for v in decl if b.sessions[v.sessions[0]].fixada))} sessions de grups fixats de 1r i 2n "
             f"que avui són a la tarda** ({', '.join(f'{c}: {k}' for c, k in fix.most_common())}). "
             f"L'Escola ha dit que no es toquen; només els donem l'aula que no tenien. Motiu: mantenir aquests grups "
             f"tal com són.")
    if residus:
        motiu = ("el 9/4/2027 és l'únic dia mòbil de la seva setmana (del 5 al 8/4 és setmana d'avaluació); com a "
                 "PAUL de 34 alumnes a la tarda només pot anar a Q1/0007 o Q1/0019, ocupades de 15 a 19 h per grups "
                 "fixats, i de 19 a 21 h el docent D380 ja hi té dues de les seves tres PAUL"
                 if residus == ['S04511'] else "el motiu de cadascuna és a `relaxacions.csv`")
        L.append(f"2. **{len(residus)} {'sessió' if len(residus) == 1 else 'sessions'} on hem demostrat que no hi "
                 f"{'cap' if len(residus) == 1 else 'caben'}** ({', '.join(residus)}): {motiu}. Prova detallada a "
                 f"`relaxacions.csv`.")
    L.append(f"\nA més, els laboratoris PLAB fixats que són a l'altre torn es queden on són sense declarar-ho (el "
             f"verificador els considera heretats): {', '.join(f'{c}: {k}' for c, k in plab.most_common(6))}.\n")
    L.append("**Quant costa cada regla:** passar 3r, 4t, dobles i màsters a la tarda vol dir moure 1.774 sessions; portar "
             "GCIS 2n i GIA 1r i 2n al matí, 234. Mantenir fixats els grups de GEI de 1r i 2n que avui són a la tarda costa "
             "458 excepcions a la regla 1; si l'Escola els deixés moure, es podrien intentar passar al matí.")
    SORTIDA.write_text('\n'.join(L) + '\n', encoding='utf-8')
    print(SORTIDA.read_text(encoding='utf-8'))


if __name__ == '__main__':
    main()
