from fastapi import APIRouter, Depends, Query, HTTPException, Response
from pydantic import BaseModel
from auth import verify_token, verify_admin_key
from services.tesis_service import (
    get_tesis_list, get_tesis_detail, get_pending_tesis, get_tesis_by_id,
    approve_tesis, reject_tesis, create_tesis, get_approved_tesis, unpublish_tesis,
    generar_pdf_tesis,
)

router = APIRouter(prefix="/api/v1/tesis", tags=["tesis"])

# Router de administración SEPARADO — no debe llevar la dependencia `paid`
# (sesión de usuario de pago) que main.py aplica a `router` al registrarlo.
# Solo depende de X-Admin-Key, igual que los endpoints /admin/* de auth.py
# y analytics.py. Ver conversación 17/07/2026: al estar en el mismo router
# que las rutas públicas, heredaba `paid` y expulsaba al admin a la
# pantalla de login normal en cuanto caducaba su sesión de usuario, aunque
# tuviera la clave de admin correcta.
#
# La comprobación de la clave ya no vive aquí -- deduplicada en
# auth.verify_admin_key (Fase 2.4 del Plan Maestro, 20/07/2026).
admin_router = APIRouter(prefix="/api/v1/tesis/admin", tags=["tesis-admin"])


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


@router.get("/id/{tesis_id}/pdf")
async def tesis_pdf(tesis_id: int, user=Depends(verify_token)):
    """Descarga en PDF de una tesis ya aprobada y publicada -- ver
    conversación 18/07/2026. Ruta bajo /id/ para no chocar con /{ticker}."""
    t = get_tesis_by_id(tesis_id)
    if not t or t.get("status") != "approved":
        raise HTTPException(status_code=404, detail="Tesis no encontrada")
    try:
        pdf_bytes = generar_pdf_tesis(t)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"No se pudo generar el PDF: {e}")
    filename = f"RSU_{t['ticker']}_{t.get('fecha', '')}.pdf".replace(" ", "_")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


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
async def admin_pending_tesis(_admin: None = Depends(verify_admin_key)):
    """Bandeja de tesis a la espera de revisión — panel de admin,
    pestaña TESIS PENDIENTES."""
    return {"items": get_pending_tesis()}


@admin_router.get("/approved")
async def admin_approved_tesis(limit: int = 20, _admin: None = Depends(verify_admin_key)):
    """Últimas tesis aprobadas, para poder retirarlas si hace falta."""
    return {"items": get_approved_tesis(limit=limit)}


@admin_router.post("/{tesis_id}/unpublish")
async def admin_unpublish_tesis(tesis_id: int, _admin: None = Depends(verify_admin_key)):
    """Retira una tesis ya aprobada -- vuelve a pendiente, desaparece de
    la sección pública al instante."""
    ok = unpublish_tesis(tesis_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Tesis no encontrada o no estaba aprobada")
    return {"ok": True}


@admin_router.post("/{tesis_id}/approve")
async def admin_approve_tesis(tesis_id: int, _admin: None = Depends(verify_admin_key)):
    ok = approve_tesis(tesis_id, approved_by="admin")
    if not ok:
        raise HTTPException(status_code=404, detail="Tesis no encontrada o ya revisada")
    return {"ok": True}


@admin_router.post("/{tesis_id}/reject")
async def admin_reject_tesis(tesis_id: int, _admin: None = Depends(verify_admin_key)):
    ok = reject_tesis(tesis_id, approved_by="admin")
    if not ok:
        raise HTTPException(status_code=404, detail="Tesis no encontrada o ya revisada")
    return {"ok": True}


@admin_router.get("/{tesis_id}")
async def admin_get_tesis(tesis_id: int, _admin: None = Depends(verify_admin_key)):
    t = get_tesis_by_id(tesis_id)
    if not t:
        raise HTTPException(status_code=404, detail="Tesis no encontrada")
    return t


@admin_router.post("/create")
async def admin_create_tesis(req: CreateTesisRequest, _admin: None = Depends(verify_admin_key)):
    """Creación manual — sustituye al flujo antiguo de añadir una fila al
    Google Sheet. Por defecto queda 'pending' igual que las del agente,
    salvo que se indique status='approved' explícitamente."""
    try:
        new_id = create_tesis(
            ticker=req.ticker, contenido=req.contenido, rating=req.rating,
            titulo=req.titulo, nombre=req.nombre, sector=req.sector, autor=req.autor,
            resumen=req.resumen, imagen=req.imagen, riesgo=req.riesgo,
            precio_objetivo=req.precio_objetivo, fuente="manual", status=req.status
        )
    except ValueError as e:
        # Estado o rating fuera de los valores conocidos. Se devuelve 400 con
        # el motivo en vez de dejar que salga un 500: quien se equivoca aquí
        # está escribiendo a mano y necesita saber qué valor esperaba el
        # sistema. Ver ESTADOS_VALIDOS en tesis_service.
        raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True, "id": new_id}