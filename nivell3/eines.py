# Eines (sense IA a dins): funcions que l'agent pot cridar. Cada una es pot provar a mà, retorna dades
# estructurades i les fonts (id_sessio o aules) que demostren la resposta, i diu explícitament quan no troba res.
#
# - consulta_sql: només SELECT, amb límit de files
# - horari_grup: on i quan té classe un grup
# - horari_aula: què passa en una aula
# - aules_lliures: aules prou grans i lliures en una data i hora (avisa de la reserva de 2 aules, regla 8)
# - verifica: crida avalua() del verificador oficial
# - que_passa_si: aplica un canvi en memòria i compara el verificador abans i després
# - resol_imprevist: reutilitza l'eina del 5.3 (nivell2/p53_imprevist): aula tancada o sessió cancel·lada
# - esborrany_avis: redacta (mai no envia) l'avís i l'entrada del registre de canvis
#
# Totes treballen sobre l'«horari actual» (per defecte el nostre 5.2, lliuraments/proposta-torns.csv) i, si no es diu
# el contrari, sobre el 2n semestre. Totes tornen un diccionari que es pot passar a JSON, amb una clau 'fonts'.
from __future__ import annotations

import collections
import datetime as dt
import sys
from pathlib import Path

from dades import (DIES, LLIURAMENTS, PAQUET, PROPOSTA_PARTIDA, PROPOSTA_PER_DEFECTE, ROOT, ConsultaNoPermesa,
                   carrega, hhmm, minuts)

sys.path.insert(0, str(ROOT / 'repte-horaris-escola'))
sys.path.insert(0, str(ROOT / 'nivell2' / 'p53_imprevist'))

from horaris.check import FRANGES, avalua  # noqa: E402
from horaris.model import Tancament, carrega_base, llegeix_proposta, llegeix_relaxacions  # noqa: E402

import avisos  # noqa: E402

MAX_LLISTA = 40
TIPUS = {'aula': 'Aules docents', 'seminari': 'Seminaris', 'laboratori': 'Laboratoris docents',
         'informatica': 'Aules informàtiques', 'informàtica': 'Aules informàtiques'}

# les propostes que coneix l'assistent: fitxer, mode del verificador, escenari i relaxacions declarades
PROPOSTES = {
    'torns': dict(fitxer=PROPOSTA_PER_DEFECTE, relax=LLIURAMENTS / 'relaxacions.csv'),
    'aules': dict(fitxer=LLIURAMENTS / 'proposta-aules.csv', nomes_aules=True),
    'imprevist': dict(fitxer=LLIURAMENTS / 'proposta-imprevist.csv', escenari=PAQUET / 'escenaris' / 'contingencies',
                      relax=LLIURAMENTS / 'relaxacions-imprevist.csv'),
    'grau-nou': dict(fitxer=LLIURAMENTS / 'proposta-grau-nou.csv', escenari=PAQUET / 'escenaris' / 'grau-nou-40',
                     relax=LLIURAMENTS / 'relaxacions.csv'),
    'partida': dict(fitxer=PROPOSTA_PARTIDA),
}

d = carrega()


# ---------------------------------------------------------------------------------------------- utilitats
def _data(x) -> dt.date | None:
    if x in (None, ''):
        return None
    return x if isinstance(x, dt.date) else dt.date.fromisoformat(str(x))


def _dia(x) -> str | None:
    if not x:
        return None
    x = str(x).strip().lower()
    noms = {'l': 'L', 'dilluns': 'L', 'm': 'M', 'dimarts': 'M', 'x': 'X', 'dimecres': 'X', 'j': 'J', 'dijous': 'J',
            'v': 'V', 'divendres': 'V', 'monday': 'L', 'tuesday': 'M', 'wednesday': 'X', 'thursday': 'J',
            'friday': 'V'}
    if x not in noms:
        raise ValueError(f"Dia desconegut: «{x}». Feu servir L, M, X, J o V (o el nom del dia).")
    return noms[x]


def _hora(x) -> int:
    x = str(x).strip().replace('.', ':').replace('h', ':')
    if ':' not in x:
        x += ':00'
    h, m = x.split(':')[:2]
    return int(h) * 60 + int(m or 0)


