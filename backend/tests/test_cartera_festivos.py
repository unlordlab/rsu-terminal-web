"""
El día después de Labor Day, la Cartera entera se quedó sin «HOY %».

EL CASO, 08/09/2026, reportado por el usuario: «En la sección cartera no se ven
los % hoy, ni el global de % hoy». Reproducido antes de tocar nada, llamando a
la función real con tickers reales:

    AAPL   chg=None  sin_datos_hoy=True  prev_fecha=2026-09-04
    MSFT   chg=None  sin_datos_hoy=True  prev_fecha=2026-09-04
    NVDA   chg=None  sin_datos_hoy=True  prev_fecha=2026-09-04

LA CAUSA. `_ultima_sesion_esperada()` retrocedía saltando solo sábados y
domingos, así que el martes 08/09 esperaba que la última sesión cerrada fuese
el **lunes 07/09** — que era **Labor Day**, con la bolsa cerrada. La última
barra real era la del viernes 04/09, y el guardia de «faltan sesiones» la tomó
por un proveedor degradado: `chg` a None y un guion en cada fila.

Y EL GLOBAL DESAPARECÍA POR CONSTRUCCIÓN, no por un segundo fallo: `pnl_dia_pct`
se calcula solo con las filas que NO tienen `sin_datos_hoy`. Con todas
marcadas, la lista quedaba vacía y la métrica no se emitía.

LA DECISIÓN VIEJA ERA RAZONABLE Y LA CUENTA ESTABA MAL. El docstring anterior
decía: «No conoce los festivos [...] puede saltar de más y mostrar "—" un día:
es la dirección segura del error». Preferir callarse antes que enseñar el
movimiento de varias sesiones como si fuera el del día es correcto — pero el
fallo NO cae el día del festivo, cae el día DESPUÉS, con el mercado abierto.

SEGUNDO DEFECTO, y es el patrón que este proyecto lleva semanas persiguiendo:
la rama que se ejecutó ese día se rendía **sin intentar Finnhub**, mientras la
rama de al lado —el mismo caso, otra condición— sí lo intentaba desde hacía
semanas. Un arreglo aplicado a una rama y no a su hermana.

POR REGLA Y NO POR LISTA. Los festivos se calculan (shared/festivos_mercado.py).
Una lista de fechas caduca en silencio y nadie se entera hasta que un usuario
lo reporta, que es exactamente cómo se ha llegado hasta aquí.

Uso:
    cd backend
    python -m pytest tests/test_cartera_festivos.py -v
"""
import os
import sys
from datetime import date, datetime
from contextlib import contextmanager
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'shared'))

import yfinance as _yf  # noqa: E402
import festivos_mercado as F  # noqa: E402
import services.cartera_service as C  # noqa: E402

NY = ZoneInfo("America/New_York")


def _en(momento):
    """Congela la hora de Nueva York que lee _ultima_sesion_esperada()."""
    real = C.datetime

    class _Falso(real):
        @classmethod
        def now(cls, tz=None):
            return momento
    return patch.object(C, "datetime", _Falso)


# ── El día exacto que lo rompió ──────────────────────────────────────────────

def test_el_martes_despues_de_Labor_Day_espera_el_VIERNES():
    """EL test. Antes devolvía el lunes 07/09, que fue festivo, y por eso la
    cartera entera se quedó a «—» con el mercado abierto."""
    with _en(datetime(2026, 9, 8, 10, 36, tzinfo=NY)):
        assert C._ultima_sesion_esperada() == date(2026, 9, 4), (
            "sigue esperando una sesión que no existió: el guardia de «faltan "
            "sesiones» saltará en falso y no habrá «HOY %» en toda la cartera")


def test_el_propio_dia_del_festivo_tambien_mira_al_viernes():
    """El lunes festivo, con el mercado cerrado todo el día, la última sesión
    sigue siendo el viernes — no el propio lunes."""
    with _en(datetime(2026, 9, 7, 18, 0, tzinfo=NY)):
        assert C._ultima_sesion_esperada() == date(2026, 9, 4)


def test_un_martes_normal_sigue_esperando_el_lunes():
    """El arreglo no puede aflojar el guardia los días corrientes: si deja de
    detectar sesiones que faltan de verdad, vuelve el fallo del 11/08 —
    movimientos de varios días presentados como los de hoy."""
    with _en(datetime(2026, 9, 15, 10, 0, tzinfo=NY)):
        assert C._ultima_sesion_esperada() == date(2026, 9, 14)


# ── La sesión en curso ───────────────────────────────────────────────────────

def test_durante_la_sesion_la_ultima_CERRADA_es_la_anterior():
    """A las 10:00 la barra de hoy está a medias: la última completa es la de
    ayer. Es lo que ya hacía y no puede cambiar."""
    with _en(datetime(2026, 9, 15, 10, 0, tzinfo=NY)):
        assert C._ultima_sesion_esperada() == date(2026, 9, 14)


def test_despues_del_cierre_ya_cuenta_la_de_hoy():
    with _en(datetime(2026, 9, 15, 16, 30, tzinfo=NY)):
        assert C._ultima_sesion_esperada() == date(2026, 9, 15)


