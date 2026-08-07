"""
Test de regresión del volumen relativo de Reddit Pulse (hallazgo #27 de la
auditoría de Market, 07/08/2026).

Ese cálculo existía desde siempre en el backend pero no se pintaba en ningún
sitio, y arrastraba los dos mismos defectos que ya se habían corregido en las
alertas de Watchlist (hallazgo #3 de su auditoría):

- El día de hoy entraba en su propio promedio, lo que acerca el cociente a 1
  y disimula justo los días anómalos que se quieren detectar.
- Con el mercado abierto se comparaba un día PARCIAL contra promedios de días
  COMPLETOS, así que el ratio salía bajo por construcción (a las 10:00 de
  Nueva York solo ha transcurrido un 8% de la sesión).

Uso:
    cd backend
    python -m pytest tests/test_reddit_vol_ratio.py -v
"""
import sys, os
from unittest.mock import patch

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.market_service import _vol_ratio_desde_serie  # noqa: E402


def test_el_promedio_excluye_el_dia_de_hoy():
    # 9 sesiones de 100 y un hoy de 500. Excluyendo hoy, el promedio es 100
    # exacto y el ratio es 5.0. Si hoy entrara en su propio promedio, el
    # promedio subiría a 140 y el ratio bajaría a 3.57 -- la versión anterior.
    serie = pd.Series([100.0] * 9 + [500.0])
    with patch('services.market_service.session_fraction_elapsed', return_value=None):
        assert _vol_ratio_desde_serie(serie) == 5.0


def test_con_el_mercado_abierto_se_escala_por_la_fraccion_de_sesion():
    # A media sesión (frac=0.5), un volumen igual al promedio de días
    # completos ya es el doble del ritmo normal: va camino de doblarlo al
    # cierre. Sin escalar saldría 1.0 y parecería un día corriente.
    serie = pd.Series([100.0] * 9 + [100.0])
    with patch('services.market_service.session_fraction_elapsed', return_value=0.5):
        assert _vol_ratio_desde_serie(serie) == 2.0
    with patch('services.market_service.session_fraction_elapsed', return_value=None):
        assert _vol_ratio_desde_serie(serie) == 1.0


def test_sin_datos_suficientes_devuelve_none_no_un_uno():
    # Un 1.0 se leería como "volumen normal"; la ausencia se admite como tal
    # y el frontend pinta un guion. Mismo criterio que el resto del proyecto.
    with patch('services.market_service.session_fraction_elapsed', return_value=None):
        assert _vol_ratio_desde_serie(None) is None
        assert _vol_ratio_desde_serie(pd.Series([100.0, 200.0])) is None          # menos de 3 puntos
        assert _vol_ratio_desde_serie(pd.Series([0.0, 0.0, 0.0, 0.0])) is None    # promedio 0
        assert _vol_ratio_desde_serie(pd.Series([100.0, 100.0, 100.0, 0.0])) is None  # hoy sin volumen
