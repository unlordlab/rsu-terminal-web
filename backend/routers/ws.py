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

async def _authenticate(websocket: WebSocket) -> bool:
    token = websocket.query_params.get("token")
    if not token or decode_token(token) is None:
        await websocket.close(code=4401)
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
    if not await _authenticate(websocket):
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