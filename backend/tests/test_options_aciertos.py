"""
¿Acierta el flujo de opciones? Lo que protege este fichero es que la respuesta
sea honesta, no que sea buena.

EL HALLAZGO (#25). El módulo llevaba desde julio guardando operaciones con su
fecha, su prima y el precio del subyacente, y nadie había comprobado nunca si
predicen algo. El Algoritmo y CANSLIM sí tienen ese seguimiento.

DONDE UN SEGUIMIENTO MIENTE FACIL, que es lo que se ata aquí:

1. MEDIR CONTRA CERO. En un tramo alcista, «apostó al alza y subió» acierta
   casi siempre sin que la señal aporte nada. Se mide contra el S&P 500 en la
   MISMA ventana.

2. DAR UN PORCENTAJE SIN LA MUESTRA. Un 70% sobre 7 casos no es un 70%. Cada
   bloque lleva su `n` y un `suficiente` que dice si se puede leer.

3. RELLENAR UN HORIZONTE QUE NO SE HA CUMPLIDO con la última sesión
   disponible: sería un horizonte más corto disfrazado del que se pide.

4. MEDIR ALGO DISTINTO DE LO QUE SE ENSEÑA. Si el seguimiento contara
   operaciones que la pantalla descarta por rutinarias, el resultado no diría
   nada sobre lo que el usuario mira.

Uso:
    cd backend
    python -m pytest tests/test_options_aciertos.py -v
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


@pytest.fixture
def bd(monkeypatch):
    ruta = os.path.join(tempfile.mkdtemp(), "flow.db")
    monkeypatch.setattr(T, "DB_PATH", ruta, raising=False)
    monkeypatch.setattr(O, "DB_PATH", ruta, raising=False)
    O.init_db()
    T.init_db()
    return ruta


def _op(bd, fecha, ticker, tipo, accion, premium, volume=5_000, oi=1_000, precio=100.0):
    conn = sqlite3.connect(bd)
    conn.execute(
        "INSERT INTO options_flow (scan_date, scan_ts, ticker, strike, exp, type, action, "
        "premium, premium_fmt, volume, oi, vol_oi_ratio, score, signal, price, strike_pct, "
        "iv, underlying_price) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (fecha, fecha + " 23:00", ticker, 100.0, "2026-12-18", tipo, accion, premium,
         "$1M", volume, oi, (volume / oi if oi else 0), 5, "ALTA", precio, "+0%", 0.3, precio))
    conn.commit(); conn.close()


def _serie(precios, inicio="2026-08-03"):
    """Serie diaria de cierres con índice de fechas laborables."""
    idx = pd.bdate_range(start=inicio, periods=len(precios))
    return pd.Series(precios, index=idx, dtype=float)


def _fila(bd, ticker="XOM"):
    conn = sqlite3.connect(bd); conn.row_factory = sqlite3.Row
    r = conn.execute("SELECT * FROM flow_tracked WHERE ticker=?", (ticker,)).fetchone()
    conn.close()
    return r


# ── Qué se registra ──────────────────────────────────────────────────────────

def test_una_senal_por_ticker_y_sesion_con_su_direccion(bd):
    """La señal es «hoy el dinero en XOM apostaba al alza», no cada contrato
    por separado: es lo que el usuario ve en pantalla."""
    _op(bd, "2026-08-03", "XOM", "call", "buy", 9_000_000)
    _op(bd, "2026-08-03", "XOM", "put",  "buy", 1_000_000)
    r = T.registrar_senales("2026-08-03")
    assert r["guardadas"] == 1
    fila = _fila(bd)
    assert fila["nps"] == 80.0 and fila["n_ops"] == 2
    assert fila["precio_entrada"] == 100.0


def test_registrar_dos_veces_no_duplica_ni_reescribe(bd):
    """El precio de entrada de una sesión no cambia después."""
    _op(bd, "2026-08-03", "XOM", "call", "buy", 9_000_000)
    assert T.registrar_senales("2026-08-03")["guardadas"] == 1
    assert T.registrar_senales("2026-08-03")["guardadas"] == 0


def test_lo_rutinario_no_entra_en_el_seguimiento(bd):
    """Si se midiera lo que la pantalla descarta, el resultado no diría nada
    sobre lo que el usuario mira."""
    _op(bd, "2026-08-03", "AAA", "call", "buy", 50_000_000, volume=500, oi=50_000)
    assert T.registrar_senales("2026-08-03")["guardadas"] == 0


def test_backfill_recorre_todas_las_sesiones_guardadas(bd):
    """Aquí SÍ hay pasado que reconstruir: el escaneo lleva desde julio
    guardando el precio del subyacente."""
    for f in ("2026-08-03", "2026-08-04", "2026-08-05"):
        _op(bd, f, "XOM", "call", "buy", 9_000_000)
    r = T.backfill()
    assert r["sesiones"] == 3 and r["guardadas"] == 3


# ── Contra qué se mide ───────────────────────────────────────────────────────

def _con_precios(bd, xom, spy):
    """El servicio importa download_batch DENTRO de la función, así que basta
    con parchear el módulo compartido: no hace falta red en ningún test."""
    close_d = {"XOM": _serie(xom), "SPY": _serie(spy)}
    with patch("yf_batch.download_batch", return_value=(close_d, {})):
        return T.actualizar_resultados()


def test_el_retorno_se_guarda_junto_al_del_indice(bd):
    _op(bd, "2026-08-03", "XOM", "call", "buy", 9_000_000)
    T.registrar_senales("2026-08-03")
    # XOM +10% en 5 sesiones; SPY +4% en las mismas.
    _con_precios(bd, [100, 101, 102, 103, 104, 110] + [110] * 20,
                     [100, 101, 102, 103, 103, 104] + [104] * 20)
    fila = _fila(bd)
    assert fila["ret_5d"] == 10.0
    assert fila["spy_5d"] == 4.0, "sin la referencia no hay contra qué juzgar"


def test_subir_menos_que_el_indice_NO_es_un_acierto_alcista(bd):
    """EL test. Contra cero, esta señal «acertaría»: apostó al alza y el
    ticker subió un 4%. Pero el índice subió un 9% -- estar en ese valor fue
    peor que no hacer nada."""
    _op(bd, "2026-08-03", "XOM", "call", "buy", 9_000_000)
    T.registrar_senales("2026-08-03")
    _con_precios(bd, [100, 100, 100, 100, 100, 104] + [104] * 20,
                     [100, 100, 100, 100, 100, 109] + [109] * 20)
    r = T.resumen()
    b = r["horizontes"]["5"]["todas"]
    assert b["n"] == 1
    assert b["aciertos_pct"] == 0.0, "ha contado como acierto quedarse por detrás del índice"
    assert b["exceso_dirigido"] == -5.0


def test_una_senal_bajista_acierta_si_el_valor_lo_hace_PEOR_que_el_indice(bd):
    _op(bd, "2026-08-03", "XOM", "put", "buy", 9_000_000)
    T.registrar_senales("2026-08-03")
    assert _fila(bd)["nps"] == -100.0
    _con_precios(bd, [100, 100, 100, 100, 100,  95] + [95] * 20,
                     [100, 100, 100, 100, 100, 105] + [105] * 20)
    b = T.resumen()["horizontes"]["5"]["todas"]
    assert b["aciertos_pct"] == 100.0
    # El valor cayó un 5% mientras el índice subía un 5%: quedarse 10 puntos
    # por detrás es un ACIERTO de una señal bajista, asi que dirigido = +10.
    assert b["exceso_dirigido"] == 10.0
    assert b["exceso_universo"] == -10.0, "el del universo va sin signo de la apuesta"


# ── Lo que no se puede saber todavía ─────────────────────────────────────────

def test_un_horizonte_que_no_se_ha_cumplido_se_queda_vacio(bd):
    """No se aproxima con la última sesión disponible: sería un horizonte más
    corto disfrazado del que se pide."""
    _op(bd, "2026-08-03", "XOM", "call", "buy", 9_000_000)
    T.registrar_senales("2026-08-03")
    _con_precios(bd, [100, 101, 102, 103, 104, 110], [100] * 6)
    fila = _fila(bd)
    assert fila["ret_5d"] == 10.0
    assert fila["ret_10d"] is None, "ha rellenado 10 sesiones con solo 6 de histórico"
    assert fila["ret_20d"] is None


def test_una_muestra_pequeña_se_declara_insuficiente(bd):
    """Un 100% de aciertos sobre un caso no es un 100%."""
    _op(bd, "2026-08-03", "XOM", "call", "buy", 9_000_000)
    T.registrar_senales("2026-08-03")
    _con_precios(bd, [100] * 5 + [110] + [110] * 20, [100] * 26)
    b = T.resumen()["horizontes"]["5"]["todas"]
    assert b["n"] == 1
    assert b["suficiente"] is False, "una muestra de 1 no puede presentarse como concluyente"
    assert T.resumen()["min_muestra"] == T.MIN_MUESTRA


def test_sin_señales_no_se_inventa_un_porcentaje(bd):
    r = T.resumen()
    assert r["senales"] == 0
    for d in ("5", "10", "20"):
        assert r["horizontes"][d]["todas"]["aciertos_pct"] is None
        assert r["horizontes"][d]["todas"]["suficiente"] is False


def test_el_escaneo_engancha_el_seguimiento(bd):
    """Que el motor exista no sirve de nada si el escaneo nocturno no lo
    llama: el seguimiento se quedaría vacío para siempre.

    SE MIRA EL CODIGO, NO EL TEXTO. Buscar el nombre a secas pasaba en verde
    con la llamada sustituida por `reg = {...}  # registrar_senales
    desactivado` -- el comentario contiene el nombre. Es la tercera vez que el
    mismo atajo me engaña (ver la nota de descartadas y el pintor del
    grafico), asi que aqui se quitan los comentarios antes de mirar."""
    import inspect
    codigo = [l.split("#")[0] for l in inspect.getsource(O.run_and_save_scan).splitlines()]
    assert any("registrar_senales(" in l for l in codigo), (
        "el escaneo no registra las señales del dia: el seguimiento nunca "
        "tendra nada que medir")
    assert any("actualizar_resultados(" in l for l in codigo), (
        "nadie rellena los retornos: las señales quedarian registradas para "
        "siempre sin resultado")


def test_el_exceso_dirigido_y_el_del_universo_NO_son_lo_mismo(bd):
    """EL test de esta correccion, y sale de un numero real de produccion:
    aciertos por DEBAJO del 50% con un «exceso» POSITIVO y creciente. No era
    una ventaja -- era el sesgo del universo colandose por la puerta de atras,
    porque la media mezclaba las dos direcciones y una señal bajista fallida
    (el valor sube) sumaba positivo.

    Aqui: dos señales bajistas que fallan (sus valores baten al indice). El
    universo sale +10 y la ventaja de seguir la señal, -10."""
    _op(bd, "2026-08-03", "XOM", "put", "buy", 9_000_000)
    _op(bd, "2026-08-03", "AAA", "put", "buy", 9_000_000)
    T.registrar_senales("2026-08-03")
    close_d = {
        "XOM": _serie([100] * 5 + [110] + [110] * 20),
        "AAA": _serie([100] * 5 + [110] + [110] * 20),
        "SPY": _serie([100] * 26),
    }
    with patch("yf_batch.download_batch", return_value=(close_d, {})):
        T.actualizar_resultados()
    b = T.resumen()["horizontes"]["5"]["todas"]
    assert b["n"] == 2
    assert b["aciertos_pct"] == 0.0, "las dos señales bajistas han fallado"
    assert b["exceso_universo"] == 10.0, (
        "estar en esos valores batio al indice: ese es el baseline a batir")
    assert b["exceso_dirigido"] == -10.0, (
        "seguir la señal habria costado 10 puntos; si esto sale positivo, el "
        "signo de la apuesta no se esta aplicando")
