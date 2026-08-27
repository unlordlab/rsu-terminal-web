"""
El briefing llamó «cierre» a una sesión que aún tenía horas por delante.

EL CASO, 27/08/2026. El cron de las 07:00 UTC no se disparó, así que el usuario
lanzó el Action A MANO -- con Wall Street abierto. `yf.history()` devuelve
entonces la barra PARCIAL del día en curso, y el prompt le afirmaba al modelo,
en dos reglas distintas, que esos porcentajes eran de cierre. El briefing abrió
con «El S&P 500 CIERRA en positivo gracias a Nvidia» sobre una sesión viva.

NINGÚN DATO ERA FALSO. Lo falso era la etiqueta que les ponía el script:

    briefing   cierre real 26/08   sesión 27/08 (más tarde)
    NVDA  +7%       -1,59%              +8,19%
    XLU  -1,23%     +0,46%              -1,14%     <- el signo cambiado

Y UN AGRAVANTE QUE NO DEPENDE DE LA HORA: la amplitud sale del Gist del
Scanner, que se escribe de noche -- es SIEMPRE del cierre anterior. El bloque
no llevaba fecha, así que el briefing explicó un +0,27% del día 27 con las
tripas del día 26 (280/216, 56,5% al alza), un día en el que el S&P cerró
plano. Dos sesiones cosidas en una narración, sin nada que permitiera notarlo.

LA LECCIÓN: un dato correcto con una etiqueta incorrecta miente igual que un
dato inventado, y es mucho más difícil de ver -- porque cotejarlo contra la
fuente sale bien.

Uso:
    cd backend
    python -m pytest tests/test_briefing_sesion.py -v
"""
import os
import sys
from datetime import date, datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'scripts'))

import daily_briefing as D  # noqa: E402

NY = ZoneInfo("America/New_York")
RUTA_SCRIPT = os.path.join(os.path.dirname(__file__), '..', '..', 'scripts',
                           'daily_briefing.py')


def _et(y, m, d, h, mi=0):
    return datetime(y, m, d, h, mi, tzinfo=NY)


# ── ¿Cierre o sesión a medias? ───────────────────────────────────────────────

def test_la_barra_de_HOY_con_el_mercado_abierto_es_una_sesion_sin_cerrar():
    """EL test. Es exactamente el caso del 27/08: la barra del día en curso
    capturada a media mañana de Nueva York."""
    assert D.sesion_sin_cerrar(date(2026, 8, 27), _et(2026, 8, 27, 10, 30)) is True


def test_la_barra_de_HOY_despues_del_cierre_ya_es_un_cierre():
    assert D.sesion_sin_cerrar(date(2026, 8, 27), _et(2026, 8, 27, 16, 30)) is False


def test_a_las_16_00_en_punto_ya_ha_cerrado():
    """El límite es la campana, no un rato después."""
    assert D.sesion_sin_cerrar(date(2026, 8, 27), _et(2026, 8, 27, 16, 0)) is False


def test_la_ejecucion_normal_del_cron_ve_un_CIERRE():
    """El cron son las 07:00 UTC = 03:00 ET: a esa hora la última barra es la de
    AYER, así que el caso normal no cambia de comportamiento."""
    assert D.sesion_sin_cerrar(date(2026, 8, 26), _et(2026, 8, 27, 3, 0)) is False


def test_un_festivo_o_un_finde_no_necesitan_calendario_de_festivos():
    """Sin sesión no hay barra de hoy, así que el caso se resuelve solo. Se
    pregunta por la fecha de la BARRA justamente para no mantener un calendario
    de festivos que se quedaría desactualizado en silencio."""
    lunes_festivo = _et(2026, 8, 31, 11, 0)
    assert D.sesion_sin_cerrar(date(2026, 8, 28), lunes_festivo) is False


def test_sin_barra_no_se_afirma_que_haya_sesion_en_curso():
    assert D.sesion_sin_cerrar(None, _et(2026, 8, 27, 10, 0)) is False


# ── Lo que ve el modelo ──────────────────────────────────────────────────────

def _prompt(sesion, breadth=None, calendario=None):
    d = {
        "date": "27/08/2026", "time": "09:30", "sesion": sesion,
        "sectors": {}, "calendar": calendario or [],
    }
    return D.build_prompt(d, [], [], [], breadth or {}, [], [], [])


def test_una_sesion_en_curso_se_rotula_como_tal_en_el_prompt():
    """EL otro test. Que el script lo detecte no sirve de nada si el modelo no
    lo recibe."""
    p = _prompt({"en_curso": True, "fecha": "2026-08-27", "hora_et": "09:30"})
    assert "ESTADO DE LA SESION: EN CURSO" in p
    assert "2026-08-27" in p and "09:30 ET" in p
    assert "ESTADO DE LA SESION: CERRADA" not in p


