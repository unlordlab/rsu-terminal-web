from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from services.market_service import get_indices
from services.rsu_algoritmo_service import get_rsu_algoritmo
from services.cartera_service import get_cartera
from auth import decode_token
from datetime import datetime, timezone
import asyncio
import json
import math
import yfinance as yf
import pytz
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "shared"))
import market_calendar  # noqa: E402

router = APIRouter()

# La CLAVE tiene que coincidir con el identificador que la pantalla pone en
# `data-ws-ticker`, porque es por ahí por donde se emparejan la fila y el tick.
# "GOLD" y "DXY" coincidían por casualidad; "OIL" no —la fila de petróleo se
# llama "WTI"— así que ese precio nunca se actualizaba en vivo. Bitcoin tiene
# su propio caso: la fila usa el par completo "BTC-USD", y eso se resuelve en
# el frontend probando también esa forma. Ver auditoría Market, hallazgo #8.
PRICE_TICKERS = {
    "BTC":  "BTC-USD",
    "GOLD": "GC=F",
    "WTI":  "CL=F",
    "DXY":  "DX-Y.NYB",
    "AAPL": "AAPL",
    "MSFT": "MSFT",
    "GOOGL":"GOOGL",
    "AMZN": "AMZN",
    "NVDA": "NVDA",
    "META": "META",
    "TSLA": "TSLA",
    "MEME": "MEME",
    "VUG":  "VUG",
    "SMH":  "SMH",
}

# ── AUTENTICACIÓN ─────────────────────────────────────────────────────────────
#
# El navegador no permite fijar cabeceras propias (como Authorization) en el
# handshake de un WebSocket, así que el token viaja como query param
# (?token=...), tal y como ya lo manda el frontend (core/websocket.js y
# cartera.js). Antes de aceptar la conexión, lo validamos igual que en las
# rutas HTTP normales (auth.decode_token). Si falta o no es válido, se
# rechaza la conexión con el código de cierre 4401 (rango reservado para uso
# de la aplicación) y no se acepta el socket.

async def _authenticate(websocket: WebSocket, min_tier: str | None = None) -> bool:
    # ── Validación de Origin (contra Cross-Site WebSocket Hijacking) ──────
    # Un navegador siempre envía la cabecera Origin en un handshake de WS.
    # Si viene y su host NO coincide con el host al que se conecta (mismo
    # origen), es una página de terceros intentando abrir un WS con la
    # sesión del usuario -- se rechaza. Si NO viene Origin, es un cliente
    # no-navegador (curl, script propio): se permite, porque el vector de
    # ataque CSWSH existe solo desde navegadores. Comparar contra el Host
    # de la propia petición (en vez de una lista configurada) hace que
    # esto funcione igual hoy con la IP y mañana con el dominio, sin tocar
    # nada. Ver auditoría 19/07/2026, hallazgo #8.
    origin = websocket.headers.get("origin")
    if origin:
        from urllib.parse import urlparse
        origin_host = (urlparse(origin).hostname or "").lower()
        request_host = (websocket.headers.get("host") or "").split(":")[0].lower()
        if not origin_host or origin_host != request_host:
            await websocket.close(code=4403)
            return False

    # La cookie de sesión también viaja en el handshake de un WebSocket del
    # mismo origen, así que es la vía principal desde el paso a cookie
    # httpOnly -- y de paso el token deja de ir en la URL, donde acababa en
    # los logs de acceso del servidor. El query param se mantiene como
    # respaldo para las sesiones abiertas antes del cambio, que todavía
    # llevan su token en el navegador.
    from auth import COOKIE_NAME
    token = websocket.cookies.get(COOKIE_NAME) or websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4401)
        return False
    payload = decode_token(token)
    if payload is None:
        await websocket.close(code=4401)
        return False
    # Misma comprobación de token_version que verify_token() en auth.py --
    # sin esto, una sesión revocada por HTTP seguiría viva indefinidamente
    # en el WebSocket (Cartera en vivo, etc.), ya que aquí no se pasa por
    # verify_token. Ver conversación 20/07/2026.
    from services import users_service
    email = payload.get("sub")
    ws_user = users_service.get_user_by_email(email) if email else None
    if ws_user is None or ws_user.get("token_version", 0) != payload.get("tv", 0):
        await websocket.close(code=4401)
        return False
    if min_tier:
        # Igual que en require_tier (auth.py): se consulta el tier ACTUAL en
        # base de datos, no el que quedó grabado en el JWT al hacer login,
        # para que una subida de tier por parte del admin surta efecto sin
        # esperar a que expire el token viejo.
        from auth import TIER_ORDER
        from services import users_service
        email      = payload.get("sub")
        user       = users_service.get_user_by_email(email) if email else None
        user_tier  = user["tier"] if user else payload.get("tier", "free")
        if TIER_ORDER.get(user_tier, 0) < TIER_ORDER.get(min_tier, 0):
            await websocket.close(code=4403)
            return False
    return True

