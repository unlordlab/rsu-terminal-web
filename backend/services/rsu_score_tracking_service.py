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


HORIZONTES_DIAS = (5, 10, 20, 60)


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
    # EL S&P 500 DEL MISMO PERIODO (14/09/2026, a petición del usuario). Hasta
    # entonces el RSU Score era el único seguimiento sin baseline: CANSLIM, las
    # tesis y Options Flow ya se medían contra el índice. Sin él, «+6% a 20
    # días» no dice nada si el mercado hizo +9%. Se añaden las columnas a una
    # tabla que ya existe en producción, así que ALTER y no CREATE.
    existentes = {r["name"] for r in conn.execute("PRAGMA table_info(score_tracked)")}
    for dias in HORIZONTES_DIAS:
        if f"spy_{dias}d" not in existentes:
            conn.execute(f"ALTER TABLE score_tracked ADD COLUMN spy_{dias}d REAL")
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
    # También las filas que ya tienen resultado pero no su S&P 500: las
    # anteriores al 14/09/2026. El cierre del índice de cualquier fecha pasada
    # se puede recuperar, así que no hace falta empezar la comparación de cero.
    sin_spy = " OR ".join(f"(resultado_{d}d IS NOT NULL AND spy_{d}d IS NULL)" for d in HORIZONTES_DIAS)
    pendientes = conn.execute(
        "SELECT id, ticker, fecha, precio_entrada, resultado_5d, resultado_10d, resultado_20d, resultado_60d, "
        "spy_5d, spy_10d, spy_20d, spy_60d "
        f"FROM score_tracked WHERE resultado_60d IS NULL OR {sin_spy}"
    ).fetchall()
    conn.close()
    if not pendientes:
        return {"actualizadas": 0}

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "shared"))
    from yf_batch import download_batch  # noqa: E402

    tickers = list({r["ticker"] for r in pendientes} | {"SPY"})
    # min_history=1: el default de 130
    # (pensado para RS/RW, que necesita histórico largo) descartaría
    # CUALQUIER ticker aquí, porque "6mo" son ~126 sesiones (<130) -- la
    # suficiencia real de datos ya la comprueba el bucle de abajo fila a
    # fila (pos_entrada + dias >= len(closes)), no hace falta un umbral
    # aquí también.
    # 1 año y no 6 meses: el relleno del S&P 500 de las filas antiguas puede
    # necesitar ir más atrás que el horizonte de 60 sesiones de las pendientes.
    close_d, _ = download_batch(tickers, period="1y", batch_size=40, min_history=1, log_prefix="[RSUScoreTracking] ")
    spy = close_d.get("SPY")
    spy_fechas = [d.date() for d in spy.index] if spy is not None and not spy.empty else []

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
        # El S&P 500 en la MISMA ventana que el valor.
        #
        # LA VENTANA DEL VALOR: de `precio_entrada` —el precio que tenía la
        # ficha al registrarse— al cierre N sesiones después de la primera
        # sesión en o tras la fecha. Y ese precio de entrada es casi siempre el
        # CIERRE ANTERIOR: se registra al abrir Research, y se abre sobre todo
        # antes de la apertura de Nueva York (MSFT el domingo 26/07 a 381,70, el
        # cierre del viernes). La primera versión arrancaba el índice en el
        # cierre SIGUIENTE y se dejaba fuera un día que el valor sí contaba.
        # Por eso el índice parte del último cierre ANTERIOR a la fecha y acaba
        # en la misma sesión que el valor. Un registro hecho en plena sesión
        # queda con una diferencia de horas, no de un día.
        pos_spy = next((i for i, d in enumerate(spy_fechas) if d >= fecha_entrada), None)
        if pos_spy is not None and pos_spy >= 1:
            base_spy = float(spy.iloc[pos_spy - 1])
            for dias in HORIZONTES_DIAS:
                col = f"spy_{dias}d"
                tiene_resultado = row[f"resultado_{dias}d"] is not None or f"resultado_{dias}d" in cambios
                if row[col] is not None or not tiene_resultado or pos_spy + dias >= len(spy) or base_spy <= 0:
                    continue
                cambios[col] = round((float(spy.iloc[pos_spy + dias]) - base_spy) / base_spy * 100, 2)
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
    rows = conn.execute("SELECT score, resultado_5d, resultado_10d, resultado_20d, resultado_60d, "
                        "spy_5d, spy_10d, spy_20d, spy_60d FROM score_tracked").fetchall()
    conn.close()

    def _exceso(rows_bucket, dias):
        pares = [(r[f"resultado_{dias}d"], r[f"spy_{dias}d"]) for r in rows_bucket
                 if r[f"resultado_{dias}d"] is not None and r[f"spy_{dias}d"] is not None]
        return round(sum(a - s for a, s in pares) / len(pares), 2) if pares else None

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
            # Cuántos tienen ya resultado a cada plazo. `n` cuenta también los
            # que aún no han cumplido el plazo, y una media de 20 días sacada
            # de 3 casos no se puede leer igual que una de 300 (Track Record).
            "n_20d": sum(1 for r in en_bucket if r["resultado_20d"] is not None),
            "n_60d": sum(1 for r in en_bucket if r["resultado_60d"] is not None),
            # Retorno del valor MENOS el del S&P 500 en la misma ventana, solo
            # con las filas que tienen los dos. Es la cifra que dice si la nota
            # aporta algo frente a comprar el índice.
            **{f"vs_spy_{d}d": _exceso(en_bucket, d) for d in HORIZONTES_DIAS},
            **{f"n_vs_spy_{d}d": sum(1 for r in en_bucket if r[f"resultado_{d}d"] is not None and r[f"spy_{d}d"] is not None)
               for d in HORIZONTES_DIAS},
        })
    return resumen


