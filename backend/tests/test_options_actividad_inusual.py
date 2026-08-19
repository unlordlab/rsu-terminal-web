"""
Solo lo inusual: volumen por encima del open interest.

EL CASO. El usuario comparó su Options Flow con una herramienta de referencia
y dijo que la suya no le servía: SNDK con 23 entradas en un día y en todas las
direcciones, CVX cinco veces seguidas, primas de decenas de millones. La
referencia enseñaba 2 entradas de SNDK en una semana.

MI PRIMER DIAGNÓSTICO FUE FALSO. Dije que era un problema de FUENTE DE DATOS:
que la referencia leía operaciones individuales de la cinta OPRA y nosotros
solo agregados de cierre, y que ningún filtro podía salvar esa distancia. El
usuario no se lo tragó -- «la base de ejemplo debe tener otros parámetros de
filtrado, ¿no?» -- y tenía razón. Al comprobar uno de sus contratos (SNDK 2350,
13,1M) sale exactamente con NUESTRA fórmula: ~1.115 contratos x $117 x 100. Es
el mismo tipo de número. Lo que cambia es qué se deja pasar.

LO QUE FALTABA, medido sobre un escaneo real: de 19 entradas, solo 4 tenían
más volumen del día que open interest previo. Los tickers distintos bajaban de
10 a 4, y CVNA dejaba de salir cinco veces.

Ese cociente es la definición clásica de actividad inusual: por encima de 1 se
han negociado hoy más contratos de los que existían abiertos, o sea
posicionamiento NUEVO en vez del trasiego rutinario de una cadena líquida. Y
explica de paso las direcciones contradictorias: resumir el día entero de un
valor muy activo no tiene una dirección que descubrir -- hubo compras y ventas,
como siempre.

SE FILTRA AL ENSEÑAR, NO AL GUARDAR. Un día de opciones no se puede recuperar
después, así que tirar datos por un umbral que todavía se está calibrando sería
irreversible. Se guarda todo lo que pasa los mínimos y se decide en pantalla.

Uso:
    cd backend
    python -m pytest tests/test_options_actividad_inusual.py -v
"""
import os
import sqlite3
import sys
import tempfile
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import services.options_service as O  # noqa: E402

FECHA = "2026-08-18"


def _bd(filas):
    """filas = (ticker, tipo, accion, strike, volume, oi, premium)"""
    tmp = os.path.join(tempfile.mkdtemp(), "flow.db")
    with patch.object(O, "DB_PATH", tmp):
        O.init_db()
    conn = sqlite3.connect(tmp)
    for t, tipo, acc, k, vol, oi, prem in filas:
        conn.execute(
            "INSERT INTO options_flow (scan_date, scan_ts, ticker, strike, exp, type, "
            "action, premium, premium_fmt, volume, oi, vol_oi_ratio, score, signal, "
            "price, strike_pct, iv, underlying_price) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (FECHA, FECHA + " 23:00:00", t, k, "2026-09-18", tipo, acc, prem,
             f"${prem/1e6:.1f}M", vol, oi, (vol/oi if oi else 0), 5, "ALTA",
             1.0, "+0%", 0.3, 100.0))
    conn.commit(); conn.close()
    return tmp


def _panel(tmp):
    with patch.object(O, "DB_PATH", tmp), \
         patch("services.cartera_service.get_cartera_tickers", return_value=set()), \
         patch.object(O, "get_oi_changes", return_value={"increase": [], "decrease": []}), \
         patch.object(O, "_obtener_contratos_repetidos", return_value=set()):
        return O.get_options_flow_simple()


def _cuantas(d):
    return sum(len(d[k]) for k in ("calls_bought", "puts_sold", "puts_bought", "calls_sold"))


# ── El corte ─────────────────────────────────────────────────────────────────

def test_lo_rutinario_no_llega_a_la_pantalla():
    """EL test. Volumen POR DEBAJO del open interest es trasiego normal de una
    cadena líquida, no alguien tomando una posición."""
    tmp = _bd([
        ("CVX", "call", "buy", 180.0,  500, 50_000, 34_700_000),  # vol/OI = 0,01
        ("CVX", "call", "buy", 140.0,  400, 40_000, 29_900_000),
        ("APO", "put",  "sell", 165.0, 3_000, 1_000,  3_600_000),  # vol/OI = 3
    ])
    d = _panel(tmp)
    assert _cuantas(d) == 1, [e["ticker"] for k in ("calls_bought","puts_sold") for e in d[k]]
    assert d["puts_sold"][0]["ticker"] == "APO"
    assert d["descartadas_rutina"] == 2


def test_una_prima_enorme_no_basta_para_entrar():
    """Lo que decidía antes era el tamaño, y por eso los primeros puestos los
    ocupaban siempre los valores más líquidos: mucho volumen diario sobre
    cadenas gigantes, que no dice nada de nadie."""
    tmp = _bd([("CVX", "call", "buy", 180.0, 900, 90_000, 99_000_000)])
    d = _panel(tmp)
    assert _cuantas(d) == 0, "una prima de 99M ha entrado siendo rutinaria"