# ── HELPERS ───────────────────────────────────────────────────────────────────

def _get_quick_prices() -> list:
    """Precio y variación diaria de la barra superior de Market.

    LA VENTANA ES DE 7 DÍAS Y NO DE 2 A PROPÓSITO. Esto pedía `period="2d"`,
    que devuelve como mucho dos filas, y daba por hecho que `iloc[-2]` era la
    sesión anterior. Con dos filas esa suposición no se puede ni comprobar: no
    hay margen para VER que falta una sesión por medio. Cuando yfinance se
    salta una barra —pasa por símbolo, y más desde el VPS, porque Yahoo limita
    las IP de centro de datos— `iloc[-2]` es el cierre de hace DOS sesiones y
    el porcentaje es el de dos días con la etiqueta del actual.

    Es el mismo patrón que hizo fallar el «HOY %» de Cartera tres días
    seguidos (11, 12 y 13/08/2026); ver `cartera_service._fetch_price_single`.
    Allí se arregló mirando la FECHA de las barras en vez de su posición, y
    aquí se aplica el mismo criterio con el mismo helper compartido
    (`shared/market_calendar.py`), para que no se vuelvan a separar.

    MEDIDO ANTES DE TOCAR NADA (13/08/2026, 10:36-10:52 Nueva York): de los 14
    símbolos, 0 tenían hueco en ese momento, y en un mes de historial (24
    sesiones × 14 símbolos) no faltaba ninguna barra. O sea: el fallo NO se
    estaba produciendo al medirlo desde una IP residencial. La comprobación se
    añade igualmente porque el código no tenía ninguna defensa —era incapaz de
    detectar la condición aunque se diera—, porque el mismo patrón sí reventó
    de forma repetida en producción con la cartera, y porque la medición desde
    aquí no dice nada de lo que ve el VPS, que es donde duele.
    """
    result = []
    for name, ticker in PRICE_TICKERS.items():
        try:
            t    = yf.Ticker(ticker)
            hist = t.history(period="7d", interval="1d")
            if hist.empty or "Close" not in hist:
                continue
            # dropna() por el mismo motivo que en _get_daily_bars: Yahoo
            # devuelve la fila de la sesión en curso con el cierre a NaN
            # mientras no ha asentado, y ese NaN se propagaría hasta el JSON.
            closes = hist["Close"].dropna()
            if len(closes) < 2:
                continue
            last   = float(closes.iloc[-1])
            prev   = float(closes.iloc[-2])
            if not prev or not math.isfinite(prev) or not math.isfinite(last):
                continue
            f_ult  = closes.index[-1].date()
            f_prev = closes.index[-2].date()

            # ¿El cierre de referencia es de la sesión INMEDIATAMENTE anterior
            # a la última barra, o hay sesiones por medio? Cripto cotiza los
            # siete días, así que ahí «la anterior» es el día natural anterior;
            # aplicarle el calendario bursátil descartaría un dato bueno cada
            # lunes.
            esperada_prev = (market_calendar.dia_anterior_a(f_ult)
                             if market_calendar.cotiza_todos_los_dias(ticker)
                             else market_calendar.sesion_anterior_a(f_ult))

            fila = {"name": name, "ticker": ticker, "price": round(last, 2),
                    # De qué sesión es el dato. Viaja siempre, para que la
                    # pantalla pueda decirlo en vez de dar por hecho que es hoy.
                    "chg_fecha": str(f_ult)}

            if f_prev != esperada_prev:
                # Faltan sesiones entre las dos barras: el porcentaje que
                # saldría de aquí es el de VARIOS días, y en la barra superior
                # se leería como el del día. Se prefiere no decirlo -- mismo
                # criterio anti-fabricación que Cartera: un número plausible y
                # falso engaña más que un hueco.
                #
                # El precio SÍ se publica: ese es real y útil. Lo que se calla
                # es la variación, que es lo que no sabemos.
                fila.update({"chg": None, "sin_datos_hoy": True,
                             "ultimo_cierre": str(f_prev)})
            else:
                fila.update({"chg": round((last - prev) / prev * 100, 2),
                             "sin_datos_hoy": False})
                # La referencia es buena, pero la última barra puede ser vieja:
                # con el proveedor degradado el porcentaje sale internamente
                # coherente y de hace días (así estuvo Cartera cuatro días
                # congelada en el viernes 7 sin que nada lo dijera). Dos
                # sesiones de margen, igual que _estado_de_los_precios(), para
                # que un festivo no dispare el aviso.
                desfase = (market_calendar.ultima_sesion_esperada() - f_ult).days
                if desfase >= 2:
                    fila["sesion_desfasada"] = True

            # Se manda TAMBIÉN el símbolo real, no solo la clave.
            #
            # La pantalla identifica cada fila por el símbolo de yfinance
            # (`data-ws-ticker="CL=F"`, `"BTC-USD"`), mientras que aquí solo
            # viajaba la clave del diccionario ("OIL", "BTC"). Para acciones
            # coincidían por casualidad —la clave ES el símbolo— y por eso
            # funcionaban; para materias primas y cripto no casaban nunca, así
            # que esas filas jamás recibían precio en vivo. Ver auditoría
            # Market, hallazgo #8.
            result.append(fila)
        except Exception:
            continue
    return result

