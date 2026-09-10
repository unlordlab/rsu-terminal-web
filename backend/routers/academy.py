from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator

from auth import verify_token
from services import academy_service, users_service

router = APIRouter(prefix="/api/v1/academy", tags=["academy"])


def _user_id(payload: dict) -> int:
    uid = users_service.get_user_id(payload)
    if uid is None:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")
    return uid


class LeccionCompletada(BaseModel):
    lesson_key: str = Field(..., min_length=3, max_length=12)

    @field_validator("lesson_key")
    @classmethod
    def _validar(cls, v):
        v = v.strip()
        if not academy_service.es_lesson_key_valida(v):
            raise ValueError("Clave de lección inválida")
        return v


class QuizCompletado(BaseModel):
    module_id: int = Field(..., ge=0, le=999)
    score: int = Field(..., ge=0, le=999)
    total: int = Field(..., ge=1, le=999)

    @field_validator("total")
    @classmethod
    def _coherente(cls, total, info):
        score = info.data.get("score")
        if score is not None and score > total:
            raise ValueError("score no puede superar a total")
        return total


@router.get("/progress")
async def progreso(user=Depends(verify_token)):
    return academy_service.obtener_progreso(_user_id(user))


@router.post("/progress/lesson")
async def completar_leccion(req: LeccionCompletada, user=Depends(verify_token)):
    return academy_service.marcar_leccion(_user_id(user), req.lesson_key)


@router.post("/progress/quiz")
async def completar_quiz(req: QuizCompletado, user=Depends(verify_token)):
    return academy_service.marcar_quiz(_user_id(user), req.module_id, req.score, req.total)


@router.delete("/progress")
async def reiniciar(user=Depends(verify_token)):
    return academy_service.reiniciar_progreso(_user_id(user))


# ── Certificado de finalización (Páginas Contenido #23) ──────────────────────
# Reiniciar el progreso NO borra un certificado ya emitido: certifica lo que se
# completó, y no caduca.

class PedirCertificado(BaseModel):
    nombre: str = Field(..., max_length=120)


@router.get("/certificado")
async def estado_certificado(user=Depends(verify_token)):
    return academy_service.estado_certificado(_user_id(user))


@router.post("/certificado")
async def pedir_certificado(req: PedirCertificado, user=Depends(verify_token)):
    return academy_service.emitir_certificado(_user_id(user), req.nombre)


@router.get("/certificado/pdf")
async def certificado_pdf(user=Depends(verify_token)):
    from fastapi.responses import Response
    pdf, cert = academy_service.pdf_certificado(_user_id(user))
    if pdf is None:
        raise HTTPException(status_code=404, detail="Todavía no tienes certificado")
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition":
                             f'attachment; filename="RSU_Academy_{cert["codigo"]}.pdf"'})