def test_el_corte_esta_en_las_16_05_no_en_las_16_00():
    """Cinco minutos de margen para que el proveedor publique la barra."""
    with _en(datetime(2026, 9, 15, 16, 4, tzinfo=NY)):
        assert C._ultima_sesion_esperada() == date(2026, 9, 14)
    with _en(datetime(2026, 9, 15, 16, 5, tzinfo=NY)):
        assert C._ultima_sesion_esperada() == date(2026, 9, 15)


def test_el_sabado_por_la_tarde_no_inventa_una_sesion():
    """`cerrada_la_de_hoy` es cierto (son más de las 16:05) pero el sábado no
    hay sesión que cerrar. La primera versión que escribí devolvía el sábado."""
    with _en(datetime(2026, 9, 12, 20, 0, tzinfo=NY)):
        assert C._ultima_sesion_esperada() == date(2026, 9, 11)


def test_el_lunes_por_la_manana_mira_al_viernes():
    with _en(datetime(2026, 9, 14, 9, 0, tzinfo=NY)):
        assert C._ultima_sesion_esperada() == date(2026, 9, 11)


# ── Los festivos, calculados ─────────────────────────────────────────────────

def test_los_diez_festivos_de_2026():
    """Calculados, no copiados: una lista caduca en silencio."""
    assert sorted(F.festivos_nyse(2026)) == [
        date(2026, 1, 1),    # Año Nuevo (jueves)
        date(2026, 1, 19),   # MLK, 3er lunes de enero
        date(2026, 2, 16),   # Washington, 3er lunes de febrero
        date(2026, 4, 3),    # Viernes Santo
        date(2026, 5, 25),   # Memorial, último lunes de mayo
        date(2026, 6, 19),   # Juneteenth (viernes)
        date(2026, 7, 3),    # 4 de julio cae SÁBADO -> viernes 3
        date(2026, 9, 7),    # Labor Day, el que rompió la cartera
        date(2026, 11, 26),  # Thanksgiving, 4º jueves
        date(2026, 12, 25),  # Navidad (viernes)
    ]


def test_las_fechas_fijas_en_fin_de_semana_se_trasladan():
    """Sábado al viernes anterior, domingo al lunes siguiente."""
    f27 = F.festivos_nyse(2027)
    assert date(2027, 6, 18) in f27, "Juneteenth cae sábado 19: se observa el viernes 18"
    assert date(2027, 7, 5) in f27, "el 4 de julio cae domingo: se observa el lunes 5"
    assert date(2027, 12, 24) in f27, "Navidad cae sábado 25: se observa el viernes 24"


def test_ano_nuevo_en_sabado_NO_se_traslada_al_31_de_diciembre():
    """La excepción del NYSE: la regla general adelantaría al viernes 31, pero
    ese día la bolsa ABRE. El festivo simplemente no se observa.

    Sin esto, un 31 de diciembre se daría por cerrado y el «HOY %» de toda la
    cartera desaparecería exactamente igual que el 08/09."""
    anios = [a for a in range(2026, 2046) if date(a, 1, 1).weekday() == 5]
    assert anios, "no hay ningún 1 de enero en sábado en 20 años: revisar el test"
    for a in anios:
        # El 31 de diciembre anterior sale de `festivos_nyse(a)`, NO de
        # `festivos_nyse(a-1)`: la regla de traslado se aplica al 1 de enero de
        # `a` y lo empuja al año anterior. Mi primera versión miraba el
        # conjunto equivocado y por eso el sabotaje se escapó -- un test verde
        # sobre la excepción que decía proteger.
        assert date(a - 1, 12, 31) not in F.festivos_nyse(a), a
        assert date(a, 1, 1) not in F.festivos_nyse(a), a
        assert F.sesion_habil(date(a - 1, 12, 31)), (
            f"el 31/12/{a - 1} se da por cerrado y la bolsa abre: sería el "
            f"mismo «HOY %» vacío del 08/09")


def test_viernes_santo_sale_de_la_Pascua():
    """El único que no es «fecha fija» ni «enésimo lunes de»."""
    assert F._pascua(2026) == date(2026, 4, 5)
    assert date(2026, 4, 3) in F.festivos_nyse(2026)
    assert F._pascua(2027) == date(2027, 3, 28)
    assert date(2027, 3, 26) in F.festivos_nyse(2027)


def test_ningun_festivo_calculado_cae_en_fin_de_semana():
    """Un festivo en sábado no cierra nada: si sale uno, la regla de traslado
    está mal y se estarían descartando sesiones reales."""
    for anio in range(2026, 2041):
        for f in F.festivos_nyse(anio):
            assert f.weekday() < 5, f"{f} cae en fin de semana"


def test_sesion_anterior_salta_festivos_y_fines_de_semana():
    assert F.sesion_anterior(date(2026, 9, 8)) == date(2026, 9, 4)   # salta Labor Day
    assert F.sesion_anterior(date(2026, 9, 14)) == date(2026, 9, 11)  # salta el finde
    assert F.sesion_anterior(date(2026, 11, 27)) == date(2026, 11, 25)  # salta Thanksgiving


