"""
Test del Indicador RSU de flujo de dinero (shared/rsu_flow.py).

Fija las dos propiedades que lo distinguen del indicador en el que se inspira
y que son fáciles de romper en un refactor: que el VOLUMEN pesa de verdad (sin
él sería otra medida de precio) y que la salida es un percentil acotado 0-100
del propio valor, no una magnitud suelta.

Uso:
    cd backend
    python -m pytest tests/test_rsu_flow.py -v
"""
import sys, os

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'shared'))

from rsu_flow import calcular_flujo, zona, VENTANA_PCT, MIN_PCT  # noqa: E402


def _serie(n=400, cierre_en="medio", volumen=1_000_000):
    """Sesiones sintéticas con el cierre siempre en el mismo sitio del rango."""
    high = np.full(n, 110.0)
    low = np.full(n, 90.0)
    if cierre_en == "maximos":
        close = np.full(n, 110.0)
    elif cierre_en == "minimos":
        close = np.full(n, 90.0)
    else:
        close = np.full(n, 100.0)
    return pd.DataFrame({
        "High": high, "Low": low, "Close": close,
        "Volume": np.full(n, float(volumen)),
    }, index=pd.date_range("2024-01-01", periods=n, freq="B"))


def test_la_salida_es_un_percentil_acotado_entre_0_y_100():
    rng = np.random.default_rng(7)
    n = 500
    close = 100 + np.cumsum(rng.normal(0, 1, n))
    df = pd.DataFrame({
        "High": close + 2, "Low": close - 2, "Close": close,
        "Volume": rng.integers(500_000, 2_000_000, n).astype(float),
    }, index=pd.date_range("2024-01-01", periods=n, freq="B"))
    f = calcular_flujo(df).dropna()
    assert len(f) > 0
    assert f.min() >= 0 and f.max() <= 100


def test_sin_historia_suficiente_no_se_inventa_un_valor():
    # Por debajo del mínimo para situar el dato, todo NaN: no hay con qué
    # comparar, y un 50 por defecto se leería como "ritmo normal" medido.
    f = calcular_flujo(_serie(n=MIN_PCT - 10))
    assert f.isna().all()


def test_el_volumen_cambia_el_resultado_no_es_solo_precio():
    """Dos series con EXACTAMENTE el mismo precio y distinto reparto de
    volumen tienen que dar flujos distintos. Si no, el volumen no está
    pesando y el indicador sería otra medida de precio -- justo lo que se le
    critica al indicador original."""
    rng = np.random.default_rng(11)
    n = 400
    close = 100 + np.cumsum(rng.normal(0, 1, n))
    # El cierre tiene que caer en sitios DISTINTOS de su rango en cada sesión.
    # Con High=close+2 y Low=close-2 el cierre queda siempre en el centro
    # exacto, la presión es 0 todos los días y el volumen no puede cambiar
    # nada -- el primer intento de este test caía justo en esa trampa.
    pos = rng.uniform(0.05, 0.95, n)          # dónde cierra dentro del rango
    low = close - 4 * pos
    high = low + 4
    base = {"High": high, "Low": low, "Close": close}
    idx = pd.date_range("2024-01-01", periods=n, freq="B")

    vol_plano = pd.DataFrame({**base, "Volume": np.full(n, 1_000_000.0)}, index=idx)
    # Mismo precio, pero el volumen se concentra en las sesiones alcistas
    subidas = np.r_[False, np.diff(close) > 0]
    vol_sesgado = pd.DataFrame(
        {**base, "Volume": np.where(subidas, 3_000_000.0, 300_000.0)}, index=idx)

    a = calcular_flujo(vol_plano).dropna()
    b = calcular_flujo(vol_sesgado).dropna()
    assert not np.allclose(a.values, b.values), (
        "El volumen no está afectando al resultado: con el mismo precio y "
        "distinto volumen el flujo sale idéntico."
    )


def test_las_zonas_cortan_en_20_y_80():
    assert zona(95) == "entrando"
    assert zona(80) == "entrando"
    assert zona(79.9) == "neutro"
    assert zona(50) == "neutro"
    assert zona(20.1) == "neutro"
    assert zona(20) == "saliendo"
    assert zona(0) == "saliendo"
    assert zona(None) is None
