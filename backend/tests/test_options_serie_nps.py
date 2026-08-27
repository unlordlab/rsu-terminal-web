"""
El sesgo por sesion de un valor: una barra por dia, y los dias que faltan no
son ceros.

EL HALLAZGO (#20). El modulo no tenia ni un grafico: cero `new Chart` y cero
`<canvas>` en toda la pagina. La vista de ticker enseñaba un `NET SCORE`
suelto -- un numero acumulado del periodo entero-- y una tabla de filas, sin
forma de ver si el dinero de un valor lleva varios dias apostando en la misma
direccion o si es una sola sesion suelta.

LO QUE HAY QUE PROTEGER, que es donde un grafico miente facil:

1. LA CONSULTA ES PROPIA. La de la tabla lleva `LIMIT 200`, asi que en un
   periodo largo recorta las sesiones mas antiguas. En una tabla es aceptable;
   en una serie temporal seria una mentira silenciosa -- el grafico empezaria
   mas tarde de lo que dice el periodo elegido y nadie lo notaria.

2. LOS DIAS SIN ACTIVIDAD NO SALEN COMO CERO. Un cero significa «hubo tanto
   alcista como bajista». Un dia sin operaciones inusuales no es eso: es que
   no hubo nada que contar.

3. EL MISMO CORTE QUE LA TABLA. Si el grafico contara operaciones que la tabla
   de debajo no enseña, dos numeros de la misma pantalla dirian cosas
   distintas sin avisar.

4. UN DIA CON UNA SOLA OPERACION DA ±100. Es aritmetica, no conviccion, y el
   dato tiene que viajar para que la pantalla pueda decirlo.

Uso:
    cd backend
    python -m pytest tests/test_options_serie_nps.py -v
"""
import os
import sqlite3
import sys
import tempfile
from datetime import datetime, timedelta
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import services.options_service as O  # noqa: E402


def _bd(filas):
    """filas = (fecha, tipo, accion, volume, oi, premium)"""
    tmp = os.path.join(tempfile.mkdtemp(), "flow.db")
    with patch.object(O, "DB_PATH", tmp):
        O.init_db()
    conn = sqlite3.connect(tmp)
    for i, (fecha, tipo, acc, vol, oi, prem) in enumerate(filas):
        conn.execute(
            "INSERT INTO options_flow (scan_date, scan_ts, ticker, strike, exp, type, "
            "action, premium, premium_fmt, volume, oi, vol_oi_ratio, score, signal, "
            "price, strike_pct, iv, underlying_price) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (fecha, fecha + " 23:00:00", "XOM", 100.0 + i, "2026-12-18", tipo, acc,
             prem, f"${prem/1e6:.1f}M", vol, oi, (vol / oi if oi else 0), 5, "ALTA",
             1.0, "+0%", 0.3, 100.0))
    conn.commit(); conn.close()
    return tmp


def _serie(tmp, period="4m"):
    with patch.object(O, "DB_PATH", tmp), \
         patch("services.cartera_service.get_cartera_tickers", return_value=set()), \
         patch.object(O, "_obtener_contratos_repetidos", return_value=set()):
        return O.get_ticker_flow_simple("XOM", period)


# Las fechas se calculan desde HOY DE VERDAD, no se clavan. Estaban fijas en
# "2026-08-19", y el 27/08 el test del periodo "1w" empezo a fallar solo: la
# ventana de una semana ya no alcanzaba a esa fecha, la consulta salia vacia y
# `get_ticker_flow_simple` devolvia su respuesta de error -- sin `serie_nps`--
# asi que el fallo aparecia como un KeyError feo en vez de como lo que era.
# Un test que da por hecho que hoy es un dia concreto caduca sin avisar.
_HOY = datetime.now()
HOY  = _HOY.strftime("%Y-%m-%d")
AYER = (_HOY - timedelta(days=1)).strftime("%Y-%m-%d")
HACE_UNA_SEMANA = (_HOY - timedelta(days=7)).strftime("%Y-%m-%d")
HACE_16_DIAS    = (_HOY - timedelta(days=16)).strftime("%Y-%m-%d")
HACE_3_MESES    = (_HOY - timedelta(days=90)).strftime("%Y-%m-%d")


def test_una_entrada_por_sesion_con_su_sesgo_por_prima():
    """EL test. Dos dias, dos barras, cada una con su porcentaje."""
    d = _serie(_bd([
        (AYER, "call", "buy",  5_000, 1_000, 9_000_000),   # alcista
        (AYER, "put",  "buy",  5_000, 1_000, 1_000_000),   # bajista
        (HOY,  "call", "sell", 5_000, 1_000, 6_000_000),   # bajista
        (HOY,  "put",  "sell", 5_000, 1_000, 4_000_000),   # alcista
    ]))
    serie = d["serie_nps"]
    assert [p["fecha"] for p in serie] == [AYER, HOY], "las sesiones van en orden cronologico"
    assert serie[0]["nps"] == 80.0, serie[0]      # (9-1)/10
    assert serie[1]["nps"] == -20.0, serie[1]     # (4-6)/10


