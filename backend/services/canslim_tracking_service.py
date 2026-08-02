"""
canslim_history.db -- qué propuso CANSLIM cada noche y qué pasó después.

POR QUÉ EXISTE (hallazgo #22 de la auditoría)

Hasta el 01/08/2026 el módulo no dejaba rastro: el scan nocturno escribe en
un Gist que el scan siguiente SOBRESCRIBE, así que no se podía responder
«¿qué proponía CANSLIM hace tres meses y cómo salió?». Sin eso, cualquier
decisión sobre el módulo -los pesos del score, los umbrales del selector-
se toma por criterio y no se puede comprobar nunca.

Mismo patrón, ya probado dos veces en producción, que
algoritmo_tracking_service.py y rsu_score_tracking_service.py: se registra
cada candidato con su precio de entrada y un job diario rellena el retorno
real a 5/10/20/60 días cuando ya ha pasado ese tiempo.

SE GUARDA EL UNIVERSO ENTERO, NO SOLO LOS CANDIDATOS BUENOS

Los ~500 tickers del scan, con su score, no solo los que superan un umbral.
Es deliberado y es la decisión de diseño que hace útil todo lo demás: la
pregunta que hay que poder contestar es «¿los de score 85 lo hacen mejor
que los de 60?», y sin los de score bajo no hay grupo de control. Guardar
solo los buenos permitiría medir si suben, que es una pregunta mucho más
floja -en un mercado alcista sube casi todo-.

El coste es asumible: ~500 filas por sesión, unos 12 MB al año, y el fichero
cae dentro del glob /app/backend/*.db que ya respalda scripts/backup_dbs.sh.

SIN BACKFILL

No se puede reconstruir el pasado: los Gists anteriores ya se sobrescribieron
y el score de hace tres meses no se puede recalcular sin los datos de aquel
día. Empieza a contar desde que se despliegue, mismo criterio que
snapshots.db y que el tracking del RSU Score.
"""
import os
import sqlite3
import sys
from datetime import datetime, timezone

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'canslim_history.db')

# Horizontes en SESIONES de mercado, no en días naturales -- mismos que usan
# los otros dos trackings, para que las tres tablas del track record se
# puedan leer juntas.
HORIZONTES = [(5, "resultado_5d"), (10, "resultado_10d"),
              (20, "resultado_20d"), (60, "resultado_60d")]


