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
import difflib
import re
import sys
from pathlib import Path

from dades import (DIES, LLIURAMENTS, PAQUET, PROPOSTA_PARTIDA, PROPOSTA_PER_DEFECTE, ROOT, ConsultaNoPermesa,
                   carrega, hhmm, minuts)

sys.path.insert(0, str(ROOT / 'repte-horaris-escola'))
sys.path.insert(0, str(ROOT / 'nivell2' / 'p53_imprevist'))

from horaris.check import DESCRIPCIO, FRANGES, avalua  # noqa: E402
from horaris.model import Tancament, carrega_base, llegeix_proposta, llegeix_relaxacions  # noqa: E402

import avisos  # noqa: E402
import prompts  # noqa: E402

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
MESOS = {'gener': 1, 'febrer': 2, 'marc': 3, 'març': 3, 'abril': 4, 'maig': 5, 'juny': 6, 'juliol': 7, 'agost': 8,
         'setembre': 9, 'octubre': 10, 'novembre': 11, 'desembre': 12}


def _data(x) -> dt.date | None:
    """Accepta AAAA-MM-DD, DD/MM/AAAA, «10 de març (de 2027)» ... Sense any, el del 2n semestre (2027)."""
    if x in (None, ''):
        return None
    if isinstance(x, dt.date):
        return x
    t = str(x).strip().lower()
    try:
        return dt.date.fromisoformat(t)
    except ValueError:
        pass
    m = re.fullmatch(r'(\d{1,2})[/.-](\d{1,2})(?:[/.-](\d{2,4}))?', t)
    if m:
        dia, mes, any_ = int(m[1]), int(m[2]), m[3]
    else:
        m = re.fullmatch(r"(\d{1,2})\s*(?:de |d')?\s*([a-zç]+)(?:\s*(?:de |del |d')?\s*(\d{4}))?", t)
        if not m or m[2] not in MESOS:
            raise ValueError(f"Data no vàlida: «{x}». Feu servir AAAA-MM-DD (per exemple 2027-03-10).")
        dia, mes, any_ = int(m[1]), MESOS[m[2]], m[3]
    any_ = int(any_) + (2000 if any_ and len(any_) == 2 else 0) if any_ else 2027
    try:
        return dt.date(any_, mes, dia)
    except ValueError:
        raise ValueError(f"Data no vàlida: «{x}».") from None


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
        return _aula_inexistent(aula)
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


def _aula_inexistent(text: str) -> dict:
    """Resposta estàndard quan una aula no existeix, amb els codis existents més semblants."""
    codis = sorted(d.aules['aula'])
    t = str(text).strip().upper()
    semblants = difflib.get_close_matches(t, codis, n=4, cutoff=0.6)
    semblants += [c for c in codis if t and t in c and c not in semblants][:4 - len(semblants)]
    return {'trobat': False, 'avis': f"No hi ha cap aula «{text}» a l'aulari.", 'aules_semblants': semblants,
            'fonts': []}


def aules_lliures(hora_inici: str = '', durada_min: int = 60, data: str = '', dia: str = '', places_min: int = 0,
                  tipus: str = '', aula: str = '', semestre: int = 2) -> dict:
    """Aules de l'aulari lliures a una hora: en una data concreta, o tots els dies d'aquell dia de la setmana del
    semestre. Comprova capacitat, solapaments i la reserva de 2 aules ordinàries lliures (regla 8).
    Amb `aula`, comprova només aquella aula (i, si no existeix, ho diu i en proposa de semblants)."""
    if aula:
        codi_aula = aula.strip().upper()
        if codi_aula not in set(d.aules['aula']):
            return _aula_inexistent(aula)
    if not hora_inici:
        return {'error': "Cal l'hora d'inici (HH:MM) per saber si una aula és lliure.", 'fonts': []}
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
    if aula:
        aules = aules[aules['aula'] == aula.strip().upper()]
    else:
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
    return {'regla': v.regla, 'explicacio': DESCRIPCIO.get(v.regla, ''), 'sessions': list(v.sessions)[:6],
            'detall': v.detall}


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


# ------------------------------------------------------------------------------------ eines d'ús quotidià
def _codi_docent(docent: str) -> str:
    """«d 380», «d-380», «380» -> D380."""
    t = re.sub(r'[\s\-_.]+', '', str(docent).strip().upper())
    return 'D' + t if t.isdigit() else t


def _regex_docent(docent: str) -> str:
    return rf'(?:^|\|){re.escape(_codi_docent(docent))}(?:\||$)'


