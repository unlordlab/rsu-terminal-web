"""
Cartera #63: la curva de la cartera, entera y honesta.

EL CASO, 14/09/2026. El usuario no entendía cómo, con un +51% de P&L medio en
las operaciones cerradas, la cartera rendía menos que el S&P 500 en el Track
Record. Medido con los datos reales, salieron cuatro cosas:

  1. LA VENTANA. Se descargaban 180 días: la curva empezaba el 24/12/2025 y la
     primera operación era del 10/02/2025. El 73% de la ganancia total se había
     hecho antes de que empezara. Ahora empieza en la primera operación.
  2. VALORES SIN PRECIO. GLXY se compró el 10/02/2025 y Yahoo no tiene cierres
     hasta el 16/05/2025; SKYT, del 10/03 al 17/07/2026. Su dinero contaba como
     aportado pero no como valor, y la curva daba un salto falso (+36,2%) el
     día que aparecía el precio. Ahora cuentan por lo que costaron.
  3. SPLITS. Yahoo reescala los cierres anteriores a un split; la hoja guarda
     las acciones de entonces. POWL (split 3 por 1 el 06/04/2026) valía un
     tercio. Ahora las acciones se multiplican por los splits posteriores.
  4. PRECIOS DE LA HOJA QUE NO CUADRAN CON SU FECHA: 28 compras y 13 ventas a
     más de un 15% del cierre de ese día (10 operaciones fechadas el mismo
     07/11/2025). Eso no lo puede arreglar el código: se detecta y se enseña.

Uso:
    cd backend
    python -m pytest tests/test_cartera_curva_completa.py -v
"""
import inspect
import os
import re
import sys
from unittest.mock import patch

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import services.cartera_service as C  # noqa: E402
import services.track_record_service as T  # noqa: E402

FRONT = os.path.join(os.path.dirname(__file__), '..', '..', 'frontend')


def _serie(fechas, valores):
    return pd.Series(valores, index=pd.to_datetime(fechas).tz_localize("UTC"), name="Close")


def _curva(precios, operaciones, splits=None):
    """get_portfolio_history con precios y splits controlados. Devuelve la
    curva, los desajustes y los argumentos con los que se pidió el histórico."""
    C._history_cache.update({"updated": 0, "data": None, "key": None, "desajustes": None})
    pedidos = []

    class _Tk:
        def __init__(self, t):
            self._t = t

        def history(self, **kw):
            pedidos.append(kw)
            return pd.DataFrame({"Close": precios[self._t]})

        @property
        def splits(self):
            return (splits or {}).get(self._t, pd.Series(dtype=float))

    abiertas = [o for o in operaciones if not o.get("fecha_cierre")]
    cerradas = [o for o in operaciones if o.get("fecha_cierre")]
    with patch.object(C.yf_executor, "map", lambda fn, it: [fn(x) for x in it]), \
         patch("yfinance.Ticker", lambda t: _Tk(t)):
        h = C.get_portfolio_history(abiertas, cerradas_rows=cerradas)
    return h, C.ultimos_desajustes(), pedidos


def _op(ticker, fecha, compra, inv=1000.0, cierre=None, venta=None):
    return {"ticker": ticker, "fecha": fecha, "compra": compra, "shares": inv / compra, "inv": inv,
            "actual": venta if venta is not None else compra, "fecha_cierre": cierre}


FECHAS = ["2025-02-10", "2025-02-11", "2025-02-12", "2025-02-13"]


# ── 1. Desde la primera operación ───────────────────────────────────────────

def test_el_historico_se_pide_desde_la_primera_operacion():
    precios = {"AAA": _serie(FECHAS, [10.0] * 4), "BBB": _serie(FECHAS, [20.0] * 4)}
    _, _, pedidos = _curva(precios, [_op("AAA", "12/02/2025", 10.0), _op("BBB", "10/02/2025", 20.0)])
    assert pedidos and all(p.get("start") == "2025-02-03" for p in pedidos), pedidos
    assert all("period" not in p for p in pedidos), "ya no se cortan los últimos 180 días"


def test_sin_ninguna_fecha_legible_se_vuelve_a_la_ventana_de_antes():
    precios = {"AAA": _serie(FECHAS, [10.0] * 4)}
    _, _, pedidos = _curva(precios, [_op("AAA", "fecha rota", 10.0)])
    assert pedidos and pedidos[0].get("period") == "180d"


# ── 2. Sin precio todavía ───────────────────────────────────────────────────

def test_comprada_antes_de_tener_precio_cuenta_por_su_coste_y_sin_salto():
    """GLXY: comprada a 34,60 cuando Yahoo aún no tenía cierres. Al aparecer el
    precio (34,60 igualmente) la curva no puede dar un salto."""
    precios = {"AAA": _serie(FECHAS, [10.0] * 4),
               "GLXY": _serie(FECHAS, [float("nan"), float("nan"), 34.6, 34.6])}
    h, desajustes, _ = _curva(precios, [_op("AAA", "10/02/2025", 10.0), _op("GLXY", "10/02/2025", 34.6)])
    assert [p["valor"] for p in h] == [2000.0] * 4, "1000 de AAA + 1000 de GLXY a su coste, también antes del precio"
    assert all(p["retorno"] == 100.0 for p in h), "sin salto el día que aparece el precio"
    assert any(d["ticker"] == "GLXY" and d["tipo"] == "sin_precio" for d in desajustes)


