"""
Tracking en vivo del algoritmo RSU — registro de resultados y notificaciones.

POR QUÉ EXISTE ESTE ARCHIVO:
Todo el trabajo de backtest hecho hasta ahora reanaliza el MISMO histórico
fijo de 20 años una y otra vez. Cada "mejora" viene de mirar mejor los mismos
datos, no de datos genuinamente nuevos — por eso hemos visto correlaciones
cambiar de signo varias veces solo con reordenar qué señales entraban en la
muestra. La única forma de mejorar el algoritmo con información real, no
retrospectiva, es dejar que cada señal que se dispare A PARTIR DE AHORA quede
registrada y, con el tiempo, se compare contra lo que de verdad pasó — sin
haber visto antes ese resultado al diseñar las reglas.

DOS RESPONSABILIDADES:
1. Detectar cambios de semáforo (ROJO/ÁMBAR/VERDE) y notificar por Telegram,
   igual que ya se hace manualmente con las entradas/salidas de Cartera.
2. Guardar cada señal VERDE/VERDE-VOL con su desglose de factores, y rellenar
   automáticamente su retorno real a 5/10/20/60 días cuando llega el momento
   — construyendo, con el paso de los meses, un panel de "Importancia de
   Variables" basado en señales reales, no en el backtest histórico.
"""
import sqlite3
import os
import json
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'algoritmo_history.db')

# Estados que merece la pena rastrear hasta el final (con retorno real a
# 5/10/20/60d) — ROJO y ÁMBAR se registran en el log de cambios de semáforo
# (para Telegram y auditoría) pero no tienen "entrada" que medir.
ESTADOS_ACCIONABLES = {"VERDE", "VERDE-VOL"}


