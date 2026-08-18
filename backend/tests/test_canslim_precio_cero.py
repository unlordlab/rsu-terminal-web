"""
CANSLIM enseñaba "$0" y "-100%" con el mercado cerrado.

EL CASO. El usuario abrió el análisis de APA con el mercado cerrado y vio:
precio **$0**, variación del día **-100,00%**, distancia al máximo **-100%**, y
la letra N del CAN SLIM fallando con un "-100.0%" que parece medido. El market
cap y los ratios fundamentales salían bien, así que no era que faltaran datos:
era el precio.

LA CAUSA. Mientras el mercado está cerrado, yfinance añade la barra de hoy con
el cierre VACÍO. `_safe(val, default=0.0)` lo convierte en un 0.0 rotundo, y de
ahí sale todo lo demás por pura aritmética:

    chg_pct       = (0 - prev)/prev * 100      -> -100%
    pct_from_high = (0 - max52s)/max52s * 100  -> -100%

Reproducido forzando el NaN sobre el histórico real de APA: price 0.0,
chg_pct -100.0, pct_from_high -100.0. Los tres números de la captura.

LO QUE DUELE DE ESTE FALLO. Es la MISMA causa que ya se arregló el 17/08 para
SPY (`get_market_status`, que anunciaba "MERCADO EN CORRECCIÓN" con el índice
por encima de sus dos medias) y para el scan nocturno (`_scan_single`). Tres
ramas hermanas del mismo fichero: se arreglaron las dos que dieron el síntoma y
se dejó viva la tercera, que es la del análisis individual. El usuario la
encontró un día después.

Uso:
    cd backend
    python -m pytest tests/test_canslim_precio_cero.py -v
"""
import os
import sys
from unittest.mock import patch

import numpy as np
import pandas as pd
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import services.canslim_service as C  # noqa: E402


def _historico(n=300, ultimo_nan=False):
    """Histórico sintético en subida suave. Con `ultimo_nan`, la última barra
    lleva el cierre vacío -- que es justo lo que devuelve yfinance mientras el
    mercado está cerrado."""
    fechas = pd.date_range(end=pd.Timestamp.today().normalize(), periods=n, freq='D')
    cierres = np.linspace(80.0, 100.0, n)
    df = pd.DataFrame({
        'Open': cierres, 'High': cierres * 1.01, 'Low': cierres * 0.99,
        'Close': cierres, 'Volume': np.full(n, 5_000_000.0),
    }, index=fechas)
    if ultimo_nan:
        df.iloc[-1, df.columns.get_loc('Close')] = np.nan
    return df


class _Tk:
    def __init__(self, df):
        self._df = df

    def history(self, **kw):
        return self._df

    @property
    def info(self):
        return {'longName': 'Prueba SA', 'sector': 'Energy',
                'industry': 'Oil & Gas E&P', 'marketCap': 14_600_000_000}

    @property
    def major_holders(self):
        return None

    @property
    def institutional_holders(self):
        return None


def _analizar(df):
    with patch.object(C.yf, "Ticker", lambda *a, **k: _Tk(df)):
        return C.analyze_ticker("PRUEBA")


# ── El caso reportado ────────────────────────────────────────────────────────

def test_con_la_barra_de_hoy_vacia_no_se_enseña_un_precio_de_cero():
    """EL test. Antes: price 0.0, chg_pct -100.0, pct_from_high -100.0."""
    r = _analizar(_historico(ultimo_nan=True))
    assert r.get("ok") is True, r.get("error")
    assert r["price"] > 0, f"precio {r['price']}: se ha vuelto a colar un cero"
    assert r["chg_pct"] > -99, f"chg_pct {r['chg_pct']}: la firma del precio a cero"
    assert r["pct_from_high"] > -99, r["pct_from_high"]


def test_usa_el_ultimo_cierre_REAL_no_el_anterior_a_el():
    """Descartar la barra vacía tiene que dejar el último cierre de verdad, no
    saltarse también uno bueno."""
    df = _historico(ultimo_nan=True)
    ultimo_real = float(df['Close'].dropna().iloc[-1])
    r = _analizar(df)
    assert r["price"] == round(ultimo_real, 2), (r["price"], ultimo_real)


def test_el_camino_normal_no_cambia():
    """Con el mercado abierto (sin barra vacía) el resultado es el de siempre."""
    df = _historico()
    r = _analizar(df)
    assert r["price"] == round(float(df['Close'].iloc[-1]), 2)
    assert r["chg_pct"] > 0  # la serie sube


# ── Y si aun así no hubiera precio ───────────────────────────────────────────

def test_sin_ningun_precio_valido_se_dice_en_vez_de_publicar_un_cero():
    """Un informe entero construido sobre un 0 es peor que no darlo: todo lo
    que cuelga del precio sale con pinta de medido diciendo lo contrario de la
    realidad."""
    df = _historico()
    df['Close'] = 0.0
    r = _analizar(df)
    assert r.get("ok") is False
    assert "precio" in r.get("error", "").lower(), r.get("error")


# ── Las tres ramas hermanas ──────────────────────────────────────────────────

def test_las_tres_ramas_que_leen_un_cierre_descartan_las_barras_vacias():
    """Lo que de verdad falló aquí no fue una línea: fue arreglar la rama que
    dio el síntoma y dejar viva la de al lado. Son tres y las tres tienen que
    filtrar -- el análisis individual, el estado de mercado (SPY) y el scan
    nocturno."""
    import inspect
    fuente = inspect.getsource(C)
    assert fuente.count("['Close'].notna()") >= 3, (
        f"solo {fuente.count(chr(91) + chr(39) + 'Close' + chr(39) + chr(93) + '.notna()')} "
        f"ramas filtran las barras vacías; tienen que ser las tres")

    for fn in (C.analyze_ticker, C.get_market_status, C._scan_single):
        src = inspect.getsource(fn)
        assert "notna()" in src, f"{fn.__name__} no descarta las barras sin cierre"
