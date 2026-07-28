from fastapi import APIRouter, Depends

from auth import verify_token
from services.track_record_service import get_track_record

router = APIRouter(prefix="/api/v1/track-record", tags=["track-record"])


@router.get("/")
async def track_record(user=Depends(verify_token)):
    """Registro real de lo que hicieron las señales de la terminal — todas,
    las buenas y las malas. Ver services/track_record_service.py para el
    porqué y para la naturaleza distinta de cada fuente (Algoritmo en vivo
    vs tesis reconstruidas con precios históricos)."""
    return get_track_record()
