"""
finnhub_stream_service.py — precios en vivo de verdad para Cartera, vía el
WebSocket de trades de Finnhub.

QUÉ HACE, Y POR QUÉ ASÍ

No sustituye a nada. Mantiene UNA conexión al feed de Finnhub, suscrita a los
tickers de las posiciones abiertas, y con cada trade que llega **escribe en el
mismo `_price_cache` de cartera_service** que ya usa todo el módulo. El
WebSocket propio de la terminal lo distribuye después sin enterarse de dónde
salió el precio, y el frontend no cambia ni una línea.

Es decir: se inyecta por debajo, no se reemplaza por arriba. Ver la auditoría
de Cartera, mejora #25.

CÓMO SE REVIERTE

Poniendo `FINNHUB_REALTIME=false` (o borrando la variable, que es el valor por
defecto). Sin el flag, este módulo no abre ninguna conexión y todo vuelve a
yfinance exactamente como estaba — no hay nada que desmontar. El camino de
yfinance sigue vivo y probado en todo momento, porque es además el que da el
CIERRE ANTERIOR (ver abajo).

LO QUE FINNHUB NO DA, Y POR QUÉ SIGUE HACIENDO FALTA YFINANCE

El feed manda trades: símbolo, precio, volumen y hora. NO manda el cierre de
la sesión anterior, que es lo que hace falta para el «HOY %». Ese dato sigue
viniendo de `_get_daily_bars()` (cacheado 6h), y este servicio solo actualiza
el precio, recalculando el porcentaje contra el `prev` que ya hubiera. Si un
ticker todavía no tiene `prev` conocido, se deja pasar el tick en vez de
inventar un cambio del 0% — mismo criterio que el resto del módulo.

LÍMITE DEL PLAN
El plan gratuito admite 50 símbolos simultáneos. Si hay más posiciones
abiertas, se suscriben las primeras 50 y se dice en el log: el resto no falla,
simplemente sigue sirviéndose por yfinance como hasta ahora.

LICENCIA — LEER ANTES DE DAR ESTO POR BUENO
Los términos de Finnhub dicen que «all plan listed on Finnhub website is
strictly for personal use unless explicitly stated otherwise» y prohíben
redistribuir los datos «or derived results» a terceros sin aprobación escrita.
Servir estos precios a los usuarios de la terminal es redistribución. El flag
viene DESACTIVADO por defecto a propósito: encenderlo es una decisión con
implicaciones de licencia, no solo técnica.
"""
import asyncio
import json
import threading
import time

import requests

from config import settings

# ── Cotización puntual por REST, complemento del WebSocket ────────────────────
#
# El WebSocket solo empuja cuando ocurre un TRADE. Un valor poco negociado, o
# uno que el plan gratuito no difunde, puede pasarse la sesión entera sin
# generar ni un tick — y entonces se queda sin porcentaje del día aunque el
# dato exista perfectamente.
#
# El endpoint /quote lo resuelve de una sola llamada: devuelve el precio
# actual (c), el CIERRE ANTERIOR (pc) y la variación ya calculada (dp). Es la
# única fuente del proyecto que da el cierre de referencia junto al precio, así
# que no depende de que las barras diarias de yfinance estén al día.
#
# Medido sobre las 46 posiciones abiertas reales: /quote las cubre TODAS,
# incluidos los ETFs (GLD, GDXJ, IBIT, KOID, BOTZ, NLR, UFO, MAGS), mientras
# que ese mismo día yfinance no tenía barra de la sesión en curso para ninguna.

QUOTE_URL = "https://finnhub.io/api/v1/quote"

# El plan gratuito admite 60 llamadas por minuto. Se deja margen a propósito:
# pasarse devuelve 429 y tumbaría también el resto de usos de la clave.
_MAX_LLAMADAS_MIN = 50
_ventana: list = []
_ventana_lock = threading.Lock()


def _hay_cupo() -> bool:
    """Ventana deslizante de 60 s, compartida entre hilos -- fetch_live_prices()
    consulta los tickers en paralelo, así que sin candado el conteo se queda
    corto justo cuando más importa."""
    ahora = time.time()
    with _ventana_lock:
        _ventana[:] = [t for t in _ventana if ahora - t < 60]
        if len(_ventana) >= _MAX_LLAMADAS_MIN:
            return False
        _ventana.append(ahora)
        return True


def quote(ticker: str) -> dict | None:
    """{price, prev, chg} de un ticker, o None si no hay dato fiable.

    Devuelve None sin ruido cuando el flag está apagado, cuando no queda cupo
    de llamadas o cuando Finnhub responde sin precio -- el llamador sigue con
    su siguiente fuente. Nunca fabrica un 0%."""
    if not settings.finnhub_realtime or not settings.finnhub_api_key:
        return None
    if not _hay_cupo():
        return None
    try:
        r = requests.get(QUOTE_URL,
                         params={"symbol": ticker, "token": settings.finnhub_api_key},
                         timeout=6)
        if r.status_code != 200:
            return None
        j = r.json()
        precio, cierre_previo = j.get("c"), j.get("pc")
        if not precio or not cierre_previo or precio <= 0 or cierre_previo <= 0:
            return None
        return {"price": round(float(precio), 2),
                "prev":  round(float(cierre_previo), 2),
                "chg":   round((float(precio) - float(cierre_previo)) / float(cierre_previo) * 100, 2)}
    except Exception:
        return None

# Tope de símbolos del plan gratuito. Si algún día se pasa a un plan superior,
# esto sube; mientras tanto, pasarse en silencio sería peor que recortar.
MAX_SIMBOLOS = 50

