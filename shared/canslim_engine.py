"""
canslim_engine.py -- núcleo técnico puro del scan CAN SLIM (retorno a 12
meses, rating de Acumulación/Distribución A-E), compartido entre
backend/services/canslim_service.py (análisis individual on-demand, y el
scan on-demand que se mantiene vivo aunque ya no sea el camino principal
del frontend) y scripts/canslim_scan.py (scan nocturno vía GitHub
Actions, sesión 32). Extraído sin cambiar la fórmula -- mismo criterio
que shared/rsrw_engine.py (sesión 14).

NO depende de nada de backend/ (fastapi, pydantic) -- scripts/ corre en el
runner de GitHub Actions sin ese entorno instalado.
"""
import math
import pandas as pd


def _safe(val, default=0.0):
    try:
        v = float(val)
        return v if not math.isnan(v) and not math.isinf(v) else default
    except Exception:
        return default


def perf_12m(hist: pd.DataFrame) -> float:
    """Retorno a ~12 meses (252 sesiones) -- misma fórmula en
    analyze_ticker(), el scan on-demand y el scan nocturno, para que el
    percentil de RS Rating compare peras con peras. Ver sesión 23."""
    price = _safe(hist['Close'].iloc[-1])
    return _safe(((price / hist['Close'].iloc[-252]) - 1) * 100) if len(hist) >= 252 else 0.0


def acc_dis_rating(hist: pd.DataFrame) -> str:
    """Rating de Acumulación/Distribución (A-E) sobre los últimos 20 días.

    Usa el multiplicador de flujo de dinero de Chaikin -- ((Close-Low) -
    (High-Close)) / (High-Low) -- que pondera CADA día según dónde cierra
    el precio DENTRO de su propio rango de la sesión (High-Low), no solo
    si cierra por encima o por debajo de la apertura.

    Antes se clasificaba cada día como "volumen alcista" o "volumen
    bajista" solo mirando Close vs Open -- eso clasifica mal los días de
    reversión: un día que abre bajo, cae más durante la sesión, pero
    CIERRA cerca del máximo del día (alguien compró fuerte en la caída,
    acumulación real) se contaba como "bajista" solo por cerrar por
    debajo de la apertura, aunque la acción del precio dentro del día
    dijera lo contrario -- justo los días más informativos para detectar
    acumulación/distribución real. Ver Plan Maestro 3.5, auditoría
    CANSLIM 19-20/07/2026.
    """
    if len(hist) < 20:
        return 'C'
    recent = hist.tail(20)
    rango = recent['High'] - recent['Low']
    # Multiplicador -1 (cierre en el mínimo del día) a +1 (cierre en el
    # máximo). Días sin rango (High==Low, rarísimo con datos reales) se
    # tratan como neutros en vez de dividir por cero.
    multiplicador = ((recent['Close'] - recent['Low']) - (recent['High'] - recent['Close'])) / rango
    multiplicador = multiplicador.replace([float('inf'), float('-inf')], 0).fillna(0)
    flujo_ponderado = (multiplicador * recent['Volume']).sum()
    volumen_total   = recent['Volume'].sum()
    if volumen_total == 0:
        return 'C'
    # flujo_ponderado/volumen_total va de -1 (distribución pura) a +1
    # (acumulación pura) -- reescalado a 0-1 para reutilizar los mismos
    # umbrales de siempre (antes "ratio" era up_vol/total, con el mismo
    # rango 0-1).
    ratio = (flujo_ponderado / volumen_total + 1) / 2
    if ratio >= 0.70: return 'A'
    if ratio >= 0.58: return 'B'
    if ratio >= 0.45: return 'C'
    if ratio >= 0.35: return 'D'
    return 'E'