# Tope de tickers por difusión del WS. Antes eran 30 a fuego y sin avisar:
# con 53 posiciones abiertas, 23 filas simplemente no recibían precio en vivo
# y no había nada en la interfaz que lo dijera (auditoría de Cartera, #B12).
# El coste real de subirlo es bajo -- fetch_live_prices() va en paralelo y
# cachea 60 s, así que en régimen estable la mayoría de tickers ni se
# descargan. Se deja un tope alto por seguridad, y si alguna vez recorta, se
# dice en el propio mensaje para que la página pueda avisar.
MAX_TICKERS_WS_CARTERA = 120


def _get_cartera_prices() -> dict:
    try:
        from services.cartera_service import get_cartera, fetch_live_prices
        data     = get_cartera()
        abiertas = data.get('abiertas', [])
        if not abiertas:
            return {"prices": [], "truncados": 0}
        todos     = list(dict.fromkeys([p['ticker'] for p in abiertas]))
        tickers   = todos[:MAX_TICKERS_WS_CARTERA]
        truncados = len(todos) - len(tickers)
        if truncados:
            print(f"[BroadcastCartera] {len(todos)} tickers abiertos, se difunden {len(tickers)} "
                  f"(tope {MAX_TICKERS_WS_CARTERA}) — {truncados} quedan sin precio en vivo")
        prices = fetch_live_prices(tickers)
        return {"prices": list(prices.values()), "truncados": truncados}
    except Exception:
        return {"prices": [], "truncados": 0}


