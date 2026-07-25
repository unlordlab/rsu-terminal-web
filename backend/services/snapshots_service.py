"""
snapshots.db -- base point-in-time, append-only, nunca UPDATE/DELETE. Ver
DATOS_IRREPRODUCIBLES_PLAN.md (21/07/2026) y sesión 25/07/2026: la
terminal calcula cada noche datos valiosos (fase Weinstein, RS%, RVOL,
amplitud de mercado, score del Algoritmo...) y los tira -- los Gists de
los scans nocturnos se sobrescriben, las ventanas móviles se podan. Esto
guarda, cada noche, lo que se sabía esa noche, para poder construir en el
futuro backtests point-in-time honestos (sin sesgo de supervivencia, sin
look-ahead de datos revisados).

Escrito desde market_cache_warm_loop() (ws.py, cada 4 min) -- NO desde un
bucle propio de 24h (ver comentario en ws.py sobre por qué: mismo error
ya corregido una vez en Options Flow). La fecha de sesión (no de
ejecución) decide si ya se escribió o no -- da igual cuántas veces se
llame esta función, o cuándo se reinicie el contenedor.
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'snapshots.db')


def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = _conn()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS snapshot_ticker (
            fecha            TEXT NOT NULL,   -- sesión real (YYYY-MM-DD), no de ejecución
            ticker           TEXT NOT NULL,
            sector           TEXT,
            precio           REAL,
            rvol             REAL,
            rs_pct           REAL,
            phase            INTEGER,         -- Weinstein diaria (1-4)
            phase_confirmed  INTEGER,         -- 0/1, debounce de 3 sesiones
            phase_weekly     INTEGER,         -- Weinstein semanal (1-4)
            above_sma50      INTEGER,         -- 0/1
            new_high         INTEGER,         -- 0/1, máx. 252 sesiones (excluye el día evaluado)
            new_low          INTEGER,         -- 0/1
            dias_absorcion   INTEGER,         -- 0-10
            PRIMARY KEY (fecha, ticker)
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS snapshot_mercado (
            fecha             TEXT PRIMARY KEY,
            advances          INTEGER,
            declines          INTEGER,
            pct_above_sma50   REAL,
            new_highs         INTEGER,
            new_lows          INTEGER,
            algoritmo_score   REAL,
            algoritmo_estado  TEXT,
            vix               REAL,
            vix_vix3m         REAL,
            credit_spread     REAL
        )
    ''')
    conn.commit()
    conn.close()


def maybe_write_daily_snapshot():
    """Punto de entrada único, llamado desde market_cache_warm_loop().
    Append-only: cada sub-función comprueba primero si YA hay fila para
    la fecha de sesión más reciente conocida, y si la hay no hace nada."""
    from services.scanner_service import get_breadth_history
    breadth_hist = get_breadth_history()
    if not breadth_hist:
        return  # scan nocturno todavía sin datos (Gist vacío/no configurado) -- no hay nada que guardar
    ultimo = breadth_hist[-1]
    fecha  = ultimo["date"]

    conn = _conn()
    try:
        _maybe_write_mercado(conn, fecha, ultimo)
        _maybe_write_ticker(conn, fecha)
    finally:
        conn.close()


def _maybe_write_mercado(conn, fecha, breadth_row):
    if conn.execute("SELECT 1 FROM snapshot_mercado WHERE fecha = ?", (fecha,)).fetchone():
        return
    try:
        from services.rsu_algoritmo_service import get_rsu_algoritmo
        algo = get_rsu_algoritmo()
        if "score" not in algo:
            return  # sin score fiable todavía -- se reintenta en el próximo tick (4 min), no se escribe a medias
        from services.market_service import get_vix_term_structure
        # Etiquetas reales de get_vix_term_structure()['data'] -- "Spot" (VIX)
        # y "3 meses" (VIX3M), no "VIX"/"VIX3M" (verificado con datos reales,
        # no supuesto).
        vix_map    = {d["label"]: d["value"] for d in get_vix_term_structure().get("data", []) if d.get("ok")}
        vix, vix3m = vix_map.get("Spot"), vix_map.get("3 meses")
        vix_ratio  = round(vix / vix3m, 3) if vix and vix3m else None
    except Exception as e:
        print(f"[Snapshots] snapshot_mercado de {fecha} incompleto, se reintenta: {type(e).__name__}: {e}")
        return

    conn.execute(
        "INSERT OR IGNORE INTO snapshot_mercado "
        "(fecha, advances, declines, pct_above_sma50, new_highs, new_lows, "
        "algoritmo_score, algoritmo_estado, vix, vix_vix3m, credit_spread) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (fecha, breadth_row.get("advances"), breadth_row.get("declines"),
         breadth_row.get("pct_above_sma50"), breadth_row.get("new_highs"), breadth_row.get("new_lows"),
         algo.get("score"), algo.get("estado"), vix, vix_ratio, algo.get("credit_spread_valor"))
    )
    conn.commit()
    print(f"[Snapshots] snapshot_mercado guardado para {fecha}")


def _maybe_write_ticker(conn, fecha):
    if conn.execute("SELECT 1 FROM snapshot_ticker WHERE fecha = ? LIMIT 1", (fecha,)).fetchone():
        return
    from services.scanner_service import get_universe_stocks
    stocks = get_universe_stocks()
    if not stocks:
        return

    def _b(v):
        return None if v is None else int(bool(v))

    rows = [
        (fecha, ticker, s.get("sector"), s.get("precio"), s.get("rvol"), s.get("rs_pct"),
         s.get("phase"), _b(s.get("phase_confirmed")), s.get("phase_weekly"),
         _b(s.get("above_sma50")), _b(s.get("new_high")), _b(s.get("new_low")), s.get("dias_absorcion"))
        for ticker, s in stocks.items()
    ]
    conn.executemany(
        "INSERT OR IGNORE INTO snapshot_ticker "
        "(fecha, ticker, sector, precio, rvol, rs_pct, phase, phase_confirmed, "
        "phase_weekly, above_sma50, new_high, new_low, dias_absorcion) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        rows
    )
    conn.commit()
    print(f"[Snapshots] snapshot_ticker guardado para {fecha} ({len(rows)} tickers)")


init_db()
