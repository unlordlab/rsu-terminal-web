"""
Test de la detección de precios rancios en Cartera.

DE DÓNDE SALE. El usuario reportó el 11/08 que la columna "HOY %" llevaba
días mal. Al rastrearlo, el porcentaje no estaba mal calculado: estaba
CONGELADO en el viernes 7 de agosto. Los tres tickers que se revisaron
coincidían en el mismo cierre de referencia:

    COHR  $352,27 (+5,40%)  -> prev implícito $334,22 = cierre del 06/08
    RKLB   $83,52 (+10,37%) -> prev implícito  $75,67 = cierre del 06/08
    SPCX  $132,69 (+15,46%) -> prev implícito $114,92 = cierre del 06/08

Precio de media sesión del 07/08 contra cierre del 06/08: internamente
coherente y correcto... para el 7 de agosto. Mientras tanto la columna
DÍAS sí estaba al día, así que la página parecía fresca.

Lo que no se podía ver desde la pantalla es justo eso: un número plausible
y viejo engaña más que un hueco. El backend ya sabía de qué sesión era el
dato (`chg_fecha` por fila), pero nadie lo resumía ni lo enseñaba.

QUÉ FIJA ESTE FICHERO: que el desfase se detecte y NO se griten falsos
positivos, que es lo que haría inútil el aviso. Un fin de semana o un
festivo no son datos rancios.

Uso:
    cd backend
    python -m pytest tests/test_cartera_sesion.py -v
"""
import sys, os
from datetime import date
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import services.cartera_service as C  # noqa: E402


def _con_sesion_esperada(dia, filas):
    """Fija cuál es la última sesión que debería haber, para no depender de
    cuándo se ejecute el test."""
    with patch.object(C, "_ultima_sesion_esperada", return_value=dia):
        return C._estado_de_los_precios(filas)


def test_datos_de_la_ultima_sesion_no_avisan():
    r = _con_sesion_esperada(date(2026, 8, 10), [{"chg_fecha": "2026-08-10"}])
    assert r["sesion_desfasada"] is False
    assert r["sesion_desfase_dias"] == 0
    assert r["sesion_datos"] == "2026-08-10"


def test_el_caso_reportado_si_avisa():
    """Lo que estaba viendo el usuario: datos del viernes 7 cuando la última
    sesión era la del lunes 10."""
    r = _con_sesion_esperada(date(2026, 8, 10), [{"chg_fecha": "2026-08-07"}])
    assert r["sesion_desfasada"] is True
    assert r["sesion_desfase_dias"] == 3


def test_un_dia_de_retraso_no_grita():
    """Margen deliberado de un día: `_ultima_sesion_esperada()` no conoce los
    festivos, y vale más callarse el 4 de julio que dar un aviso falso cada
    vez que el mercado cierra por fiesta."""
    r = _con_sesion_esperada(date(2026, 8, 11), [{"chg_fecha": "2026-08-10"}])
    assert r["sesion_desfasada"] is False


def test_se_toma_la_sesion_mas_reciente_de_todas_las_filas():
    """Si un solo ticker se queda atrás no es un problema de la cartera; lo
    que importa es si TODA la tabla se ha quedado vieja."""
    filas = [{"chg_fecha": "2026-08-07"}, {"chg_fecha": "2026-08-10"},
             {"chg_fecha": "2026-08-06"}]
    r = _con_sesion_esperada(date(2026, 8, 10), filas)
    assert r["sesion_datos"] == "2026-08-10"
    assert r["sesion_desfasada"] is False


def test_sin_fechas_no_se_inventa_un_veredicto():
    r = _con_sesion_esperada(date(2026, 8, 10), [{"chg_fecha": None}, {}])
    assert r["sesion_datos"] is None
    assert r["sesion_desfasada"] is False


def test_una_fecha_con_formato_raro_no_rompe_la_pagina():
    """Cartera entera se cae si esto lanza. Ante un formato inesperado se
    devuelve lo que se sabe y no se afirma nada del desfase."""
    r = _con_sesion_esperada(date(2026, 8, 10), [{"chg_fecha": "10/08/2026"}])
    assert r["sesion_desfasada"] is False
    assert r["sesion_desfase_dias"] is None


