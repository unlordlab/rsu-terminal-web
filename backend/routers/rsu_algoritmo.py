from fastapi import APIRouter, Depends, Query
from auth import verify_token
from services.rsu_algoritmo_service import get_rsu_algoritmo, get_rsu_algoritmo_backtest

router = APIRouter(prefix="/api/v1/algoritmo", tags=["algoritmo"])

@router.get("/")
async def algoritmo(user=Depends(verify_token)):
    return get_rsu_algoritmo()

@router.get("/backtest")
async def algoritmo_backtest(years: int = Query(10, ge=2, le=20), user=Depends(verify_token)):
    return get_rsu_algoritmo_backtest(years=years)

@router.get("/candidatos")
async def algoritmo_candidatos(user=Depends(verify_token)):
    """El puente "cuándo → qué": en qué mirar cuando el semáforo se ponga
    verde. Se sirve siempre, no solo en VERDE — verlos en ÁMBAR es lo que
    permite tener la decisión tomada de antemano."""
    from services.algoritmo_candidatos_service import get_candidatos_algoritmo
    return get_candidatos_algoritmo()


@router.get("/historial-real")
async def algoritmo_historial_real(user=Depends(verify_token)):
    """
    Historial en vivo — distinto del backtest histórico: son señales reales
    disparadas desde que este tracking se activó, con su resultado real
    (según haya pasado suficiente tiempo), no un recálculo retrospectivo.
    Empieza vacío y se va llenando solo con el tiempo.
    """
    from services.algoritmo_tracking_service import obtener_historial_cambios, obtener_senales_tracked
    return {
        "ok": True,
        "cambios_semaforo": obtener_historial_cambios(limit=30),
        "senales": obtener_senales_tracked(limit=100),
    }