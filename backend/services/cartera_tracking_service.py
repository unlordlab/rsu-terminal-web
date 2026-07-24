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


def _mensaje_apertura(row):
    return (
        "🟢 *NUEVA ENTRADA*\n\n"
        f"📈 Ticker: {row['ticker']}\n"
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

    enviadas = 0
    for row in data.get('abiertas', []):
        clave = f"{row['ticker']}|{row['fecha']}|apertura"
        if es_primera_vez:
            conn.execute(
                "INSERT OR IGNORE INTO notificadas (clave, tipo, ticker, enviado_en) VALUES (?,?,?,?)",
                (clave, 'apertura', row['ticker'], datetime.utcnow().isoformat())
            )
            continue
        if _reclamar(conn, clave, 'apertura', row['ticker']):
            enviar_telegram(_mensaje_apertura(row))
            enviadas += 1

    for row in data.get('cerradas', []):
        # Misma fecha de ENTRADA que en apertura (no la de cierre) — es la
        # clave natural que conecta ambos eventos de la misma posición.
        clave = f"{row['ticker']}|{row['fecha']}|cierre"
        if es_primera_vez:
            conn.execute(
                "INSERT OR IGNORE INTO notificadas (clave, tipo, ticker, enviado_en) VALUES (?,?,?,?)",
                (clave, 'cierre', row['ticker'], datetime.utcnow().isoformat())
            )
            continue
        if _reclamar(conn, clave, 'cierre', row['ticker']):
            enviar_telegram(_mensaje_cierre(row))
            enviadas += 1

    conn.commit()
    conn.close()

    if es_primera_vez:
        print("[CarteraTracking] Primera ejecución — posiciones existentes memorizadas sin enviar Telegram (evita un aluvión de mensajes con todo el histórico)")
    elif enviadas:
        print(f"[CarteraTracking] {enviadas} notificación(es) enviada(s)")
    return {"enviadas": enviadas, "bootstrap": es_primera_vez}


init_db()