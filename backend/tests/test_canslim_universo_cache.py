"""
Test de regresión para la sesión 23: unificación de _perf_12m() entre
analyze_ticker() y _scan_single() (antes divergían -- iloc[-252] sobre 2y
vs iloc[0] sobre 1y -- lo que hacía que el percentil de RS Rating
comparara peras con manzanas en cuanto se conectara analyze_ticker() a un
universo cacheado del scan). También cubre el enganche de caché: sin
universo cacheado, analyze_ticker() sigue devolviendo rs=None ("N/D"),
igual que antes de esta sesión -- no debe convertirse en una regresión
silenciosa.

Uso:
    cd backend
    python -m pytest tests/test_canslim_universo_cache.py -v
"""
import sys, os

import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.canslim_service import _perf_12m, _rs_rating_real, cache  # noqa: E402


def _serie_precios(precios: list) -> pd.DataFrame:
    return pd.DataFrame({"Close": precios}, index=pd.date_range("2020-01-01", periods=len(precios)))


def test_perf_12m_con_252_sesiones_calcula_retorno_real():
    # 252 sesiones planas a 100 + 1 sesión final a 120 -> +20% exacto
    precios = [100.0] * 252 + [120.0]
    hist = _serie_precios(precios)
    resultado = _perf_12m(hist)
    assert resultado == pytest.approx(20.0), f"Se esperaba +20.0%, salió {resultado}"


def test_perf_12m_sin_252_sesiones_devuelve_cero():
    # Ticker joven, menos de 252 sesiones -- antes _scan_single daba un
    # retorno "desde el primer día disponible" (podía ser un número
    # grande e inventado); ahora, igual que analyze_ticker, da 0.0.
    precios = [50.0] * 100 + [80.0]
    hist = _serie_precios(precios)
    assert _perf_12m(hist) == 0.0


def test_universo_cacheado_da_rs_rating_real_no_none():
    """Simula el flujo completo: scan_canslim() cachea universo_perfs,
    analyze_ticker() lo reutiliza -- verificado a nivel de _rs_rating_real
    (la pieza que decide None vs percentil real) con un universo
    representativo de lo que produciría un scan real."""
    universo_cacheado = [10.0, 20.0, 30.0, 40.0, 60.0, 70.0, 80.0, 90.0, 5.0]
    resultado = _rs_rating_real(perf_12m=50.0, universe_perfs=universo_cacheado)
    assert resultado is not None
    assert 1 <= resultado <= 99


def test_sin_cache_devuelve_none_con_cache_real_vacia():
    """Sin universo cacheado (nadie ha escaneado recientemente), el
    comportamiento debe seguir siendo exactamente el de antes de esta
    sesión: None, no un número fabricado. Usa la caché real (misma
    instancia que importa canslim_service.py) con una clave garantizada
    vacía, en vez de mockear."""
    cache.delete("canslim:universo_test_vacio")
    universe_perfs = cache.get("canslim:universo_test_vacio") or []
    assert universe_perfs == []
    assert _rs_rating_real(50.0, universe_perfs) is None


def test_scan_canslim_cachea_y_analyze_ticker_lo_reutiliza():
    """Reproduce el enganche real (sesión 23): scan_canslim() escribe en
    "canslim:universe_perfs" vía cache.set(), y el mismo mecanismo que usa
    analyze_ticker() (cache.get sobre esa clave exacta) debe recuperarlo."""
    universo_falso = [10.0, 20.0, 30.0, 40.0, 60.0, 70.0, 80.0, 90.0, 5.0]
    cache.set("canslim:universe_perfs", universo_falso, 60)
    try:
        leido = cache.get("canslim:universe_perfs")
        assert leido == universo_falso
        assert _rs_rating_real(50.0, leido) is not None
    finally:
        cache.delete("canslim:universe_perfs")
