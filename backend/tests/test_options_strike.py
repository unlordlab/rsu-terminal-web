"""
¿Llegó el precio al strike? El examen que la propia apuesta se puso.

LA PREGUNTA ES DEL USUARIO, 21/08, y es mejor que la que yo había construido:
medir el retorno a 5, 10 o 20 sesiones mide algo que quien compró nunca
prometió. Una call a 340 con vencimiento el 18/09 es una apuesta CONCRETA --
que el precio llegue a 340 antes de esa fecha-- y tiene su propio examen.

LO QUE HAY QUE PROTEGER, y sale de dos cosas que fallaron al construirlo:

1. UN CONTRATO YA DENTRO DEL DINERO NO PRUEBA NADA. Una call con el strike por
   DEBAJO del precio «llega al strike» el primer día sin que ocurra nada.
   Medido sobre los contratos guardados: 60 de 124 estaban así y tocaban el
   100%. Con ellos dentro el resultado salía 81,5%; sin ellos, 64,1%. La
   diferencia entre esas dos cifras es enteramente este defecto.

2. TOCAR ES INTRADÍA. Con cierres se pierde la mitad de los toques: hay que
   mirar máximos (call) y mínimos (put).

3. EL DÍA DEL ESCANEO NO CUENTA. El escaneo corre con el mercado ya cerrado,
   así que el recorrido de ese día ya había ocurrido cuando se detectó la
   operación. Contarlo sería mirar hacia atrás.

4. UN CONTRATO VIVO NO ES UN FALLO. Si todavía le queda vida y no ha tocado,
   queda pendiente -- contarlo como fallo hundiría el porcentaje con apuestas
   que aún pueden resolverse.

Uso:
    cd backend
    python -m pytest tests/test_options_strike.py -v
"""
import os
import sqlite3
import sys
import tempfile
from unittest.mock import patch

import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import services.options_tracking_service as T  # noqa: E402
import services.options_service as O  # noqa: E402

HOY = "2026-09-30"          # "hoy" para los tests: todo lo de agosto ya venció
SCAN = "2026-08-03"


@pytest.fixture
def bd(monkeypatch):
    ruta = os.path.join(tempfile.mkdtemp(), "flow.db")
    monkeypatch.setattr(T, "DB_PATH", ruta, raising=False)
    monkeypatch.setattr(O, "DB_PATH", ruta, raising=False)
    O.init_db()
    T.init_db()
    T.init_db_strike()
    return ruta


def _op(bd, tipo, accion, strike, spot, exp="2026-08-21", fecha=SCAN, ticker="XOM"):
    conn = sqlite3.connect(bd)
    conn.execute(
        "INSERT INTO options_flow (scan_date, scan_ts, ticker, strike, exp, type, action, "
        "premium, premium_fmt, volume, oi, vol_oi_ratio, score, signal, price, strike_pct, "
        "iv, underlying_price) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (fecha, fecha + " 23:00", ticker, strike, exp, tipo, accion, 1_000_000, "$1M",
         5_000, 1_000, 5.0, 5, "ALTA", spot, "+0%", 0.3, spot))
    conn.commit(); conn.close()


def _precios(altos, bajos, inicio=SCAN):
    idx = pd.bdate_range(start=inicio, periods=len(altos))
    return pd.DataFrame({"High": altos, "Low": bajos}, index=idx)


def _evaluar(hl, hoy=HOY):
    with patch("yf_batch.download_batch", return_value=({}, {}, {"XOM": hl})):
        return T.actualizar_toque_strike(hoy=hoy)


def _fila(bd):
    conn = sqlite3.connect(bd); conn.row_factory = sqlite3.Row
    r = conn.execute("SELECT * FROM strike_tocado").fetchone()
    conn.close()
    return r


# ── El veredicto ─────────────────────────────────────────────────────────────

def test_una_call_que_llega_a_su_strike_cuenta_como_tocada(bd):
    _op(bd, "call", "buy", strike=110.0, spot=100.0)
    _evaluar(_precios(altos=[100, 103, 107, 112, 112], bajos=[99] * 5))
    fila = _fila(bd)
    assert fila["tocado"] == 1
    assert fila["fecha_toque"] == "2026-08-06", "la fecha es la del PRIMER toque"


def test_una_call_que_se_queda_corta_y_vence_cuenta_como_fallo(bd):
    _op(bd, "call", "buy", strike=110.0, spot=100.0)
    _evaluar(_precios(altos=[100, 103, 107, 109, 109], bajos=[99] * 5))
    assert _fila(bd)["tocado"] == 0


def test_una_put_se_juzga_con_los_MINIMOS_no_con_los_maximos(bd):
    """El precio baja a 89 en algún momento aunque cierre arriba: la put a 90
    llegó a su strike."""
    _op(bd, "put", "buy", strike=90.0, spot=100.0)
    _evaluar(_precios(altos=[101] * 5, bajos=[100, 97, 94, 89, 95]))
    assert _fila(bd)["tocado"] == 1


def test_tocar_es_INTRADIA_no_de_cierre(bd):
    """Con cierres se perdería: el máximo llega a 111 un día en que todo lo
    demás está por debajo del strike."""
    _op(bd, "call", "buy", strike=110.0, spot=100.0)
    _evaluar(_precios(altos=[101, 102, 111, 103, 104], bajos=[99] * 5))
    assert _fila(bd)["tocado"] == 1


