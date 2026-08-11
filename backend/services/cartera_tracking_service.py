"""
Notificaciones de Telegram para Cartera — nuevas entradas y cierres de posición.

Cartera se lee en directo de un Google Sheet (get_cartera(), sin base de datos
propia) — no hay un "evento" nativo de apertura/cierre al que engancharse,
así que este módulo compara periódicamente el estado actual contra lo que ya
se ha notificado antes, usando una clave estable (ticker + fecha de entrada +
tipo de evento) para no repetir avisos.

BOOTSTRAP: la primera vez que corre esto (base de datos vacía), NO envía nada
— solo memoriza qué posiciones ya existen. Si no, la primera ejecución
mandaría un aluvión de mensajes con todo el histórico de la hoja. A partir de
ahí, solo se notifica lo que sea genuinamente nuevo.
"""
import sqlite3
import os
from datetime import datetime

from services.telegram_service import enviar_telegram
# Los pesos objetivo por nivel (CORE 5% / HIGH 3% / LOTTERY 1%) viven en un
# solo sitio: se importan en vez de repetirlos aquí, para que cambiarlos en
# cartera_service.py no deje el aviso de Telegram diciendo otra cosa.
from services.cartera_service import TIER_WEIGHTS

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'cartera_notificaciones.db')


def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = _conn()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS notificadas (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            clave       TEXT UNIQUE NOT NULL,   -- ticker|fecha_entrada|tipo
            tipo        TEXT NOT NULL,          -- 'apertura' | 'cierre'
            ticker      TEXT,
            enviado_en  TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()


def _linea_nivel(row) -> str:
    """Nivel de convicción de la operación, para que el aviso diga no solo QUÉ
    se ha comprado sino cuánto pesa — un LOTTERY y un CORE son decisiones muy
    distintas y hasta ahora llegaban al Telegram exactamente iguales.

    El peso objetivo (5/3/1%) va entre paréntesis, pero el importe en $ NO se
    incluye a propósito: el `inv` de la fila es el tamaño que la simulación de
    niveles ASIGNA sobre `capital_total`, no lo ejecutado en el bróker, y en
    un aviso suelto ese número se lee como si fuera real. El % objetivo dice
    lo mismo sin prometer más de lo que es.

    Si la hoja no trae un nivel que `norm_tier()` reconozca se etiqueta «sin
    clasificar», no se supone uno — mismo criterio que el resto de Cartera.
    """
    tier = row.get("tier")
    if not tier:
        return "🎯 Nivel: sin clasificar\n"
    peso = TIER_WEIGHTS.get(tier)
    return f"🎯 Nivel: {tier}" + (f" ({peso:g}% objetivo)\n" if peso else "\n")


def _mensaje_apertura(row):
    return (
        "🟢 *NUEVA ENTRADA*\n\n"
        f"📈 Ticker: {row['ticker']}\n"
        f"{_linea_nivel(row)}"
        f"💰 P. Compra: ${row['compra']}\n"
        f"📅 Fecha: {row['fecha']}\n\n"
        "_CARTERA RSU // POSICIÓN ABIERTA_"
    )


def _mensaje_cierre(row):
    positivo = row['pnl'] > 0
    check    = "✅" if positivo else "❌"
    signo    = "+" if row['pnl'] >= 0 else ""
    return (
        "🔴 *POSICIÓN CERRADA*\n\n"
        f"📈 Ticker: {row['ticker']}\n"
        f"{_linea_nivel(row)}"
        f"💰 P. Entrada: ${row['compra']}\n"
        f"💵 P&L: {signo}{row['pnl']}% {check}\n"
        f"📅 Entrada: {row['fecha']}\n\n"
        "_CARTERA RSU // POSICIÓN CERRADA_"
    )


def _reclamar(conn, clave, tipo, ticker):
    """Intenta reservar la clave de dedup ANTES de enviar nada -- el propio
    INSERT OR IGNORE (protegido por el UNIQUE de la columna `clave`) es el
    chequeo: si esta llamada es la primera en insertarla, rowcount=1 y "gana"
    el derecho a enviar el Telegram; si ya existía (otra llamada la reservó
    antes), rowcount=0 y no se envía nada. Se comitea de inmediato para que
    la reserva sea visible al momento a cualquier otra conexión concurrente.

    Antes, el envío ocurría ANTES de este INSERT (con un SELECT previo de
    solo lectura) -- dos llamadas solapadas (p.ej. el bucle de 15 min
    coincidiendo con una llamada manual a /notificaciones/check) podían ver
    ambas "no existe todavía" y las dos mandaban el aviso. Ver reporte del
    usuario 24/07/2026 (avisos duplicados en Cartera y en el semáforo del
    Algoritmo -- mismo patrón corregido también en
    algoritmo_tracking_service.py::procesar_resultado_algoritmo)."""
    cur = conn.execute(
        "INSERT OR IGNORE INTO notificadas (clave, tipo, ticker, enviado_en) VALUES (?,?,?,?)",
        (clave, tipo, ticker, datetime.utcnow().isoformat())
    )
    conn.commit()
    return cur.rowcount == 1


def _clave(row, tipo: str) -> str:
    """Identidad de una operación a efectos de «¿ya avisé de esto?».

    Incluye el PRECIO DE COMPRA. Antes era solo `ticker|fecha|tipo`, así que
    dos lotes del mismo ticker abiertos el mismo día compartían clave y del
    segundo no se avisaba nunca (auditoría de Cartera, #B17).

    Y NO se usa el `id` de fila, que también es único: ese id sale del orden
    de las filas del CSV (`ticker-<índice>`), así que insertar una fila en
    medio de la hoja desplazaría el índice de todas las de abajo, cambiaría
    sus claves y provocaría un aluvión de avisos repetidos. El precio de
    compra, en cambio, no se mueve cuando reordenas la hoja.
    """
    return f"{row['ticker']}|{row['fecha']}|{row.get('compra')}|{tipo}"


def _clave_legado(row, tipo: str) -> str:
    """La clave anterior al fix de #B17, sin precio de compra."""
    return f"{row['ticker']}|{row['fecha']}|{tipo}"


def _avisado_con_formato_viejo(conn, row, tipo: str) -> bool:
    """Puente para el cambio de formato de clave (#B17). Se consulta DESPUÉS
    de reclamar la clave nueva, no antes: si esta operación ya se avisó en su
    día con el formato antiguo, la clave nueva queda registrada igual pero no
    se reenvía nada. Sin esto, el primer arranque tras el despliegue habría
    mandado un Telegram por cada posición viva.

    Efecto secundario asumido y correcto: para las posiciones que YA existían,
    dos lotes del mismo ticker y día comparten clave antigua, así que el
    segundo tampoco se avisará ahora — reenviar hoy la apertura de un lote de
    hace meses sería ruido. A partir de este despliegue, cada lote nuevo tiene
    su propia clave y sí se avisa por separado, que es lo que pedía #B17."""
    return conn.execute(
        "SELECT 1 FROM notificadas WHERE clave = ?", (_clave_legado(row, tipo),)
    ).fetchone() is not None


def procesar_cartera_notificaciones():
    """
    Job periódico — compara el estado actual de Cartera contra lo ya
    notificado, y envía por Telegram cualquier apertura o cierre nuevo.
    """
    from services.cartera_service import get_cartera

    data = get_cartera()
    if not data.get('ok'):
        print(f"[CarteraTracking] Error obteniendo cartera: {data.get('error')}")
        return {"error": data.get('error')}

    conn = _conn()
    es_primera_vez = conn.execute("SELECT COUNT(*) as c FROM notificadas").fetchone()['c'] == 0

    enviadas   = 0
    migradas   = 0
    # La fecha de la clave es siempre la de ENTRADA, también en los cierres:
    # es lo que conecta ambos eventos de la misma posición.
    for tipo, filas, mensaje in (
        ('apertura', data.get('abiertas', []), _mensaje_apertura),
        ('cierre',   data.get('cerradas', []), _mensaje_cierre),
    ):
        for row in filas:
            clave = _clave(row, tipo)
            if es_primera_vez:
                conn.execute(
                    "INSERT OR IGNORE INTO notificadas (clave, tipo, ticker, enviado_en) VALUES (?,?,?,?)",
                    (clave, tipo, row['ticker'], datetime.utcnow().isoformat())
                )
                continue
            # Reclamar primero (es lo que evita el envío duplicado entre el
            # bucle periódico y una llamada manual concurrente), decidir
            # después si de verdad hay que mandar algo.
            if not _reclamar(conn, clave, tipo, row['ticker']):
                continue
            if _avisado_con_formato_viejo(conn, row, tipo):
                migradas += 1
                continue
            enviar_telegram(mensaje(row))
            enviadas += 1

    conn.commit()
    conn.close()

    if es_primera_vez:
        print("[CarteraTracking] Primera ejecución — posiciones existentes memorizadas sin enviar Telegram (evita un aluvión de mensajes con todo el histórico)")
    else:
        if migradas:
            print(f"[CarteraTracking] {migradas} operación(es) ya avisada(s) con el formato de clave anterior — reetiquetadas sin enviar nada")
        if enviadas:
            print(f"[CarteraTracking] {enviadas} notificación(es) enviada(s)")
    return {"enviadas": enviadas, "migradas": migradas, "bootstrap": es_primera_vez}


init_db()