def _fora_semestre(data: dt.date | None) -> str:
    """Avís si la data no cau dins del 2n semestre (o no és lectiva); cadena buida si és un dia normal."""
    if not data:
        return ''
    h2 = d.horari[d.horari['semestre'] == 2]['data_nova']
    ini, fi = h2.min(), h2.max()
    if data < ini or data > fi:
        return (f"El {data} és fora del 2n semestre (de {ini} a {fi}): no hi ha classes a l'horari. "
                f"Digueu una data d'aquest període.")
    c = _calendari(data, 0, 24 * 60)
    if c:
        return f'El {data} no és un dia lectiu normal ({c}).'
    return ''


def ocupacio(hora_inici: str, data: str = '', dia: str = '', durada_min: int = 60, tipus_sessio: str = '',
             cohort: str = '', semestre: int = 2) -> dict:
    """Quines classes hi ha a una hora (qui té classe, a quines aules). Amb `data`: aquell dia concret; amb `dia`
    (L..V): el patró setmanal d'aquell dia de la setmana. Filtres opcionals: tipus (TE, PAUL, PLAB, SEM) i cohort."""
    if not (data or dia):
        return {'error': 'Cal una data (AAAA-MM-DD) o un dia de la setmana.', 'fonts': []}
    ini = _hora(hora_inici)
    fi = ini + int(durada_min)
    avis = _fora_semestre(_data(data)) if data else ''
    if 'fora del 2n semestre' in avis:
        return {'trobat': False, 'avis': avis, 'fonts': []}
    h = _filtra(semestre, data, dia)
    h = h[(h['ini_min'] < fi) & (h['fi_min'] > ini) & (h['sense_espai'] != '1')]
    if tipus_sessio:
        h = h[h['tipus'] == tipus_sessio.strip().upper()]
    if cohort:
        h = h[h['titulacions_curs'].str.contains(cohort, case=False, regex=False)]
    if h.empty:
        return {'trobat': False, 'franja': f'{hhmm(ini)}-{hhmm(fi)}', 'avis': avis or 'Cap classe en aquesta franja.',
                'fonts': []}
    res = {'trobat': True, 'franja': f'{hhmm(ini)}-{hhmm(fi)}', 'sessions': len(h),
           'per_tipus': h['tipus'].value_counts().to_dict(), 'aules_ocupades': int(h['aula_nova'].nunique()),
           'fonts': h['id_sessio'].head(MAX_LLISTA).tolist()}
    if avis:
        res['avis'] = avis
    if data:
        res['classes'] = [_ses(f) for _, f in h.sort_values(['ini_min', 'aula_nova']).head(MAX_LLISTA).iterrows()]
    else:
        res['setmanal'] = _patro(h)
        res['nota'] = "Patró setmanal: cada fila és una classe que es repeteix el mateix dia i hora tot el semestre."
    if len(h) > MAX_LLISTA:
        res['nota_llista'] = f'Es mostren {MAX_LLISTA} de {len(h)}; afegiu un filtre (tipus_sessio, cohort) per acotar.'
    return res


def horari_docent(docent: str, data: str = '', dia: str = '', setmana: str = '', semestre: int = 2) -> dict:
    """Les classes d'un docent (codi tipus D380): per a una data, un dia, una setmana ISO o el patró setmanal."""
    h = _filtra(semestre, data, dia, setmana)
    h = h[h['docents'].str.contains(_regex_docent(docent), regex=True, na=False)]
    if h.empty:
        existeix = d.horari['docents'].str.contains(_regex_docent(docent), regex=True, na=False).any()
        return {'trobat': False, 'fonts': [], 'avis': ('Aquest docent no té classe amb aquests filtres.' if existeix
                else f"No hi ha cap docent «{docent}» a les dades (els codis són com D380).")}
    res = {'trobat': True, 'docent': _codi_docent(docent), 'sessions': len(h),
           'fonts': h['id_sessio'].head(MAX_LLISTA).tolist()}
    if data or setmana:
        res['classes'] = [_ses(f) for _, f in h.sort_values(['data_nova', 'ini_min']).head(MAX_LLISTA).iterrows()]
    else:
        res['setmanal'] = _patro(h)
    return res