async def _build_payload() -> dict:
    loop         = asyncio.get_event_loop()
    indices_data = await loop.run_in_executor(None, get_indices)
    prices_data  = await loop.run_in_executor(None, _get_quick_prices)
    algo_data    = await loop.run_in_executor(None, get_rsu_algoritmo)

    indices_simple = []
    for idx in indices_data.get("data", []):
        if idx.get("ok"):
            indices_simple.append({
                "ticker": idx["ticker"],
                "price":  idx["price"],
                "chg":    idx["pct"],
            })

    madrid         = pytz.timezone("Europe/Madrid")
    now_madrid     = datetime.now(timezone.utc).astimezone(madrid)
    timestamp_madrid = now_madrid.strftime('%H:%M:%S')

    return {
        "type":    "market_update",
        "indices": indices_simple,
        "prices":  prices_data,
        "algo": {
            "score":  algo_data.get("score", 0),
            "estado": algo_data.get("estado", ""),
            "color":  algo_data.get("color", "#888"),
            "senal":  algo_data.get("senal", ""),
        } if algo_data.get("ok") else None,
        "timestamp": timestamp_madrid,
    }

# ── CONNECTION MANAGERS ───────────────────────────────────────────────────────

class ConnectionManager:
    def __init__(self):
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.active:
            self.active.remove(ws)

    async def broadcast(self, data: dict):
        dead = []
        for ws in self.active:
            try:
                await ws.send_text(json.dumps(data))
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


class CarteraManager:
    def __init__(self):
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.active:
            self.active.remove(ws)

    async def broadcast(self, data: dict):
        dead = []
        for ws in self.active:
            try:
                await ws.send_text(json.dumps(data))
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


manager         = ConnectionManager()
cartera_manager = CarteraManager()

# ── WEBSOCKET ENDPOINTS ───────────────────────────────────────────────────────

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    if not await _authenticate(websocket):
        return
    await manager.connect(websocket)
    try:
        payload = await _build_payload()
        await websocket.send_text(json.dumps(payload))
        while True:
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=65.0)
            except asyncio.TimeoutError:
                await websocket.send_text(json.dumps({"type": "ping"}))
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)


@router.websocket("/ws/cartera")
async def websocket_cartera(websocket: WebSocket):
    if not await _authenticate(websocket, min_tier="tier1"):
        return
    await cartera_manager.connect(websocket)
    try:
        loop   = asyncio.get_event_loop()
        snap   = await loop.run_in_executor(None, _get_cartera_prices)
        await websocket.send_text(json.dumps({"type": "cartera_update", **snap}))
        while True:
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=65.0)
            except asyncio.TimeoutError:
                await websocket.send_text(json.dumps({"type": "ping"}))
    except WebSocketDisconnect:
        cartera_manager.disconnect(websocket)
    except Exception:
        cartera_manager.disconnect(websocket)

# ── SUPERVISOR ────────────────────────────────────────────────────────────────
#
# Las 10 tareas de fondo de main.py tienen la forma "while True: sleep;
# try/except" -- eso protege DENTRO de cada vuelta, pero si algo revienta
# FUERA de ese try (o dentro del propio manejo del error -- ya nos pasó en
# esta sesión: un print() con una flecha "→" lanzó UnicodeEncodeError en la
# consola de Windows, capturado solo porque ya estaba dentro de un try
# ajeno), la Task de asyncio muere para siempre. Sin log, sin reinicio -- el
# único síntoma es notar días después que algo dejó de funcionar (alertas
# que no llegan, ingesta que no corre...). supervisar() envuelve cada bucle
# para que, si el bucle entero muere, se relance solo tras un cooldown, con
# un log explícito de cuándo y por qué. Ver auditoría de infraestructura,
# hallazgo #7, 21/07/2026.
async def supervisar(nombre: str, corrutina_factory, cooldown: int = 60):
    while True:
        try:
            await corrutina_factory()
        except asyncio.CancelledError:
            raise  # shutdown real (task.cancel() en main.py) -- no es un fallo, no reintentar
        except Exception as e:
            print(f"[Supervisor] '{nombre}' murió: {type(e).__name__}: {e} -- reiniciando en {cooldown}s")
            await asyncio.sleep(cooldown)


# ── BACKGROUND LOOPS ──────────────────────────────────────────────────────────

