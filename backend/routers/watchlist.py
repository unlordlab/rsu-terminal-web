from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from auth import verify_token
from services import users_service, watchlist_service

router = APIRouter(prefix="/api/v1/watchlist", tags=["watchlist"])


def _user_id(payload: dict) -> int:
    email = payload.get("sub")
    user  = users_service.get_user_by_email(email) if email else None
    if not user:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")
    return user["id"]


class WatchlistAdd(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=15)


class AlertCreate(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=15)
    condition: str        # 'above' | 'below'
    target_price: float
    metric: str = "price"  # 'price' | 'rvol'


# ── WATCHLIST ────────────────────────────────────────────────────────────────

@router.get("")
async def list_watchlist(user=Depends(verify_token)):
    return watchlist_service.get_watchlist(_user_id(user))


@router.post("")
async def add_watchlist(body: WatchlistAdd, user=Depends(verify_token)):
    return watchlist_service.add_to_watchlist(_user_id(user), body.ticker)


@router.delete("/{ticker}")
async def remove_watchlist(ticker: str, user=Depends(verify_token)):
    return watchlist_service.remove_from_watchlist(_user_id(user), ticker)


# ── ALERTAS ──────────────────────────────────────────────────────────────────
# Nota de rutas: van antes que /{ticker} arriba a nivel de prefijo distinto
# (/alerts vs raíz), así que no hay colisión de path entre "eliminar ticker
# de watchlist" y "listar/crear alertas".

@router.get("/alerts")
async def list_alerts(user=Depends(verify_token)):
    return watchlist_service.get_alerts(_user_id(user))


@router.post("/alerts")
async def add_alert(body: AlertCreate, user=Depends(verify_token)):
    return watchlist_service.create_alert(_user_id(user), body.ticker, body.condition, body.target_price, body.metric)


@router.delete("/alerts/triggered")
async def clear_triggered(user=Depends(verify_token)):
    return watchlist_service.clear_triggered_alerts(_user_id(user))


@router.delete("/alerts/{alert_id}")
async def remove_alert(alert_id: int, user=Depends(verify_token)):
    return watchlist_service.delete_alert(_user_id(user), alert_id)


@router.post("/alerts/mark-seen")
async def mark_alerts_seen(user=Depends(verify_token)):
    return watchlist_service.mark_alerts_seen(_user_id(user))


@router.get("/alerts/unseen-count")
async def unseen_count(user=Depends(verify_token)):
    return {"count": watchlist_service.get_unseen_triggered_count(_user_id(user))}