def cerca_assignatura(text: str) -> dict:
    """Troba assignatures pel nom o pel codi i en dona els grups, cohorts, docents i sessions del 2n semestre."""
    h = d.horari[d.horari['semestre'] == 2]
    t = text.strip()
    m = h[h['assignatura'].str.contains(t, case=False, regex=False) | (h['codi'] == t)]
    if m.empty:
        noms = sorted(set(h['assignatura']))
        return {'trobat': False, 'avis': f'Cap assignatura coincideix amb «{text}».',
                'semblants': difflib.get_close_matches(t, noms, n=5, cutoff=0.4), 'fonts': []}
    out = []
    for (codi, nom), x in m.groupby(['codi', 'assignatura']):
        out.append({'codi': codi, 'assignatura': nom, 'sessions': len(x), 'grups': sorted(set(x['grup'])),
                    'cohorts': sorted({c for v in x['titulacions_curs'] for c in v.split('|') if c}),
                    'docents': sorted({c for v in x['docents'] for c in v.split('|') if c}),
                    'exemples_id_sessio': x['id_sessio'].head(2).tolist()})
    return {'trobat': True, 'assignatures': out[:15], 'n_assignatures': len(out),
            'fonts': [e for o in out[:15] for e in o['exemples_id_sessio']][:MAX_LLISTA]}


def info_aules(places_min: int = 0, tipus: str = '', edifici: str = '') -> dict:
    """Llista de les aules (capacitat, tipus, si és ordinària), filtrable per capacitat mínima, tipus o edifici."""
    a = d.aules
    if tipus:
        a = a[a['tipus'] == TIPUS.get(tipus.lower(), tipus)]
    if edifici:
        a = a[a['edifici'].str.upper() == edifici.strip().upper()]
    a = a[a['capacitat'] >= int(places_min)].sort_values(['capacitat', 'aula'])
    if a.empty:
        return {'trobat': False, 'avis': 'Cap aula amb aquests filtres.', 'fonts': []}
    return {'trobat': True, 'n_aules': len(a), 'n_ordinaries': int(a['ordinaria'].sum()), 'aules': [
        {'aula': r['aula'], 'tipus': r['tipus'], 'capacitat': int(r['capacitat']), 'ordinaria': bool(r['ordinaria'])}
        for _, r in a.head(60).iterrows()], 'fonts': a['aula'].head(MAX_LLISTA).tolist()}


def reserva_aules(data: str = '', dia: str = '') -> dict:
    """Comprova la regla de les 2 aules ordinàries lliures: per a una data, un dia de la setmana o tot el semestre,
    la franja amb menys aules ordinàries lliures."""
    ordinaries = set(d.aules.loc[d.aules['ordinaria'] == 1, 'aula'])
    h2 = d.horari[d.horari['semestre'] == 2]
    if data:
        dates = [_data(data)]
    elif dia:
        k = _dia(dia)
        dates = sorted({x for x in h2['data_nova'] if 'LMXJV'[x.weekday()] == k})
    else:
        dates = sorted(set(h2['data_nova']))
    h = h2[h2['aula_nova'].isin(ordinaries) & (h2['sense_espai'] != '1') & h2['data_nova'].isin(dates)]
    pitjor, sota = None, []
    for data_ in dates:
        x = h[h['data_nova'] == data_]
        for f0 in FRANGES:
            lliures = len(ordinaries) - x[(x['ini_min'] < f0 + 60) & (x['fi_min'] > f0)]['aula_nova'].nunique()
            if pitjor is None or lliures < pitjor[0]:
                pitjor = (lliures, str(data_), hhmm(f0))
            if lliures < 2:
                sota.append({'data': str(data_), 'franja': hhmm(f0), 'lliures': lliures})
    return {'aules_ordinaries': len(ordinaries), 'dates_comprovades': len(dates),
            'minim_lliures': pitjor[0] if pitjor else None,
            'on_es_minim': {'data': pitjor[1], 'franja': pitjor[2]} if pitjor else None,
            'franges_sota_2': sota[:20], 'n_franges_sota_2': len(sota), 'compleix_regla_8': not sota, 'fonts': []}