def _ses(fila) -> dict:
    """Una sessió de l'horari actual en format compacte per al LLM."""
    return {'id_sessio': fila['id_sessio'], 'codi': fila['codi'], 'assignatura': fila['assignatura'],
            'grup': fila['grup'], 'tipus': fila['tipus'], 'data': str(fila['data_nova']), 'dia': fila['dia_nou'],
            'h_ini': fila['h_ini_nou'], 'h_fi': fila['h_fi_nou'], 'aula': fila['aula_nova'] or '(sense aula)',
            'cohorts': fila['titulacions_curs'], 'docents': fila['docents']}


def _patro(df) -> list[dict]:
    """Agrupa sessions que es repeteixen (mateix grup, dia, hora i aula) en una fila «setmanal»."""
    if df.empty:
        return []
    g = df.groupby(['codi', 'assignatura', 'grup', 'tipus', 'dia_nou', 'h_ini_nou', 'h_fi_nou', 'aula_nova'],
                   dropna=False)
    out = []
    for (codi, assig, grup, tipus, dia, hi, hf, aula), x in g:
        x = x.sort_values('data_nova')
        out.append({'codi': codi, 'assignatura': assig, 'grup': grup, 'tipus': tipus, 'dia': dia, 'h_ini': hi,
                    'h_fi': hf, 'aula': aula or '(sense aula)', 'sessions': len(x),
                    'primera': str(x['data_nova'].iloc[0]), 'darrera': str(x['data_nova'].iloc[-1]),
                    'exemples_id_sessio': x['id_sessio'].head(3).tolist()})
    return sorted(out, key=lambda r: ('LMXJV'.find(r['dia']), r['h_ini'], r['codi']))[:MAX_LLISTA]


def _filtra(semestre=2, data=None, dia=None, setmana=None):
    h = d.horari
    if semestre:
        h = h[h['semestre'] == int(semestre)]
    if data:
        h = h[h['data_nova'] == _data(data)]
    if dia:
        h = h[h['dia_nou'] == _dia(dia)]
    if setmana:
        h = h[h['setmana_nova'] == str(setmana)]
    return h


# ------------------------------------------------------------------------------------------------ eines
def consulta_sql(sql: str) -> dict:
    """Consulta SQL de només lectura (DuckDB) sobre les taules sessions, aules, calendari i horari."""
    try:
        r = d.consulta_lectura(sql)
    except ConsultaNoPermesa as e:
        return {'error': str(e), 'fonts': []}
    except Exception as e:   # SQL mal escrit: es torna l'error perquè el LLM el pugui corregir
        return {'error': f'{type(e).__name__}: {e}', 'fonts': []}
    fonts = []
    if 'id_sessio' in r['columnes']:
        i = r['columnes'].index('id_sessio')
        fonts = [f[i] for f in r['files']][:MAX_LLISTA]
    if not r['files']:
        r['avis'] = 'La consulta no ha trobat cap fila.'
    r['fonts'] = fonts
    return r


def horari_grup(grup: str = '', codi: str = '', assignatura: str = '', cohort: str = '', dia: str = '',
                data: str = '', setmana: str = '', semestre: int = 2) -> dict:
    """On i quan té classe un grup. `grup` pot ser exacte (TE/81, PAUL/811) o un número de línia (81 = TE/81 i els
    seus subgrups 811, 812...)."""
    h = _filtra(semestre, data, dia, setmana)
    if grup:
        g = grup.strip().upper()
        h = h[h['grup'] == g] if '/' in g else h[h['grup'].str.match(rf'^[A-Z]+/{g}\d*$')]
    if codi:
        h = h[h['codi'] == str(codi).strip()]
    if assignatura:
        h = h[h['assignatura'].str.contains(assignatura, case=False, regex=False)]
    if cohort:
        h = h[h['titulacions_curs'].str.contains(cohort, case=False, regex=False)]
    if h.empty:
        return {'trobat': False, 'avis': 'Cap sessió amb aquests filtres a l\'horari actual.', 'fonts': []}
    res = {'trobat': True, 'sessions': len(h), 'setmanal': _patro(h), 'fonts': h['id_sessio'].head(MAX_LLISTA).tolist()}
    if data:
        res['sessions_del_dia'] = [_ses(f) for _, f in h.sort_values('ini_min').head(MAX_LLISTA).iterrows()]
    return res


