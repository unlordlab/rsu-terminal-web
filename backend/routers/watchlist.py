import re
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from auth import verify_token
from services import users_service, watchlist_service

router = APIRouter(prefix="/api/v1/watchlist", tags=["watchlist"])

# Mismo patrón que routers/research.py -- limita el ticker a lo que un
# símbolo real puede contener. Antes solo se validaba longitud, así que un
# ticker con comillas/HTML se guardaba tal cual y se reflejaba sin escapar
# en watchlist.js (onclick/data-ticker) -- esto cierra el vector en origen.
_TICKER_RE = re.compile(r"^[A-Z0-9.\-^=]{1,12}$")


def _validar_ticker(v: str) -> str:
    v = v.strip().upper()
    if not _TICKER_RE.match(v):
        raise ValueError("Ticker inválido")
    return v


def _user_id(payload: dict) -> int:
    uid = users_service.get_user_id(payload)
    if uid is None:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")
    return uid


class WatchlistAdd(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=15)
    lista: Optional[str] = None

    @field_validator("ticker")
    @classmethod
    def _ticker(cls, v):
        return _validar_ticker(v)


class WatchlistEdit(BaseModel):
    """Lo que se puede cambiar de un ticker ya seguido. Los dos campos son
    opcionales y se aplican solo si vienen: así el mismo endpoint sirve para
    guardar la nota, para mover de lista, o para las dos cosas."""
    nota:  Optional[str] = Field(None, max_length=watchlist_service.MAX_NOTA)
    lista: Optional[str] = Field(None, max_length=watchlist_service.LARGO_LISTA)


class ListaRename(BaseModel):
    nuevo: str = Field(..., min_length=1, max_length=watchlist_service.LARGO_LISTA)


class AlertCreate(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=15)
    condition: str = "above"       # 'above' | 'below' — ignorado si metric='ema_touch'/'senal'
    target_price: float = 0        # ignorado si metric='ema_touch'/'senal'
    metric: str = "price"          # 'price' | 'rvol' | 'ema_touch' | 'senal'
    ema_period: Optional[int] = None   # 10 | 20 | 50 | 200 — obligatorio si metric='ema_touch'
    senal: Optional[str] = Field(None, max_length=32)   # obligatorio si metric='senal'

    @field_validator("ticker")
    @classmethod
    def _ticker(cls, v):
        return _validar_ticker(v)


# ── WATCHLIST ────────────────────────────────────────────────────────────────

@router.get("")
async def list_watchlist(user=Depends(verify_token)):
    return watchlist_service.get_watchlist(_user_id(user))


@router.post("")
async def add_watchlist(body: WatchlistAdd, user=Depends(verify_token)):
    return watchlist_service.add_to_watchlist(_user_id(user), body.ticker, body.lista)


@router.put("/listas/{nombre}")
async def renombrar_lista(nombre: str, body: ListaRename, user=Depends(verify_token)):
    """Va ANTES que /{ticker} a propósito: FastAPI resuelve por orden y
    `listas` encajaría en el patrón del ticker."""
    return watchlist_service.renombrar_lista(_user_id(user), nombre, body.nuevo)


@router.put("/{ticker}")
async def editar_watchlist(ticker: str, body: WatchlistEdit, user=Depends(verify_token)):
    uid = _user_id(user)
    ticker = _validar_ticker(ticker)
    r = {"ok": True}
    if body.lista is not None:
        r = watchlist_service.mover_a_lista(uid, ticker, body.lista)
        if not r.get("ok"):
            return r
    if body.nota is not None:
        r = watchlist_service.set_nota(uid, ticker, body.nota)
    return r


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
    return watchlist_service.create_alert(_user_id(user), body.ticker, body.condition,
                                          body.target_price, body.metric, body.ema_period,
                                          body.senal)


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