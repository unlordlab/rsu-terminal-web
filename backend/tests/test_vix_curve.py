"""
Test de la forma de la curva VIX/VIX3M (shared/vix_curve.py, hallazgo #32 de
la auditoría de Market, 07/08/2026).

Estos umbrales gobiernan dos cosas a la vez: lo que el RSU Algoritmo PUNTÚA
(+7 en backwardation, +3 con la curva tensa) y lo que el widget del VIX
ENSEÑA. Antes vivían clavados como literales dentro del scoring del
Algoritmo; al sacarlos a shared/ hay que fijar que los bordes se comportan
exactamente igual que las comparaciones originales (`> 1.0`, `> 0.95`), o el
Algoritmo cambiaría de puntuación sin que nadie lo pidiera.

Uso:
    cd backend
    python -m pytest tests/test_vix_curve.py -v
"""
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'shared'))

from vix_curve import (  # noqa: E402
    vix_ratio, zona_curva, UMBRAL_BACKWARDATION, UMBRAL_TENSION,
)


def test_los_umbrales_son_los_mismos_numeros_que_estaban_en_el_scoring():
    # Si alguien los recalibra, que sea a propósito: el Algoritmo puntúa con
    # ellos y cambiarlos mueve el score de todos los días del backtest.
    assert UMBRAL_BACKWARDATION == 1.0
    assert UMBRAL_TENSION == 0.95


def test_los_bordes_se_comportan_como_las_comparaciones_originales():
    # El scoring usaba `> 1.0` y `> 0.95`, no `>=`: justo EN el umbral cae al
    # tramo de abajo. Fijarlo evita que un refactor futuro lo convierta en
    # `>=` y regale 7 puntos un día que la curva está exactamente plana.
    assert zona_curva(1.001) == "backwardation"
    assert zona_curva(1.0) == "tensa"
    assert zona_curva(0.951) == "tensa"
    assert zona_curva(0.95) == "normal"
    assert zona_curva(0.80) == "normal"


def test_sin_las_dos_patas_no_hay_ratio_ni_zona():
    # Ni un 1.0 por defecto, que se leería como "curva plana" real.
    assert vix_ratio(14.9, None) is None
    assert vix_ratio(None, 18.7) is None
    assert vix_ratio(14.9, 0) is None       # denominador no positivo
    assert vix_ratio(14.9, -3) is None
    assert vix_ratio("no soy un numero", 18.7) is None
    assert zona_curva(None) is None


def test_el_ratio_es_spot_entre_tres_meses_no_al_reves():
    # Invertirlo daría la lectura contraria en cada zona.
    assert vix_ratio(20.0, 16.0) == 1.25
    assert zona_curva(vix_ratio(20.0, 16.0)) == "backwardation"
    assert vix_ratio(16.0, 20.0) == 0.8
    assert zona_curva(vix_ratio(16.0, 20.0)) == "normal"
