from fastapi import APIRouter, Depends

from auth import usuario_opcional
from services.track_record_service import get_track_record, para_visitante

router = APIRouter(prefix="/api/v1/track-record", tags=["track-record"])


@router.get("/")
async def track_record(usuario=Depends(usuario_opcional)):
    """Registro real de lo que hicieron las señales de la terminal — todas,
    las buenas y las malas. Ver services/track_record_service.py para el
    porqué y para la naturaleza distinta de cada fuente (Algoritmo en vivo
    vs tesis reconstruidas con precios históricos).

    PÚBLICO desde el 14/09/2026, por decisión del usuario: es la prueba de que
    las herramientas funcionan, y una prueba que solo ve quien ya ha pagado no
    convence a nadie. Sigue pasando por el límite de peticiones por IP del
    router (main.py). Lo que se retiene a quien no paga está en
    para_visitante()."""
    data = get_track_record()
    if not data.get("ok"):
        return data
    return para_visitante(data, usuario)