# Cada cuánto se revisa si la lista de posiciones abiertas ha cambiado (una
# compra o un cierre) para ajustar las suscripciones.
INTERVALO_RESUSCRIPCION = 300  # 5 min

_estado = {
    "conectado":   False,
    "suscritos":   [],
    "ticks":       0,
    "ultimo_tick": None,
    "truncado":    0,
}


def estado() -> dict:
    """Snapshot para diagnóstico — lo usa el endpoint de estado y los logs."""
    return dict(_estado)


def _tickers_abiertos() -> list:
    from services.cartera_service import get_cartera
    data = get_cartera()
    if not data.get("ok"):
        return []
    return list(dict.fromkeys(p["ticker"] for p in data.get("abiertas", [])))


def _aplicar_trade(ticker: str, precio: float) -> bool:
    """Escribe el precio en el caché compartido de Cartera.

    Devuelve False —y no toca nada— si todavía no se conoce el cierre anterior
    de ese ticker: sin `prev` no hay forma de calcular el «HOY %», y publicar
    el precio con un 0% sería exactamente el dato fabricado que este módulo
    lleva tiempo quitando (ver #A3).
    """
    from services.cartera_service import _price_cache

    previo = _price_cache.get(ticker)
    prev = (previo or {}).get("prev")
    if not prev or prev <= 0:
        return False

    _price_cache[ticker] = {
        "ticker":  ticker,
        "price":   round(precio, 2),
        "prev":    prev,
        "chg":     round((precio - prev) / prev * 100, 2),
        "updated": time.time(),
        # Marca de origen: permite distinguir en diagnóstico un precio de
        # stream de uno de yfinance sin tener que adivinarlo por la hora.
        "fuente":  "finnhub",
    }
    return True


async def _sembrar_cierres_anteriores(tickers: list) -> None:
    """Rellena el caché con las barras diarias de yfinance ANTES de arrancar el
    stream, para que el primer trade de cada ticker ya tenga contra qué
    compararse. Sin esto, los primeros minutos se descartarían todos los ticks
    por falta de `prev`."""
    from services.cartera_service import fetch_live_prices
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, fetch_live_prices, tickers)


async def stream_loop():
    """Bucle principal. Lo arranca main.py bajo ws.supervisar(), así que si
    revienta con una excepción no capturada se relanza solo."""
    # OJO con salir de aquí con `return`: ws.supervisar() solo espera cuando la
    # corrutina muere por EXCEPCIÓN — si retorna limpiamente la relanza de
    # inmediato, y un `return` seco convertía esto en un bucle cerrado que
    # inundaba el log y consumía CPU con el flag apagado (visto al arrancar el
    # backend en la verificación). Cuando no hay nada que hacer, se aparca.
    motivo = None
    if not getattr(settings, "finnhub_realtime", False):
        motivo = "desactivado (FINNHUB_REALTIME=false) — Cartera sigue con yfinance"
    elif not getattr(settings, "finnhub_api_key", ""):
        motivo = "sin FINNHUB_API_KEY — no se abre el stream"
    if motivo:
        print(f"[FinnhubStream] {motivo}")
        while True:                       # aparcado, no terminado
            await asyncio.sleep(3600)

    import websockets

    url = "wss://ws.finnhub.io?token=" + settings.finnhub_api_key

    while True:
        tickers_todos = await asyncio.get_event_loop().run_in_executor(None, _tickers_abiertos)
        tickers = tickers_todos[:MAX_SIMBOLOS]
        _estado["truncado"] = len(tickers_todos) - len(tickers)
        if _estado["truncado"]:
            print(f"[FinnhubStream] {len(tickers_todos)} posiciones abiertas y el plan admite "
                  f"{MAX_SIMBOLOS}: {_estado['truncado']} seguirán por yfinance")
        if not tickers:
            await asyncio.sleep(INTERVALO_RESUSCRIPCION)
            continue

        await _sembrar_cierres_anteriores(tickers)

        try:
            async with websockets.connect(url, open_timeout=20, ping_interval=20) as ws:
                for t in tickers:
                    await ws.send(json.dumps({"type": "subscribe", "symbol": t}))
                _estado.update({"conectado": True, "suscritos": tickers})
                print(f"[FinnhubStream] Conectado, {len(tickers)} símbolos suscritos")

                limite = time.time() + INTERVALO_RESUSCRIPCION
                while time.time() < limite:
                    try:
                        crudo = await asyncio.wait_for(ws.recv(), timeout=30)
                    except asyncio.TimeoutError:
                        continue  # mercado parado: no es un fallo, se sigue esperando
                    try:
                        msg = json.loads(crudo)
                    except Exception:
                        continue
                    if msg.get("type") == "error":
                        print(f"[FinnhubStream] Error del servidor: {msg}")
                        continue
                    if msg.get("type") != "trade":
                        continue
                    for tr in msg.get("data", []):
                        if _aplicar_trade(tr["s"], float(tr["p"])):
                            _estado["ticks"] += 1
                            _estado["ultimo_tick"] = time.time()
        except asyncio.CancelledError:
            raise
        except Exception as e:
            # Cortes de red, rechazos del proveedor, límite alcanzado... nada de
            # esto debe tumbar Cartera: se marca desconectado y, en cuanto los
            # precios del caché envejecen (60s), fetch_live_prices vuelve a
            # yfinance por su cuenta. La degradación es automática.
            print(f"[FinnhubStream] Conexión caída ({type(e).__name__}: {e}) — "
                  f"Cartera vuelve a yfinance mientras tanto")
            _estado["conectado"] = False
            await asyncio.sleep(30)
            continue

        _estado["conectado"] = False
