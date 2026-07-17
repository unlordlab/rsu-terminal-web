from fastapi import APIRouter, Depends, Query, Header, HTTPException
from pydantic import BaseModel
from auth import verify_token
from config import settings
from services.tesis_service import (
    get_tesis_list, get_tesis_detail, get_pending_tesis, get_tesis_by_id,
    approve_tesis, reject_tesis, create_tesis,
)

router = APIRouter(prefix="/api/v1/tesis", tags=["tesis"])


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


@router.get("/admin/pending")
async def admin_pending_tesis(x_admin_key: str = Header(None)):
    """Bandeja de tesis a la espera de revisión — panel de admin,
    pestaña TESIS PENDIENTES."""
    _check_admin(x_admin_key)
    return {"items": get_pending_tesis()}


@router.post("/admin/{tesis_id}/approve")
async def admin_approve_tesis(tesis_id: int, x_admin_key: str = Header(None)):
    _check_admin(x_admin_key)
    ok = approve_tesis(tesis_id, approved_by="admin")
    if not ok:
        raise HTTPException(status_code=404, detail="Tesis no encontrada o ya revisada")
    return {"ok": True}


@router.post("/admin/{tesis_id}/reject")
async def admin_reject_tesis(tesis_id: int, x_admin_key: str = Header(None)):
    _check_admin(x_admin_key)
    ok = reject_tesis(tesis_id, approved_by="admin")
    if not ok:
        raise HTTPException(status_code=404, detail="Tesis no encontrada o ya revisada")
    return {"ok": True}


@router.get("/admin/{tesis_id}")
async def admin_get_tesis(tesis_id: int, x_admin_key: str = Header(None)):
    _check_admin(x_admin_key)
    t = get_tesis_by_id(tesis_id)
    if not t:
        raise HTTPException(status_code=404, detail="Tesis no encontrada")
    return t


@router.post("/admin/create")
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