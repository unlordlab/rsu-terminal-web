"""
¿Acierta el flujo de opciones? Seguimiento de las señales contra lo que hizo
después el precio.

EL HALLAZGO (#25). Options Flow lleva desde julio guardando operaciones con su
fecha, su prima y el precio del subyacente, y **nadie ha comprobado nunca si
predicen algo**. El Algoritmo y CANSLIM sí tienen ese seguimiento; este módulo
opinaba sin haberse medido.

QUÉ SE CONSIDERA UNA SEÑAL. Una por **ticker y sesión**, no una por contrato:
lo que el usuario ve en pantalla es «hoy el dinero en XOM apostaba al alza»,
no cada línea por separado. La dirección sale del mismo sesgo por prima que
pinta el gráfico de la vista de ticker, y solo cuenta actividad inusual (el
mismo corte que la pantalla, MIN_VOL_OI_INUSUAL) -- si se midiera algo
distinto de lo que se enseña, el resultado no diría nada sobre lo que el
usuario mira.

CONTRA QUÉ SE MIDE. Contra el S&P 500 en la MISMA ventana, no contra cero.
Medir contra cero en un mercado que sube es la forma más fácil de fabricar un
acierto: en un tramo alcista, «apostó al alza y subió» acierta casi siempre
sin que la señal aporte nada. Se guarda el retorno del ticker, el del SPY y se
juzga por la diferencia.

LO QUE ESTO NO PUEDE HACER TODAVÍA. Con pocas semanas de escaneos guardados,
cualquier porcentaje sale de una muestra minúscula. Por eso `resumen()`
devuelve siempre `n` y marca `suficiente: False` por debajo de MIN_MUESTRA:
un 70% de aciertos sobre 7 casos no es un 70%, es ruido con dos decimales.
"""
import os
import sqlite3
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "shared"))

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'options_flow.db')

HORIZONTES = (5, 10, 20)
# Por debajo de esto no se da un porcentaje como si significara algo. 30 no es
# un número mágico: es el mínimo por debajo del cual un solo caso mueve el
# resultado varios puntos, así que no se puede leer como tendencia.
MIN_MUESTRA = 30
# Una sesión con sesgo de +3% no es una apuesta direccional, es empate. El
# resumen separa las señales claras del resto en vez de meterlo todo junto.
UMBRAL_CLARA = 50.0


def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = _conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS flow_tracked (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_date      TEXT NOT NULL,
            ticker         TEXT NOT NULL,
            nps            REAL NOT NULL,
            n_ops          INTEGER NOT NULL,
            prima_total    REAL,
            precio_entrada REAL NOT NULL,
            ret_5d         REAL, ret_10d  REAL, ret_20d  REAL,
            spy_5d         REAL, spy_10d  REAL, spy_20d  REAL,
            actualizado_en TEXT,
            creado_en      TEXT NOT NULL,
            UNIQUE(scan_date, ticker)
        )
    """)
    conn.commit()
    conn.close()


_SQL_SENALES = """
    SELECT ticker,
           SUM(CASE WHEN (type='call' AND action='buy') OR (type='put' AND action='sell')
                    THEN premium ELSE 0 END) AS bull,
           SUM(CASE WHEN (type='put' AND action='buy') OR (type='call' AND action='sell')
                    THEN premium ELSE 0 END) AS bear,
           COUNT(*) AS n,
           MAX(underlying_price) AS precio
    FROM options_flow
    WHERE scan_date = ?
      AND oi > 0 AND volume IS NOT NULL
      AND (CAST(volume AS REAL) / oi) >= ?
    GROUP BY ticker
