"""
Options Flow: más de la mitad de las entradas llevaban una dirección inventada.

EL DEFECTO. Todo el módulo se apoya en un booleano: si cada operación fue una
compra o una venta. De ahí salen las cuatro tablas, el sesgo del día y el Net
Premium Score. Se calculaba así:

    if bid > 0 and ask > bid:
        is_buy = price_o >= (bid + ask) / 2     # esto sí mide dirección
    else:
        is_buy = (vol / oi >= 0.3) if oi > 0 else True    # esto NO

La segunda rama estaba puesta como red de seguridad, pero `volumen/open
interest` no mide dirección: mide actividad nueva frente a posiciones que ya
existían. Un contrato con 200.000 de open interest y 50.000 de volumen (ratio
0,25) salía etiquetado «venta» aunque fueran compras masivas; uno recién
listado, con poco OI, salía «compra» pasara lo que pasara.

MEDIDO con los escaneos reales guardados: del escaneo del 17/08, solo **9 de
19 entradas (47,4%)** tenían bid/ask. Las otras 10 llevaban una dirección que
nadie había medido — y por eso aparecían entradas alcistas y bajistas
contradiciéndose sobre el mismo ticker el mismo día, que fue justo lo que
reportó el usuario mirando AMAT.

LA DECISIÓN: fuera. Media entrada de la que no se sabe el signo es peor que
ninguna, porque se puede leer exactamente al revés y desde la pantalla no hay
forma de notarlo.

Y de ahí sale la segunda mitad de este arreglo, que es la que evita cambiar un
problema por otro: si se descartan en silencio, un día en el que el proveedor
no dé bid/ask se ve igual que un día tranquilo. Así que se cuentan y se dicen
— el mismo agujero que ya se tapó una vez con `oi_cero`.

Uso:
    cd backend
    python -m pytest tests/test_options_direccion.py -v
"""
import os
import sys
from unittest.mock import patch

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import services.options_service as O  # noqa: E402


def _fila(bid, ask, last=5.0, vol=5000, oi=20000, strike=100.0):
    return {
        "strike": strike, "lastPrice": last, "bid": bid, "ask": ask,
        "volume": vol, "openInterest": oi, "impliedVolatility": 0.35,
    }


class _Cadena:
    def __init__(self, calls, puts=()):
        self.calls = pd.DataFrame(list(calls))
        self.puts = pd.DataFrame(list(puts)) if puts else pd.DataFrame(
            columns=list(_fila(0, 0).keys()))


def _correr(filas_call):
    """Ejecuta _process_chain sobre una cadena controlada, sin red."""
    from datetime import datetime, timedelta
    exp = (datetime.now().date() + timedelta(days=30)).strftime('%Y-%m-%d')

    class Tk:
        @property
        def fast_info(self):
            class FI:
                last_price = 100.0
            return FI()

        @property
        def options(self):
            return [exp]

        def option_chain(self, _e):
            return _Cadena(filas_call)

        def history(self, **kw):
            return pd.DataFrame()

    with patch.object(O.yf, "Ticker", return_value=Tk()), \
         patch.object(O, "_get_next_earnings", return_value=None), \
         patch.object(O, "_ticker_baseline", return_value=None):
        return O._process_chain("TEST", min_premium=1_000, min_score=0)


# ── La regla: sin bid/ask, la entrada no existe ──────────────────────────────

def test_sin_bid_ask_la_entrada_no_se_publica():
    """EL test. Antes esta misma fila salía publicada con `action` puesto por
    vol/OI, que no mide dirección."""
    r = _correr([_fila(bid=0, ask=0)])
    assert r["ok"] is True
    entradas = (r["calls_bought"] + r["calls_sold"]
                + r["puts_bought"] + r["puts_sold"])
    assert entradas == [], \
        f"se ha publicado una entrada sin poder saber su direccion: {entradas}"


def test_con_bid_ask_valido_la_entrada_si_se_publica_y_con_la_direccion_real():
    """El camino bueno no se toca: precio por encima del punto medio del
    diferencial = agresor comprador."""
    # bid 4, ask 6 -> punto medio 5; lastPrice 5.5 esta por encima => compra
    r = _correr([_fila(bid=4.0, ask=6.0, last=5.5)])
    assert len(r["calls_bought"]) == 1, r["calls_bought"]
    assert r["calls_bought"][0]["action"] == "buy"
    assert r["calls_sold"] == []


def test_precio_por_debajo_del_punto_medio_es_venta():
    r = _correr([_fila(bid=4.0, ask=6.0, last=4.2)])
    assert len(r["calls_sold"]) == 1, r["calls_sold"]
    assert r["calls_sold"][0]["action"] == "sell"
    assert r["calls_bought"] == []


