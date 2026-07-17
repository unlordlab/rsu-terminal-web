from fastapi import APIRouter, Header, HTTPException
from config import settings
from services.academy_review_service import (
    get_pending_reviews, approve_review, reject_review, get_approved_reviews, unapprove_review,
)

# Router SEPARADO y aislado, SIN dependencia `paid` -- misma lección que
# con tesis.py (ver conversación 17/07/2026): si esto se registrara junto
# a rutas que sí exigen sesión de usuario de pago, cualquier admin se
# vería expulsado a la pantalla de login normal en cuanto su sesión de
# usuario caducara, aunque tuviera la clave de admin correcta.
router = APIRouter(prefix="/api/v1/academy-review", tags=["academy-review"])


def _check_admin(x_admin_key: str):
    if not settings.admin_key or x_admin_key != settings.admin_key:
        raise HTTPException(status_code=401, detail="Clave de administrador inválida")


@router.get("/pending")
async def pending_reviews(x_admin_key: str = Header(None)):
    """Bandeja de revisiones/lecciones nuevas de Elia a la espera de
    aprobación — panel de admin, pestaña ACADEMY PENDIENTE."""
    _check_admin(x_admin_key)
    return {"items": get_pending_reviews()}


@router.post("/{review_id}/approve")
async def approve(review_id: int, x_admin_key: str = Header(None)):
    _check_admin(x_admin_key)
    ok = approve_review(review_id, approved_by="admin")
    if not ok:
        raise HTTPException(status_code=404, detail="Revisión no encontrada o ya gestionada")
    return {"ok": True}


@router.post("/{review_id}/reject")
async def reject(review_id: int, x_admin_key: str = Header(None)):
    _check_admin(x_admin_key)
    ok = reject_review(review_id, approved_by="admin")
    if not ok:
        raise HTTPException(status_code=404, detail="Revisión no encontrada o ya gestionada")
    return {"ok": True}


@router.get("/approved")
async def approved(limit: int = 20, x_admin_key: str = Header(None)):
    _check_admin(x_admin_key)
    return {"items": get_approved_reviews(limit=limit)}


@router.post("/{review_id}/unapprove")
async def unapprove(review_id: int, x_admin_key: str = Header(None)):
    _check_admin(x_admin_key)
    ok = unapprove_review(review_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Revisión no encontrada o no estaba aprobada")
    return {"ok": True}