def horari_aula(aula: str, data: str = '', dia: str = '', setmana: str = '', semestre: int = 2) -> dict:
    """Què passa en una aula: les seves classes (per a una data concreta, o el patró setmanal)."""
    aula = aula.strip().upper()
    if aula not in set(d.aules['aula']):
        return {'trobat': False, 'avis': f'{aula} no és cap aula de l\'aulari.', 'fonts': []}
    info = d.aules[d.aules['aula'] == aula].iloc[0]
    h = _filtra(semestre, data, dia, setmana)
    h = h[(h['aula_nova'] == aula) & (h['sense_espai'] != '1')]
    res = {'aula': aula, 'tipus': info['tipus'], 'capacitat': int(info['capacitat']), 'sessions': len(h),
           'fonts': h['id_sessio'].head(MAX_LLISTA).tolist()}
    if data:
        res['classes'] = [_ses(f) for _, f in h.sort_values('ini_min').iterrows()]
    else:
        res['setmanal'] = _patro(h)
    if h.empty:
        res['avis'] = 'Cap classe en aquesta aula amb aquests filtres.'
    return res


def _calendari(data: dt.date, ini: int, fi: int) -> str:
    c = d.calendari[d.calendari['data'] == data]
    for _, r in c.iterrows():
        if not r['h_ini'] or (minuts(r['h_ini']) < fi and minuts(r['h_fi']) > ini):
            return f"{r['tipus']}: {r['motiu']}"
    return ''


def aules_lliures(hora_inici: str, durada_min: int = 60, data: str = '', dia: str = '', places_min: int = 0,
                  tipus: str = '', semestre: int = 2) -> dict:
    """Aules de l'aulari lliures a una hora: en una data concreta, o tots els dies d'aquell dia de la setmana del
    semestre. Comprova capacitat, solapaments i la reserva de 2 aules ordinàries lliures (regla 8)."""
    ini = _hora(hora_inici)
    fi = ini + int(durada_min)
    if data:
        dates = [_data(data)]
    elif dia:
        k = _dia(dia)
        dates = sorted({x for x in d.horari.loc[d.horari['semestre'] == int(semestre), 'data_nova']
                        if 'LMXJV'[x.weekday()] == k})
    else:
        return {'error': 'Cal una data (AAAA-MM-DD) o un dia de la setmana.', 'fonts': []}
    aules = d.aules
    if tipus:
        aules = aules[aules['tipus'] == TIPUS.get(tipus.lower(), tipus)]
    aules = aules[aules['capacitat'] >= int(places_min)]
    ordinaries = set(d.aules.loc[d.aules['ordinaria'] == 1, 'aula'])
    h = d.horari[(d.horari['aula_nova'] != '') & (d.horari['sense_espai'] != '1')]
    h = h[h['data_nova'].isin(dates)]
    ocupades = collections.defaultdict(list)   # (aula, data) -> sessions que hi solapen
    for _, f in h[(h['ini_min'] < fi) & (h['fi_min'] > ini)].iterrows():
        ocupades[(f['aula_nova'], f['data_nova'])].append(f['id_sessio'])
    franges = [f0 for f0 in FRANGES if ini < f0 + 60 and fi > f0]
    ord_ocupades = {}   # (data, franja) -> nombre d'aules ordinàries ocupades
    for data_ in dates:
        x = h[h['data_nova'] == data_]
        for f0 in franges:
            y = x[(x['ini_min'] < f0 + 60) & (x['fi_min'] > f0) & x['aula_nova'].isin(ordinaries)]
            ord_ocupades[(data_, f0)] = y['aula_nova'].nunique()
    files, fonts = [], []
    for _, a in aules.sort_values(['capacitat', 'aula']).iterrows():
        dates_ocupada = [str(x) for x in dates if ocupades.get((a['aula'], x))]
        for x in dates:
            fonts += ocupades.get((a['aula'], x), [])
        reserva = []
        if a['aula'] in ordinaries:
            reserva = [str(x) for x in dates if not ocupades.get((a['aula'], x))
                       and any(len(ordinaries) - ord_ocupades[(x, f0)] - 1 < 2 for f0 in franges)]
        files.append({'aula': a['aula'], 'tipus': a['tipus'], 'capacitat': int(a['capacitat']),
                      'lliure_totes_les_dates': not dates_ocupada, 'dates_ocupada': dates_ocupada[:10],
                      'trencaria_reserva_regla8': reserva[:10]})
    lliures = [f for f in files if f['lliure_totes_les_dates'] and not f['trencaria_reserva_regla8']]
    avisos_cal = {str(x): _calendari(x, ini, fi) for x in dates if _calendari(x, ini, fi)}
    return {'franja': f'{hhmm(ini)}-{hhmm(fi)}', 'dates_comprovades': len(dates),
            'primera_data': str(dates[0]) if dates else None, 'darrera_data': str(dates[-1]) if dates else None,
            'aules_lliures': lliures[:MAX_LLISTA], 'n_lliures': len(lliures),
            'altres_aules': [f for f in files if f not in lliures][:15],
            'calendari': avisos_cal, 'fonts': sorted(set(fonts))[:MAX_LLISTA],
            'nota': "Lliure = cap classe de l'horari actual solapa aquesta franja en cap de les dates comprovades i "
                    "no deixa menys de 2 aules ordinàries lliures. Les fonts són les sessions que ocupen les aules "
                    "no lliures."}


