"""
Test de get_cartera_tickers() -- el set de tickers en posicion abierta que
alimenta los badges 💼 de ocho modulos.

Lo que fija este fichero es el FILTRO, que es donde estuvo el error. La
primera version de la lectura rapida filtraba en negativo ("que el estado no
diga CERRADA") y eso deja pasar las filas a medias: las que se empiezan a
teclear en la hoja y quedan sin estado ni precio de compra. Con datos reales
daba 45 tickers frente a los 44 de la pagina de Cartera, y el de mas era una
fila sin completar. Un badge que dice "lo tienes en cartera" cuando la pagina
de Cartera no lo enseña es peor que no tener badge.

Uso:
    cd backend
    python -m pytest tests/test_cartera_tickers.py -v
"""
import sys, os
from unittest.mock import patch

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import services.cartera_service as C  # noqa: E402


HOJA = pd.DataFrame({
    "Fecha":         ["01/01/2026", "02/01/2026", "03/01/2026", "23/07/2026", "04/01/2026"],
    "Ticker":        ["AAPL",       "MSFT",       "TSLA",       "ORCL",       "nvda"],
    "Estado":        ["ABIERTA",    "Open",       "CERRADA",    None,         "abierta"],
    "Precio Compra": [150.0,        300.0,        200.0,        None,         100.0],
})


def _con_hoja(df):
    """Fuerza la lectura de la hoja: se vacian las dos cachés (la de la
    cartera completa y la del propio set) para que no salga por un atajo.

    URL_CARTERA se fija a un valor de mentira a proposito. get_cartera_tickers()
    comprueba que la URL exista ANTES de leer nada, asi que sin esto el
    parcheo de read_csv no llega a usarse nunca y la funcion devuelve un
    conjunto vacio por "URL_CARTERA no configurada" -- el test pasaba en
    local (donde hay .env con la URL real) y fallaba en CI, que arranca sin
    .env. Dos commits con el CI en rojo salieron de aqui."""
    from services.cache import cache
    C._cartera_cache.clear()
    cache.delete(C._TICKERS_CACHE_KEY)
    with patch.object(C.settings, "url_cartera", "https://example.invalid/hoja.csv"), \
         patch.object(C.pd, "read_csv", return_value=df), \
         patch.object(cache, "set"), \
         patch.object(cache, "get", return_value=None):
        return C.get_cartera_tickers()


def test_solo_las_abiertas_y_en_mayusculas():
    assert _con_hoja(HOJA) == {"AAPL", "MSFT", "NVDA"}


def test_una_fila_a_medias_no_cuenta_como_posicion():
    """ORCL: sin estado, sin precio de compra. La pagina de Cartera la
    descarta y este set tiene que descartarla igual, o el badge mentiria."""
    assert "ORCL" not in _con_hoja(HOJA)


def test_las_cerradas_no_cuentan():
    assert "TSLA" not in _con_hoja(HOJA)


def test_sin_columna_de_estado_no_se_adivina():
    """Sin estado no hay forma de saber que esta abierto. Devolver todos los
    tickers de la hoja marcaria como 'en cartera' operaciones ya cerradas."""
    sin_estado = HOJA.drop(columns=["Estado"])
    assert _con_hoja(sin_estado) == set()


def test_un_fallo_al_leer_la_hoja_no_tumba_a_quien_llama():
    """Ocho modulos usan esto para un icono. Un problema de Cartera no puede
    llevarse por delante Research, Scanner o Insider."""
    from services.cache import cache
    C._cartera_cache.clear()
    cache.delete(C._TICKERS_CACHE_KEY)
    # Con URL valida, para que el fallo que se prueba sea el de la lectura y
    # no el de la URL ausente -- si no, este test pasaria sin llegar nunca a
    # read_csv, que es justo lo que dice estar comprobando.
    with patch.object(C.settings, "url_cartera", "https://example.invalid/hoja.csv"), \
         patch.object(C.pd, "read_csv", side_effect=Exception("hoja caida")), \
         patch.object(cache, "get", return_value=None), patch.object(cache, "set"):
        assert C.get_cartera_tickers() == set()
