"""
Test del flujo de opciones en Research (12/08/2026, hallazgo #21 de la
auditoría de Options Flow: "Research no llama a `api/v1/options` ni una vez").

El dato ya estaba calculado y guardado por el escaneo nocturno; lo que faltaba
era enseñarlo donde se mira un valor. `get_flow_badge()` es deliberadamente
distinta de `get_ticker_history_summary()`: aquella pide el precio a yfinance
para el upside, y esto se llama desde `get_research()`, que ya tiene precio y
no debe gastar cuota de Yahoo para pintar una etiqueta.

Uso:
    cd backend
    python -m pytest tests/test_options_flow_badge.py -v
"""
import os
import sqlite3
import sys
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import services.options_service as O  # noqa: E402


def _fecha(hace_dias):
    return (datetime.now() - timedelta(days=hace_dias)).strftime("%Y-%m-%d")


@pytest.fixture()
def db(tmp_path):
    ruta = str(tmp_path / "flow_test.db")
    conn = sqlite3.connect(ruta)
    conn.execute("""CREATE TABLE options_flow (
        id INTEGER PRIMARY KEY AUTOINCREMENT, scan_date TEXT NOT NULL,
        scan_ts TEXT NOT NULL, ticker TEXT NOT NULL, strike REAL, exp TEXT,
        type TEXT, action TEXT, premium REAL, premium_fmt TEXT, volume INTEGER,
        oi INTEGER, vol_oi_ratio REAL, score INTEGER, signal TEXT, price REAL,
        strike_pct TEXT, iv REAL, underlying_price REAL,
        is_block INTEGER DEFAULT 0)""")
    conn.commit()
    conn.close()
    with patch.object(O, "DB_PATH", ruta), patch.object(O, "init_db", lambda: None):
        yield ruta


def _insertar(ruta, filas):
    """filas: (ticker, tipo, accion, prima, score, dias_atras)"""
    conn = sqlite3.connect(ruta)
    conn.executemany(
        "INSERT INTO options_flow (scan_date, scan_ts, ticker, type, action, premium, score) "
        "VALUES (?,?,?,?,?,?,?)",
        [(_fecha(d), "x", t, tipo, acc, prem, sc) for t, tipo, acc, prem, sc, d in filas])
    conn.commit()
    conn.close()


# ── Sin dato, nada -- y eso es lo normal ─────────────────────────────────────

def test_un_ticker_sin_flujo_devuelve_none(db):
    """La mayoría de valores no tienen nada la mayoría de días: el escaneo solo
    guarda lo que pasa sus filtros. `None` hace que la sección no se pinte, en
    vez de una tarjeta vacía o llena de ceros."""
    assert O.get_flow_badge("AAPL") is None


def test_lo_que_esta_fuera_de_la_ventana_no_cuenta(db):
    """Flujo de hace un mes no dice nada de hoy. Es justo lo que pasa con la
    base local: su último escaneo es del 23/07 y por eso todo sale None."""
    _insertar(db, [("AAPL", "call", "buy", 1_000_000, 8, 40)])
    assert O.get_flow_badge("AAPL", days=14) is None
    assert O.get_flow_badge("AAPL", days=60) is not None


# ── El sesgo ─────────────────────────────────────────────────────────────────

def test_comprar_calls_es_alcista(db):
    _insertar(db, [("AAA", "call", "buy", 1_000_000, 8, 2)])
    b = O.get_flow_badge("AAA")
    assert b["sesgo"] == "ALCISTA" and b["nps"] == 1.0


def test_comprar_puts_es_bajista(db):
    _insertar(db, [("AAA", "put", "buy", 1_000_000, 8, 2)])
    assert O.get_flow_badge("AAA")["sesgo"] == "BAJISTA"


def test_vender_puts_tambien_cuenta_como_alcista(db):
    """Quien vende puts cobra por comprometerse a comprar más abajo: apuesta a
    que no baja. Es el mismo criterio que usa el módulo de Options Flow, para
    que las dos pantallas no digan cosas distintas del mismo ticker."""
    _insertar(db, [("AAA", "put", "sell", 1_000_000, 8, 2)])
    assert O.get_flow_badge("AAA")["sesgo"] == "ALCISTA"


def test_un_reparto_casi_igualado_es_mixto(db):
    """Sin umbral, un 51/49 se anunciaría como «alcista». Por debajo de ±0,20
    hay flujo pero no dirección."""
    _insertar(db, [("AAA", "call", "buy", 510_000, 5, 1),
                   ("AAA", "put",  "buy", 490_000, 5, 1)])
    assert O.get_flow_badge("AAA")["sesgo"] == "MIXTO"


def test_el_sesgo_nunca_contradice_al_numero_que_se_enseña(db):
    """Con el NPS crudo, un 0,1997 se pintaba como «0.2» y se etiquetaba MIXTO
    porque no llegaba al umbral de 0,20 — una contradicción que el usuario no
    puede resolver desde la pantalla. Se clasifica sobre el valor redondeado."""
    _insertar(db, [("AAA", "call", "buy", 599_900, 5, 1),
                   ("AAA", "put",  "buy", 400_100, 5, 1)])
    b = O.get_flow_badge("AAA")
    assert b["nps"] == 0.2 and b["sesgo"] == "ALCISTA"


# ── El resto del contenido ───────────────────────────────────────────────────

def test_se_pondera_por_dinero_no_por_numero_de_operaciones(db):
    """Tres operaciones pequeñas no pesan más que una grande: lo que importa es
    cuánto dinero se ha movido."""
    _insertar(db, [("AAA", "put",  "buy",    10_000, 4, 1),
                   ("AAA", "put",  "buy",    10_000, 4, 1),
                   ("AAA", "put",  "buy",    10_000, 4, 1),
                   ("AAA", "call", "buy", 5_000_000, 9, 1)])
    assert O.get_flow_badge("AAA")["sesgo"] == "ALCISTA"


def test_el_resumen_trae_lo_que_pinta_la_tarjeta(db):
    _insertar(db, [("AAA", "call", "buy", 2_000_000, 7, 3),
                   ("AAA", "call", "buy", 1_000_000, 9, 1)])
    b = O.get_flow_badge("AAA")
    assert b["n_señales"] == 2
    assert b["prima_total"] == 3_000_000
    assert b["score_max"] == 9, "la señal más fuerte, no la última"
    assert b["ultimo_scan"] == _fecha(1)
    assert b["dias"] == 14
    assert b["prima_fmt"]


def test_una_base_que_no_existe_no_tumba_el_research(db, tmp_path):
    """En una instalación nueva el escaneo nocturno no ha corrido nunca. Que
    Research se caiga por una etiqueta de otro módulo sería absurdo."""
    with patch.object(O, "DB_PATH", str(tmp_path / "no_existe.db")):
        assert O.get_flow_badge("AAA") is None


def test_research_expone_el_campo_y_aguanta_el_fallo():
    """El puente de Research devuelve None ante cualquier error del módulo de
    opciones en vez de propagarlo."""
    import services.research_service as R
    with patch("services.options_service.get_flow_badge",
               side_effect=RuntimeError("la base explotó")):
        assert R._get_flow_badge("AAA") is None