# ── 3. Splits ───────────────────────────────────────────────────────────────

def test_un_split_posterior_a_la_compra_no_divide_el_valor():
    """POWL: comprada a 300; split 3 por 1 después; Yahoo da el histórico
    reescalado (100). 10 acciones de entonces valen 3.000, no 1.000."""
    precios = {"POWL": _serie(FECHAS, [100.0, 100.0, 100.0, 110.0])}
    splits = {"POWL": pd.Series([3.0], index=pd.to_datetime(["2025-02-12"]).tz_localize("UTC"))}
    h, desajustes, _ = _curva(precios, [_op("POWL", "10/02/2025", 300.0, inv=3000.0)], splits)
    assert h[0]["valor"] == 3000.0
    assert h[-1]["valor"] == 3300.0 and h[-1]["retorno"] == 110.0
    assert not [d for d in desajustes if d["ticker"] == "POWL"], "con el split, el precio de compra SÍ cuadra"


def test_un_split_anterior_a_la_compra_no_se_aplica():
    precios = {"NFLX": _serie(FECHAS, [77.0] * 4)}
    splits = {"NFLX": pd.Series([10.0], index=pd.to_datetime(["2024-11-17"]).tz_localize("UTC"))}
    h, _, _ = _curva(precios, [_op("NFLX", "10/02/2025", 77.0, inv=770.0)], splits)
    assert h[0]["valor"] == 770.0


# ── 4. Precios que no cuadran con su fecha ──────────────────────────────────

def test_detecta_compra_y_venta_que_no_cuadran_con_el_cierre():
    precios = {"NBIS": _serie(FECHAS, [111.28, 111.0, 111.0, 98.04]),
               "OK": _serie(FECHAS, [50.0, 51.0, 52.0, 53.0])}
    ops = [_op("NBIS", "10/02/2025", 44.25, cierre="13/02/2025", venta=240.30),
           _op("OK", "10/02/2025", 51.0, cierre="13/02/2025", venta=52.5)]
    _, desajustes, _ = _curva(precios, ops)
    compra = next(d for d in desajustes if d["ticker"] == "NBIS" and d["tipo"] == "compra")
    venta = next(d for d in desajustes if d["ticker"] == "NBIS" and d["tipo"] == "venta")
    assert compra["cierre_ese_dia"] == 111.28 and compra["diferencia_pct"] == 151.5
    assert venta["cierre_ese_dia"] == 98.04 and venta["diferencia_pct"] == -59.2
    assert not [d for d in desajustes if d["ticker"] == "OK"], "comprar a media sesión no es un desajuste"


def test_el_umbral_es_el_medido():
    assert C.UMBRAL_DESAJUSTE_PRECIO == 15.0


def test_get_cartera_publica_los_desajustes():
    fuente = inspect.getsource(C.get_cartera)
    assert '"desajustes_precio": ultimos_desajustes()' in fuente
    i_hist = fuente.index("history = get_portfolio_history(")
    i_des = fuente.index('"desajustes_precio": ultimos_desajustes()')
    assert i_hist < i_des, "los desajustes salen del cálculo de la curva: después, no antes"


# ── Track Record ────────────────────────────────────────────────────────────

def test_el_track_record_avisa_cuantas_operaciones_estan_por_revisar(monkeypatch):
    import services.cartera_service as CS
    import yf_batch  # noqa: F401
    historia = [{"fecha": "2025-02-10", "retorno": 100.0}, {"fecha": "2025-02-11", "retorno": 101.0}]
    monkeypatch.setattr(CS, "get_cartera", lambda: {"ok": True, "history": historia, "desajustes_precio": [
        {"ticker": "NBIS", "fecha": "07/11/2025", "tipo": "compra"},
        {"ticker": "NBIS", "fecha": "07/12/2025", "tipo": "venta"},
        {"ticker": "GLXY", "fecha": "10/02/2025", "tipo": "sin_precio"},
    ]})
    pedidos = []

    def descarga(tickers, **kw):
        pedidos.append(kw)
        return {"SPY": pd.Series([500.0, 505.0], index=pd.to_datetime(["2025-02-10", "2025-02-11"]))}, {}
    monkeypatch.setattr(T, "download_batch", descarga)
    c = T._track_record_cartera()
    assert c["operaciones_por_revisar"] == 2, "sin precio no es un error de la hoja: no cuenta"
    assert c["spy_pct"] == 1.0
    assert pedidos[0]["period"] == "5y", "con 1 año el S&P 500 no llega al primer día de la curva"


def test_las_paginas_lo_ensenan():
    with open(os.path.join(FRONT, 'pages', 'cartera.js'), encoding='utf-8') as f:
        cartera = f.read()
    assert "html += avisoDesajustesPrecio(data.desajustes_precio);" in cartera
    with open(os.path.join(FRONT, 'pages', 'track_record.js'), encoding='utf-8') as f:
        tr = f.read()
    seccion = tr[tr.index("function seccionCartera"):]
    assert "c.operaciones_por_revisar" in seccion[:3000] and "avisoRevision + kpis" in seccion
