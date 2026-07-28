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