def test_el_dia_del_escaneo_no_cuenta(bd):
    """El escaneo corre con el mercado cerrado: lo que hizo el precio ESE día
    ya había pasado cuando se detectó la operación. Contarlo sería mirar hacia
    atrás."""
    _op(bd, "call", "buy", strike=110.0, spot=100.0)
    # El único día que supera el strike es el propio día del escaneo.
    _evaluar(_precios(altos=[115, 101, 102, 103, 104], bajos=[99] * 5))
    assert _fila(bd)["tocado"] == 0, "ha contado el recorrido del día del escaneo"


def test_un_contrato_que_sigue_vivo_no_es_un_fallo(bd):
    """Todavía le queda vida: no ha tocado, pero aún puede."""
    _op(bd, "call", "buy", strike=110.0, spot=100.0, exp="2026-12-18")
    r = _evaluar(_precios(altos=[101] * 5, bajos=[99] * 5), hoy="2026-08-10")
    assert r["siguen_vivos"] == 1
    assert _fila(bd) is None, "no puede haber veredicto de algo sin resolver"


# ── Lo que hace que el porcentaje signifique algo ────────────────────────────

def test_un_contrato_YA_dentro_del_dinero_no_cuenta_en_el_total(bd):
    """EL test. Una call con el strike por DEBAJO del precio llega a su strike
    el primer día sin que ocurra nada. Medido en real: 60 de 124 contratos
    estaban así y tocaban el 100%, subiendo el resultado global de 64,1% a
    81,5%."""
    _op(bd, "call", "buy", strike=90.0, spot=100.0)     # ya dentro
    _evaluar(_precios(altos=[101] * 5, bajos=[99] * 5))
    r = T.resumen_strike()
    assert r["total"]["n"] == 0, "un contrato que ya estaba dentro ha entrado en el total"
    assert r["ya_en_el_dinero"]["n"] == 1
    assert r["ya_en_el_dinero"]["tocaron_pct"] == 100.0


def test_una_put_ya_dentro_del_dinero_tambien_se_aparta(bd):
    """El mismo caso al otro lado: strike POR ENCIMA del precio."""
    _op(bd, "put", "buy", strike=110.0, spot=100.0)
    _evaluar(_precios(altos=[101] * 5, bajos=[99] * 5))
    r = T.resumen_strike()
    assert r["total"]["n"] == 0 and r["ya_en_el_dinero"]["n"] == 1


def test_el_porcentaje_se_calcula_solo_sobre_los_resueltos(bd):
    _op(bd, "call", "buy", strike=110.0, spot=100.0, exp="2026-08-21")
    _op(bd, "call", "buy", strike=120.0, spot=100.0, exp="2026-08-21")
    _evaluar(_precios(altos=[100, 105, 112, 112, 112], bajos=[99] * 5))
    t = T.resumen_strike()["total"]
    assert t["n"] == 2 and t["tocaron"] == 1 and t["tocaron_pct"] == 50.0


def test_se_desglosa_por_tipo_de_operacion(bd):
    """Tocar significa lo contrario según el lado: en una put VENDIDA es justo
    lo que el vendedor no quería."""
    _op(bd, "put", "sell", strike=90.0, spot=100.0)
    _evaluar(_precios(altos=[101] * 5, bajos=[100, 97, 94, 89, 95]))
    r = T.resumen_strike()
    assert r["por_tipo"]["Venta de put"]["n"] == 1
    assert r["por_tipo"]["Venta de put"]["tocaron_pct"] == 100.0
    assert r["por_tipo"]["Compra de call"]["n"] == 0


def test_evaluar_dos_veces_no_cambia_un_veredicto_ya_dado(bd):
    """Un contrato que tocó no puede des-tocar."""
    _op(bd, "call", "buy", strike=110.0, spot=100.0)
    hl = _precios(altos=[100, 103, 107, 112, 112], bajos=[99] * 5)
    _evaluar(hl)
    segunda = _evaluar(hl)
    assert segunda["evaluados"] == 0, "ha vuelto a evaluar algo ya resuelto"
    assert T.resumen_strike()["total"]["n"] == 1


def test_lo_rutinario_no_se_evalua(bd):
    """Mismo criterio que el resto del módulo: si no es actividad inusual, no
    se mide -- no sería lo que la pantalla enseña."""
    conn = sqlite3.connect(bd)
    conn.execute(
        "INSERT INTO options_flow (scan_date, scan_ts, ticker, strike, exp, type, action, "
        "premium, premium_fmt, volume, oi, vol_oi_ratio, score, signal, price, strike_pct, "
        "iv, underlying_price) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (SCAN, SCAN + " 23:00", "XOM", 110.0, "2026-08-21", "call", "buy", 1_000_000,
         "$1M", 500, 50_000, 0.01, 5, "ALTA", 100.0, "+0%", 0.3, 100.0))
    conn.commit(); conn.close()
    r = _evaluar(_precios(altos=[100, 103, 107, 112, 112], bajos=[99] * 5))
    assert r["evaluados"] == 0
