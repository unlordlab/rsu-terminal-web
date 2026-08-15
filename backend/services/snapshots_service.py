"""
snapshots.db -- base point-in-time, append-only, nunca UPDATE/DELETE. Ver
DATOS_IRREPRODUCIBLES_PLAN.md (21/07/2026) y sesión 25/07/2026: la
terminal calcula cada noche datos valiosos (fase Weinstein, RS%, RVOL,
amplitud de mercado, score del Algoritmo, equity de Cartera...) y los
tira -- los Gists de los scans nocturnos se sobrescriben, las ventanas
móviles se podan. Esto guarda, cada noche, lo que se sabía esa noche,
para poder construir en el futuro backtests point-in-time honestos (sin
sesgo de supervivencia, sin look-ahead de datos revisados).

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
    # Columnas añadidas después de que la tabla ya existiera en producción, así
    # que van como ALTER TABLE idempotente -- mismo patrón que users_service.
    #
    # Por qué hacen falta: el Fear & Greed y el ratio put/call solo dan el valor
    # de HOY. Un 0,76 de put/call o un 38 de Fear & Greed no dicen nada sin
    # saber si eso es alto o bajo para el mercado actual, y ninguna de las dos
    # fuentes ofrece histórico gratis (CNN da 4 puntos sueltos y CBOE solo el
    # día). Guardándolos aquí, junto al resto de la foto diaria, el contexto se
    # construye solo. Ver hallazgos #30 y #31 de la auditoría de Market.
    for columna in ("fear_greed REAL", "put_call REAL"):
        try:
            conn.execute(f"ALTER TABLE snapshot_mercado ADD COLUMN {columna}")
        except sqlite3.OperationalError:
            pass   # ya existía
    conn.execute('''
        CREATE TABLE IF NOT EXISTS snapshot_cartera (
            fecha               TEXT PRIMARY KEY,
            equity              REAL,
            invertido           REAL,
            liquidez            REAL,
            pnl_no_realizado    REAL,
            pnl_realizado_acum  REAL,
            n_posiciones        INTEGER
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS snapshot_tematico (
            fecha         TEXT NOT NULL,   -- sesión real, no de ejecución
            cesta         TEXT NOT NULL,
            avg_score     REAL,            -- percentil RS medio de la cesta
            avg_momentum  REAL,            -- % de la cesta acelerando
            basket        INTEGER,         -- valores con dato ese día
            PRIMARY KEY (fecha, cesta)
        )
    ''')
    conn.execute("CREATE INDEX IF NOT EXISTS idx_tematico_cesta ON snapshot_tematico(cesta, fecha)")
    # rs_score se añade el 02/08/2026 (RS/RW #16). Va por ALTER y no dentro
    # del CREATE de arriba porque las bases que ya existen en producción no
    # se recrean: el CREATE TABLE IF NOT EXISTS las deja intactas y la
    # columna nueva nunca aparecería. Mismo patrón idempotente que
    # users_service con las columnas de Telegram.
    try:
        conn.execute("ALTER TABLE snapshot_ticker ADD COLUMN rs_score REAL")
    except sqlite3.OperationalError:
        pass
    # breadth pasa a ser la métrica que ordena el módulo (15/08/2026), así que
    # es la que hay que seguir en el tiempo. Por ALTER, mismo motivo.
    try:
        conn.execute("ALTER TABLE snapshot_tematico ADD COLUMN breadth REAL")
    except sqlite3.OperationalError:
        pass
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
        _maybe_write_cartera(conn, fecha)
        _maybe_write_tematico(conn, fecha)
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

    # Fear & Greed y put/call van en su propio try: son las dos piezas mas
    # fragiles de la fila (una depende de CNN y la otra de raspar la pagina de
    # CBOE). Si fallan, la fila se guarda igual con el resto -- perder la foto
    # entera del dia por no tener uno de estos dos seria un mal negocio, y
    # ademas el hueco queda como NULL, que es la verdad.
    #
    # Cuando se captura: la fecha sale del scan nocturno, asi que una fecha
    # nueva no aparece hasta que ese scan publica, ya cerrado el mercado. O
    # sea, se guarda el valor de CIERRE y no uno de media sesion -- que es lo
    # que hace comparables unos dias con otros. Si algun dia la fecha pasara a
    # venir de otro sitio, habria que revisar esto.
    fg = pc = None
    try:
        from services.market_service import get_fear_greed
        d = get_fear_greed()
        if d.get("ok"):
            fg = d.get("score")
    except Exception as e:
        print(f"[Snapshots] sin Fear & Greed para {fecha}: {type(e).__name__}")
    try:
        from services.putcall_service import get_put_call_ratio
        d = get_put_call_ratio()
        if d.get("ok"):
            pc = d.get("total")
    except Exception as e:
        print(f"[Snapshots] sin put/call para {fecha}: {type(e).__name__}")

    conn.execute(
        "INSERT OR IGNORE INTO snapshot_mercado "
        "(fecha, advances, declines, pct_above_sma50, new_highs, new_lows, "
        "algoritmo_score, algoritmo_estado, vix, vix_vix3m, credit_spread, "
        "fear_greed, put_call) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (fecha, breadth_row.get("advances"), breadth_row.get("declines"),
         breadth_row.get("pct_above_sma50"), breadth_row.get("new_highs"), breadth_row.get("new_lows"),
         algo.get("score"), algo.get("estado"), vix, vix_ratio, algo.get("credit_spread_valor"),
         fg, pc)
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
         s.get("rs_score"),
         s.get("phase"), _b(s.get("phase_confirmed")), s.get("phase_weekly"),
         _b(s.get("above_sma50")), _b(s.get("new_high")), _b(s.get("new_low")), s.get("dias_absorcion"))
        for ticker, s in stocks.items()
    ]
    conn.executemany(
        "INSERT OR IGNORE INTO snapshot_ticker "
        "(fecha, ticker, sector, precio, rvol, rs_pct, rs_score, phase, phase_confirmed, "
        "phase_weekly, above_sma50, new_high, new_low, dias_absorcion) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        rows
    )
    conn.commit()
    print(f"[Snapshots] snapshot_ticker guardado para {fecha} ({len(rows)} tickers)")


def _maybe_write_cartera(conn, fecha):
    if conn.execute("SELECT 1 FROM snapshot_cartera WHERE fecha = ?", (fecha,)).fetchone():
        return
    try:
        from services.cartera_service import get_cartera
        c = get_cartera()
        metrics = c.get("metrics", {})
        if "pnl_realizado_acum" not in metrics or "capital_disponible" not in metrics:
            return  # simulación de tiers no disponible todavía (sin columna
                     # Nivel, o sin posiciones abiertas) -- se reintenta, no se fabrica
        equity = round(metrics.get("total_val", 0.0) + metrics["capital_disponible"], 2)
        n_pos  = len(c.get("abiertas", []))
    except Exception as e:
        print(f"[Snapshots] snapshot_cartera de {fecha} incompleto, se reintenta: {type(e).__name__}: {e}")
        return

    conn.execute(
        "INSERT OR IGNORE INTO snapshot_cartera "
        "(fecha, equity, invertido, liquidez, pnl_no_realizado, pnl_realizado_acum, n_posiciones) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (fecha, equity, metrics.get("total_inv"), metrics["capital_disponible"],
         metrics.get("pnl_neto"), metrics["pnl_realizado_acum"], n_pos)
    )
    conn.commit()
    print(f"[Snapshots] snapshot_cartera guardado para {fecha}")


# ── LECTURA ───────────────────────────────────────────────────────────────────
# Hasta el 01/08/2026 este módulo era solo de ESCRITURA: guardaba cada noche
# sin que nadie leyera nunca. Estas dos funciones abren la puerta de lectura
# para RS/RW #20 (histórico del percentil RS). El escritor no se toca.

# Cuánto histórico se conserva por cesta. Medido el 15/08/2026 antes de
# elegirlo: son 29 filas al día -- una por cesta, no 500 como snapshot_ticker --
# así que 30 días ocupan 91 KB, un año 768 KB y veinte años 15 MB. El espacio no
# es la restricción aquí; lo que decide es para qué sirve el dato. Con 400 días
# se puede comparar una cesta contra el mismo mes del año anterior, que es la
# pregunta interesante, por unos 840 KB.
TEMATICO_RETENCION_DIAS = 400


def _maybe_write_tematico(conn, fecha):
    """Score y aceleración de cada cesta temática, un registro por sesión.

    El Gist del scan temático SE SOBRESCRIBE cada noche, así que sin esto el
    módulo solo puede decir cómo está una cesta hoy, nunca si viene subiendo.
    Es el mismo problema que resolvieron las otras tres tablas de este fichero,
    aplicado al único scan que faltaba.

    No se puede reconstruir hacia atrás: empieza a contar desde el despliegue.
    """
    if conn.execute("SELECT 1 FROM snapshot_tematico WHERE fecha = ? LIMIT 1", (fecha,)).fetchone():
        return
    try:
        from services.thematic_service import get_thematic_composition
        datos = get_thematic_composition()
        if not datos.get("ok") or not datos.get("sectors"):
            return   # sin scan válido todavía -- se reintenta, no se escribe a medias
        filas = [
            (fecha, s["sector"], s.get("avg_score"), s.get("avg_momentum"),
             s.get("basket"), s.get("breadth"))
            for s in datos["sectors"] if s.get("avg_score") is not None
        ]
    except Exception as e:
        print(f"[Snapshots] snapshot_tematico de {fecha} incompleto, se reintenta: {type(e).__name__}: {e}")
        return
    if not filas:
        return
    conn.executemany(
        "INSERT OR IGNORE INTO snapshot_tematico (fecha, cesta, avg_score, avg_momentum, basket, breadth) "
        "VALUES (?, ?, ?, ?, ?, ?)", filas)
    borradas = _purgar_tematico(conn, fecha)
    conn.commit()
    print(f"[Snapshots] snapshot_tematico guardado para {fecha} ({len(filas)} cestas"
          + (f", {borradas} filas viejas purgadas)" if borradas else ")"))


def _purgar_tematico(conn, fecha_actual: str) -> int:
    """Retira lo que cae fuera de la ventana. Se cuenta desde la fecha de
    SESIÓN, no desde el reloj del proceso: así la purga no depende de cuándo se
    reinició el contenedor, mismo criterio que el resto del fichero."""
    from datetime import datetime, timedelta
    try:
        corte = (datetime.strptime(fecha_actual, "%Y-%m-%d")
                 - timedelta(days=TEMATICO_RETENCION_DIAS)).strftime("%Y-%m-%d")
    except ValueError:
        return 0
    cur = conn.execute("DELETE FROM snapshot_tematico WHERE fecha < ?", (corte,))
    return cur.rowcount or 0


def variacion_por_cesta(ventanas=(5, 20)) -> dict:
    """{cesta: {"d5": +18.2, "d20": -3.1}} -- cuánto ha cambiado la AMPLITUD de
    cada cesta respecto a hace N sesiones.

    Sobre la amplitud y no sobre la media, porque es la métrica que ordena el
    módulo: la pregunta es qué cestas están GANANDO liderazgo, no cuáles suben
    de nota. Las filas anteriores al 15/08/2026 no tienen amplitud guardada y
    esas ventanas salen a None, igual que si faltara histórico.

    Es lo que distingue "esta cesta está arriba" de "esta cesta está SUBIENDO".
    Una que ya lleva meses arriba no es una oportunidad; una que gana 18 puntos
    en cinco sesiones es una rotación en curso.

    Solo se compara contra sesiones que existen de verdad: si aún no hay
    histórico suficiente, esa ventana sale a None en vez de compararse contra
    la fila más antigua que haya, que daría una variación inventada."""
    conn = _conn()
    try:
        fechas = [r["fecha"] for r in conn.execute(
            "SELECT DISTINCT fecha FROM snapshot_tematico ORDER BY fecha DESC").fetchall()]
        if not fechas:
            return {}
        hoy = {r["cesta"]: r["breadth"] for r in conn.execute(
            "SELECT cesta, breadth FROM snapshot_tematico WHERE fecha = ?", (fechas[0],)).fetchall()}
        salida = {c: {} for c in hoy}
        for n in ventanas:
            clave = f"d{n}"
            if len(fechas) <= n:
                for c in salida:
                    salida[c][clave] = None
                continue
            antes = {r["cesta"]: r["breadth"] for r in conn.execute(
                "SELECT cesta, breadth FROM snapshot_tematico WHERE fecha = ?", (fechas[n],)).fetchall()}
            for c, v in hoy.items():
                previo = antes.get(c)
                salida[c][clave] = round(v - previo, 1) if (previo is not None and v is not None) else None
        return salida
    finally:
        conn.close()


# Qué cuenta como "estar en cabeza". Por UMBRAL y no por puesto: con un top 5
# siempre habría cinco cestas en cabeza, incluso en un mercado sin ningún
# liderazgo -- y eso también es información. Mismo criterio que hace que una
# cesta sin líderes marque 0 en vez de "la menos mala".
# Calibrado sobre el scan real del 15/08/2026: con 40 quedan dentro 5 de las 29
# cestas (CYBER 74,5 · STORAGE 73,8 · PHOTONICS 45,2 · SOFTWARE 43,3 ·
# MEMORY 42,2), que es un grupo de cabeza reconocible y no media tabla.
UMBRAL_LIDERAZGO = 40.0
VENTANA_PERSISTENCIA = 30   # sesiones que mira la columna "de 30"
MINIMO_RACHA = 5            # por debajo, una racha no significa nada
MINIMO_SERIE = 3            # puntos mínimos para que una minigráfica se lea


def persistencia_por_cesta(umbral: float = UMBRAL_LIDERAZGO) -> dict:
    """{cesta: {racha, en_ventana, ventana_real, serie}} -- cuánto LLEVA cada
    cesta en cabeza, no si está hoy.

    Es la diferencia entre una tendencia y un pico. Dos cestas pueden subir lo
    mismo esta semana y ser cosas distintas: una que lleva once sesiones
    seguidas arriba es una rotación asentada; una que llegó ayer, ruido.

    - `racha`: sesiones consecutivas, contando desde la más reciente, con la
      amplitud por encima del umbral. None con menos de MINIMO_RACHA sesiones
      de histórico -- una racha de 2 sobre 2 sesiones no dice nada.
    - `en_ventana` / `ventana_real`: en cuántas de las últimas 30 estuvo por
      encima, y sobre cuántas se ha podido mirar de verdad. Las dos juntas,
      porque mientras el histórico se llena "8" a secas se leería como 8 de 30
      cuando puede ser 8 de 10.
    - `serie`: amplitudes de la ventana, de la más antigua a la más reciente,
      para la minigráfica. None con menos de MINIMO_SERIE puntos.
    """
    conn = _conn()
    try:
        fechas = [r["fecha"] for r in conn.execute(
            "SELECT DISTINCT fecha FROM snapshot_tematico ORDER BY fecha DESC "
            "LIMIT ?", (VENTANA_PERSISTENCIA,)).fetchall()]
        if not fechas:
            return {}
        filas = conn.execute(
            "SELECT fecha, cesta, breadth FROM snapshot_tematico WHERE fecha >= ? "
            "ORDER BY fecha DESC", (fechas[-1],)).fetchall()
    finally:
        conn.close()

    # {cesta: [amplitud de la más reciente a la más antigua]}
    por_cesta = {}
    for r in filas:
        por_cesta.setdefault(r["cesta"], {})[r["fecha"]] = r["breadth"]

    salida = {}
    for cesta, por_fecha in por_cesta.items():
        # Se recorre la lista de fechas, no las claves del dict: una cesta que
        # falte un día no debe "saltarse" esa sesión y encadenar una racha que
        # en realidad se rompió.
        serie_desc = [por_fecha.get(f) for f in fechas]

        racha = None
        if len(fechas) >= MINIMO_RACHA:
            racha = 0
            for v in serie_desc:
                if v is not None and v >= umbral:
                    racha += 1
                else:
                    break

        medidas = [v for v in serie_desc if v is not None]
        serie_asc = [v for v in reversed(serie_desc) if v is not None]
        salida[cesta] = {
            "racha":        racha,
            "en_ventana":   sum(1 for v in medidas if v >= umbral),
            "ventana_real": len(medidas),
            "serie":        serie_asc if len(serie_asc) >= MINIMO_SERIE else None,
        }
    return salida


def fechas_snapshot_ticker(limite: int = 60) -> list:
    """Fechas de sesión con datos, de la más reciente a la más antigua."""
    conn = _conn()
    try:
        return [r["fecha"] for r in conn.execute(
            "SELECT DISTINCT fecha FROM snapshot_ticker ORDER BY fecha DESC LIMIT ?",
            (limite,)
        ).fetchall()]
    finally:
        conn.close()


def rs_pct_en_fecha(fecha: str) -> dict:
    """{ticker: rs_pct} de una sesión concreta. Se excluyen los nulos: un
    ticker sin percentil ese día no puede compararse, y arrastrarlo como 0
    lo convertiría en una caída inventada de 80 puntos."""
    conn = _conn()
    try:
        return {
            r["ticker"]: r["rs_pct"]
            for r in conn.execute(
                "SELECT ticker, rs_pct FROM snapshot_ticker "
                "WHERE fecha = ? AND rs_pct IS NOT NULL", (fecha,)
            ).fetchall()
        }
    finally:
        conn.close()


def filas_rs_sector(fechas: list) -> dict:
    """{fecha: [{ticker, sector, rs_pct, rs_score}]} para varias sesiones.

    Una sola consulta en vez de una por fecha: la amplitud del liderazgo
    (RS/RW #16) recorre una ventana entera, y hacer un viaje a la base por
    sesión multiplicaría por 20 lo que cabe en un `IN`.

    Se excluyen las filas sin sector o sin percentil: los dos análisis que
    leen esto agrupan POR sector, así que una fila sin sector no puede
    entrar en ningún grupo, y meterla en uno de "desconocido" inventaría un
    duodécimo sector que no existe.
    """
    if not fechas:
        return {}
    conn = _conn()
    try:
        marcas = ",".join("?" * len(fechas))
        out = {f: [] for f in fechas}
        for r in conn.execute(
            f"SELECT fecha, ticker, sector, rs_pct, rs_score FROM snapshot_ticker "
            f"WHERE fecha IN ({marcas}) AND rs_pct IS NOT NULL "
            f"AND sector IS NOT NULL AND sector != ''",
            list(fechas),
        ).fetchall():
            out[r["fecha"]].append({
                "ticker":   r["ticker"],
                "sector":   r["sector"],
                "rs_pct":   r["rs_pct"],
                "rs_score": r["rs_score"],
            })
        return out
    finally:
        conn.close()


def historico_sentimiento(dias: int = 180, minimo: int = 15) -> dict:
    """Serie diaria de Fear & Greed y ratio put/call, para ponerlas en contexto.

    `minimo` no es un capricho: con cuatro puntos, una linea de tendencia
    engana mas que informa -- se ve una "tendencia" que es ruido. Por debajo de
    ese numero se devuelve `ok: False` con cuantos dias van, para que la
    pantalla pueda decir la verdad ("aun no hay suficiente historico") en vez
    de pintar un grafico que no sostiene nada.

    El historico empieza el dia que esto se despliega: ni CNN ni CBOE regalan
    el pasado, asi que no hay nada que rellenar hacia atras y no se intenta.
    """
    conn = _conn()
    try:
        filas = conn.execute(
            "SELECT fecha, fear_greed, put_call FROM snapshot_mercado "
            "WHERE fear_greed IS NOT NULL OR put_call IS NOT NULL "
            "ORDER BY fecha DESC LIMIT ?", (dias,)
        ).fetchall()
    except sqlite3.OperationalError:
        return {"ok": False, "dias": 0, "error": "El historico aun no esta creado"}
    finally:
        conn.close()

    filas = list(reversed(filas))          # cronologico, para pintar
    fg = [{"fecha": f["fecha"], "valor": f["fear_greed"]} for f in filas if f["fear_greed"] is not None]
    pc = [{"fecha": f["fecha"], "valor": f["put_call"]} for f in filas if f["put_call"] is not None]

    if len(fg) < minimo and len(pc) < minimo:
        return {"ok": False, "dias": max(len(fg), len(pc)), "minimo": minimo}

    def _resumen(serie):
        if len(serie) < minimo:
            return None
        vals = [p["valor"] for p in serie]
        actual = vals[-1]
        # Percentil del valor de hoy dentro de lo guardado: es la lectura que
        # de verdad da contexto ("esto es alto para lo normal ultimamente"),
        # mas que la media.
        pct = sum(1 for v in vals if v < actual) / len(vals) * 100
        return {"serie": serie, "actual": actual, "percentil": round(pct),
                "min": min(vals), "max": max(vals), "n": len(vals)}

    return {"ok": True, "fear_greed": _resumen(fg), "put_call": _resumen(pc),
            "dias": len(filas)}


init_db()