def test_un_dia_sin_actividad_inusual_NO_sale_como_cero():
    """Un cero dice «hubo tanto alcista como bajista». Un dia sin operaciones
    inusuales no dice eso: dice que no hubo nada que contar."""
    d = _serie(_bd([
        (AYER, "call", "buy", 500, 50_000, 9_000_000),   # rutinaria: vol/OI = 0,01
        (HOY,  "call", "buy", 5_000, 1_000, 9_000_000),
    ]))
    fechas = [p["fecha"] for p in d["serie_nps"]]
    assert fechas == [HOY], f"la sesion sin nada inusual no puede aparecer: {d['serie_nps']}"


def test_la_serie_usa_el_mismo_corte_que_la_tabla_de_debajo():
    """Si el grafico contara operaciones que la tabla no enseña, dos numeros de
    la misma pantalla dirian cosas distintas sin avisar."""
    d = _serie(_bd([
        (HOY, "call", "buy", 5_000, 1_000,   9_000_000),   # inusual
        (HOY, "put",  "buy",   900, 1_000, 100_000_000),   # rutinaria, y enorme
    ]))
    assert d["total"] == 1, "la tabla solo enseña la inusual"
    assert len(d["serie_nps"]) == 1
    assert d["serie_nps"][0]["nps"] == 100.0, (
        "la prima rutinaria de 100M se ha colado en el grafico: la tabla dice "
        "alcista y el grafico diria bajista")


def test_se_dice_en_cuantas_operaciones_se_apoya_cada_sesion():
    """Un dia con una sola operacion marca ±100 y en un grafico parece una
    conviccion tremenda. El dato tiene que viajar para poder avisarlo."""
    d = _serie(_bd([
        (AYER, "call", "buy", 5_000, 1_000, 9_000_000),
        (HOY,  "call", "buy", 5_000, 1_000, 3_000_000),
        (HOY,  "call", "buy", 5_000, 1_000, 3_000_000),
        (HOY,  "put",  "buy", 5_000, 1_000, 1_000_000),
    ]))
    por_fecha = {p["fecha"]: p for p in d["serie_nps"]}
    assert por_fecha[AYER]["n"] == 1 and por_fecha[AYER]["nps"] == 100.0
    assert por_fecha[HOY]["n"] == 3


def test_el_periodo_recorta_por_fecha():
    """Pedir una semana no puede devolver sesiones de hace tres meses."""
    d = _serie(_bd([
        (HACE_3_MESES, "call", "buy", 5_000, 1_000, 9_000_000),
        (HOY,          "call", "buy", 5_000, 1_000, 9_000_000),
    ]), period="1w")
    assert all(p["fecha"] >= HACE_UNA_SEMANA for p in d["serie_nps"]), d["serie_nps"]
    assert [p["fecha"] for p in d["serie_nps"]] == [HOY]


def test_la_serie_NO_usa_la_consulta_con_LIMIT_de_la_tabla():
    """El sabotaje que los demas no cazan. La consulta de la tabla trae como
    mucho 200 filas ordenadas por fecha y prima: si la serie saliera de ahi, un
    valor muy activo perderia sus sesiones mas ANTIGUAS y el grafico empezaria
    mas tarde de lo que dice el periodo, sin avisar de nada.

    250 operaciones repartidas en dos dias: 249 el dia mas reciente y una el
    mas antiguo. Con el LIMIT de la tabla, esa primera sesion desaparece."""
    filas = [(HOY, "call", "buy", 5_000, 1_000, 9_000_000) for _ in range(249)]
    filas.append((HACE_16_DIAS, "put", "buy", 5_000, 1_000, 9_000_000))
    d = _serie(_bd(filas))
    fechas = [p["fecha"] for p in d["serie_nps"]]
    assert HACE_16_DIAS in fechas, (
        f"la sesion mas antigua se ha perdido: la serie sale de la consulta "
        f"recortada de la tabla, no de la suya. Fechas: {fechas}")


def test_el_grafico_se_pinta_y_se_destruye():
    """Mismo tipo de comprobacion que la nota de descartadas: que la funcion
    exista no sirve de nada si nadie la llama. Y un Chart.js que no se destruye
    se queda con el canvas y sus escuchas de resize -- la fuga que ya se cerro
    en Market con sus siete graficos."""
    ruta = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "pages", "options.js")
    with open(ruta, encoding="utf-8") as fh:
        fuente = fh.read()
    # Buscar el texto NO basta: una linea comentada lo contiene igual, y el
    # sabotaje de comentar la llamada pasaba en verde. Es exactamente el mismo
    # error con el que se me colo la nota de descartadas.
    llamada = [l for l in fuente.splitlines()
               if l.strip().startswith("pintarGraficoNps(") and "serie_nps" in l]
    assert llamada, (
        "nadie llama al pintor (o la llamada esta comentada): el canvas se "
        "queda vacio")
    assert "export function cleanup" in fuente, (
        "la pagina crea un Chart.js y no exporta cleanup(): el router no puede "
        "destruirlo al salir")
    assert "_npsChart.destroy()" in fuente