# --------------------------------------------------------------------------------------------- verificador
_BASES: dict = {}


def _base(escenari=None):
    clau = str(escenari)
    if clau not in _BASES:
        _BASES[clau] = carrega_base(PAQUET, semestre=2, escenari=escenari)
    return _BASES[clau]


def _files(base, fitxer):
    return [f for f in llegeix_proposta(Path(fitxer)) if f.id in base.sessions]


def _violacio(v) -> dict:
    return {'regla': v.regla, 'sessions': list(v.sessions)[:6], 'detall': v.detall}


def verifica(proposta: str = 'torns') -> dict:
    """Passa el verificador oficial a una de les nostres propostes (2n semestre), amb el mateix mode, escenari i
    relaxacions que el lliurament. proposta: torns (5.2), aules (5.1), imprevist (5.3), grau-nou (5.4), partida."""
    cfg = PROPOSTES.get(proposta)
    if not cfg:
        return {'error': f"Proposta desconeguda: {proposta}. Opcions: {', '.join(PROPOSTES)}", 'fonts': []}
    base = _base(cfg.get('escenari'))
    rel = llegeix_relaxacions(cfg['relax']) if cfg.get('relax') else []
    ref = _files(base, PROPOSTA_PER_DEFECTE) if proposta == 'imprevist' else None
    inf = avalua(base, _files(base, cfg['fitxer']), rel, referencia=ref, nomes_aules=cfg.get('nomes_aules', False))
    rec = inf.recompte()
    compten = [v for v in inf.violacions if v.compta]
    return {'proposta': proposta, 'fitxer': Path(cfg['fitxer']).name, 'veredicte': inf.veredicte,
            'compten': {k: v['compten'] for k, v in rec.items() if v['compten']},
            'declarades': {k: v['declarades'] for k, v in rec.items() if v['declarades']},
            'heretades': {k: v['heretades'] for k, v in rec.items() if v['heretades']},
            'objectius': inf.objectius, 'exemples_que_compten': [_violacio(v) for v in compten[:10]],
            'fonts': sorted({s for v in compten[:10] for s in v.sessions})}


