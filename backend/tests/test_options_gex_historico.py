"""
GEX/DEX de una sesión pasada: por qué no se podía, y qué hubo que guardar.

LA PREMISA DE LA TAREA ERA FALSA, y comprobarlo fue la mitad del trabajo. La
tarea decía «el snapshot diario de la cadena ya se guarda, solo falta un
selector». Se guardaba `oi_snapshot` con strike, vencimiento, tipo y open
interest -- pero la fórmula de gamma necesita ADEMÁS la volatilidad implícita
de cada contrato y el precio del subyacente de ese día. Y los dos se estaban
leyendo del proveedor y descartando en la misma línea (`_process_chain`, donde
se arma `oi_snap`). Sin ellos el GEX de ayer no es caro de calcular: es
imposible.

Así que #184 no era «añadir un selector» sino «empezar a guardar lo que hace
falta», con la consecuencia de que el histórico empieza a contar desde el
despliegue -- los días anteriores no se pueden reconstruir, y eso se dice en
vez de rellenarse.

LO QUE SE PROTEGE AQUÍ:

  1. Un día pasado se recalcula con la MISMA fórmula que el de en vivo. Las
     dos comparten `_acumular_griegas()` y `_montar_gex()` a propósito: tener
     el cálculo dos veces es pedir que divergan, que es el error que este
     proyecto ya corrigió en el motor RS, en el McClellan y en Weinstein.
  2. Los días a vencimiento se cuentan desde la fecha de la SESIÓN, no desde
     hoy. Contar desde hoy daría las griegas de un contrato que ya ha vivido
     semanas de más, y el error crece justo en los vencimientos cortos, que
     es donde más gamma hay concentrada.
  3. Las sesiones sin IV (las anteriores al cambio) NO se ofrecen. Ofrecerlas
     daría un resultado vacío o, peor, uno construido sobre un cero.
  4. El resultado se marca `parcial`, porque la foto guarda los contratos con
     más open interest y no la cadena entera: su total no es comparable con
     el de un día en vivo, y la pantalla tiene que decirlo.

Uso:
    cd backend
    python -m pytest tests/test_options_gex_historico.py -v
"""
import os
import sqlite3
import sys
import tempfile
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import services.options_service as O  # noqa: E402

TICKER = "TEST-GEX"
FECHA = "2026-08-18"
SPOT = 100.0


def _bd_con_foto(filas=None, iv=0.30, spot=SPOT, fecha=FECHA, exp="2026-09-18"):
    """BD temporal con una foto de cadena sembrada a mano."""
    tmp = os.path.join(tempfile.mkdtemp(), "flow.db")
    filas = filas if filas is not None else [
        (95.0, exp, 'call', 1000), (100.0, exp, 'call', 5000), (105.0, exp, 'call', 2000),
        (95.0, exp, 'put', 3000), (100.0, exp, 'put', 4000), (105.0, exp, 'put', 500),
    ]
    with patch.object(O, "DB_PATH", tmp):
        O.init_db()
        O.guardar_oi_snapshot(fecha, [(TICKER, k, e, t, oi, iv, spot) for (k, e, t, oi) in filas])
    return tmp


# ── Lo que hacía falta guardar ───────────────────────────────────────────────

def test_la_foto_guarda_la_volatilidad_y_el_precio_del_subyacente():
    """Sin estos dos campos el GEX de un día pasado no se puede calcular de
    ninguna manera -- no es que sea caro, es que el dato no existe."""
    tmp = _bd_con_foto()
    conn = sqlite3.connect(tmp)
    cols = [r[1] for r in conn.execute("PRAGMA table_info(oi_snapshot)")]
    fila = conn.execute("SELECT iv, spot FROM oi_snapshot LIMIT 1").fetchone()
    conn.close()
    assert "iv" in cols and "spot" in cols, cols
    assert fila[0] == 0.30 and fila[1] == SPOT


def test_una_foto_vieja_sin_iv_no_se_ofrece_como_sesion_disponible():
    """Las filas anteriores al cambio existen pero no sirven. Ofrecerlas daría
    un resultado vacío, o peor, uno calculado sobre un cero."""
    tmp = os.path.join(tempfile.mkdtemp(), "flow.db")
    with patch.object(O, "DB_PATH", tmp):
        O.init_db()
        conn = sqlite3.connect(tmp)
        conn.execute("INSERT INTO oi_snapshot (scan_date, ticker, strike, exp, type, oi) "
                     "VALUES (?,?,?,?,?,?)", ("2026-07-22", TICKER, 100.0, "2026-08-21", "call", 900))
        conn.commit(); conn.close()
        assert O.fechas_gex_disponibles(TICKER) == []
        r = O.get_gamma_exposure_historico(TICKER, "2026-07-22")
    assert r["ok"] is False
    assert "18/08/2026" in r["error"], r["error"]


def test_una_sesion_con_iv_si_se_ofrece():
    tmp = _bd_con_foto()
    with patch.object(O, "DB_PATH", tmp):
        assert O.fechas_gex_disponibles(TICKER) == [FECHA]


# ── El cálculo ──────────────────────────────────────────────────────────────

def test_recalcula_el_gex_de_una_sesion_guardada():
    tmp = _bd_con_foto()
    with patch.object(O, "DB_PATH", tmp):
        r = O.get_gamma_exposure_historico(TICKER, FECHA, max_dte=90)
    assert r["ok"] is True, r.get("error")
    assert r["fecha"] == FECHA
    assert r["historico"] is True
    assert r["price"] == SPOT
    assert r["oi_call"] == 8000 and r["oi_put"] == 7500
    assert len(r["by_strike"]) == 3
    # Convenio de dealer: las calls suman GEX positivo y las puts negativo.
    for fila in r["by_strike"]:
        assert fila["gex_call"] >= 0, fila
        assert fila["gex_put"] <= 0, fila


