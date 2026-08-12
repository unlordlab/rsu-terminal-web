"""
Test del Put/Call ratio del día (12/08/2026, hallazgo #24 de la auditoría de
Options Flow: faltaba el ratio AGREGADO del escaneo — el que ya existía era
por ticker, sobre open interest y dentro del rango de strikes consultado).

Lo que hay que fijar aquí no es la división, que es trivial, sino las dos
cosas que hacen que el número no engañe:

  1. Que NO se confunda con el sesgo del día. Miden cosas distintas: el sesgo
     es direccional (vender un put es alcista) y el put/call solo cuenta
     contratos. Con el escaneo real del 23/07 se ve en vivo: 2,6 veces más
     calls que puts por volumen y aun así el sesgo sale NEUTRAL (54,7%),
     porque 36 de las operaciones con calls son VENTAS, que son bajistas.
  2. Que se calcule por VOLUMEN, que es la definición estándar, y que la de
     prima vaya aparte en vez de sustituirla.

Uso:
    cd backend
    python -m pytest tests/test_options_put_call.py -v
"""
import os
import sqlite3
import sys
from datetime import datetime
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import services.options_service as O  # noqa: E402


@pytest.fixture()
def db(tmp_path):
    ruta = str(tmp_path / "pc_test.db")
    conn = sqlite3.connect(ruta)
    conn.execute("""CREATE TABLE options_flow (
        id INTEGER PRIMARY KEY AUTOINCREMENT, scan_date TEXT NOT NULL,
        scan_ts TEXT NOT NULL, ticker TEXT NOT NULL, strike REAL, exp TEXT,
        type TEXT, action TEXT, premium REAL, premium_fmt TEXT, volume INTEGER,
        oi INTEGER, vol_oi_ratio REAL, score INTEGER, signal TEXT, price REAL,
        strike_pct TEXT, iv REAL, underlying_price REAL, is_block INTEGER DEFAULT 0,
        is_sweep INTEGER DEFAULT 0, near_earnings INTEGER DEFAULT 0, earnings_rel TEXT)""")
    conn.execute("""CREATE TABLE oi_snapshot (
        scan_date TEXT NOT NULL, ticker TEXT NOT NULL, strike REAL NOT NULL,
        exp TEXT, type TEXT, oi INTEGER)""")
    conn.commit()
    conn.close()
    with patch.object(O, "DB_PATH", ruta), patch.object(O, "init_db", lambda: None), \
         patch.object(O, "get_oi_changes", lambda limit=15: {"increase": [], "decrease": []}), \
         patch.object(O, "get_scan_log", lambda d=None: None), \
         patch.object(O, "_obtener_contratos_repetidos", lambda: set()), \
         patch("services.cartera_service.get_cartera_tickers", lambda: set()):
        yield ruta


def _insertar(ruta, filas, fecha="2026-08-12"):
    """filas: (tipo, accion, volumen, prima)"""
    conn = sqlite3.connect(ruta)
    conn.executemany(
        "INSERT INTO options_flow (scan_date, scan_ts, ticker, type, action, volume, premium, "
        "premium_fmt, strike, exp, oi, score) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        [(fecha, "x", "AAA", t, a, v, p, "$1M", 100.0, "2026-12-18", 500, 5)
         for t, a, v, p in filas])
    conn.commit()
    conn.close()


def _pc(ruta):
    return O.get_options_flow_simple()["put_call"]


# ── La cuenta ────────────────────────────────────────────────────────────────

def test_el_ratio_va_por_volumen_de_contratos(db):
    _insertar(db, [("call", "buy", 1000, 5_000_000),
                   ("put",  "buy",  400, 1_000_000)])
    assert _pc(db)["por_volumen"] == 0.4


def test_tambien_se_da_por_prima_y_es_otro_numero(db):
    """La de prima pesa por dinero: una operación grande cuenta más que diez
    pequeñas. No sustituye a la de volumen, va al lado."""
    _insertar(db, [("call", "buy", 1000, 1_000_000),
                   ("put",  "buy",  400, 2_000_000)])
    pc = _pc(db)
    assert pc["por_volumen"] == 0.4
    assert pc["por_prima"] == 2.0, "por dinero mandan los puts, por contratos las calls"


def test_la_direccion_de_la_orden_no_entra_en_el_ratio(db):
    """Un put vendido cuenta como put igual que uno comprado. Eso es lo que lo
    distingue del sesgo del día, y es el motivo de que los dos convivan."""
    _insertar(db, [("put", "buy", 500, 1_000_000), ("call", "buy", 500, 1_000_000)])
    a = _pc(db)["por_volumen"]
    conn = sqlite3.connect(db); conn.execute("UPDATE options_flow SET action='sell'"); conn.commit(); conn.close()
    assert _pc(db)["por_volumen"] == a, "cambiar compra por venta no puede mover el put/call"


def test_el_sesgo_y_el_put_call_pueden_discrepar_sin_que_nada_este_mal(db):
    """El caso real del 23/07: muchas más calls que puts, y aun así el sesgo no
    sale alcista porque buena parte de esas calls están VENDIDAS."""
    _insertar(db, [("call", "sell", 3000, 3_000_000),   # bajista
                   ("put",  "sell",  500, 3_000_000)])  # alcista
    d = O.get_options_flow_simple()
    assert d["put_call"]["por_volumen"] < 1, "hay muchas más calls que puts"
    assert d["dia_bias_pct"] == 50.0, "y sin embargo la dirección está empatada"


# ── Los casos sin dato ───────────────────────────────────────────────────────

def test_sin_calls_no_se_divide_entre_cero(db):
    _insertar(db, [("put", "buy", 500, 1_000_000)])
    pc = _pc(db)
    assert pc["por_volumen"] is None
    assert pc["vol_put"] == 500 and pc["vol_call"] == 0


def test_un_escaneo_sin_volumen_no_inventa_un_ratio(db):
    _insertar(db, [("call", "buy", 0, 1_000_000), ("put", "buy", 0, 1_000_000)])
    assert O.get_options_flow_simple()["put_call"] is None


# ── Lo que acompaña al número ────────────────────────────────────────────────

def test_se_dice_sobre_cuantas_operaciones_se_calcula(db):
    """La cifra no es comparable con el put/call de las bolsas: aquella mide
    todo el mercado y esta solo lo que pasó el filtro del escaneo. Que la UI
    pueda decirlo exige saber cuántas fueron."""
    _insertar(db, [("call", "buy", 100, 1_000), ("put", "buy", 100, 1_000),
                   ("call", "sell", 50, 500)])
    pc = _pc(db)
    assert pc["n_contratos"] == 3
    assert pc["prima_call_fmt"] and pc["prima_put_fmt"]


def test_solo_entra_el_ultimo_escaneo(db):
    """El ratio es DEL DÍA. Mezclar sesiones lo convertiría en otra cosa."""
    _insertar(db, [("put", "buy", 9999, 9_000_000)], fecha="2026-08-01")
    _insertar(db, [("call", "buy", 1000, 1_000_000),
                   ("put",  "buy",  200,   200_000)], fecha="2026-08-12")
    assert _pc(db)["por_volumen"] == 0.2, "el put gigante de agosto 1 no puede contar"