def que_passa_si(nou_dia: str = '', nova_hora: str = '', nova_aula: str = '', id_sessio: str = '', codi: str = '',
                 grup: str = '', dia_actual: str = '') -> dict:
    """Simula un canvi sobre el 5.2 (sense desar res) i el passa pel verificador abans i després. Es pot moure una
    sessió (id_sessio) o totes les sessions del 2n semestre d'un grup (codi + grup, opcionalment només les d'un dia)."""
    base = _base()
    rel = llegeix_relaxacions(PROPOSTES['torns']['relax'])
    files = _files(base, PROPOSTA_PER_DEFECTE)
    if id_sessio:
        objectiu = {id_sessio.strip().upper()}
    elif codi and grup:
        da = _dia(dia_actual) if dia_actual else None
        objectiu = {f.id for f in files if base.sessions[f.id].codi == str(codi).strip()
                    and base.sessions[f.id].grup == grup.strip().upper() and (not da or f.dia == da)}
    else:
        return {'error': 'Cal id_sessio, o bé codi i grup.', 'fonts': []}
    if not objectiu & {f.id for f in files}:
        return {'error': 'Cap sessió del 2n semestre coincideix amb aquests filtres.', 'fonts': []}
    nou = []
    for f in files:
        g = type(f)(**vars(f))
        if f.id in objectiu:
            if nou_dia:
                g.dia = _dia(nou_dia)
            if nova_hora:
                g.h_ini = hhmm(_hora(nova_hora))
            if nova_aula:
                g.aula = nova_aula.strip().upper()
        nou.append(g)
    abans = avalua(base, files, rel)
    despres = avalua(base, nou, rel)

    def claus(inf):
        return {(v.regla, v.sessions, v.detall if not v.sessions else ''): v for v in inf.violacions if v.compta}
    ka, kd = claus(abans), claus(despres)
    nous = [kd[k] for k in kd if k not in ka]
    resolts = [ka[k] for k in ka if k not in kd]
    return {'sessions_mogudes': len(objectiu), 'canvi': {'dia': nou_dia, 'hora': nova_hora, 'aula': nova_aula},
            'veredicte_abans': abans.veredicte, 'veredicte_despres': despres.veredicte,
            'incompliments_nous': [_violacio(v) for v in nous[:15]], 'n_incompliments_nous': len(nous),
            'incompliments_resolts': len(resolts),
            'resum': 'El canvi no trenca cap regla.' if not nous else
                     f'El canvi provoca {len(nous)} incompliments nous (vegeu la llista).',
            'fonts': sorted(objectiu)[:MAX_LLISTA]}


# ----------------------------------------------------------------------------------------------- imprevistos
def _canvis(base, h, files_in) -> list[dict]:
    """Compara la col·locació d'abans i la de després i torna els canvis en format d'avís."""
    from imprevist import Horari
    abans = Horari(base, files_in).pos
    for f in files_in:   # una sessió cancel·lada no és a «abans» (el verificador no la col·loca): la seva fila sí
        if f.id not in abans and f.id in base.cancellades:
            s = base.sessions[f.id]
            abans[f.id] = [s.data + dt.timedelta(days=DIES.index(f.dia) - s.data.weekday()), minuts(f.h_ini), f.aula]
    out = []
    for sid, (dn, ini, aula) in h.pos.items():
        if sid not in abans:
            continue
        d0, i0, a0 = abans[sid]
        if (dn, ini, aula) == (d0, i0, a0):
            continue
        s = base.sessions[sid]
        fila = d.sessions[d.sessions['id_sessio'] == sid].iloc[0]
        out.append({'id_sessio': sid, 'codi': s.codi, 'assignatura': fila['assignatura'], 'grup': s.grup,
                    'docents': sorted(s.docents), 'cohorts': list(s.cohorts),
                    'abans': {'data': str(d0), 'h_ini': hhmm(i0), 'h_fi': hhmm(i0 + s.durada), 'aula': a0},
                    'despres': {'data': str(dn), 'h_ini': hhmm(ini), 'h_fi': hhmm(ini + s.durada), 'aula': aula}})
    return out