def obtener_historial(limit: int = 100) -> list:
    conn = _conn()
    rows = conn.execute("SELECT * FROM score_tracked ORDER BY fecha DESC, id DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def historial_ticker(ticker: str, dias: int = 180, minimo: int = 5) -> dict:
    """Evolucion del RSU Score de UN ticker, para pintarla en su ficha.

    Convierte un numero instantaneo en una tendencia: un 63 no dice lo mismo
    si viene de 45 que si viene de 78.

    `minimo` por la misma razon que en el historico de sentimiento: con dos o
    tres puntos, una linea aparenta una tendencia que no existe. Por debajo se
    devuelve cuantos dias van, para que la ficha pueda decirlo en vez de
    dibujar algo que no sostiene nada.

    OJO CON COMO SE LLENA ESTO: el score se registra cuando alguien consulta
    el ticker y la cache esta vacia -- una vez al dia como mucho, y solo de
    los tickers que de verdad se miran. Un ticker que nadie consulta nunca
    tendra historial, y eso es correcto: no hay ningun proceso recorriendo
    todo el universo, ni tiene por que haberlo.
    """
    conn = _conn()
    try:
        filas = conn.execute(
            "SELECT fecha, score, label, precio_entrada, "
            "resultado_5d, resultado_20d, resultado_60d "
            "FROM score_tracked WHERE ticker = ? ORDER BY fecha DESC LIMIT ?",
            (ticker.upper(), dias)
        ).fetchall()
    except Exception:
        return {"ok": False, "dias": 0}
    finally:
        conn.close()

    filas = [dict(f) for f in reversed(filas)]     # cronologico, para pintar
    if len(filas) < minimo:
        return {"ok": False, "dias": len(filas), "minimo": minimo}

    scores = [f["score"] for f in filas]
    actual, previo = scores[-1], scores[-2]
    return {
        "ok": True,
        "serie": [{"fecha": f["fecha"], "score": f["score"], "label": f["label"]} for f in filas],
        "actual": actual,
        "cambio": actual - previo,               # respecto al ultimo registro, no a ayer
        "min": min(scores), "max": max(scores), "n": len(scores),
        # Retornos ya cumplidos, si el job diario los ha rellenado. Suelen
        # faltar en los registros recientes: 20 sesiones no han pasado aun.
        "con_resultado": sum(1 for f in filas if f["resultado_20d"] is not None),
    }


init_db()
