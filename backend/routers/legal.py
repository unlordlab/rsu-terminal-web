"""
Páginas legales. Público a propósito: quien se está planteando registrarse
tiene que poder leer la política de privacidad ANTES de tener cuenta, así que
este router NO lleva `verify_token` ni entra en `protectedRoutes` del frontend.
"""
from fastapi import APIRouter

from config import settings

router = APIRouter(prefix="/api/v1/legal", tags=["legal"])


@router.get("/titular")
async def titular():
    """Quién responde del servicio. Sale del .env y no del código porque el
    repositorio es público -- ver el comentario en config.py.

    Si falta algún dato se dice `completo: False` y la página lo advierte en
    vez de enseñar un hueco: una política sin responsable identificado no
    sirve, y es mejor que se note a que pase desapercibida."""
    nombre = settings.titular_nombre.strip()
    nif    = settings.titular_nif.strip()
    email  = settings.titular_email.strip()
    return {
        "ok": True,
        "nombre": nombre,
        "nif": nif,
        "email": email,
        "completo": bool(nombre and nif and email),
    }
