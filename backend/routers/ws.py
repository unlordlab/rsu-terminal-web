from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from services.market_service import get_indices, get_fear_greed
from services.rsu_algoritmo_service import get_rsu_algoritmo
import asyncio
import json
import yfinance as yf

router = APIRouter()

PRICE_TICKERS = {
    "BTC":  "BTC-USD",
    "GOLD": "GC=F",
    "OIL":  "CL=F",
    "DXY":  "DX-Y.NYB",
}

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

async def _build_payload() -> dict:
    loop = asyncio.get_event_loop()

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

    return {
        "type":      "market_update",
        "indices":   indices_simple,
        "prices":    prices_data,
        "algo": {
            "score":  algo_data.get("score", 0),
            "estado": algo_data.get("estado", ""),
            "color":  algo_data.get("color", "#888"),
            "senal":  algo_data.get("senal", ""),
        } if algo_data.get("ok") else None,
        "market_open": indices_data.get("timestamp", ""),
        "timestamp":   indices_data.get("timestamp", ""),
    }

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

manager = ConnectionManager()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # Enviar datos inmediatamente al conectar
        payload = await _build_payload()
        await websocket.send_text(json.dumps(payload))

        # Loop — recibir mensajes del cliente (keepalive)
        while True:
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=65.0)
            except asyncio.TimeoutError:
                # Keepalive ping
                await websocket.send_text(json.dumps({"type": "ping"}))
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)


# Background task que empuja datos cada 60 segundos
async def broadcast_loop():
    while True:
        await asyncio.sleep(60)
        if manager.active:
            try:
                payload = await _build_payload()
                await manager.broadcast(payload)
            except Exception:
                pass