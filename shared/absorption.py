"""
absorption.py -- detección de "absorción" (rotación/RVOL alto + impacto de
precio bajo, sostenido) compartida entre scripts/scanner_universe.py y
backend/services/turnover_service.py -- ambos calculaban la misma idea
(z-score de turnover/RVOL y de Amihud, normalizados con una media/desviación
móvil de 20 días) con el mismo defecto: la ventana de referencia se
autocontaminaba con el propio día anómalo que intenta detectar -- un pico
de rotación infla la media/std de su propia ventana, reduciendo su z-score
justo cuando debería dispararse. Efecto clásico de medias móviles cortas
sobre eventos raros.

Por eso Scanner tuvo que aflojar el umbral de 0.75 a 0.4 (con 0.75 daba 0
coincidencias en los 487 tickers probados) mientras turnover_service.py se
quedó en 0.75 con la misma ventana contaminada, sin coincidir nunca con
Scanner para el mismo ticker. Ver auditoría Scanner 21/07/2026, hallazgo #1.

Solución: la ventana de referencia (media/std) NO incluye el día evaluado
ni sus vecinos inmediatos -- termina GAP_DAYS antes, así el pico que se
está detectando nunca contamina su propio baseline.

NO depende de nada de backend/ (fastapi, pydantic).
"""
import pandas as pd

GAP_DAYS  = 6     # días excluidos justo antes del día evaluado
WINDOW    = 20    # tamaño de la ventana de referencia
THRESHOLD = 0.75  # umbral en desviaciones estándar -- mismo valor en Scanner y Research, no puede volver a divergir


def rolling_zscore_excluding_recent(series: pd.Series, gap_days: int = GAP_DAYS, window: int = WINDOW) -> pd.Series:
    """Z-score de `series` en cada punto, usando como referencia la media/std
    de una ventana de `window` días que TERMINA `gap_days` antes del propio
    punto evaluado -- así el día (o los días recientes) que se está
    evaluando nunca contamina su propia media/desviación de referencia."""
    baseline = series.shift(gap_days)
    mean = baseline.rolling(window).mean()
    std  = baseline.rolling(window).std()
    return (series - mean) / std
