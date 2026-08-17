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

    UN `prev` EXISTENTE NO ES UN `prev` VÁLIDO, y esa confusión es la que hacía
    que el «HOY %» volviera a salir mal un día sí y otro también. Cuando a
    yfinance le falta la barra de ayer, `_fetch_price_single()` hace lo
    correcto: devuelve `chg=None` y `sin_datos_hoy=True` para que la tabla
    pinte «—»... pero SIGUE devolviendo `prev`, que ahí no es el cierre de
    ayer sino el último que se pudo conseguir. Esta función solo miraba que
    ese número existiera y fuera positivo, así que al llegar el primer tick
    recalculaba el porcentaje contra él, convertía un «no lo sé» honesto en
    el movimiento de DOS sesiones con la etiqueta del día, y de paso borraba
    los campos que permitían avisarlo. Reproducido el 13/08/2026 con los
    números reales de la cartera: LITE salía +13,45% cuando su movimiento del
    día era +0,28%; SPCX y COHR aparecían subiendo cuando ambos bajaban.

    Por eso los arreglos anteriores no aguantaban: los tres estaban en las
    ramas de `_fetch_price_single()`, y la corrupción ocurre DESPUÉS, desde
    otro módulo que escribe en la misma caché. Y no se veía en local porque
    `FINNHUB_REALTIME` viene apagado por defecto: sin el flag este código no
    llega a ejecutarse nunca, así que toda verificación local pasaba.
    """
    from services.cartera_service import (_price_cache, _is_market_open,
                                          _ultima_sesion_esperada)

    previo = _price_cache.get(ticker) or {}
    prev = previo.get("prev")
    if not prev or prev <= 0:
        return False

    # El precio en vivo SÍ se publica en los dos caminos: el P&L de cada
    # posición se calcula contra el precio de compra, no contra `prev`, así que
    # es correcto aunque no sepamos el porcentaje del día.
    base = {**previo, "price": round(precio, 2), "prev": prev,
            "updated": time.time()}

    # ── LA REFERENCIA CADUCA, Y HASTA AHORA NADIE LO MIRABA ──────────────────
    #
    # Aquí estaba la razón de que el «HOY %» volviera a salir mal cada pocos
    # días pese a tres arreglos seguidos. Los tres vivían en las ramas de
    # `_fetch_price_single()`... y esa función DEJA DE EJECUTARSE en cuanto
    # llegan ticks: su caché tiene un TTL de 60 s, y la línea de arriba escribe
    # `updated: time.time()` en cada trade. Con el stream vivo, la entrada nunca
    # cumple 60 segundos, así que nunca se vuelve a pedir y su `prev` se queda
    # congelado en el que hubiera cuando arrancó el stream -- cruzando noches y
    # fines de semana enteros.
    #
    # Medido el 17/08/2026 (lunes) con la cartera real: de 24 posiciones, 12
    # calculaban contra el cierre del viernes 14 (correcto), 11 contra el del
    # jueves 13 y una contra el del miércoles 12. SNDK enseñaba +14,02% cuando
    # su movimiento del día era +6,72%: viernes y lunes sumados bajo la
    # etiqueta «HOY». Y como el precio sí llegaba en vivo, el número parecía
    # fresco.
    #
    # El arreglo tiene dos mitades y las dos hacen falta:
    #   1. `prev` viaja con la fecha de su sesión (`prev_fecha`), porque una
    #      referencia sin fecha no se puede validar -- solo se podía comprobar
    #      que existiera y fuera positiva, que es lo que fallaba.
    #   2. Si esa fecha no es la de la última sesión cerrada, no se publica
    #      porcentaje Y NO SE RENUEVA `updated`: así la entrada envejece, la
    #      vuelve a pedir `_fetch_price_single()` y se cura sola. Renovarla era
    #      lo que hacía inmortal al dato viejo.
    #
    # Solo se exige con el mercado abierto: fuera de sesión, `prev` es el cierre
    # anterior al que se está enseñando y no tiene por qué ser el de la última
    # sesión cerrada.
    esperada = str(_ultima_sesion_esperada())
    if _is_market_open() and previo.get("prev_fecha") != esperada:
        base.update({"chg": None, "sin_datos_hoy": True,
                     # Si ya venía una explicación de qué sesión es el dato, se
                     # respeta: es más informativa que la fecha del `prev`, y
                     # pisarla dejaba a la pantalla sin nada que contar.
                     "ultimo_cierre": (previo.get("ultimo_cierre")
                                       or previo.get("prev_fecha") or ""),
                     "fuente": "finnhub-referencia-caducada"})
        # A propósito: se conserva el `updated` anterior para que la entrada
        # caduque y se vuelva a pedir con una referencia fresca.
        base["updated"] = previo.get("updated", 0)
        _price_cache[ticker] = base
        return True

    if previo.get("chg") is None or previo.get("sin_datos_hoy"):
        # Quien puso `prev` ya dijo que no servía como referencia de hoy. Se
        # respeta: el porcentaje sigue en None y se conservan `sin_datos_hoy`
        # /`chg_fecha`/`ultimo_cierre` (vienen en `previo`), que son los que
        # permiten a la pantalla explicar de qué sesión son los datos.
        base.update({"chg": None, "fuente": "finnhub-sin-referencia"})
        _price_cache[ticker] = base
        return True

    # Marca de origen: permite distinguir en diagnóstico un precio de stream
    # de uno de yfinance sin tener que adivinarlo por la hora.
    base.update({"chg": round((precio - prev) / prev * 100, 2), "fuente": "finnhub"})
    _price_cache[ticker] = base
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
