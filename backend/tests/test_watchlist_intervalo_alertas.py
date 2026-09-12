"""
Watchlist #13: el comprobador de alertas preguntaba cada 90 s las 24 horas.

EL CASO. `routers/ws.py::alerts_check_loop()` dormía 90 segundos fijos, fines de
semana y festivos incluidos. Con el mercado cerrado eso no puede encontrar nada:
`cartera_service._fetch_price_single()` solo pide precio en vivo entre las 9:30 y
las 16:00 ET y fuera de ahí devuelve el cierre de la última barra diaria, que no
se mueve. Son 960 pasadas por fin de semana preguntando por un número sabido.

EL ARREGLO: 90 s en sesión, 15 min fuera — y el intervalo largo se recorta para
caer justo en la apertura, porque dormir 15 minutos a las 9:25 dejaría ciega la
media hora más movida del día. No se apaga del todo: hay alertas recurrentes que
se reactivan solas.

Uso:
    cd backend
    python -m pytest tests/test_watchlist_intervalo_alertas.py -v
"""
import ast
import inspect
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import services.watchlist_service as W  # noqa: E402

ET = ZoneInfo("America/New_York")
EN_SESION, FUERA = W.INTERVALO_ALERTAS_EN_SESION, W.INTERVALO_ALERTAS_FUERA


def _et(*args):
    return datetime(*args, tzinfo=ET)


@pytest.mark.parametrize("cuando,esperado,por_que", [
    (_et(2026, 9, 11, 9, 30),  EN_SESION, "el primer minuto de sesión"),
    (_et(2026, 9, 11, 12, 0),  EN_SESION, "media sesión"),
    (_et(2026, 9, 11, 15, 59), EN_SESION, "el último minuto"),
    (_et(2026, 9, 11, 16, 0),  FUERA,     "justo al cerrar"),
    (_et(2026, 9, 11, 21, 0),  FUERA,     "de noche"),
    (_et(2026, 9, 12, 11, 0),  FUERA,     "sábado"),
    (_et(2026, 9, 13, 11, 0),  FUERA,     "domingo"),
    (_et(2026, 9, 7, 12, 0),   FUERA,     "Labor Day, festivo entre semana"),
])
def test_el_intervalo_depende_de_si_el_mercado_puede_moverse(cuando, esperado, por_que):
    assert W.intervalo_comprobacion_alertas(cuando) == esperado, por_que


def test_de_madrugada_se_despierta_justo_en_la_apertura():
    """EL detalle que hace que el ahorro no cueste nada: dormir 15 minutos a
    las 9:25 dejaría sin mirar hasta las 9:40, que es media hora de sesión —
    la más movida del día."""
    assert W.intervalo_comprobacion_alertas(_et(2026, 9, 11, 9, 25)) == 5 * 60
    assert W.intervalo_comprobacion_alertas(_et(2026, 9, 11, 9, 29)) == 60


def test_a_un_segundo_de_abrir_espera_ese_segundo_y_no_medio_minuto():
    """Con un suelo de 90 s, una pasada a las 9:29:59 llegaría a las 9:31:29 —
    minuto y medio de la apertura sin mirar. Una pasada de más no le cuesta
    nada a nadie."""
    assert W.intervalo_comprobacion_alertas(_et(2026, 9, 11, 9, 29, 59)) == 5


def test_de_madrugada_de_un_dia_sin_sesion_no_se_recorta_nada():
    """El sábado a las 9:00 no hay apertura a la que llegar."""
    assert W.intervalo_comprobacion_alertas(_et(2026, 9, 12, 9, 0)) == FUERA


def test_el_ahorro_es_real_y_medible():
    """Un fin de semana entero: 1.920 pasadas contra 192."""
    antes = 48 * 3600 // 90
    despues = 48 * 3600 // FUERA
    assert antes == 1920 and despues == 192
    assert despues * 10 == antes, "el intervalo de fuera ya no ahorra un 90%"


def test_el_bucle_usa_el_intervalo_y_no_un_numero_fijo():
    """Que la función exista no sirve de nada si el bucle sigue con su 90."""
    import routers.ws as ws
    fuente = inspect.getsource(ws.alerts_check_loop)
    assert "intervalo_comprobacion_alertas()" in fuente, (
        "el bucle no pide el intervalo")
    arbol = ast.parse(fuente)
    for n in ast.walk(arbol):
        if (isinstance(n, ast.Call) and getattr(n.func, "attr", "") == "sleep"
                and n.args and isinstance(n.args[0], ast.Constant)):
            pytest.fail(f"el bucle vuelve a dormir un número fijo: {n.args[0].value}")