async def finnhub_stream_loop():
    """Precios en vivo de Cartera vía el WebSocket de Finnhub. Vive en su
    propio servicio (services/finnhub_stream_service.py); aquí solo se expone
    con la forma que espera main.py, igual que el resto de bucles.

    Sale de inmediato si FINNHUB_REALTIME está apagado, que es el valor por
    defecto — encenderlo tiene implicaciones de licencia, ver el servicio."""
    from services.finnhub_stream_service import stream_loop
    await stream_loop()


async def broadcast_loop():
    while True:
        await asyncio.sleep(60)
        if manager.active:
            try:
                payload = await _build_payload()
                await manager.broadcast(payload)
            except Exception as e:
                print(f"[Broadcast] Error: {type(e).__name__}: {e}")


async def broadcast_cartera_loop():
    while True:
        await asyncio.sleep(60)
        if cartera_manager.active:
            try:
                loop = asyncio.get_event_loop()
                snap = await loop.run_in_executor(None, _get_cartera_prices)
                await cartera_manager.broadcast({"type": "cartera_update", **snap})
            except Exception as e:
                print(f"[BroadcastCartera] Error: {type(e).__name__}: {e}")


# Comprobación de alertas de precio (Watchlist). Cada 90s revisa TODAS las
# alertas activas de TODOS los usuarios de una vez (agrupadas por ticker, un
# solo fetch de precio por ticker aunque varios usuarios compartan alerta en
# el mismo nombre). Las alertas disparadas quedan marcadas en BD
# (status='triggered', seen=0) -- el frontend las sigue descubriendo vía
# poll a /api/v1/watchlist/alerts/unseen-count para la campanita del topbar
# -- y desde el 25/07/2026 además se notifica por Telegram a quien tenga la
# cuenta vinculada (ver watchlist_service.notify_triggered_alerts y
# services/telegram_service.py). Ver hallazgo crítico #1, auditoría
# Watchlist 21/07/2026.
async def alerts_check_loop():
    while True:
        await asyncio.sleep(90)
        try:
            from services.watchlist_service import check_all_active_alerts, notify_triggered_alerts
            loop = asyncio.get_event_loop()
            triggered = await loop.run_in_executor(None, check_all_active_alerts)
            if triggered:
                await loop.run_in_executor(None, notify_triggered_alerts, triggered)
        except Exception as e:
            print(f"[AlertsCheck] Error: {type(e).__name__}: {e}")


# Long-polling del bot de Telegram para vincular cuentas de usuario (ver
# services/telegram_service.py::poll_and_process_updates). getUpdates ya
# bloquea ~25s en el lado de Telegram esperando un mensaje nuevo, así que
# este bucle no necesita más pausa que un pequeño respiro en caso de error.
# Si TELEGRAM_BOT_TOKEN no está configurado, se comprueba cada 5 min por si
# se añade luego, sin busy-loop.
async def telegram_link_poll_loop():
    while True:
        try:
            from config import settings
            if not getattr(settings, "telegram_bot_token", ""):
                await asyncio.sleep(300)
                continue
            from services.telegram_service import poll_and_process_updates
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, poll_and_process_updates)
        except Exception as e:
            print(f"[TelegramLink] Error: {type(e).__name__}: {e}")
            await asyncio.sleep(30)


# Ingesta de Insider Flow (SEC EDGAR Form 4). El feed "getcurrent" de EDGAR es
# una foto de lo que se está presentando en TODO el mercado en ese instante,
# no un histórico — así que en vez de pedirlo una vez y tirarlo cada 30 min,
# se acumula en SQLite en cada pasada (ver insider_service._ingest_cycle) y el
# feed que ve el usuario lee de ese histórico acumulado de los últimos días.
# Cada 20 min para no perder cobertura del día mientras el mercado está
# abierto sin machacar el servicio de EDGAR con demasiada frecuencia.
async def insider_ingest_loop():
    while True:
        try:
            from services.insider_service import _ingest_cycle
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, _ingest_cycle)
        except Exception as e:
            # Antes era `except Exception: pass`: si este bucle se rompía, el
            # feed se quedaba congelado sin dejar el menor rastro. Mismo
            # criterio que el resto de bucles de este fichero.
            print(f"[InsiderIngest] Error en el bucle: {type(e).__name__}: {e}")
        await asyncio.sleep(1200)