def test_sesion_habil_dice_que_no_a_los_dos_motivos():
    assert not F.sesion_habil(date(2026, 9, 7)), "Labor Day"
    assert not F.sesion_habil(date(2026, 9, 12)), "sábado"
    assert F.sesion_habil(date(2026, 9, 8)), "un martes corriente sí es hábil"


# ── La rama que se rendía sin intentar el respaldo ───────────────────────────

class _TickerSinPrecio:
    """Un `yf.Ticker` que existe pero no sabe el precio en vivo.

    Hacer que `yf.Ticker(...)` explotara no valía: es la PRIMERA línea del
    `try` de `_fetch_price_single`, así que reventaba la función entera antes
    de llegar a la rama que se quiere probar, y el test fallaba por un motivo
    que no era el suyo. Lo que hay que simular es que fast_info no da precio,
    no que yfinance no exista."""

    def __init__(self, ticker):
        self.ticker = ticker

    @property
    def fast_info(self):
        raise RuntimeError("sin precio en vivo")


@contextmanager
def _barras_que_saltan_sesiones(quote):
    """Coloca a `_fetch_price_single` en el caso del 08/09: mercado abierto y la
    última barra diaria varias sesiones por detrás de la esperada.

    DOS COSAS QUE SE ME ESCAPARON AL ESCRIBIR ESTOS TESTS, y por eso el montaje
    está aquí y no repetido en cada uno: `_get_daily_bars` devuelve CUATRO
    valores (última barra, penúltima, y las fechas de las dos), no tres; y todo
    el bloque vive dentro de `if _is_market_open()`, así que sin fijar eso el
    test ni entraba en la rama que dice comprobar. Los dos fallos daban un test
    en rojo, no en verde -- pero un montaje mal hecho que casualmente pase es
    justo lo que deja un guardián sin probar."""
    import services.finnhub_stream_service as FH
    C._price_cache.clear()
    with patch.object(FH, "quote", quote), \
         patch.object(C, "_is_market_open", return_value=True), \
         patch.object(C, "_get_daily_bars",
                      return_value=(50.0, 49.0, date(2026, 8, 20), date(2026, 8, 19))), \
         patch.object(C, "_ultima_sesion_esperada", return_value=date(2026, 9, 4)), \
         patch.object(_yf, "Ticker", _TickerSinPrecio):
        yield


def test_la_rama_de_sesiones_que_faltan_TAMBIEN_intenta_Finnhub():
    """El segundo defecto del 08/09: esta rama se rendía y devolvía «—»
    mientras la de al lado —el mismo caso, otra condición— llevaba semanas
    llamando a Finnhub. Un arreglo aplicado a una rama y no a su hermana.

    Se comprueba EJECUTANDO: `_fetch_price_single` con barras que se saltan
    sesiones tiene que acabar preguntando a Finnhub."""
    llamadas = []

    def _quote(t):
        llamadas.append(t)
        return {"price": 100.0, "prev": 98.0, "chg": 2.04}

    with _barras_que_saltan_sesiones(quote=_quote):
        entrada = C._fetch_price_single("TEST")

    assert llamadas == ["TEST"], (
        "la rama de «faltan sesiones» sigue rindiéndose sin preguntar a la otra "
        "fuente, que es como el 08/09 la cartera entera se quedó a «—»")
    assert entrada["chg"] == 2.04 and entrada["sin_datos_hoy"] is False


def test_si_Finnhub_tampoco_lo_sabe_se_dice_NO_LO_SE():
    """Sin dato de ninguna fuente se pinta «—», nunca un 0% inventado: un cero
    no es una medición, es la ausencia de una."""
    with _barras_que_saltan_sesiones(quote=lambda t: None):
        entrada = C._fetch_price_single("TEST")
    assert entrada["chg"] is None and entrada["sin_datos_hoy"] is True


# ── El global, que desaparecía por construcción ──────────────────────────────

def test_el_porcentaje_global_vuelve_cuando_las_filas_tienen_dato():
    """`pnl_dia_pct` solo suma filas sin `sin_datos_hoy`. Con todas marcadas la
    lista quedaba vacía y la métrica desaparecía entera — no era un segundo
    fallo, era el mismo llegando al agregado."""
    filas = [{"shares": 10, "actual": 110.0, "prev_close": 100.0, "sin_datos_hoy": False},
             {"shares": 5,  "actual": 190.0, "prev_close": 200.0, "sin_datos_hoy": False}]
    con = [r for r in filas if r.get("prev_close") and r["shares"] and not r.get("sin_datos_hoy")]
    hoy = sum(r["shares"] * r["actual"] for r in con)
    ayer = sum(r["shares"] * r["prev_close"] for r in con)
    assert con and round((hoy - ayer) / ayer * 100, 2) == 2.5

    marcadas = [dict(r, sin_datos_hoy=True) for r in filas]
    assert not [r for r in marcadas if not r.get("sin_datos_hoy")], (
        "con todas las filas marcadas no hay global que calcular: es el síntoma "
        "del 08/09 y se arregla en el origen, no aquí")