def resol_imprevist(tipus: str, aula: str = '', data_ini: str = '', data_fi: str = '', h_ini: str = '',
                    h_fi: str = '', id_sessio: str = '', recuperar_fins: str = '') -> dict:
    """Proposa una solució validada per a un imprevist sobre el 5.2, canviant el mínim (motor del 5.3).
    tipus='aula_tancada' (aula, data_ini, data_fi, opcionalment h_ini/h_fi: avaria, acte...) o
    tipus='cancellacio' (id_sessio, recuperar_fins). No desa res: torna els canvis i la verificació."""
    from imprevist import Horari, repara_cancellades, repara_tancades
    base = carrega_base(PAQUET, semestre=2)   # còpia nova: s'hi afegeix l'imprevist
    files = _files(base, PROPOSTA_PER_DEFECTE)
    if tipus == 'aula_tancada':
        aula = aula.strip().upper()
        if aula not in base.aules or not data_ini:
            return {'error': 'Cal una aula de l\'aulari i data_ini (AAAA-MM-DD).', 'fonts': []}
        base.tancaments.append(Tancament(aula, _data(data_ini), _data(data_fi or data_ini),
                                         _hora(h_ini) if h_ini else 0, _hora(h_fi) if h_fi else 24 * 60))
        motiu = f"l'aula {aula} no es pot fer servir ({data_ini}{' a ' + data_fi if data_fi else ''})"
    elif tipus == 'cancellacio':
        sid = id_sessio.strip().upper()
        if sid not in base.sessions or not recuperar_fins:
            return {'error': 'Cal un id_sessio del 2n semestre i recuperar_fins (AAAA-MM-DD).', 'fonts': []}
        base.cancellades[sid] = _data(recuperar_fins)
        motiu = f'la cancel·lació de la sessió {sid} del {base.sessions[sid].data}'
    else:
        return {'error': "tipus ha de ser 'aula_tancada' o 'cancellacio'.", 'fonts': []}
    rel = llegeix_relaxacions(PROPOSTES['torns']['relax'])
    abans = avalua(base, files, rel)
    h = Horari(base, files)
    log: list[str] = []
    fixades = repara_tancades(h, log) if tipus == 'aula_tancada' else []
    recuperades = repara_cancellades(h, log) if tipus == 'cancellacio' else {}
    files_out = []
    for f in files:
        g = type(f)(**vars(f))
        if f.id in h.pos:
            dn, ini, au = h.pos[f.id]
            g.dia, g.h_ini, g.aula = DIES[dn.weekday()], hhmm(ini), au
            g.data = dn.isoformat() if f.id in recuperades else ''
        files_out.append(g)
    despres = avalua(base, files_out, rel)

    def claus(inf):
        return {(v.regla, v.sessions, v.detall if not v.sessions else '') for v in inf.violacions if v.compta}
    pendents = [v for v in despres.violacions if v.compta and v.regla in ('R3-TANCADA', 'R5-RECUPERACIO')]
    nous = [v for v in despres.violacions if v.compta and (v.regla, v.sessions, v.detall if not v.sessions else '')
            not in claus(abans) and v.regla not in ('R1-FIXADA', 'R7-PLAB')]
    canvis = _canvis(base, h, files)
    return {'tipus': tipus, 'motiu': motiu, 'canvis': canvis, 'n_canvis': len(canvis),
            'sense_solucio': [x for x in log if x.startswith('SENSE SOLUCIÓ')],
            'relaxacions_necessaries': [{'regla': 'R7-PLAB' if base.sessions[x].tipus == 'PLAB' else 'R1-FIXADA',
                                         'id_sessio': x, 'motiu': 'sessió fixada en una aula que no es pot fer servir'}
                                        for x in fixades],
            'verificacio': {'imprevistos_pendents': len(pendents), 'incompliments_nous': [_violacio(v) for v in nous[:10]],
                            'correcte': not pendents and not nous},
            'fonts': [c['id_sessio'] for c in canvis][:MAX_LLISTA]}


def esborrany_avis(canvis: list, motiu: str) -> dict:
    """Redacta (no envia) els avisos al docent, als estudiants i a Gestió Acadèmica, i el registre de canvis.
    `canvis` és la llista que torna resol_imprevist."""
    r = avisos.redacta(canvis, motiu)
    r['fonts'] = [c['id_sessio'] for c in canvis][:MAX_LLISTA]
    return r


# ------------------------------------------------------------------------- catàleg d'eines per al LLM (JSON schema)
EINES = {f.__name__: f for f in (consulta_sql, horari_grup, horari_aula, aules_lliures, verifica, que_passa_si,
                                 resol_imprevist, esborrany_avis)}