# Refresco proactivo de los widgets más pesados de Market — Amplitud de
# Mercado (histórico SPY 2 años + scan de amplitud), Fed & Macro (varias
# series FRED) y Credit Spreads (2 series FRED de 260 puntos). Sin esto, el
# PRIMER usuario que entra después de que caduque la caché se come en vivo
# la llamada externa completa; con esto, se refresca por detrás antes de
# caducar y esa espera nunca la sufre ningún usuario real.
#
# Cada función se refresca a un ritmo ajustado a su propio TTL (ver
# services/cache.py) — todo en un único bucle de 4 min para no multiplicar
# tareas en segundo plano; Fed Macro y Credit Spreads simplemente se saltan
# la mayoría de ciclos.
async def market_cache_warm_loop():
    tick = 0
    while True:
        await asyncio.sleep(240)  # 4 min — ritmo del más corto (Amplitud, TTL 300s)
        tick += 240
        try:
            from services.market_service import get_market_breadth, get_fed_macro, get_credit_spreads
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, get_market_breadth)
            if tick % 1680 < 240:   # ~cada 28 min, bajo el TTL de 30 min de Fed Macro
                await loop.run_in_executor(None, get_fed_macro)
            if tick % 3360 < 240:   # ~cada 56 min, bajo el TTL de 1h de Credit Spreads
                await loop.run_in_executor(None, get_credit_spreads)
        except Exception as e:
            print(f"[MarketWarm] Error refrescando caché: {e}")
        # Snapshot point-in-time (ver services/snapshots_service.py) -- en
        # try/except propio para que un fallo aquí no interfiera con el
        # refresco de caché de arriba. maybe_write_daily_snapshot() es
        # idempotente por fecha de sesión: en el 99% de las pasadas de 4
        # min no hace nada (ya escribió hoy), solo actúa la primera vez
        # que ve una fecha de sesión nueva -- por eso no hace falta un
        # bucle propio de 24h (ver hallazgo de la sesión 35 con Options
        # Flow: un bucle "cada 24h desde que arrancó" deriva de cuándo se
        # reinició el contenedor, no de una fecha real).
        try:
            from services.snapshots_service import maybe_write_daily_snapshot
            await loop.run_in_executor(None, maybe_write_daily_snapshot)
        except Exception as e:
            print(f"[Snapshots] Error: {e}")


# Recalcula el RSU Algoritmo en vivo cada 30 min, independientemente de si
# algún usuario tiene la página abierta — si no existiera esto, un cambio de
# semáforo solo se detectaría (y notificaría por Telegram) cuando alguien
# entrase a /algoritmo por casualidad, lo que podría tardar horas o no pasar
# nunca en fin de semana. get_rsu_algoritmo() ya lleva dentro la llamada a
# procesar_resultado_algoritmo() que compara contra el último estado
# conocido y solo notifica si de verdad cambió.
async def algoritmo_check_loop():
    while True:
        await asyncio.sleep(1800)  # 30 min
        try:
            from services.rsu_algoritmo_service import get_rsu_algoritmo
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, get_rsu_algoritmo)
        except Exception as e:
            print(f"[AlgoritmoCheck] Error: {e}")

        # Calentar la caché del BACKTEST si está fría.
        #
        # El usuario reportaba "Unexpected token '<'" al abrir el backtest: el
        # cálculo tarda minutos, Nginx corta la petición a los 60s por defecto
        # y devuelve una página HTML de error 504 que el frontend intentaba
        # parsear como JSON. El cálculo del servidor SÍ terminaba y dejaba la
        # caché escrita, así que al segundo intento funcionaba — de ahí el
        # "muchas veces" en vez de "siempre".
        #
        # Calentándola aquí, el endpoint responde instantáneo desde caché y
        # nadie paga nunca el cálculo en una petición HTTP. Con TTL de 12h y
        # esta pasada cada 30 min, la ventana en la que puede estar fría baja
        # de 12 horas a 30 minutos como mucho.
        try:
            from services.cache import cache
            from services.rsu_algoritmo_service import get_rsu_algoritmo_backtest
            for years in (10, 15, 20):
                if cache.get(f"algoritmo:backtest:{years}y:v20") is None:
                    print(f"[AlgoritmoBacktest] Caché fría para {years}y — precalculando")
                    await loop.run_in_executor(None, get_rsu_algoritmo_backtest, years)
        except Exception as e:
            print(f"[AlgoritmoBacktest] Error calentando caché: {type(e).__name__}: {e}")
        # Decisión OFICIAL del semáforo (la que notifica y deja huella), en su
        # propio try/except para que un fallo aquí no rompa el calentado de
        # caché de arriba. Es idempotente por fecha de sesión: en casi todas
        # las pasadas no hace nada porque la sesión de hoy ya se procesó, y
        # solo actúa la primera vez que ve una sesión cerrada nueva. Por eso
        # no hace falta un bucle propio de 24h -- ver el comentario de
        # procesar_cierre_si_toca() y el mismo error ya corregido en Options
        # Flow (sesión 35), donde "cada 24h desde que arrancó" derivaba con
        # cada reinicio del contenedor.
        try:
            from services.rsu_algoritmo_service import procesar_cierre_si_toca
            await loop.run_in_executor(None, procesar_cierre_si_toca)
        except Exception as e:
            print(f"[AlgoritmoCierre] Error: {type(e).__name__}: {e}")