def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = _conn()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS cambios_semaforo (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha           TEXT NOT NULL,
            estado_anterior TEXT,
            estado_nuevo    TEXT NOT NULL,
            senal           TEXT,
            score           INTEGER,
            precio          REAL,
            notificado      INTEGER DEFAULT 0
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS senales_tracked (
            id                    INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha                 TEXT NOT NULL,
            estado                TEXT NOT NULL,
            senal                 TEXT,
            score                 INTEGER,
            umbral_verde          INTEGER,
            precio_entrada        REAL,
            factores              TEXT,      -- JSON: desglose por factor (para importancia de variables futura)
            gatekeeper_a          INTEGER,
            gatekeeper_b          INTEGER,
            ftd_confirmado        INTEGER,
            credit_spread_valor   REAL,
            credit_spread_nivel   TEXT,
            resultado_5d          REAL,
            resultado_10d         REAL,
            resultado_20d         REAL,
            resultado_60d         REAL,
            resultado_5d_stop     REAL,      -- mismo resultado pero simulando stop -7% (ver rsu_algoritmo_service._retornos_con_stop)
            resultado_10d_stop    REAL,
            resultado_20d_stop    REAL,
            resultado_60d_stop    REAL,
            stopeada_dia          INTEGER,   -- día (nº de sesiones desde la entrada) en que se disparó el stop, o NULL si nunca
            resultado_actualizado TEXT,
            creado_en             TEXT NOT NULL
        )
    ''')
    # Migración segura para bases de datos ya existentes creadas antes de
    # añadir las columnas *_stop — SQLite no soporta "ADD COLUMN IF NOT
    # EXISTS", así que se comprueba primero qué columnas hay de verdad.
    columnas_actuales = {row['name'] for row in conn.execute("PRAGMA table_info(senales_tracked)").fetchall()}
    for columna, tipo in [
        ('resultado_5d_stop', 'REAL'), ('resultado_10d_stop', 'REAL'),
        ('resultado_20d_stop', 'REAL'), ('resultado_60d_stop', 'REAL'),
        ('stopeada_dia', 'INTEGER'),
        # Peor caída intermedia a 60 sesiones. Sustituye a la simulación de
        # stop (31/07/2026): sin stop, lo que hay que saber es cuánto llega a
        # estar la posición en rojo antes de funcionar, porque eso es lo que
        # determina el tamaño que uno puede permitirse. Las *_stop se quedan
        # en el esquema (SQLite no borra columnas con facilidad) pero ya no se
        # escriben.
        ('peor_caida_60d', 'REAL'),
    ]:
        if columna not in columnas_actuales:
            conn.execute(f"ALTER TABLE senales_tracked ADD COLUMN {columna} {tipo}")
    # Singleton: último estado conocido, para detectar cambios sin tener que
    # releer todo el historial cada vez.
    conn.execute('''
        CREATE TABLE IF NOT EXISTS estado_actual (
            id             INTEGER PRIMARY KEY CHECK (id = 1),
            estado         TEXT,
            actualizado_en TEXT
        )
    ''')
    # fecha_sesion: qué sesión de mercado se procesó por última vez. Es lo que
    # hace idempotente la decisión diaria (ver procesar_cierre_si_toca) — sin
    # esto, cada pasada del bucle de 30 min volvería a evaluar la misma sesión.
    cols_estado = {row['name'] for row in conn.execute("PRAGMA table_info(estado_actual)").fetchall()}
    if 'fecha_sesion' not in cols_estado:
        conn.execute("ALTER TABLE estado_actual ADD COLUMN fecha_sesion TEXT")
    conn.commit()
    conn.close()


def obtener_estado_oficial():
    """Último estado oficial del semáforo, o None si todavía no hay ninguno."""
    conn = _conn()
    try:
        row = conn.execute("SELECT estado FROM estado_actual WHERE id = 1").fetchone()
        return row['estado'] if row else None
    finally:
        conn.close()


def sesion_ya_procesada(fecha_sesion: str) -> bool:
    """¿Ya se tomó la decisión oficial de esta sesión de mercado?"""
    conn = _conn()
    try:
        row = conn.execute("SELECT fecha_sesion FROM estado_actual WHERE id = 1").fetchone()
        return bool(row and row['fecha_sesion'] == fecha_sesion)
    finally:
        conn.close()


# Envío de Telegram ahora vive en telegram_service.py (compartido con Cartera,
# ver ese archivo) — se re-importa aquí con el mismo nombre para no tener que
# tocar el resto de este archivo.
from services.telegram_service import enviar_telegram as _enviar_telegram


def _emoji_estado(estado):
    return {
        "VERDE":       "🟢",
        "VERDE-VOL":   "🟡",   # verde con matices — mismo trato visual que ámbar, es una señal de cautela
        "AMBAR":       "🟡",
        "AMBAR-BAJO":  "🟠",
        "ROJO":        "🔴",
    }.get(estado, "⚪")


def _construir_mensaje(estado_anterior, resultado):
    estado = resultado.get('estado')
    emoji  = _emoji_estado(estado)
    precio = resultado.get('precio')
    score  = resultado.get('score')
    senal  = resultado.get('senal', '')

    cabecera = f"{emoji} *RSU Algoritmo — cambio de semáforo*\n{estado_anterior or '(inicio)'} → *{estado}*"
    cuerpo   = f"\nSeñal: {senal}\nScore: {score}/100\nSPY: ${precio:.2f}" if precio else f"\nSeñal: {senal}\nScore: {score}/100"

    if estado == "VERDE":
        pie = "\n\n_Punto de empezar a construir posición de forma gradual — no es el mínimo exacto._"
    elif estado == "VERDE-VOL":
        pie = "\n\n_Setup con matices — revisar advertencias antes de actuar (ver /algoritmo)._"
    elif estado in ("AMBAR", "AMBAR-BAJO"):
        pie = "\n\n_Fase de watchlist — identificar candidatos, aún no de entrada._"
    else:
        pie = ""

    return cabecera + cuerpo + pie


def procesar_resultado_algoritmo(resultado, fecha_sesion=None):
    """
    Punto de entrada principal — se llama cada vez que se recalcula el
    algoritmo en vivo (get_rsu_algoritmo). Detecta si el semáforo cambió desde
    la última vez, y si es así:
      1. Registra el cambio en cambios_semaforo.
      2. Envía notificación por Telegram.
      3. Si el nuevo estado es VERDE/VERDE-VOL, abre un registro de
         seguimiento en senales_tracked para medir su resultado real más
         adelante.
    No hace nada (silenciosamente) si el estado no ha cambiado — se llama en
    cada refresco, la mayoría de las veces no habrá nada que hacer.
    """
    if not resultado:
        return
    estado_nuevo = resultado.get('estado')
    if not estado_nuevo:
        return

    conn = _conn()
    conn.execute("INSERT OR IGNORE INTO estado_actual (id, estado, actualizado_en) VALUES (1, NULL, NULL)")
    row = conn.execute("SELECT estado FROM estado_actual WHERE id = 1").fetchone()
    estado_anterior = row['estado'] if row else None

    if estado_anterior == estado_nuevo:
        # Sin cambio de color, pero la sesión SÍ queda marcada como procesada:
        # si no, procesar_cierre_si_toca() volvería a evaluarla en cada pasada
        # del bucle de 30 min y nunca se daría por cerrada.
        if fecha_sesion:
            conn.execute("UPDATE estado_actual SET fecha_sesion = ? WHERE id = 1", (fecha_sesion,))
            conn.commit()
        conn.close()
        return

    ahora = datetime.utcnow().isoformat()

    # Compare-and-swap atómico: get_rsu_algoritmo() tiene caché de 10 min,
    # pero se refresca tanto desde ws.py::algoritmo_check_loop() (cada 30
    # min) como desde cualquier usuario cargando el Dashboard/Algoritmo --
    # si dos llamadas caen justo cuando la caché expira, ambas pueden leer
    # el mismo estado_anterior arriba antes de que ninguna escriba. Solo la
    # llamada cuyo UPDATE realmente mueve la fila (rowcount=1) "gana" la
    # transición y sigue hasta enviar Telegram; la otra ve rowcount=0 (la
    # primera ya dejó estado_actual en estado_nuevo) y no envía nada. Se
    # comitea de inmediato para que la reserva sea visible al momento.
    # INSERT OR IGNORE primero garantiza que la fila id=1 exista siempre
    # (incluida la primerísima vez, cuando la tabla está vacía). Antes, el
    # envío ocurría ANTES de este chequeo atómico. Ver reporte del usuario
    # 24/07/2026 (mismo patrón corregido también en
    # cartera_tracking_service.py::procesar_cartera_notificaciones).
    cur = conn.execute(
        "UPDATE estado_actual SET estado = ?, actualizado_en = ?, fecha_sesion = ? "
        "WHERE id = 1 AND (estado IS NULL OR estado != ?)",
        (estado_nuevo, ahora, fecha_sesion, estado_nuevo)
    )
    conn.commit()
    if cur.rowcount == 0:
        conn.close()
        return  # otra llamada concurrente ya ganó esta misma transición

    # 1. Registrar el cambio
    conn.execute(
        "INSERT INTO cambios_semaforo (fecha, estado_anterior, estado_nuevo, senal, score, precio) VALUES (?,?,?,?,?,?)",
        (ahora, estado_anterior, estado_nuevo, resultado.get('senal'), resultado.get('score'), resultado.get('precio'))
    )
    conn.commit()

    # 2. Notificar (fuera de la transacción de BD — si Telegram falla no debe perder el registro ya guardado)
    mensaje = _construir_mensaje(estado_anterior, resultado)
    enviado = _enviar_telegram(mensaje)
    conn.execute(
        "UPDATE cambios_semaforo SET notificado = ? WHERE id = (SELECT MAX(id) FROM cambios_semaforo)",
        (1 if enviado else 0,)
    )
    conn.commit()

    # 3. Si el nuevo estado es accionable, abrir seguimiento de resultado real
    if estado_nuevo in ESTADOS_ACCIONABLES:
        factores = {k: v.get('score') for k, v in (resultado.get('metricas') or {}).items() if v.get('max', 0) > 0}
        conn.execute('''
            INSERT INTO senales_tracked
                (fecha, estado, senal, score, umbral_verde, precio_entrada, factores,
                 gatekeeper_a, gatekeeper_b, ftd_confirmado, credit_spread_valor, credit_spread_nivel, creado_en)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        ''', (
            ahora, estado_nuevo, resultado.get('senal'), resultado.get('score'), resultado.get('umbral_verde'),
            resultado.get('precio'), json.dumps(factores),
            int(bool(resultado.get('gatekeeper_a'))), int(bool(resultado.get('gatekeeper_b'))),
            int(bool(resultado.get('ftd_confirmado'))),
            resultado.get('credit_spread_valor'), resultado.get('credit_spread_nivel'),
            ahora
        ))
        conn.commit()

    conn.close()


def actualizar_resultados_pendientes():
    """
    Job periódico (llamado ~1 vez al día es más que suficiente) — busca
    señales trackeadas cuya fecha ya tiene 5/10/20/60 días de trading
    cumplidos pero todavía no tienen ese resultado calculado, y lo rellena
    con precios reales de SPY.

    Desde el 31/07/2026 ya NO se simula el stop del -7%: la herramienta dejó
    de recomendarlo al medir que habría cortado 5 de las 16 señales históricas
    —incluidas las dos de marzo de 2020, que acabaron en +14,5% y +17,1%— y
    que con él la ventaja sobre días de pánico comparables se iba a cero.

    En su lugar se guarda la PEOR CAÍDA INTERMEDIA: cuánto llegó a estar la
    posición en rojo antes de funcionar. Sin stop, ese es el dato que hay que
    poder aguantar, y por tanto el que determina el tamaño de la posición.
    Las columnas *_stop se dejan en el esquema (SQLite no borra columnas con
    facilidad) pero ya no se escriben.
    """
    import yfinance as yf

    conn = _conn()
    pendientes = conn.execute('''
        SELECT id, fecha, precio_entrada, resultado_5d, resultado_10d, resultado_20d, resultado_60d
        FROM senales_tracked
        WHERE resultado_60d IS NULL
    ''').fetchall()
    conn.close()
    if not pendientes:
        return {"actualizadas": 0}

    # Descarga UNA vez el histórico reciente de SPY, cubre de sobra las
    # señales pendientes (como mucho unos meses de antigüedad).
    hist = yf.Ticker("SPY").history(period="1y")
    if hist.empty:
        print("[AlgoritmoTracking] No se pudo descargar SPY para actualizar resultados pendientes")
        return {"actualizadas": 0, "error": "sin datos SPY"}
    hist.index = hist.index.tz_localize(None) if hist.index.tz is not None else hist.index
    closes = hist['Close']
    lows   = hist['Low'].fillna(closes)

    conn = _conn()
    actualizadas = 0
    for row in pendientes:
        fecha_entrada = datetime.fromisoformat(row['fecha'])
        precio_entrada = row['precio_entrada']
        if not precio_entrada:
            continue

        # Posición (índice de sesión de trading) del primer día en o después
        # de la señal — necesaria para recorrer el camino día a día, no solo
        # el día del horizonte, porque el stop puede dispararse cualquier día
        # intermedio.
        posiciones_validas = closes.index[closes.index >= fecha_entrada]
        if posiciones_validas.empty:
            continue
        pos_entrada = closes.index.get_loc(posiciones_validas[0])

        # Peor caída intermedia hasta 60 sesiones: se recorre el camino con
        # los MÍNIMOS diarios, no los cierres, porque lo que hace vender por
        # pánico es el número en rojo durante la sesión.
        minimo_visto = precio_entrada
        for k in range(1, 61):
            if pos_entrada + k >= len(closes):
                break
            low_k = lows.iloc[pos_entrada + k]
            if low_k < minimo_visto:
                minimo_visto = float(low_k)
        peor_caida = round((minimo_visto - precio_entrada) / precio_entrada * 100, 2)

        cambios = {}
        for dias, campo, _ in [
            (5, 'resultado_5d', 'resultado_5d_stop'), (10, 'resultado_10d', 'resultado_10d_stop'),
            (20, 'resultado_20d', 'resultado_20d_stop'), (60, 'resultado_60d', 'resultado_60d_stop'),
        ]:
            if row[campo] is not None:
                continue
            if pos_entrada + dias >= len(closes):
                continue  # todavía no ha pasado suficiente tiempo de trading para este horizonte
            precio_h = float(closes.iloc[pos_entrada + dias])
            cambios[campo] = round((precio_h - precio_entrada) / precio_entrada * 100, 2)
        if cambios:
            cambios['peor_caida_60d'] = peor_caida

        if cambios:
            set_clause = ", ".join(f"{k} = ?" for k in cambios)
            conn.execute(
                f"UPDATE senales_tracked SET {set_clause}, resultado_actualizado = ? WHERE id = ?",
                (*cambios.values(), datetime.utcnow().isoformat(), row['id'])
            )
            actualizadas += 1
    conn.commit()
    conn.close()
    print(f"[AlgoritmoTracking] {actualizadas} señal(es) con resultado actualizado")
    return {"actualizadas": actualizadas}


def obtener_historial_cambios(limit=30):
    conn = _conn()
    rows = conn.execute(
        "SELECT * FROM cambios_semaforo ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def obtener_senales_tracked(limit=100):
    conn = _conn()
    rows = conn.execute(
        "SELECT * FROM senales_tracked ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    out = []
    for r in rows:
        d = dict(r)
        try:
            d['factores'] = json.loads(d['factores']) if d['factores'] else {}
        except Exception:
            d['factores'] = {}
        out.append(d)
    return out


init_db()