"""


def registrar_senales(scan_date: str) -> dict:
    """Una fila por ticker con actividad inusual en esa sesión. `INSERT OR
    IGNORE` sobre UNIQUE(scan_date, ticker): repetirlo no duplica ni reescribe
    -- el precio de entrada de una sesión no cambia después."""
    from services.options_service import MIN_VOL_OI_INUSUAL
    init_db()
    conn = _conn()
    filas = conn.execute(_SQL_SENALES, (scan_date, MIN_VOL_OI_INUSUAL)).fetchall()

    ahora = datetime.now(timezone.utc).isoformat()
    guardadas = 0
    for f in filas:
        total = (f["bull"] or 0) + (f["bear"] or 0)
        # Sin prima no hay dirección, y sin precio de entrada no hay nada que
        # medir después: se deja fuera en vez de inventar un cero.
        if total <= 0 or not f["precio"]:
            continue
        nps = round(((f["bull"] or 0) - (f["bear"] or 0)) / total * 100, 1)
        cur = conn.execute(
            "INSERT OR IGNORE INTO flow_tracked "
            "(scan_date, ticker, nps, n_ops, prima_total, precio_entrada, creado_en) "
            "VALUES (?,?,?,?,?,?,?)",
            (scan_date, f["ticker"], nps, f["n"], total, f["precio"], ahora),
        )
        guardadas += cur.rowcount
    conn.commit()
    conn.close()
    return {"scan_date": scan_date, "guardadas": guardadas, "tickers": len(filas)}


def backfill() -> dict:
    """Registra todas las sesiones ya guardadas. Se puede correr cuantas veces
    haga falta: el UNIQUE hace el resto. A diferencia de otros módulos, aquí SÍ
    hay pasado que reconstruir -- el escaneo lleva desde julio guardando el
    precio del subyacente de cada operación."""
    init_db()
    conn = _conn()
    fechas = [r[0] for r in conn.execute(
        "SELECT DISTINCT scan_date FROM options_flow ORDER BY scan_date")]
    conn.close()
    total = 0
    for f in fechas:
        total += registrar_senales(f)["guardadas"]
    return {"sesiones": len(fechas), "guardadas": total}


def _retorno(serie, fecha, dias):
    """Retorno a `dias` SESIONES vista desde la primera sesión en o después de
    `fecha`. None si todavía no ha pasado ese tiempo -- nunca se aproxima con
    la última sesión disponible, que daría un horizonte más corto disfrazado
    del que pide."""
    import pandas as pd
    if serie is None or len(serie) == 0:
        return None
    idx = serie.index
    posteriores = idx[idx >= pd.Timestamp(fecha)]
    if len(posteriores) == 0:
        return None
    pos = idx.get_loc(posteriores[0])
    if pos + dias >= len(serie):
        return None
    p0, p1 = float(serie.iloc[pos]), float(serie.iloc[pos + dias])
    if p0 <= 0:
        return None
    return round((p1 - p0) / p0 * 100, 2)


def actualizar_resultados() -> dict:
    """Rellena el retorno del ticker y el del SPY en los horizontes que ya se
    han cumplido. Descarga en LOTE (shared/yf_batch), no un yfinance por
    señal: son decenas de tickers por sesión."""
    from yf_batch import download_batch  # noqa: E402

    init_db()
    conn = _conn()
    pend = conn.execute(
        "SELECT id, scan_date, ticker, precio_entrada, ret_5d, ret_10d, ret_20d "
        "FROM flow_tracked WHERE ret_20d IS NULL"
    ).fetchall()
    conn.close()
    if not pend:
        return {"actualizadas": 0, "pendientes": 0}

    tickers = sorted({r["ticker"] for r in pend})
    # 1 año cubre de sobra: el horizonte más largo son 20 sesiones y una fila
    # deja de estar pendiente en cuanto se rellena.
    close_d, _ = download_batch(tickers + ["SPY"], period="1y", batch_size=40,
                                min_history=25, log_prefix="[FlowTracking] ")
    spy = close_d.get("SPY")
    if spy is None or len(spy) == 0:
        return {"actualizadas": 0, "error": "sin datos de SPY: no hay contra qué comparar"}

    conn = _conn()
    actualizadas = 0
    for r in pend:
        serie = close_d.get(r["ticker"])
        cambios = {}
        for dias in HORIZONTES:
            if r[f"ret_{dias}d"] is not None:
                continue
            ret = _retorno(serie, r["scan_date"], dias)
            ref = _retorno(spy,   r["scan_date"], dias)
            # Los dos o ninguno: un retorno sin su referencia no se puede
            # juzgar, y guardarlo a medias invitaría a compararlo contra cero.
            if ret is None or ref is None:
                continue
            cambios[f"ret_{dias}d"] = ret
            cambios[f"spy_{dias}d"] = ref
        if cambios:
            sets = ", ".join(f"{k} = ?" for k in cambios)
            conn.execute(
                f"UPDATE flow_tracked SET {sets}, actualizado_en = ? WHERE id = ?",
                (*cambios.values(), datetime.now(timezone.utc).isoformat(), r["id"]),
            )
            actualizadas += 1
    conn.commit()
    conn.close()
    return {"actualizadas": actualizadas, "pendientes": len(pend)}


def _bloque(rows, dias):
    campo, ref = f"ret_{dias}d", f"spy_{dias}d"
    con_dato = [r for r in rows if r[campo] is not None and r[ref] is not None]
    if not con_dato:
        return {"n": 0, "suficiente": False, "aciertos_pct": None, "exceso_medio": None}
    excesos = [r[campo] - r[ref] for r in con_dato]
    # Acierto = batió al SPY si la señal era alcista, o se quedó por detrás si
    # era bajista.
    aciertos = sum(1 for r, e in zip(con_dato, excesos) if (e > 0) == (r["nps"] > 0))
    return {
        "n": len(con_dato),
        "suficiente": len(con_dato) >= MIN_MUESTRA,
        "aciertos_pct": round(aciertos / len(con_dato) * 100, 1),
        "exceso_medio": round(sum(excesos) / len(excesos), 2),
    }


def resumen() -> dict:
    """Aciertos por dirección y horizonte, SIEMPRE con la muestra al lado."""
    init_db()
    conn = _conn()
    filas = conn.execute("SELECT * FROM flow_tracked").fetchall()
    conn.close()

    claras   = [r for r in filas if abs(r["nps"]) >= UMBRAL_CLARA]
    alcistas = [r for r in filas if r["nps"] > 0]
    bajistas = [r for r in filas if r["nps"] < 0]

    return {
        "ok": True,
        "senales": len(filas),
        "sesiones": len({r["scan_date"] for r in filas}),
        "min_muestra": MIN_MUESTRA,
        "umbral_clara": UMBRAL_CLARA,
        "horizontes": {
            str(d): {
                "todas":    _bloque(filas, d),
                "claras":   _bloque(claras, d),
                "alcistas": _bloque(alcistas, d),
                "bajistas": _bloque(bajistas, d),
            } for d in HORIZONTES
        },
    }


init_db()