# Una vez al día, rellena el retorno real (5/10/20/60d) de las señales
# VERDE/VERDE-VOL trackeadas cuyo horizonte ya se ha cumplido. No hace falta
# más frecuencia — los resultados solo cambian con el cierre del día.
async def algoritmo_resultados_loop():
    while True:
        await asyncio.sleep(86400)  # 24h
        try:
            from services.algoritmo_tracking_service import actualizar_resultados_pendientes
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, actualizar_resultados_pendientes)
        except Exception as e:
            print(f"[AlgoritmoResultados] Error: {e}")


# Mismo patrón que algoritmo_resultados_loop(), pero para el tracking del
# RSU Score por ticker (ver services/rsu_score_tracking_service.py) --
# rellena resultado_5d/10d/20d/60d de las señales cuyo horizonte ya se ha
# cumplido. Una vez al día basta, el resultado solo cambia con el cierre.
async def rsu_score_resultados_loop():
    while True:
        await asyncio.sleep(86400)  # 24h
        try:
            from services.rsu_score_tracking_service import actualizar_resultados_pendientes
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, actualizar_resultados_pendientes)
        except Exception as e:
            print(f"[RSUScoreResultados] Error: {e}")


# El tercero del mismo patrón: rellena el retorno real de los candidatos que
# propuso el scan de CANSLIM (services/canslim_tracking_service.py). Es el
# más pesado de los tres -- decenas de miles de filas pendientes-, pero los
# tickers distintos son ~500, así que se resuelve con una sola descarga en
# lote. Una vez al día basta: el resultado solo cambia con el cierre.
async def canslim_resultados_loop():
    while True:
        await asyncio.sleep(86400)  # 24h
        try:
            from services.canslim_tracking_service import actualizar_resultados_pendientes
            loop = asyncio.get_event_loop()
            res = await loop.run_in_executor(None, actualizar_resultados_pendientes)
            if res and res.get("actualizadas"):
                print(f"[CANSLIMResultados] {res['actualizadas']} filas actualizadas "
                      f"de {res['pendientes']} pendientes")
        except Exception as e:
            print(f"[CANSLIMResultados] Error: {e}")


# Revisa Cartera (Google Sheet) cada 15 min buscando aperturas/cierres nuevos
# y notifica por Telegram — el sheet lo edita Marc a mano, así que no hace
# falta más frecuencia que esta para no perderse cambios durante horario de
# mercado sin golpear la hoja constantemente.
async def cartera_check_loop():
    while True:
        await asyncio.sleep(900)  # 15 min
        try:
            from services.cartera_tracking_service import procesar_cartera_notificaciones
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, procesar_cartera_notificaciones)
        except Exception as e:
            print(f"[CarteraCheck] Error: {e}")
