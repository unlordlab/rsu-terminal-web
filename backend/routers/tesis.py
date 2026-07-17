from fastapi import APIRouter, Depends, Query, Header, HTTPException
from pydantic import BaseModel
from auth import verify_token
from config import settings
from services.tesis_service import (
    get_tesis_list, get_tesis_detail, get_pending_tesis, get_tesis_by_id,
    approve_tesis, reject_tesis, create_tesis, get_approved_tesis, unpublish_tesis,
)

router = APIRouter(prefix="/api/v1/tesis", tags=["tesis"])

# Router de administración SEPARADO — no debe llevar la dependencia `paid`
# (sesión de usuario de pago) que main.py aplica a `router` al registrarlo.
# Solo depende de X-Admin-Key, igual que los endpoints /admin/* de auth.py
# y analytics.py. Ver conversación 17/07/2026: al estar en el mismo router
# que las rutas públicas, heredaba `paid` y expulsaba al admin a la
# pantalla de login normal en cuanto caducaba su sesión de usuario, aunque
# tuviera la clave de admin correcta.
admin_router = APIRouter(prefix="/api/v1/tesis/admin", tags=["tesis-admin"])


def _check_admin(x_admin_key: str):
    if not settings.admin_key or x_admin_key != settings.admin_key:
        raise HTTPException(status_code=401, detail="Clave de administrador inválida")


# ── Público (requiere sesión de usuario normal) ─────────────────────────

@router.get("/")
async def tesis_list(
    search:   str = Query(""),
    rating:   str = Query(""),
    page:     int = Query(1, ge=1),
    per_page: int = Query(9, ge=1, le=30),
    user=Depends(verify_token)
):
    return get_tesis_list(search=search, rating=rating, page=page, per_page=per_page)


@router.get("/{ticker}")
async def tesis_detail(
    ticker: str,
    fecha:  str = Query(""),
    user=Depends(verify_token)
):
    return get_tesis_detail(ticker=ticker, fecha=fecha)


# ── Administración (X-Admin-Key) ────────────────────────────────────────

class CreateTesisRequest(BaseModel):
    ticker: str
    contenido: str
    rating: str = "HOLD"
    titulo: str = ""
    nombre: str = ""
    sector: str = ""
    autor: str = ""
    resumen: str = ""
    imagen: str = ""
    riesgo: str = ""
    precio_objetivo: float | None = None
    status: str = "pending"  # permite crear ya aprobada si se escribe a mano


@admin_router.get("/pending")
async def admin_pending_tesis(x_admin_key: str = Header(None)):
    """Bandeja de tesis a la espera de revisión — panel de admin,
    pestaña TESIS PENDIENTES."""
    _check_admin(x_admin_key)
    return {"items": get_pending_tesis()}


@admin_router.get("/approved")
async def admin_approved_tesis(limit: int = 20, x_admin_key: str = Header(None)):
    """Últimas tesis aprobadas, para poder retirarlas si hace falta."""
    _check_admin(x_admin_key)
    return {"items": get_approved_tesis(limit=limit)}


@admin_router.post("/{tesis_id}/unpublish")
async def admin_unpublish_tesis(tesis_id: int, x_admin_key: str = Header(None)):
    """Retira una tesis ya aprobada -- vuelve a pendiente, desaparece de
    la sección pública al instante."""
    _check_admin(x_admin_key)
    ok = unpublish_tesis(tesis_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Tesis no encontrada o no estaba aprobada")
    return {"ok": True}


@admin_router.post("/{tesis_id}/approve")
async def admin_approve_tesis(tesis_id: int, x_admin_key: str = Header(None)):
    _check_admin(x_admin_key)
    ok = approve_tesis(tesis_id, approved_by="admin")
    if not ok:
        raise HTTPException(status_code=404, detail="Tesis no encontrada o ya revisada")
    return {"ok": True}


@admin_router.post("/{tesis_id}/reject")
async def admin_reject_tesis(tesis_id: int, x_admin_key: str = Header(None)):
    _check_admin(x_admin_key)
    ok = reject_tesis(tesis_id, approved_by="admin")
    if not ok:
        raise HTTPException(status_code=404, detail="Tesis no encontrada o ya revisada")
    return {"ok": True}


@admin_router.get("/{tesis_id}")
async def admin_get_tesis(tesis_id: int, x_admin_key: str = Header(None)):
    _check_admin(x_admin_key)
    t = get_tesis_by_id(tesis_id)
    if not t:
        raise HTTPException(status_code=404, detail="Tesis no encontrada")
    return t


@admin_router.post("/create")
async def admin_create_tesis(req: CreateTesisRequest, x_admin_key: str = Header(None)):
    """Creación manual — sustituye al flujo antiguo de añadir una fila al
    Google Sheet. Por defecto queda 'pending' igual que las del agente,
    salvo que se indique status='approved' explícitamente."""
    _check_admin(x_admin_key)
    new_id = create_tesis(
        ticker=req.ticker, contenido=req.contenido, rating=req.rating,
        titulo=req.titulo, nombre=req.nombre, sector=req.sector, autor=req.autor,
        resumen=req.resumen, imagen=req.imagen, riesgo=req.riesgo,
        precio_objetivo=req.precio_objetivo, fuente="manual", status=req.status
    )
    return {"ok": True, "id": new_id}