def test_un_diferencial_invertido_o_a_cero_tampoco_vale():
    """`ask <= bid` no es un diferencial real; no se puede sacar un punto medio
    con sentido, asi que tampoco se publica."""
    for bid, ask in [(5.0, 5.0), (6.0, 4.0), (0.0, 5.0), (5.0, 0.0)]:
        r = _correr([_fila(bid=bid, ask=ask)])
        entradas = (r["calls_bought"] + r["calls_sold"]
                    + r["puts_bought"] + r["puts_sold"])
        assert entradas == [], f"bid={bid} ask={ask} no deberia publicar nada"


# ── La otra mitad: que el descarte se vea ────────────────────────────────────

def test_lo_descartado_se_cuenta():
    """Si se descartan en silencio, un dia sin bid/ask se lee como un dia
    tranquilo. Es el mismo agujero que ya se tapo una vez con `oi_cero`."""
    r = _correr([_fila(bid=0, ask=0), _fila(bid=0, ask=0, strike=105.0)])
    assert r["sin_direccion"] == 2, \
        f"descartadas 2 pero contadas {r.get('sin_direccion')}"


def test_lo_publicado_no_se_cuenta_como_descartado():
    r = _correr([_fila(bid=4.0, ask=6.0, last=5.5)])
    assert r["sin_direccion"] == 0


def test_el_escaneo_suma_los_descartes_de_todos_los_valores():
    """El contador tiene que llegar hasta arriba: es lo que permite que la
    pantalla avise en vez de enseñar un dia vacio sin explicacion."""
    def chain_falsa(ticker, min_premium=0, min_score=0):
        return {"ticker": ticker, "ok": True, "price": 10.0,
                "sentiment": "NEUTRAL", "sentiment_prem": "NEUTRAL",
                "net_prem_score": 0.0, "pc_ratio_prem": 1.0,
                "bull_prem": 0.0, "bear_prem": 0.0,
                "total_call_prem": 0.0, "total_put_prem": 0.0, "total_prem": 0.0,
                "oi_max": 100, "oi_snapshot": [],
                "calls_bought": [], "puts_bought": [],
                "calls_sold": [], "puts_sold": [],
                "next_earnings": None, "sin_direccion": 7}

    with patch.object(O, "_process_chain", chain_falsa), \
         patch("services.cartera_service.get_cartera_tickers", return_value=set()):
        r = O.get_options_flow(tickers=["AAA", "BBB", "CCC"])
    assert r["sin_direccion"] == 21, r.get("sin_direccion")


def test_muchos_descartes_marcan_el_escaneo_como_incompleto():
    """Un dia con 400 operaciones descartadas y 3 publicadas NO es un dia
    tranquilo, y la pantalla tiene que poder decirlo."""
    import sqlite3
    import tempfile
    tmp = os.path.join(tempfile.mkdtemp(), "flow.db")
    with patch.object(O, "DB_PATH", tmp):
        O.init_db()
        O.guardar_scan_log("2026-08-18", "2026-08-18 23:00:00", pedidos=579,
                           respondidos=575, con_flujo=40, entradas=3,
                           oi_cero=1, sin_direccion=400)
        d = O.get_scan_log("2026-08-18")
    assert d is not None
    assert d["sin_direccion"] == 400
    assert d["sin_direccion_alto"] is True
    assert d["incompleto"] is True, \
        "3 entradas publicadas frente a 400 descartadas no puede pasar por dia normal"
    assert d["cobertura_baja"] is False, "la cobertura fue buena: el motivo es otro"


def test_pocos_descartes_no_marcan_nada():
    """El aviso tiene que ser raro para que signifique algo."""
    import tempfile
    tmp = os.path.join(tempfile.mkdtemp(), "flow.db")
    with patch.object(O, "DB_PATH", tmp):
        O.init_db()
        O.guardar_scan_log("2026-08-18", "2026-08-18 23:00:00", pedidos=579,
                           respondidos=575, con_flujo=200, entradas=180,
                           oi_cero=1, sin_direccion=12)
        d = O.get_scan_log("2026-08-18")
    assert d["sin_direccion_alto"] is False
    assert d["incompleto"] is False


def test_los_escaneos_viejos_sin_la_columna_no_inventan_un_cero():
    """Los escaneos anteriores a este cambio no tienen el dato. Ausencia se
    dice, no se rellena con un 0 que parecería «no se descartó nada»."""
    import sqlite3
    import tempfile
    tmp = os.path.join(tempfile.mkdtemp(), "flow.db")
    with patch.object(O, "DB_PATH", tmp):
        O.init_db()
        conn = sqlite3.connect(tmp)
        conn.execute("INSERT INTO scan_log (scan_date, scan_ts, pedidos, respondidos, "
                     "con_flujo, entradas, oi_cero) VALUES (?,?,?,?,?,?,?)",
                     ("2026-07-22", "2026-07-22 23:00:00", 579, 500, 150, 148, 2))
        conn.commit()
        conn.close()
        d = O.get_scan_log("2026-07-22")
    assert d["sin_direccion"] is None
    assert d["sin_direccion_alto"] is False