def test_una_sesion_cerrada_se_rotula_como_cierre_CON_SU_FECHA():
    p = _prompt({"en_curso": False, "fecha": "2026-08-26", "hora_et": "03:00"})
    assert "ESTADO DE LA SESION: CERRADA" in p
    assert "2026-08-26" in p


def test_las_reglas_del_prompt_ya_no_AFIRMAN_que_todo_es_un_cierre():
    """Las dos reglas decían «los porcentajes corresponden al cierre de sesión»
    y «Datos sectoriales: son de CIERRE, no intradía» pasara lo que pasara. Que
    la etiqueta sea correcta no sirve si al lado hay una regla que la contradice
    -- el modelo recibiría dos instrucciones opuestas."""
    with open(RUTA_SCRIPT, encoding="utf-8") as fh:
        fuente = fh.read()
    assert "los porcentajes de arriba corresponden al cierre de sesión" not in fuente, (
        "sigue afirmando que los porcentajes son de cierre pase lo que pase")
    assert "Datos sectoriales: son de CIERRE, no intradía." not in fuente
    assert fuente.count("ESTADO DE LA SESIÓN") >= 2, (
        "las dos reglas de datos sectoriales no remiten a la etiqueta de estado")


def test_la_etiqueta_se_calcula_de_verdad_en_get_market_data():
    """Que build_prompt sepa pintarla no sirve de nada si nadie la calcula: sin
    esto, `sesion` llega vacía cada día y todo se rotula como CERRADA."""
    import inspect
    fuente = inspect.getsource(D.get_market_data)
    assert "sesion_sin_cerrar(" in fuente, (
        "get_market_data no llama al detector: la etiqueta sería siempre la "
        "misma, que es justo el fallo que se está arreglando")
    assert 'data["sesion"]' in fuente


# ── La amplitud va una sesión por detrás, siempre ────────────────────────────

_BREADTH = {"pct_above_sma50": 55.1, "mcclellan": -39.0, "mcclellan_estado": "NEUTRO",
            "abi": 11.4, "advances": 1056, "declines": 1328, "new_highs": 89,
            "new_lows": 15, "nh_nl": 74, "sp500_advances": 280,
            "sp500_declines": 216, "sp500_pct_al_alza": 56.5,
            "universo_amplitud": 2384, "universe_size": 498}


def test_la_amplitud_llega_al_prompt_CON_SU_FECHA():
    """El escaneo del Scanner es nocturno y siempre lleva su fecha. Sin ella el
    modelo cose la amplitud a los precios como si fueran del mismo día."""
    p = _prompt({"en_curso": True, "fecha": "2026-08-27", "hora_et": "09:30"},
                breadth=dict(_BREADTH, fecha="2026-08-26"))
    assert "2026-08-26" in p, "la amplitud sigue llegando sin fecha"


def test_si_la_amplitud_va_por_detras_de_los_precios_SE_DICE():
    """El caso del 27/08: precios intradía del día 27, amplitud del cierre del
    26. El briefing explicó un +0,27% del día 27 con las tripas del día 26."""
    p = _prompt({"en_curso": True, "fecha": "2026-08-27", "hora_et": "09:30"},
                breadth=dict(_BREADTH, fecha="2026-08-26"))
    assert "POR DETRAS" in p or "POR DETRÁS" in p
    assert "2026-08-27" in p, "no dice de qué sesión son los precios"


def test_si_van_a_LA_PAR_no_se_dice_que_la_amplitud_va_por_detras():
    """EL test que faltaba, y que casi cuesta cambiar una etiqueta falsa por
    otra. En la ejecución normal del cron (03:00 ET) los precios son el cierre
    de ayer y el escaneo nocturno del Scanner TAMBIÉN: es la misma sesión.
    Afirmar ahí que la amplitud «va por detrás» sería mentir en el camino que
    se recorre todos los días, para arreglar el que se recorre una vez."""
    p = _prompt({"en_curso": False, "fecha": "2026-08-26", "hora_et": "03:00"},
                breadth=dict(_BREADTH, fecha="2026-08-26"))
    assert "POR DETRAS" not in p and "POR DETRÁS" not in p, (
        "dice que la amplitud va por detrás de los precios cuando las dos son "
        "de la misma sesión")
    assert "MISMA sesion" in p or "MISMA sesión" in p


def test_sin_fecha_de_amplitud_no_se_inventa_una():
    p = _prompt({"en_curso": False, "fecha": "2026-08-26", "hora_et": "03:00"},
                breadth=dict(_BREADTH))
    assert "cierre del None" not in p