def test_usa_la_misma_formula_que_el_gex_en_vivo():
    """EL test de fondo. Si el histórico y el de en vivo calcularan por su
    cuenta, acabarían divergiendo sin que nadie se enterara -- ya pasó en este
    proyecto con el motor RS, el McClellan y las fases de Weinstein."""
    from datetime import datetime
    exp = "2026-09-18"
    dias = (datetime.strptime(exp, "%Y-%m-%d").date()
            - datetime.strptime(FECHA, "%Y-%m-%d").date()).days
    T = max(dias, 0.5) / 365.0

    esperado = {}
    O._acumular_griegas(esperado, True, 5000, 0.30, 100.0, SPOT, T)

    tmp = _bd_con_foto(filas=[(100.0, exp, 'call', 5000)])
    with patch.object(O, "DB_PATH", tmp):
        r = O.get_gamma_exposure_historico(TICKER, FECHA, max_dte=90)
    assert r["ok"] is True, r.get("error")
    assert r["by_strike"][0]["gex_call"] == round(esperado[100.0]["gex_call"], 0)
    assert r["by_strike"][0]["dex_call"] == round(esperado[100.0]["dex_call"], 0)


def test_los_dias_a_vencimiento_se_cuentan_desde_la_sesion_no_desde_hoy():
    """Contar desde hoy daría las griegas de un contrato que ya ha vivido
    semanas de más, y el error crece justo en los vencimientos cortos, que es
    donde más gamma hay.

    LAS FECHAS SON RELATIVAS A HOY A PROPÓSITO, y esto es el test, no un
    detalle. La primera versión ponía la sesión en la fecha de hoy -- y así
    «desde hoy» y «desde la sesión» dan el mismo número, con lo que el test
    pasaba igual aunque el código contara mal. Lo destapó el sabotaje:
    cambiar `sesion` por `datetime.now()` no rompía nada. Con la sesión 14
    días atrás, un vencimiento a 30 días de ELLA está a 16 de hoy, y los dos
    criterios ya no se pueden confundir."""
    from datetime import date, timedelta
    sesion = date.today() - timedelta(days=14)
    exp    = sesion + timedelta(days=30)

    tmp = _bd_con_foto(filas=[(100.0, exp.strftime("%Y-%m-%d"), 'call', 5000)],
                       fecha=sesion.strftime("%Y-%m-%d"))
    with patch.object(O, "DB_PATH", tmp):
        r = O.get_gamma_exposure_historico(TICKER, sesion.strftime("%Y-%m-%d"), max_dte=45)
    assert r["ok"] is True, r.get("error")
    assert r["exp_days_range"] == [30, 30], (
        f"{r['exp_days_range']}: 30 es desde la sesion, 16 seria desde hoy")


def test_un_vencimiento_fuera_del_max_dte_no_entra():
    tmp = _bd_con_foto(filas=[(100.0, "2026-12-18", 'call', 5000)])
    with patch.object(O, "DB_PATH", tmp):
        r = O.get_gamma_exposure_historico(TICKER, FECHA, max_dte=30)
    assert r["ok"] is False
    assert "Max DTE" in r["error"]


def test_solo_entran_los_strikes_del_rango_pedido():
    tmp = _bd_con_foto(filas=[
        (100.0, "2026-09-18", 'call', 1000),
        (140.0, "2026-09-18", 'call', 9000),   # fuera de un ±10
    ])
    with patch.object(O, "DB_PATH", tmp):
        r = O.get_gamma_exposure_historico(TICKER, FECHA, max_dte=90, strike_range=10)
    assert r["ok"] is True, r.get("error")
    assert [f["strike"] for f in r["by_strike"]] == [100.0]


# ── Y decir lo que es ────────────────────────────────────────────────────────

def test_el_historico_se_marca_como_parcial():
    """La foto guarda los contratos con más open interest, no la cadena
    entera, así que su total sale por debajo del que habría dado ese día en
    vivo. Sin marcarlo, alguien compararía los dos números como si midieran lo
    mismo."""
    tmp = _bd_con_foto()
    with patch.object(O, "DB_PATH", tmp):
        r = O.get_gamma_exposure_historico(TICKER, FECHA, max_dte=90)
    assert r["parcial"] is True


def test_el_gex_en_vivo_no_se_marca_ni_historico_ni_parcial():
    """El camino de siempre no cambia de significado por este añadido."""
    tmp = _bd_con_foto()
    with patch.object(O, "DB_PATH", tmp):
        r = O.get_gamma_exposure_historico(TICKER, FECHA, max_dte=90)
    # El montador es compartido: con fecha=None tiene que salir limpio.
    vivo = O._montar_gex("AAA", 100.0, {100.0: {"gex_call": 1.0, "gex_put": 0.0,
                                                "dex_call": 1.0, "dex_put": 0.0}},
                         10, 5, 50, 12.0, 1, 30)
    assert vivo["historico"] is False and vivo["parcial"] is False
    assert vivo["fecha"] is None
    assert r["historico"] is True


def test_un_dia_sin_foto_dice_cuales_hay():
    """Un «no hay datos» a secas deja al usuario sin saber qué pedir."""
    tmp = _bd_con_foto()
    with patch.object(O, "DB_PATH", tmp):
        r = O.get_gamma_exposure_historico(TICKER, "2026-08-01")
    assert r["ok"] is False
    assert FECHA in r["error"], r["error"]
