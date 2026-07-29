"""
Las sorpresas de resultados dejan de depender de una API de 25 peticiones/día.

Hallazgo del 29/07/2026: el gráfico de sorpresas de Research venía de Alpha
Vantage, cuyo plan gratuito son 25 peticiones AL DÍA. Con ~100 usuarios ese
presupuesto se agota a primera hora y, a partir de ahí, la API devuelve un
aviso de límite en vez de datos -- `quarterly_earnings` llega vacío y el
frontend deja de pintar la sección entera. El MISMO ticker enseñaba el
gráfico o no según la hora, y desaparecía en silencio.

Comprobado en vivo ese día: la respuesta era
{"Information": "...our standard API rate limit is 25 requests per day..."}
y la función devolvía {}.

yfinance da lo mismo gratis, con 24 trimestres en vez de 8, sin clave ni
límite y sin una petición de red extra.

Uso:
    cd backend
    python -m pytest tests/test_quarterly_earnings.py -v
"""
import os
import sys
from unittest.mock import patch

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import services.research_service as rs  # noqa: E402


def _df_earnings(filas):
    """Misma forma que yfinance.Ticker.earnings_dates: índice de fechas
    (descendente) y las tres columnas de EPS."""
    idx = pd.to_datetime([f[0] for f in filas])
    return pd.DataFrame(
        {"EPS Estimate": [f[1] for f in filas],
         "Reported EPS": [f[2] for f in filas],
         "Surprise(%)":  [f[3] for f in filas]},
        index=idx,
    )


def _con_earnings(df):
    class _Ticker:
        def __init__(self, *a, **k): pass
        @property
        def earnings_dates(self): return df
    return patch.object(rs.yf, "Ticker", _Ticker)


def test_devuelve_los_trimestres_con_el_formato_que_espera_el_grafico():
    df = _df_earnings([
        ("2026-07-28", 0.93, 0.97, 4.05),
        ("2026-04-28", 0.81, 0.86, 5.88),
    ])
    with _con_earnings(df):
        r = rs._get_quarterly_earnings("TEST")

    qe = r["quarterly_earnings"]
    assert len(qe) == 2
    assert qe[0] == {"date": "2026-07-28", "reported": 0.97,
                     "estimated": 0.93, "surprise": 4.05}


def test_las_fechas_futuras_ya_anunciadas_no_cuentan_como_publicadas():
    """earnings_dates incluye los próximos resultados ya programados, con el
    EPS reportado a NaN. Colarlos pintaría una barra vacía en el gráfico."""
    df = _df_earnings([
        ("2026-10-27", 1.00, float("nan"), float("nan")),   # aún no publicado
        ("2026-07-28", 0.93, 0.97, 4.05),
    ])
    with _con_earnings(df):
        qe = rs._get_quarterly_earnings("TEST")["quarterly_earnings"]

    assert len(qe) == 1
    assert qe[0]["date"] == "2026-07-28"


def test_se_limita_a_8_trimestres_aunque_haya_mas():
    """yfinance da 24; el gráfico está pensado para 8 y meterle 24 lo
    apelmazaría. El tope es una decisión de presentación, no un límite de
    datos."""
    filas = [(f"{2021 + i // 4:04d}-{(i % 4) * 3 + 1:02d}-15", 1.0, 1.1, 10.0)
             for i in range(20)]
    with _con_earnings(_df_earnings(filas)):
        qe = rs._get_quarterly_earnings("TEST")["quarterly_earnings"]
    assert len(qe) == 8


def test_sin_datos_devuelve_vacio_sin_reventar():
    for vacio in (None, pd.DataFrame()):
        with _con_earnings(vacio):
            assert rs._get_quarterly_earnings("TEST") == {}


def test_alpha_vantage_ya_no_se_usa_en_research():
    """La clave sigue en Settings a propósito (quitarla sin tocar antes el
    .env del VPS tumbaría el arranque, como pasó el 20/07/2026 con
    openrouter_api_key), pero ninguna función puede volver a llamarla."""
    ruta = os.path.join(os.path.dirname(__file__), '..', 'services', 'research_service.py')
    with open(ruta, encoding='utf-8') as f:
        codigo = f.read()
    assert "alphavantage.co" not in codigo
    assert "_get_alpha_vantage" not in codigo
