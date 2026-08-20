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
    """Dos medias, no una, y la diferencia entre ellas es el hallazgo.

    `exceso_dirigido` es lo que se ganaría SIGUIENDO la señal: el exceso sobre
    el índice con el signo de la apuesta (si la señal era bajista, que el valor
    caiga respecto al índice suma a favor). Es el único que se puede leer como
    ventaja.

    `exceso_universo` es cómo se comportaron esos valores frente al índice sin
    mirar la dirección. Es el BASELINE que hay que batir: si simplemente estar
    en valores con actividad inusual de opciones ya bate al S&P 500, la
    dirección de la señal no ha aportado nada aunque el número salga bonito.

    Hasta el 21/08 solo se daba el segundo, llamado `exceso_medio`, y eso era
    engañoso: mezclaba las dos direcciones, así que una señal bajista fallida
    (el valor sube) sumaba POSITIVO. Con aciertos por debajo del 50% y un
    "exceso" creciente a la vez, el número parecía una ventaja y era el sesgo
    del universo."""
    campo, ref = f"ret_{dias}d", f"spy_{dias}d"
    con_dato = [r for r in rows if r[campo] is not None and r[ref] is not None]
    if not con_dato:
        return {"n": 0, "suficiente": False, "aciertos_pct": None,
                "exceso_dirigido": None, "exceso_universo": None}
    excesos   = [r[campo] - r[ref] for r in con_dato]
    dirigidos = [e if r["nps"] > 0 else -e for r, e in zip(con_dato, excesos)]
    # Acierto = batió al SPY si la señal era alcista, o se quedó por detrás si
    # era bajista.
    aciertos = sum(1 for d in dirigidos if d > 0)
    return {
        "n": len(con_dato),
        "suficiente": len(con_dato) >= MIN_MUESTRA,
        "aciertos_pct": round(aciertos / len(con_dato) * 100, 1),
        "exceso_dirigido": round(sum(dirigidos) / len(dirigidos), 2),
        "exceso_universo": round(sum(excesos) / len(excesos), 2),
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


# ── ¿Llegó el precio al strike? ──────────────────────────────────────────────
#
# LA PREGUNTA, planteada por el usuario el 21/08 y mejor que la mía: medir el
# retorno a 5, 10 o 20 sesiones es medir algo que quien compró nunca prometió.
# Una call a 340 con vencimiento el 18/09 es una apuesta CONCRETA -- que el
# precio llegue a 340 antes de esa fecha-- y esa apuesta tiene su propio
# examen. Aquí se corrige el examen.
#
# UNIDAD: el CONTRATO, no el ticker-sesión. Es lo que se apostó.
#
# CRITERIO: call, tocó si el MÁXIMO llegó al strike; put, si el MÍNIMO bajó a
# él. Comprar o vender no cambia si tocó, cambia si eso es buena noticia -- por
# eso el resumen desglosa por tipo de operación en vez de dar un número solo.
#
# LO QUE ESTO NO MIDE, y hay que decirlo donde se enseñe: tocar el strike NO es
# ganar dinero. No tenemos el precio de la opción a lo largo de su vida, así
# que una call puede tocar su strike y perder igualmente por la prima pagada.
# Es un criterio de DIRECCIÓN, no de rentabilidad.

def init_db_strike():
    conn = _conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS strike_tocado (
            scan_date   TEXT NOT NULL,
            ticker      TEXT NOT NULL,
            strike      REAL NOT NULL,
            exp         TEXT NOT NULL,
            type        TEXT NOT NULL,
            action      TEXT NOT NULL,
            spot_inicio REAL,
            tocado      INTEGER,          -- 1 tocó · 0 venció sin tocar · NULL sigue vivo
            fecha_toque TEXT,
            evaluado_en TEXT,
            PRIMARY KEY (scan_date, ticker, strike, exp, type, action)
        )
    """)
    conn.commit()
    conn.close()


def actualizar_toque_strike(hoy: str = None) -> dict:
    """Recorre los contratos inusuales guardados y comprueba si el subyacente
    llegó a su strike entre el día del escaneo y el vencimiento.

    Solo mira los que siguen sin resolver (`tocado IS NULL`): un contrato que
    ya tocó no puede des-tocar, y uno que venció sin tocar tampoco cambia."""
    import pandas as pd
    from yf_batch import download_batch  # noqa: E402
    from services.options_service import MIN_VOL_OI_INUSUAL

    init_db()
    init_db_strike()
    hoy = hoy or datetime.now(timezone.utc).strftime("%Y-%m-%d")

    conn = _conn()
    # Los contratos inusuales que aún no tienen veredicto. Se comparan contra
    # la tabla de veredictos por su identidad completa (el mismo contrato
    # detectado en dos sesiones distintas son dos apuestas distintas).
    filas = conn.execute(
        """
        SELECT f.scan_date, f.ticker, f.strike, f.exp, f.type, f.action,
               f.underlying_price AS spot
        FROM options_flow f
        LEFT JOIN strike_tocado t
               ON t.scan_date = f.scan_date AND t.ticker = f.ticker
              AND t.strike = f.strike AND t.exp = f.exp
              AND t.type = f.type AND t.action = f.action
        WHERE f.oi > 0 AND f.volume IS NOT NULL
          AND (CAST(f.volume AS REAL) / f.oi) >= ?
          AND f.strike > 0
          AND (t.tocado IS NULL)
        """,
        (MIN_VOL_OI_INUSUAL,),
    ).fetchall()
    conn.close()
    if not filas:
        return {"evaluados": 0, "pendientes": 0}

    tickers = sorted({r["ticker"] for r in filas})
    # Con máximos y mínimos: tocar el strike es un suceso INTRADÍA, y mirarlo
    # con cierres se perdería la mitad de los toques.
    close_d, _, hl_d = download_batch(tickers, period="1y", batch_size=40,
                                      min_history=25, include_hl=True,
                                      log_prefix="[StrikeToque] ")

    conn = _conn()
    ahora = datetime.now(timezone.utc).isoformat()
    tocados = vencidos = vivos = 0
    for r in filas:
        hl = hl_d.get(r["ticker"])
        if hl is None or len(hl) == 0:
            continue
        desde = pd.Timestamp(r["scan_date"])
        hasta = pd.Timestamp(min(r["exp"], hoy))
        # El día del escaneo NO cuenta: el escaneo corre con el mercado ya
        # cerrado, así que el recorrido de ese día ya había ocurrido cuando la
        # operación se detectó. Contarlo sería mirar hacia atrás.
        tramo = hl[(hl.index > desde) & (hl.index <= hasta)]
        if len(tramo) == 0:
            vivos += 1
            continue
        if r["type"] == "call":
            alcanzo = tramo["High"] >= r["strike"]
        else:
            alcanzo = tramo["Low"] <= r["strike"]
        idx = alcanzo[alcanzo].index
        if len(idx):
            veredicto, cuando = 1, idx[0].strftime("%Y-%m-%d")
            tocados += 1
        elif r["exp"] <= hoy:
            veredicto, cuando = 0, None      # venció sin llegar
            vencidos += 1
        else:
            vivos += 1
            continue                         # sigue vivo: sin veredicto todavía
        conn.execute(
            "INSERT OR REPLACE INTO strike_tocado (scan_date, ticker, strike, exp, type, "
            "action, spot_inicio, tocado, fecha_toque, evaluado_en) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (r["scan_date"], r["ticker"], r["strike"], r["exp"], r["type"], r["action"],
             r["spot"], veredicto, cuando, ahora),
        )
    conn.commit()
    conn.close()
    return {"evaluados": tocados + vencidos, "tocados": tocados,
            "vencidos_sin_tocar": vencidos, "siguen_vivos": vivos}


_ETIQUETA = {("call", "buy"): "Compra de call", ("put", "sell"): "Venta de put",
             ("put", "buy"): "Compra de put", ("call", "sell"): "Venta de call"}


def _ya_en_el_dinero(r) -> bool:
    """¿El precio ya había alcanzado el strike el día que se detectó?

    ESTO ES LO QUE HACE QUE EL PORCENTAJE SIGNIFIQUE ALGO. Una call cuyo strike
    está POR DEBAJO del precio ya está dentro del dinero: «llega al strike» el
    primer día sin que ocurra nada, y contarla como acierto es contar un
    suceso que ya había pasado antes de la apuesta.

    Medido el 21/08 sobre los contratos guardados: 60 de 124 estaban así, y
    tocaban el 100%. Con ellos dentro, el resultado global salía 81,5%; sin
    ellos, 64,1%. La diferencia entre las dos cifras es enteramente esto.
    """
    if not r["spot_inicio"]:
        return False
    if r["type"] == "call":
        return r["spot_inicio"] >= r["strike"]
    return r["spot_inicio"] <= r["strike"]


def resumen_strike() -> dict:
    """Porcentaje de contratos inusuales que llegaron a su strike.

    La cifra principal es la de los que estaban FUERA del dinero al
    detectarse, que son los únicos que tenían algo que alcanzar. Los que ya
    estaban dentro se cuentan aparte y se etiquetan, en vez de sumarlos al
    total o de esconderlos.

    Desglosado por tipo de operación porque tocar significa lo contrario según
    el lado: en una call comprada es el escenario que se buscaba; en una put
    VENDIDA, tocar es justo lo que el vendedor no quería."""
    init_db_strike()
    conn = _conn()
    filas = conn.execute("SELECT * FROM strike_tocado").fetchall()
    conn.close()

    def _bloque(rows):
        resueltos = [r for r in rows if r["tocado"] is not None]
        vivos = len(rows) - len(resueltos)
        if not resueltos:
            return {"n": 0, "vivos": vivos, "tocaron": 0, "tocaron_pct": None,
                    "suficiente": False}
        t = sum(1 for r in resueltos if r["tocado"])
        return {"n": len(resueltos), "vivos": vivos, "tocaron": t,
                "tocaron_pct": round(t / len(resueltos) * 100, 1),
                "suficiente": len(resueltos) >= MIN_MUESTRA}

    fuera = [r for r in filas if not _ya_en_el_dinero(r)]
    dentro = [r for r in filas if _ya_en_el_dinero(r)]

    return {
        "ok": True,
        "total": _bloque(fuera),
        "por_tipo": {etiqueta: _bloque([r for r in fuera
                                        if r["type"] == tipo and r["action"] == accion])
                     for (tipo, accion), etiqueta in _ETIQUETA.items()},
        # Aparte y con nombre, no sumados: no prueban nada.
        "ya_en_el_dinero": _bloque(dentro),
        "nota": ("Solo cuentan los contratos que estaban FUERA del dinero al detectarse: "
                 "los que ya estaban dentro alcanzan su strike el primer día sin que ocurra "
                 "nada. Y llegar al strike es un criterio de DIRECCIÓN, no de rentabilidad: "
                 "una call puede alcanzarlo y perder igualmente por la prima pagada. Los "
                 "contratos que siguen vivos no cuentan como fallo."),
    }