def _gist_falso(ultima_fecha):
    """Un Gist del Scanner mínimo, con 56 sesiones para que salga el McClellan.
    La última lleva la fecha que se le pase."""
    import json
    from unittest.mock import MagicMock
    fechas = [f"2026-06-{d:02d}" for d in range(1, 29)] * 2
    fechas[-1] = ultima_fecha
    hist = [{"date": f, "advances": 1056, "declines": 1328, "new_highs": 89,
             "new_lows": 15, "pct_above_sma50": 55.1} for f in fechas]
    contenido = {
        "stocks": {"AAPL": {"above_sma50": True}},
        "breadth_history": hist,
        "breadth_sp500": [{"date": ultima_fecha, "advances": 280, "declines": 216}],
        "breadth_russell": [{"date": ultima_fecha, "advances": 776, "declines": 1112}],
        "universe_size": 498,
    }
    r = MagicMock(status_code=200)
    r.json.return_value = {"files": {D.SCANNER_GIST_FILE: {"content": json.dumps(contenido)}}}
    return r


def test_la_fecha_de_la_amplitud_sale_del_GIST_no_del_dia_de_ejecucion():
    """Si se rellenara con la fecha de ejecución en vez de con la del escaneo,
    la etiqueta mentiría exactamente igual que antes -- y con peor pinta,
    porque entonces afirmaría que la amplitud SÍ es de hoy.

    La primera versión de este test miraba el TEXTO del código (que apareciera
    `breadth_hist[-1]`) y el sabotaje se le escapó, porque esa expresión sigue
    usándose tres líneas más arriba para otra cosa. Comprobar una regla contra
    su propia silueta en el fuente no comprueba nada: hay que ejecutarla."""
    from unittest.mock import patch
    with patch.object(D.requests, "get", return_value=_gist_falso("2026-08-26")):
        b = D.get_rsu_breadth_signals()
    assert b["fecha"] == "2026-08-26", (
        "la amplitud no trae la fecha del último escaneo del Gist")

    # Una fecha imposible de confundir con la de hoy: si el sabotaje rellenara
    # con `datetime.now()`, aquí saldría 2026-08-27 y no 1999-01-04.
    hoy = datetime.now().strftime("%Y-%m-%d")
    with patch.object(D.requests, "get", return_value=_gist_falso("1999-01-04")):
        b2 = D.get_rsu_breadth_signals()
    assert b2["fecha"] == "1999-01-04" and b2["fecha"] != hoy, (
        "la fecha se está rellenando con el día de ejecución, no con la del "
        "escaneo: volvería a decir que la amplitud es de hoy cuando es de ayer")


# ── El calendario dice si el dato YA ha salido ───────────────────────────────

def _ev(actual=""):
    return {"time": "08:30", "pais": "USD", "event": "Unemployment Claims",
            "forecast": "208K", "previous": "206K", "impact": "High",
            "actual": actual}


def test_el_calendario_dice_cuando_un_dato_YA_se_ha_publicado():
    """`actual` se recogía en get_market_data() desde siempre y se tiraba antes
    de llegar al prompt: el modelo no podía distinguir un dato publicado de una
    previsión. El 27/08 acertó las peticiones de paro por los titulares, no por
    el calendario."""
    p = _prompt({"en_curso": True, "fecha": "2026-08-27", "hora_et": "09:30"},
                calendario=[_ev("203K")])
    assert "203K" in p, "el dato ya publicado no llega al prompt"


def test_un_dato_que_aun_no_ha_salido_se_marca_como_tal():
    p = _prompt({"en_curso": True, "fecha": "2026-08-27", "hora_et": "09:30"},
                calendario=[_ev("")])
    assert "aún no" in p
    assert "208K" in p and "206K" in p, "el consenso y el previo siguen viajando"


def test_la_cabecera_de_la_tabla_tiene_la_columna_nueva():
    """Una fila con 7 celdas bajo una cabecera de 6 se lee mal: el modelo
    alinearía el dato publicado bajo «Consenso»."""
    p = _prompt({"en_curso": False, "fecha": "2026-08-26", "hora_et": "03:00"},
                calendario=[_ev("203K")])
    cabecera = [l for l in p.splitlines() if l.startswith("| Hora (ET)")][0]
    fila = [l for l in p.splitlines() if "Unemployment Claims" in l][0]
    assert "Publicado" in cabecera
    assert cabecera.count("|") == fila.count("|"), (
        "la fila y la cabecera del calendario no tienen el mismo número de columnas")


def test_la_fila_de_relleno_tambien_cuadra_con_la_cabecera():
    """El día sin eventos usa una fila fija escrita a mano: si se le olvida la
    columna nueva, la tabla queda torcida justo los días más tranquilos."""
    p = _prompt({"en_curso": False, "fecha": "2026-08-26", "hora_et": "03:00"},
                calendario=[])
    cabecera = [l for l in p.splitlines() if l.startswith("| Hora (ET)")][0]
    fila = [l for l in p.splitlines() if "Sin eventos de alto impacto" in l][0]
    assert cabecera.count("|") == fila.count("|")
