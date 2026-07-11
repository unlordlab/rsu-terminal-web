from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from services.market_service import get_indices
from services.rsu_algoritmo_service import get_rsu_algoritmo
from services.cartera_service import get_cartera
from auth import decode_token
from datetime import datetime, timezone
import asyncio
import json
import yfinance as yf
import pytz

router = APIRouter()

PRICE_TICKERS = {
    "BTC":  "BTC-USD",
    "GOLD": "GC=F",
    "OIL":  "CL=F",
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
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4401)
        return False
    payload = decode_token(token)
    if payload is None:
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
    result = []
    for name, ticker in PRICE_TICKERS.items():
        try:
            t    = yf.Ticker(ticker)
            hist = t.history(period="2d", interval="1d")
            if len(hist) < 2: continue
            prev = float(hist['Close'].iloc[-2])
            last = float(hist['Close'].iloc[-1])
            chg  = (last - prev) / prev * 100
            result.append({"name": name, "price": round(last, 2), "chg": round(chg, 2)})
        except Exception:
            continue
    return result

def _get_cartera_prices() -> list:
    try:
        from services.cartera_service import get_cartera, fetch_live_prices
        data     = get_cartera()
        abiertas = data.get('abiertas', [])
        if not abiertas:
            return []
        tickers = list(dict.fromkeys([p['ticker'] for p in abiertas]))[:30]
        prices  = fetch_live_prices(tickers)
        return list(prices.values())
    except Exception:
        return []


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
        prices = await loop.run_in_executor(None, _get_cartera_prices)
        await websocket.send_text(json.dumps({"type": "cartera_update", "prices": prices}))
        while True:
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=65.0)
            except asyncio.TimeoutError:
                await websocket.send_text(json.dumps({"type": "ping"}))
    except WebSocketDisconnect:
        cartera_manager.disconnect(websocket)
    except Exception:
        cartera_manager.disconnect(websocket)

# ── BACKGROUND LOOPS ──────────────────────────────────────────────────────────

async def broadcast_loop():
    while True:
        await asyncio.sleep(60)
        if manager.active:
            try:
                payload = await _build_payload()
                await manager.broadcast(payload)
            except Exception:
                pass


async def broadcast_cartera_loop():
    while True:
        await asyncio.sleep(60)
        if cartera_manager.active:
            try:
                loop   = asyncio.get_event_loop()
                prices = await loop.run_in_executor(None, _get_cartera_prices)
                await cartera_manager.broadcast({"type": "cartera_update", "prices": prices})
            except Exception:
                pass


# Comprobación de alertas de precio (Watchlist). Cada 90s revisa TODAS las
# alertas activas de TODOS los usuarios de una vez (agrupadas por ticker, un
# solo fetch de precio por ticker aunque varios usuarios compartan alerta en
# el mismo nombre). No hay push en tiempo real por WebSocket todavía — las
# alertas disparadas quedan marcadas en BD (status='triggered', seen=0) y el
# frontend las descubre haciendo poll a /api/v1/watchlist/alerts/unseen-count
# (misma cadencia, ~60-90s) para la campanita del topbar. Si en el futuro se
# monta un canal de notificación por usuario (Discord/Telegram/email), este
# es el punto donde engancharlo: la lista `triggered` ya trae, por cada
# alerta, user_id/ticker/condition/target_price/triggered_price.
async def alerts_check_loop():
    while True:
        await asyncio.sleep(90)
        try:
            from services.watchlist_service import check_all_active_alerts
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, check_all_active_alerts)
        except Exception:
            pass


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
        except Exception:
            pass
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