def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = _conn()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS candidatos_tracked (
            id                    INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha                 TEXT NOT NULL,   -- fecha del scan (YYYY-MM-DD)
            ticker                TEXT NOT NULL,
            score                 INTEGER NOT NULL,
            rs                    INTEGER,
            trend_score           INTEGER,         -- 0-7 del Trend Template
            acc_dis               TEXT,
            vol_ratio             REAL,
            near_new_high         INTEGER,         -- 0/1
            is_3wt                INTEGER,         -- 0/1
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
    # El agregado del track record filtra por fecha y por tramo de score;
    # con ~125.000 filas al año, sin índice eso es un escaneo completo.
    conn.execute('CREATE INDEX IF NOT EXISTS idx_cand_fecha ON candidatos_tracked(fecha)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_cand_score ON candidatos_tracked(score)')
    conn.commit()
    conn.close()


def registrar_scan(candidatos: list, fecha: str) -> dict:
    """Guarda el universo de un scan. Idempotente por UNIQUE(ticker, fecha):
    llamarla dos veces el mismo día no duplica nada, así que puede colgarse
    de una función cacheada sin miedo.

    `fecha` es la del SCAN (cuándo se generó el Gist), no la de ejecución --
    si el backend se reinicia tres veces en un día, las tres ven la misma
    fecha y solo la primera inserta.
    """
    if not candidatos or not fecha:
        return {"insertados": 0}

    ahora = datetime.now(timezone.utc).isoformat()
    filas = []
    for c in candidatos:
        precio = c.get("price")
        ticker = c.get("ticker")
        # Sin precio de entrada no hay retorno que calcular después: la fila
        # sería ruido permanente en la tabla. Se descarta en vez de guardarla
        # con un 0 que luego produciría retornos infinitos.
        if not ticker or not precio or precio <= 0:
            continue
        filas.append((
            fecha, ticker, c.get("score", 0), c.get("rs"), c.get("trend_score"),
            c.get("acc_dis"), c.get("vol_ratio"),
            1 if c.get("near_new_high") else 0,
            1 if c.get("is_3wt") else 0,
            precio, ahora,
        ))
    if not filas:
        return {"insertados": 0}

    conn = _conn()
    try:
        cur = conn.executemany(
            "INSERT OR IGNORE INTO candidatos_tracked "
            "(fecha, ticker, score, rs, trend_score, acc_dis, vol_ratio, "
            "near_new_high, is_3wt, precio_entrada, creado_en) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            filas
        )
        conn.commit()
        return {"insertados": cur.rowcount}
    finally:
        conn.close()


def ya_registrado(fecha: str) -> bool:
    """¿Hay ya filas de este scan? Evita reconstruir la lista entera en cada
    lectura del Gist -- una sola consulta indexada."""
    if not fecha:
        return True
    conn = _conn()
    try:
        return conn.execute(
            "SELECT 1 FROM candidatos_tracked WHERE fecha = ? LIMIT 1", (fecha,)
        ).fetchone() is not None
    finally:
        conn.close()


def actualizar_resultados_pendientes() -> dict:
    """Job diario: rellena los retornos de las filas cuyo horizonte ya se ha
    cumplido. Descarga en LOTE -- las filas pendientes son decenas de miles,
    pero los tickers distintos son ~500, así que es UNA descarga."""
    conn = _conn()
    pendientes = conn.execute(
        "SELECT id, ticker, fecha, precio_entrada, "
        "resultado_5d, resultado_10d, resultado_20d, resultado_60d "
        "FROM candidatos_tracked WHERE resultado_60d IS NULL"
    ).fetchall()
    conn.close()
    if not pendientes:
        return {"actualizadas": 0, "pendientes": 0}

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "shared"))
    from yf_batch import download_batch  # noqa: E402

    tickers = sorted({r["ticker"] for r in pendientes})
    # 6 meses cubre cualquier fila pendiente: el horizonte máximo son 60
    # sesiones y una fila deja de estar pendiente en cuanto se rellena.
    # min_history=1 por el mismo motivo que en rsu_score_tracking: el default
    # de 130 descartaría todo, porque "6mo" son ~126 sesiones. La suficiencia
    # real la comprueba el bucle fila a fila.
    close_d, _ = download_batch(tickers, period="6mo", batch_size=40,
                                min_history=1, log_prefix="[CANSLIMTracking] ")

    conn = _conn()
    actualizadas = 0
    try:
        for row in pendientes:
            closes = close_d.get(row["ticker"])
            if closes is None or closes.empty:
                continue
            try:
                fecha_entrada = datetime.strptime(row["fecha"], "%Y-%m-%d").date()
            except (ValueError, TypeError):
                continue
            idx = [d.date() for d in closes.index]
            pos = next((i for i, d in enumerate(idx) if d >= fecha_entrada), None)
            if pos is None:
                continue
            cambios = {}
            for dias, campo in HORIZONTES:
                if row[campo] is not None or pos + dias >= len(closes):
                    continue
                precio_h = float(closes.iloc[pos + dias])
                cambios[campo] = round(
                    (precio_h - row["precio_entrada"]) / row["precio_entrada"] * 100, 2)
            if cambios:
                sets = ", ".join(f"{k} = ?" for k in cambios)
                conn.execute(
                    f"UPDATE candidatos_tracked SET {sets}, resultado_actualizado = ? WHERE id = ?",
                    (*cambios.values(), datetime.now(timezone.utc).isoformat(), row["id"])
                )
                actualizadas += 1
        conn.commit()
    finally:
        conn.close()
    return {"actualizadas": actualizadas, "pendientes": len(pendientes)}


def obtener_filas(limit: int = 200000) -> list:
    """Todo lo registrado, para que el track record agregue por donde quiera.
    El límite alto es una red de seguridad contra un crecimiento inesperado,
    no un filtro previsto: con ~500 filas por sesión son unos 400 días."""
    conn = _conn()
    try:
        filas = conn.execute(
            "SELECT * FROM candidatos_tracked ORDER BY fecha DESC, score DESC LIMIT ?",
            (limit,)
        ).fetchall()
        return [dict(f) for f in filas]
    finally:
        conn.close()


def fechas_registradas() -> list:
    conn = _conn()
    try:
        return [r["fecha"] for r in conn.execute(
            "SELECT DISTINCT fecha FROM candidatos_tracked ORDER BY fecha").fetchall()]
    finally:
        conn.close()


init_db()