_S, _I = {'type': 'string'}, {'type': 'integer'}
ESQUEMES = [
    {'name': 'consulta_sql', 'description': (
        "Consulta SQL de NOMÉS LECTURA (DuckDB, una sola SELECT) sobre les taules: sessions (una fila per sessió: "
        "id_sessio, codi, assignatura, tipus TE/PAUL/PLAB/SEM, grup, data, dia, h_ini, h_fi, durada_min, alumnes, "
        "aula_partida, titulacions_curs, torn_requerit, fixada, docents, sense_espai, semestre), aules (aula, edifici, "
        "tipus, descripcio, capacitat, ordinaria), calendari (data, tipus, h_ini, h_fi, motiu) i horari (com sessions "
        "més l'horari actual: data_nova, dia_nou, h_ini_nou, h_fi_nou, ini_min, fi_min, aula_nova, setmana_nova). "
        "Inclou sempre id_sessio quan consultis sessions. Màxim 200 files."),
     'parameters': {'type': 'object', 'properties': {'sql': _S}, 'required': ['sql']}},
    {'name': 'horari_grup', 'description': (
        "On i quan té classe un grup a l'horari actual (2n semestre per defecte). grup exacte (TE/81, PAUL/811) o "
        "número de línia (81 = TE/81 i subgrups). Es pot filtrar per codi, assignatura, cohort (p. ex. GED:1r), dia "
        "(L M X J V), data (AAAA-MM-DD) o setmana ISO (2027-W06)."),
     'parameters': {'type': 'object', 'properties': {
         'grup': _S, 'codi': _S, 'assignatura': _S, 'cohort': _S, 'dia': _S, 'data': _S, 'setmana': _S,
         'semestre': _I}}},
    {'name': 'horari_aula', 'description': "Classes d'una aula a l'horari actual: per a una data, un dia o el patró setmanal.",
     'parameters': {'type': 'object', 'properties': {'aula': _S, 'data': _S, 'dia': _S, 'setmana': _S, 'semestre': _I},
                    'required': ['aula']}},
    {'name': 'aules_lliures', 'description': (
        "Aules lliures a una hora a l'horari actual, amb capacitat mínima i tipus opcional (aula, seminari, "
        "laboratori, informatica). Amb data comprova aquell dia; amb dia (L..V) comprova tots els dies d'aquell dia "
        "de la setmana del semestre. Respecta la reserva de 2 aules ordinàries (regla 8)."),
     'parameters': {'type': 'object', 'properties': {
         'hora_inici': _S, 'durada_min': _I, 'data': _S, 'dia': _S, 'places_min': _I, 'tipus': _S, 'semestre': _I},
         'required': ['hora_inici']}},
    {'name': 'verifica', 'description': (
        "Passa el verificador oficial a una proposta: torns (5.2, l'horari actual), aules (5.1), imprevist (5.3), "
        "grau-nou (5.4) o partida (l'horari d'avui). Torna el veredicte, els incompliments per regla i exemples."),
     'parameters': {'type': 'object', 'properties': {'proposta': {'type': 'string', 'enum': list(PROPOSTES)}}}},
    {'name': 'que_passa_si', 'description': (
        "Simula moure una sessió (id_sessio) o les sessions d'un grup (codi + grup, opcionalment dia_actual) a un altre "
        "dia (nou_dia), hora (nova_hora, HH:MM) o aula (nova_aula), i diu quines regles trencaria segons el "
        "verificador. No desa res."),
     'parameters': {'type': 'object', 'properties': {
         'nou_dia': _S, 'nova_hora': _S, 'nova_aula': _S, 'id_sessio': _S, 'codi': _S, 'grup': _S, 'dia_actual': _S}}},
    {'name': 'resol_imprevist', 'description': (
        "Proposa una solució validada pel verificador per a un imprevist, canviant el mínim: tipus='aula_tancada' "
        "(aula, data_ini, data_fi; opcionalment h_ini, h_fi) per a una avaria o un acte; tipus='cancellacio' "
        "(id_sessio, recuperar_fins) per recuperar una sessió cancel·lada. No desa res."),
     'parameters': {'type': 'object', 'properties': {
         'tipus': {'type': 'string', 'enum': ['aula_tancada', 'cancellacio']}, 'aula': _S, 'data_ini': _S,
         'data_fi': _S, 'h_ini': _S, 'h_fi': _S, 'id_sessio': _S, 'recuperar_fins': _S}, 'required': ['tipus']}},
    {'name': 'esborrany_avis', 'description': (
        "Redacta (NO envia) els avisos per al docent, l'alumnat i Gestió Acadèmica i el registre de canvis. Si no es "
        "passa 'canvis', es fan servir els de l'últim resol_imprevist d'aquesta conversa."),
     'parameters': {'type': 'object', 'properties': {'canvis': {'type': 'array', 'items': {'type': 'object'}},
                                                     'motiu': _S}, 'required': ['motiu']}},
]
