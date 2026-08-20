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


def test_la_nota_de_descartadas_no_solo_existe_sino_que_se_PINTA():
    """El fallo que esto vigila lo cometi yo y lo vio el usuario en pantalla:
    la nota quedo DECLARADA en options.js pero nadie la metio en el `return`,
    asi que era codigo muerto y la pagina seguia sin explicar por que hay
    menos filas. Lo peor es como lo «verifique»: evalue el fragmento suelto
    en el navegador y comprobe que producia el HTML correcto -- lo cual es
    cierto y no demuestra nada, porque nada lo renderizaba.

    Comprobar que la constante existe habria pasado igual de verde. Lo que
    hay que atar es que aparezca en la linea que construye la pagina."""
    import os
    ruta = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "pages", "options.js")
    with open(ruta, encoding="utf-8") as fh:
        fuente = fh.read()
    declarada = "const notaRutina" in fuente
    pintada = [l for l in fuente.split("\n")
               if l.strip().startswith("return ") and "notaRutina" in l]
    assert declarada, "ha desaparecido la nota de descartadas"
    assert pintada, (
        "notaRutina esta declarada pero NO aparece en ningun return: es codigo "
        "muerto y la pantalla vuelve a no explicar por que hay pocas filas")


# ── Una por valor ────────────────────────────────────────────────────────────
#
# CALIBRADO CONTRA PRODUCCION el 20/08/2026, sobre el escaneo del 19/08 (140
# operaciones). La tabla que decidio los dos cortes:
#
#     vol/OI >= 1     87 entradas   55 tickers   MSFT x6
#     vol/OI >= 2     62            41           MSFT x6
#     vol/OI >= 3     42            33           INTC x3
#
# MSFT aguanta seis veces hasta vol/OI >= 2 y NO son filas rutinarias: son seis
# contratos genuinamente inusuales del mismo valor el mismo dia. Por eso hacen
# falta dos cortes distintos y no basta con subir el umbral.

def test_el_mismo_valor_no_ocupa_seis_filas_aunque_las_seis_sean_inusuales():
    """El caso MSFT, tal cual salio en produccion."""
    tmp = _bd([("MSFT", "call", "sell", 400.0 + i, 5_000, 1_000, 20_000_000 - i * 100)
               for i in range(6)]
              + [("INTC", "call", "buy", 30.0, 4_000, 1_000, 900_000)])
    d = _panel(tmp)
    assert _cuantas(d) == 2, "un valor sigue ocupando varias filas"
    assert d["repetidas_del_mismo"] == 5
    assert d["max_por_ticker"] == O.MAX_POR_TICKER


def test_la_que_sobrevive_es_la_de_mayor_prima():
    """Eleccion documentada en MAX_POR_TICKER: la pantalla ordena y se lee por
    prima, asi que la representante del valor es la mas grande del dia."""
    tmp = _bd([("MSFT", "call", "sell", 400.0, 5_000, 1_000, 3_000_000),
               ("MSFT", "call", "sell", 410.0, 5_000, 1_000, 20_000_000),
               ("MSFT", "call", "sell", 420.0, 5_000, 1_000, 1_000_000)])
    d = _panel(tmp)
    assert _cuantas(d) == 1
    assert d["calls_sold"][0]["premium"] == 20_000_000


def test_el_tope_es_por_VALOR_no_por_tabla():
    """Si el tope se aplicara dentro de cada tabla por separado, un valor con
    actividad en las dos direcciones volveria a salir cuatro veces con
    direcciones que se contradicen -- que es media queja del usuario."""
    tmp = _bd([("XOM", "call", "buy",  120.0, 5_000, 1_000, 9_000_000),
               ("XOM", "put",  "buy",  110.0, 5_000, 1_000, 8_000_000),
               ("XOM", "call", "sell", 130.0, 5_000, 1_000, 7_000_000),
               ("XOM", "put",  "sell", 100.0, 5_000, 1_000, 6_000_000)])
    d = _panel(tmp)
    assert _cuantas(d) == 1, "el mismo valor aparece en varias tablas a la vez"


def test_el_sesgo_del_dia_NO_se_calcula_sobre_la_lista_recortada():
    """El tope es de PANTALLA. Si el sesgo se calculara sobre lo que cabe en la
    tabla, un porcentaje del dia dependeria de cuantas filas quepan -- que no
    significa nada.

    LOS NUMEROS ESTAN ELEGIDOS PARA QUE LA DIFERENCIA CAMBIE LA CONCLUSION, no
    solo el decimal: cinco compras de calls de MSFT de 10M (50M alcistas) y una
    compra de puts de INTC de 30M. Sobre todo lo inusual el dia es ALCISTA
    (50 de 80 = 62,5%); sobre las dos filas visibles saldria BAJISTA (10 de 40
    = 25%). Una primera version de este test usaba 1M en vez de 30M y daba
    90,9% frente a 98%: pasaba en verde con el calculo mal puesto, porque el
    umbral que comprobaba (>90) no separaba los dos casos. Lo descubrio el
    sabotaje de mover los acumuladores detras del tope."""
    tmp = _bd([("MSFT", "call", "buy", 400.0 + i, 5_000, 1_000, 10_000_000) for i in range(5)]
              + [("INTC", "put", "buy", 30.0, 4_000, 1_000, 30_000_000)])
    d = _panel(tmp)
    assert _cuantas(d) == 2, "en pantalla se ve una operacion por valor"
    assert d["dia_bias_label"] == "ALCISTA", (
        "el sesgo se ha calculado sobre las filas visibles: sale bajista un dia "
        "en el que la prima alcista es casi el doble de la bajista")
    assert d["dia_bias_pct"] == 62.5, d["dia_bias_pct"]


def test_el_umbral_subio_a_2_y_esta_dicho_en_la_respuesta():
    """Una entrada con vol/OI = 1,5 pasaba el corte viejo y ya no pasa. El
    numero viaja en la respuesta para que la pantalla no tenga que
    adivinarlo."""
    tmp = _bd([("AAA", "call", "buy", 10.0, 1_500, 1_000, 500_000),
               ("BBB", "call", "buy", 10.0, 2_100, 1_000, 500_000)])
    d = _panel(tmp)
    assert _cuantas(d) == 1
    assert d["calls_bought"][0]["ticker"] == "BBB"
    assert d["umbral_vol_oi"] == 2.0


def test_la_nota_habla_de_los_DOS_cortes_no_solo_del_primero():
    """Las dos cifras cuentan cosas distintas: una es lo que no merece
    mirarse, la otra es lo que si y esta a un clic. Si la pantalla solo
    mencionara la primera, las repetidas pareceria que se han perdido."""
    import os
    ruta = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "pages", "options.js")
    with open(ruta, encoding="utf-8") as fh:
        fuente = fh.read()
    assert "descartadas_rutina" in fuente
    assert "repetidas_del_mismo" in fuente, (
        "la nota no menciona las operaciones del mismo valor: pareceria que se "
        "han tirado, cuando estan guardadas y se ven entrando al ticker")
