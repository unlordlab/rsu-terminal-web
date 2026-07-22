"""
rsrw_engine.py -- núcleo matemático del cálculo de Relative Strength (RS)
compartido entre backend/services/rsrw_service.py, scripts/rsrw_scan.py,
scripts/scanner_universe.py y scripts/thematic_scan.py. La fórmula core
(_rs_smooth, PERIODS, WEIGHTS, EMA_SMOOTH) ya era idéntica carácter por
carácter en los 4 sitios (verificado 22/07/2026), pero dos capas
alrededor habían divergido en silencio: el método de percentil (rsrw_scan.py
hacía un ranking manual por posición, distinto al pandas rank(pct=True)
de los otros 3 en cuanto hay empates) y rs_momentum (el fix de normalizar
por día solo había llegado a rsrw_scan.py). Unificado aquí para que no
puedan volver a divergir sin que nadie se dé cuenta -- mismo criterio que
weinstein_phases.py y time_utils.py.

IMPORTANTE: no depende de nada de backend/ (fastapi, pydantic) -- scripts/
corre en el runner de GitHub Actions sin ese entorno instalado.
"""
import numpy as np
import pandas as pd

PERIODS    = [21, 63, 126]
WEIGHTS    = {21: 0.20, 63: 0.35, 126: 0.45}
EMA_SMOOTH = 10
TREND_WIN  = 21

# SECTOR_ETFS/GICS_MAP -- promovidos aquí en la sesión 19 (dedup de
# universos S&P500): estaban duplicados carácter por carácter en
# scripts/rsrw_scan.py y backend/services/rsrw_service.py. NO confundir
# con SECTOR_ETFS/SECTOR_ETFS_BREADTH de backend/services/market_service.py,
# que tienen estructura y uso distintos (heatmap sectorial / amplitud), no
# son el mismo duplicado.
SECTOR_ETFS = {
    "Tecnología": "XLK", "Salud": "XLV", "Financieros": "XLF",
    "Consumo Discrecional": "XLY", "Consumo Básico": "XLP", "Industriales": "XLI",
    "Energía": "XLE", "Materiales": "XLB", "Servicios Públicos": "XLU",
    "Bienes Raíces": "XLRE", "Comunicaciones": "XLC",
}

GICS_MAP = {
    "Information Technology": "Tecnología", "Health Care": "Salud",
    "Financials": "Financieros", "Consumer Discretionary": "Consumo Discrecional",
    "Consumer Staples": "Consumo Básico", "Industrials": "Industriales",
    "Energy": "Energía", "Materials": "Materiales", "Utilities": "Servicios Públicos",
    "Real Estate": "Bienes Raíces", "Communication Services": "Comunicaciones",
}


def rs_smooth(prices: pd.Series, benchmark: pd.Series, period: int) -> pd.Series:
    """Diferencial de retorno vs benchmark, suavizado con EMA."""
    rs = prices.pct_change(period) - benchmark.pct_change(period)
    return rs.ewm(span=EMA_SMOOTH, min_periods=3).mean()


def rs_trend_slope(rs_series: pd.Series) -> float:
    """Pendiente normalizada de la RS -- numpy puro, sin scipy."""
    recent = rs_series.dropna().iloc[-TREND_WIN:]
    if len(recent) < 5:
        return 0.0
    x     = np.arange(len(recent), dtype=float)
    slope = float(np.polyfit(x, recent.values, 1)[0])
    std   = float(recent.std())
    return round(slope / std if std > 0 else 0.0, 4)


def rs_percentile(scores: pd.Series) -> pd.Series:
    """Percentil dentro del universo -- rank(pct=True) promedia rangos
    empatados (a diferencia del ranking manual por posición que tenía
    antes rsrw_scan.py, que no trataba los empates igual)."""
    return scores.rank(pct=True).mul(100).round(1)


def rs_momentum(rs_21d: float, rs_63d: float) -> int:
    """¿El ritmo de outperformance RECIENTE es más rápido que el de medio
    plazo? Compara diferenciales normalizados por nº de días -- comparar
    rs_21d > rs_63d en crudo sesga hacia "63d gana" solo por acumular más
    tiempo, no por aceleración real. Ver Plan Maestro 3.3, auditoría RS/RW
    19-20/07/2026 (el fix original, que solo había llegado a
    scripts/rsrw_scan.py)."""
    ritmo_21d = rs_21d / 21
    ritmo_63d = rs_63d / 63
    return 1 if ritmo_21d > ritmo_63d else 0