# ── La función que decide cuál es la última sesión ───────────────────────

@pytest.mark.parametrize("ahora,esperada,motivo", [
    ("2026-08-11 03:00", date(2026, 8, 10), "de madrugada, la última completa es la de ayer"),
    ("2026-08-11 12:00", date(2026, 8, 10), "en plena sesión, la última COMPLETA sigue siendo la de ayer"),
    ("2026-08-11 17:00", date(2026, 8, 11), "tras el cierre, ya cuenta la de hoy"),
    ("2026-08-08 12:00", date(2026, 8, 7),  "sábado -> viernes"),
    ("2026-08-09 12:00", date(2026, 8, 7),  "domingo -> viernes"),
])
def test_cual_es_la_ultima_sesion_segun_el_momento(ahora, esperada, motivo):
    from datetime import datetime
    from zoneinfo import ZoneInfo
    fijo = datetime.strptime(ahora, "%Y-%m-%d %H:%M").replace(tzinfo=ZoneInfo("America/New_York"))

    class _dt(C.datetime):
        @classmethod
        def now(cls, tz=None):
            return fijo

    with patch.object(C, "datetime", _dt):
        assert C._ultima_sesion_esperada() == esperada, motivo


# ── El hueco de sesiones: precio de hoy contra un cierre de anteayer ─────

def _precio_con_barras(fecha_ultima, last=379.13, prev=334.22, vivo=324.15):
    """Ejecuta _fetch_price_single con el mercado abierto y unas barras
    diarias cuya ULTIMA fecha se controla, que es la variable del fallo."""
    C._price_cache.clear()

    class _FastInfo:
        last_price = vivo

    class _Ticker:
        fast_info = _FastInfo()

    with patch.object(C, "_get_daily_bars", return_value=(last, prev, fecha_ultima)), \
         patch("yfinance.Ticker", return_value=_Ticker()), \
         patch.object(C, "_is_market_open", return_value=True), \
         patch.object(C, "_ultima_sesion_esperada", return_value=date(2026, 8, 10)):
        return C._fetch_price_single("COHR")


def test_si_faltan_sesiones_no_se_inventa_el_porcentaje_del_dia():
    """EL CASO REPORTADO el 11/08, medido al céntimo antes de arreglarlo.

    Con el mercado abierto la terminal enseñaba COHR -14,50%, LITE -10,09%
    y RKLB -6,31%. Esos números eran exactos... contra el cierre del
    VIERNES 7, porque las barras diarias no traían la sesión del lunes 10.
    Contra el cierre real de ayer eran -0,31%, -1,62% y -3,05%.

    La rama que lo producía empareja el precio de hoy con la última barra
    conocida dando por hecho que es la de AYER. Cuando el proveedor se
    salta sesiones deja de serlo, y sale el movimiento de varios días
    etiquetado como el de hoy -- peor que no dar nada, porque es
    plausible."""
    r = _precio_con_barras(date(2026, 8, 7))     # falta la sesión del 10
    assert r["chg"] is None, f"se inventó un {r['chg']}% con una sesión de hueco"
    assert r["sin_datos_hoy"] is True
    assert r["ultimo_cierre"] == "2026-08-07"


def test_con_las_barras_al_dia_el_porcentaje_se_calcula_normal():
    """La otra mitad: el guardia NO puede saltar en el caso corriente. A
    primera hora de una sesión normal todavía no hay barra de hoy y la
    última ES la de ayer -- ahí el cálculo debe seguir saliendo."""
    r = _precio_con_barras(date(2026, 8, 10))    # la última es la sesión anterior
    assert r["chg"] is not None
    assert r["sin_datos_hoy"] is False


def test_si_la_barra_de_hoy_ya_esta_publicada_se_usa_la_anterior():
    r = _precio_con_barras(date(2026, 8, 11))
    assert r["chg"] is not None
    assert r["prev"] == 334.22, "con la barra de hoy publicada, el cierre de referencia es el penúltimo"