def sessions_canviades(codi: str = '', grup: str = '', cohort: str = '', assignatura: str = '') -> dict:
    """Quines sessions han canviat de dia o d'hora respecte de l'horari d'avui (partida) a causa del 5.2."""
    h = d.horari[d.horari['semestre'] == 2]
    if codi:
        h = h[h['codi'] == str(codi).strip()]
    if grup:
        g = grup.strip().upper()
        h = h[h['grup'] == g] if '/' in g else h[h['grup'].str.match(rf'^[A-Z]+/{g}\d*$')]
    if cohort:
        h = h[h['titulacions_curs'].str.contains(cohort, case=False, regex=False)]
    if assignatura:
        h = h[h['assignatura'].str.contains(assignatura, case=False, regex=False)]
    if h.empty:
        return {'trobat': False, 'avis': 'Cap sessió amb aquests filtres.', 'fonts': []}
    c = h[(h['dia'] != h['dia_nou']) | (h['h_ini'] != h['h_ini_nou'])]
    res = {'trobat': True, 'sessions': len(h), 'canviades': len(c), 'sense_canvi': len(h) - len(c),
           'fonts': c['id_sessio'].head(MAX_LLISTA).tolist()}
    g = c.groupby(['codi', 'assignatura', 'grup', 'dia', 'h_ini', 'dia_nou', 'h_ini_nou']).size().reset_index(name='n')
    res['canvis'] = [{'codi': r.codi, 'assignatura': r.assignatura, 'grup': r.grup,
                      'abans': f'{r.dia} {r.h_ini}', 'ara': f'{r.dia_nou} {r.h_ini_nou}', 'sessions': int(r.n)}
                     for r in g.head(MAX_LLISTA).itertuples()]
    return res


def calendari_info(data: str = '') -> dict:
    """El període del 2n semestre i els dies no lectius (festius, aturades, avaluació); amb `data`, diu si és lectiu."""
    h2 = d.horari[d.horari['semestre'] == 2]
    cal = d.calendari[(d.calendari['data'] >= h2['data_nova'].min()) & (d.calendari['data'] <= h2['data_nova'].max())]
    res = {'semestre_2': {'primer_dia': str(h2['data_nova'].min()), 'darrer_dia': str(h2['data_nova'].max())},
           'dies_no_lectius': [{'data': str(r['data']), 'tipus': r['tipus'], 'motiu': r['motiu']}
                               for _, r in cal.iterrows()][:40], 'fonts': []}
    if data:
        x = _data(data)
        n = int((h2['data_nova'] == x).sum())
        res['consulta'] = {'data': str(x), 'sessions_aquell_dia': n,
                           'avis': _fora_semestre(x) or ('Dia lectiu normal.' if n else 'Cap sessió aquest dia.')}
    return res


def aturada(data: str, h_ini: str = '00:00', h_fi: str = '', motiu: str = "una aturada de l'activitat acadèmica") -> dict:
    """Aturada general: totes les classes d'una data a partir d'una hora (o dins d'una franja) queden cancel·lades.
    Afecta les classes que COMENCEN dins la franja (les ja començades es compten a part). Torna les sessions,
    docents i cohorts afectats perquè es pugui redactar l'avís. No desa res."""
    x = _data(data)
    avis = _fora_semestre(x)
    if 'fora del 2n semestre' in avis:
        return {'error': avis, 'fonts': []}
    ini = _hora(h_ini)
    fi = _hora(h_fi) if h_fi else 24 * 60
    h = d.horari[(d.horari['semestre'] == 2) & (d.horari['data_nova'] == x) & (d.horari['sense_espai'] != '1')]
    en_curs = int(((h['ini_min'] < ini) & (h['fi_min'] > ini)).sum())   # ja començades: no s'inclouen
    h = h[(h['ini_min'] >= ini) & (h['ini_min'] < fi)]
    if h.empty:
        return {'trobat': False, 'avis': avis or 'Cap classe afectada en aquesta franja.', 'fonts': []}
    canvis = []
    for _, f in h.sort_values(['ini_min', 'aula_nova']).iterrows():
        canvis.append({'id_sessio': f['id_sessio'], 'codi': f['codi'], 'assignatura': f['assignatura'],
                       'grup': f['grup'], 'docents': [c for c in f['docents'].split('|') if c],
                       'cohorts': [c for c in f['titulacions_curs'].split('|') if c],
                       'abans': {'data': str(x), 'h_ini': f['h_ini_nou'], 'h_fi': f['h_fi_nou'], 'aula': f['aula_nova']},
                       'despres': {'data': str(x), 'h_ini': f['h_ini_nou'], 'h_fi': f['h_fi_nou'], 'aula': '',
                                   'cancellada': True}})
    return {'data': str(x), 'franja_afectada': f"{hhmm(ini)}-{hhmm(fi) if h_fi else 'final del dia'}", 'motiu': motiu,
            'sessions_afectades': len(canvis), 'ja_en_curs_a_l_hora_d_inici': en_curs,
            'docents_afectats': len({c for v in canvis for c in v['docents']}),
            'cohorts_afectades': sorted({c for v in canvis for c in v['cohorts']}),
            'per_tipus': h['tipus'].value_counts().to_dict(), 'canvis': canvis,
            'nota': "No s'ha desat ni cancel·lat res a l'horari: és només la llista de sessions afectades. Les classes "
                    "s'hauran de recuperar més endavant (això no ho decideix l'assistent).",
            'fonts': [c['id_sessio'] for c in canvis][:MAX_LLISTA]}


