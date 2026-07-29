"""
Tracking del RSU Score contra retornos reales -- ver TODO_RSU_TERMINAL.md
4.2: "¿un 90 le gana a un 40?", en ~3 meses de datos acumulados.

A diferencia del RSU Algoritmo (algoritmo_tracking_service.py, lectura de
mercado general, una señal ROJO/ÁMBAR/VERDE por día), el RSU Score es POR
TICKER y se calcula bajo demanda cada vez que alguien visita
/research/{ticker} -- no hay scan nocturno. registrar_score() se llama
desde get_research() en cada cache-miss; INSERT OR IGNORE sobre
UNIQUE(ticker, fecha) deduplica aunque varias peticiones concurrentes
recalculen el mismo ticker el mismo día (mismo patrón ya usado para
corregir un bug real de duplicados en cartera_tracking_service.py).

NO simula stop-loss (a diferencia del Algoritmo): el RSU Score es una
nota de calidad/research, no una señal de trading con regla de salida
definida.
"""
import sqlite3
import os
import sys
import json
from datetime import datetime, timezone

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'rsu_score_history.db')


def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = _conn()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS score_tracked (
            id                    INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker                TEXT NOT NULL,
            fecha                 TEXT NOT NULL,   -- YYYY-MM-DD, primera vez visto ese día
            score                 INTEGER NOT NULL,
            label                 TEXT,
            breakdown             TEXT,             -- JSON [{"label","pts","max"}]
            n_categorias          INTEGER,
            precio_entrada        REAL NOT NULL,
            resultado_5d          REAL,
            resultado_10d         REAL,
            resultado_20d         REAL,
            resultado_60d         REAL,
            resultado_actualizado TEXT,
            creado_en             TEXT NOT NULL,
            UNIQUE(ticker, fecha)
        )
    ''')
    conn.commit()
    conn.close()


def registrar_score(ticker: str, rsu_score: dict, price: float):
    """Llamada desde get_research() en cada cache-miss. INSERT OR IGNORE
    sobre UNIQUE(ticker, fecha) -- si ya se registró hoy este ticker
    (aunque venga de otra petición concurrente), no hace nada. No se
    fabrica un registro si falta score/breakdown/precio.

    Tampoco se registra lo que la ficha NO publica: desde el 29/07/2026,
    _compute_rsu_score() devuelve score=None cuando hay menos de 3 de las 5
    categorías con datos (caso típico de los ETF, que no tienen
    fundamentales). Guardarlos aquí contaminaría el propio track record: la
    pregunta que este historial existe para responder -- "¿un 90 le gana a un
    40?" -- no tiene sentido si en la muestra hay SPY y QQQ con un 100 salido
    de un único indicador técnico."""
    if not price or not rsu_score or not rsu_score.get("breakdown"):
        return
    if rsu_score.get("score") is None:
        return
    fecha = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    ahora = datetime.now(timezone.utc).isoformat()
    breakdown = [{"label": c["label"], "pts": c["pts"], "max": c["max"]} for c in rsu_score["breakdown"]]
    conn = _conn()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO score_tracked "
            "(ticker, fecha, score, label, breakdown, n_categorias, precio_entrada, creado_en) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (ticker, fecha, rsu_score["score"], rsu_score.get("label"),
             json.dumps(breakdown), len(breakdown), price, ahora)
        )
        conn.commit()
    finally:
        conn.close()


def actualizar_resultados_pendientes():
    """Job diario -- rellena resultado_5d/10d/20d/60d de las señales cuyo
    horizonte ya se ha cumplido. Descarga en LOTE (shared/yf_batch.py,
    mismo patrón ya usado en 4 sitios del proyecto) en vez de un
    yf.Ticker por señal pendiente."""
    conn = _conn()
    pendientes = conn.execute(
        "SELECT id, ticker, fecha, precio_entrada, resultado_5d, resultado_10d, resultado_20d, resultado_60d "
        "FROM score_tracked WHERE resultado_60d IS NULL"
    ).fetchall()
    conn.close()
    if not pendientes:
        return {"actualizadas": 0}

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "shared"))
    from yf_batch import download_batch  # noqa: E402

    tickers = list({r["ticker"] for r in pendientes})
    # 6 meses cubre de sobra cualquier fila pendiente: el horizonte máximo
    # es 60 sesiones (~3 meses) y una fila deja de estar "pendiente" en
    # cuanto resultado_60d se rellena. min_history=1: el default de 130
    # (pensado para RS/RW, que necesita histórico largo) descartaría
    # CUALQUIER ticker aquí, porque "6mo" son ~126 sesiones (<130) -- la
    # suficiencia real de datos ya la comprueba el bucle de abajo fila a
    # fila (pos_entrada + dias >= len(closes)), no hace falta un umbral
    # aquí también.
    close_d, _ = download_batch(tickers, period="6mo", batch_size=40, min_history=1, log_prefix="[RSUScoreTracking] ")

    conn = _conn()
    actualizadas = 0
    for row in pendientes:
        closes = close_d.get(row["ticker"])
        if closes is None or closes.empty:
            continue
        fecha_entrada = datetime.strptime(row["fecha"], "%Y-%m-%d").date()
        idx_dates = [d.date() for d in closes.index]
        pos_entrada = next((i for i, d in enumerate(idx_dates) if d >= fecha_entrada), None)
        if pos_entrada is None:
            continue
        cambios = {}
        for dias, campo in [(5, "resultado_5d"), (10, "resultado_10d"), (20, "resultado_20d"), (60, "resultado_60d")]:
            if row[campo] is not None or pos_entrada + dias >= len(closes):
                continue
            precio_h = float(closes.iloc[pos_entrada + dias])
            cambios[campo] = round((precio_h - row["precio_entrada"]) / row["precio_entrada"] * 100, 2)
        if cambios:
            set_clause = ", ".join(f"{k} = ?" for k in cambios)
            conn.execute(
                f"UPDATE score_tracked SET {set_clause}, resultado_actualizado = ? WHERE id = ?",
                (*cambios.values(), datetime.now(timezone.utc).isoformat(), row["id"])
            )
            actualizadas += 1
    conn.commit()
    conn.close()
    return {"actualizadas": actualizadas}


# Mismos cortes que ya usa _compute_rsu_score() para el campo "label" --
# no se inventan rangos nuevos sin relación con lo que el usuario ya ve.
BUCKETS = [(80, 101, "COMPRA FUERTE"), (65, 80, "COMPRA"), (50, 65, "NEUTRAL"),
           (35, 50, "PRECAUCIÓN"), (0, 35, "EVITAR")]


def obtener_resumen_por_bucket() -> list:
    conn = _conn()
    rows = conn.execute("SELECT score, resultado_5d, resultado_10d, resultado_20d, resultado_60d FROM score_tracked").fetchall()
    conn.close()

    def _avg(rows_bucket, campo):
        vals = [r[campo] for r in rows_bucket if r[campo] is not None]
        return round(sum(vals) / len(vals), 2) if vals else None

    resumen = []
    for lo, hi, label in BUCKETS:
        en_bucket = [r for r in rows if lo <= r["score"] < hi]
        resumen.append({
            "bucket": label, "rango": f"{lo}-{hi-1}", "n": len(en_bucket),
            "avg_5d": _avg(en_bucket, "resultado_5d"), "avg_10d": _avg(en_bucket, "resultado_10d"),
            "avg_20d": _avg(en_bucket, "resultado_20d"), "avg_60d": _avg(en_bucket, "resultado_60d"),
        })
    return resumen


def obtener_historial(limit: int = 100) -> list:
    conn = _conn()
    rows = conn.execute("SELECT * FROM score_tracked ORDER BY fecha DESC, id DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


init_db()