def test_una_prima_pequeña_si_entra_si_es_inusual():
    """Y al revés: lo que importa no es cuánto dinero, sino que se haya
    operado más de lo que había abierto."""
    tmp = _bd([("CLSK", "put", "buy", 11.0, 800, 200, 181_000)])
    d = _panel(tmp)
    assert _cuantas(d) == 1
    assert d["puts_bought"][0]["ticker"] == "CLSK"


def test_el_mismo_ticker_deja_de_repetirse_cinco_veces():
    """El síntoma que reportó el usuario: CVX cinco veces el mismo día, con
    direcciones que se contradicen."""
    tmp = _bd([("CVX", "call", "buy", 180.0 + i, 500, 50_000, 30_000_000 - i)
               for i in range(5)]
              + [("CVX", "call", "buy", 200.0, 5_000, 1_000, 1_000_000)])
    d = _panel(tmp)
    assert _cuantas(d) == 1, "sigue repitiendose"
    assert d["descartadas_rutina"] == 5


def test_sin_open_interest_no_se_puede_juzgar_y_no_entra():
    """Con OI = 0 el cociente no existe. Dejarlo pasar sería colar justo lo
    que no se puede evaluar."""
    tmp = _bd([("XYZ", "call", "buy", 50.0, 5_000, 0, 2_000_000)])
    assert _cuantas(_panel(tmp)) == 0


# ── Que se diga, no que se calle ─────────────────────────────────────────────

def test_la_pantalla_puede_decir_cuantas_se_dejaron_fuera():
    """Una pantalla con tres filas donde antes había veinte tiene que explicar
    por qué, o parece que el escaneo ha fallado -- que es justo la confusión
    que este módulo arrastraba."""
    tmp = _bd([("CVX", "call", "buy", 180.0, 500, 50_000, 34_000_000),
               ("APO", "put", "sell", 165.0, 3_000, 1_000, 3_600_000)])
    d = _panel(tmp)
    assert d["descartadas_rutina"] == 1
    assert d["umbral_vol_oi"] == O.MIN_VOL_OI_INUSUAL


def test_el_dato_se_guarda_igual_aunque_no_se_enseñe():
    """Se filtra al ENSEÑAR. Un día de opciones no se recupera después, así que
    tirarlo por un umbral que todavía se está calibrando sería irreversible."""
    tmp = _bd([("CVX", "call", "buy", 180.0, 500, 50_000, 34_000_000)])
    conn = sqlite3.connect(tmp)
    guardadas = conn.execute("SELECT COUNT(*) FROM options_flow").fetchone()[0]
    conn.close()
    assert guardadas == 1, "el filtro ha borrado datos en vez de solo ocultarlos"
    assert _cuantas(_panel(tmp)) == 0


def test_el_escaneo_NO_filtra_por_volumen_sobre_open_interest_al_guardar():
    """El sabotaje que los demás tests no cazaban, y es el que importa: si
    alguien mueve este corte de la pantalla al guardado, la base deja de
    registrar lo rutinario y ese dato NO se recupera al día siguiente.

    Los otros tests insertan filas directamente, así que no ven lo que hace
    `_process_chain()`. Este mira su código."""
    import inspect
    fuente = inspect.getsource(O._process_chain)
    lineas = [l.strip() for l in fuente.split("\n")
              if "continue" in l or "vol / oi" in l or "vol/oi" in l]
    sospechosas = [l for l in lineas if ("vol / oi" in l or "vol/oi" in l)]
    assert not sospechosas, (
        f"el escaneo parece filtrar por vol/OI antes de guardar: {sospechosas}. "
        f"Ese corte va en la PANTALLA (MIN_VOL_OI_INUSUAL); al guardar se "
        f"perderia un dato que no se puede recuperar despues.")


# ── Y que no prometa lo que no mide ──────────────────────────────────────────

def test_el_modulo_no_llama_sweep_a_tres_entradas_de_la_misma_cadena():
    """Un sweep es UNA orden partida entre varios mercados a la vez, y la
    Academia se lo ensena asi al usuario ("sugiere urgencia por entrar"). Lo
    que el modulo detecta es otra cosa: 3+ contratos del mismo vencimiento
    con volumen por encima del open interest. El dato de cierre no trae la
    microestructura de la ejecucion, asi que la etiqueta prometia algo que
    el numero no sostiene."""
    import inspect
    fuente = inspect.getsource(O)
    assert '"sweeps"' not in fuente, "la respuesta sigue exportando una lista llamada 'sweeps'"
    assert not hasattr(O, "_detect_sweeps"), (
        "sigue existiendo _detect_sweeps: ese nombre promete una deteccion "
        "de ejecucion que este dato no permite")
    assert hasattr(O, "_detectar_repeticion_en_cadena")