def ajuda() -> dict:
    """Què sap fer l'assistent i què no."""
    return {'pot_fer': prompts.POT_FER, 'no_pot_fer': prompts.NO_POT_FER, 'fonts': []}


# ------------------------------------------------------------------------- catàleg d'eines per al LLM (JSON schema)
EINES = {f.__name__: f for f in (consulta_sql, horari_grup, horari_aula, aules_lliures, verifica, que_passa_si,
                                 resol_imprevist, esborrany_avis, ocupacio, horari_docent, cerca_assignatura,
                                 info_aules, reserva_aules, sessions_canviades, calendari_info, aturada, ajuda)}

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
        "de la setmana del semestre. Respecta la reserva de 2 aules ordinàries (regla 8). Amb 'aula' comprova només "
        "aquella aula; si no existeix, ho diu i en proposa de semblants (encara que no es doni l'hora)."),
     'parameters': {'type': 'object', 'properties': {
         'hora_inici': _S, 'durada_min': _I, 'data': _S, 'dia': _S, 'places_min': _I, 'tipus': _S, 'aula': _S,
         'semestre': _I}}},
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
    {'name': 'ocupacio', 'description': (
        "QUINES CLASSES HI HA a una hora (qui té classe i a quines aules): amb data (AAAA-MM-DD) aquell dia; amb dia "
        "(L M X J V; dimecres = X) el patró setmanal. Filtres opcionals tipus_sessio (TE, PAUL, PLAB, SEM) i cohort. "
        "Fes-la servir per a «què hi ha dimarts a les 11?» abans que consulta_sql."),
     'parameters': {'type': 'object', 'properties': {'hora_inici': _S, 'data': _S, 'dia': _S, 'durada_min': _I,
                                                     'tipus_sessio': _S, 'cohort': _S}, 'required': ['hora_inici']}},
    {'name': 'horari_docent', 'description': "Classes d'un docent (codi com D380) per a una data, un dia, una setmana ISO o el patró setmanal.",
     'parameters': {'type': 'object', 'properties': {'docent': _S, 'data': _S, 'dia': _S, 'setmana': _S},
                    'required': ['docent']}},
    {'name': 'cerca_assignatura', 'description': "Troba una assignatura pel nom (o part) o pel codi: grups, cohorts, docents i sessions.",
     'parameters': {'type': 'object', 'properties': {'text': _S}, 'required': ['text']}},
    {'name': 'info_aules', 'description': "Llista d'aules amb capacitat i tipus, filtrable per places_min, tipus o edifici (Q, B...). No mira l'ocupació (per això, aules_lliures).",
     'parameters': {'type': 'object', 'properties': {'places_min': _I, 'tipus': _S, 'edifici': _S}}},
    {'name': 'reserva_aules', 'description': "Comprova la regla de les 2 aules ordinàries sempre lliures: la franja amb menys aules lliures, per a una data, un dia de la setmana o tot el semestre.",
     'parameters': {'type': 'object', 'properties': {'data': _S, 'dia': _S}}},
    {'name': 'sessions_canviades', 'description': "Quines sessions han canviat de dia o hora respecte de l'horari d'avui a causa del 5.2, per grup, codi, cohort o assignatura.",
     'parameters': {'type': 'object', 'properties': {'codi': _S, 'grup': _S, 'cohort': _S, 'assignatura': _S}}},
    {'name': 'calendari_info', 'description': "Primer i darrer dia del 2n semestre, festius i setmanes no lectives; amb data, diu si és un dia lectiu.",
     'parameters': {'type': 'object', 'properties': {'data': _S}}},
    {'name': 'aturada', 'description': (
        "ATURADA GENERAL o cancel·lació de totes les classes d'una data a partir d'una hora (h_ini) o dins d'una "
        "franja (h_fi opcional): torna les sessions, docents i cohorts afectats. No desa res. Després, si es demana "
        "l'avís, crida esborrany_avis (fa servir aquestes sessions)."),
     'parameters': {'type': 'object', 'properties': {'data': _S, 'h_ini': _S, 'h_fi': _S, 'motiu': _S},
                    'required': ['data']}},
    {'name': 'ajuda', 'description': "Què sap fer l'assistent i què no. Crida-la si et pregunten què pots fer.",
     'parameters': {'type': 'object', 'properties': {}}},
]
