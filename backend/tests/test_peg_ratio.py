"""
El PEG no puede contar el crecimiento dos veces.

Hallazgo del 29/07/2026, revisando ANET a mano en la terminal: el PEG se
calculaba como `forwardPE / earningsGrowth`, y eso rompía dos reglas a la vez.

  1. Un P/E FORWARD ya descuenta el crecimiento -- es más bajo precisamente
     porque anticipa que el beneficio va a subir. Volver a dividirlo por el
     crecimiento lo cuenta dos veces, así que el PEG sale sistemáticamente
     bajo.
  2. `earningsGrowth` de Yahoo es el crecimiento del último trimestre
     interanual: un dato TRAILING. Emparejarlo con un P/E forward mezcla dos
     horizontes distintos.

Medido sobre una muestra del S&P 500: el 67% de los tickers salían por debajo
del PEG de Yahoo, con un ratio mediano de 0,54 -- la mitad. Y el filtro de
sanidad de entonces (0 < v <= 15) solo cazaba los altos, así que artefactos
como MLM (0,02 frente a 2,79 real) o IRM (0,05 frente a 2,70) se mostraban
tal cual. Un PEG de 0,02 en pantalla grita "chollo".

No es un decimal: en ANET daba 1,52 ("valoración razonable, PEG < 2") cuando
el real ronda 2,2 ("cara"). Cambia la lectura cualitativa.

Uso:
    cd backend
    python -m pytest tests/test_peg_ratio.py -v
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.research_service import calcular_peg  # noqa: E402


# Datos reales de ANET tomados el 29/07/2026 (precio 169,71).
ANET_TRAILING_PEG = 2.1778
ANET_PEG          = 2.18
ANET_TRAILING_PE  = 58.723183
ANET_FORWARD_PE   = 37.987774
ANET_GROWTH       = 0.25


def test_se_prefiere_el_peg_de_yahoo_que_es_el_contrastable():
    """Yahoo lo calcula con crecimiento esperado a largo plazo -- la
    definición de manual, y la que cuadra con Yahoo web o GuruFocus."""
    assert calcular_peg(ANET_TRAILING_PEG, ANET_PEG, ANET_TRAILING_PE, ANET_GROWTH) == ANET_TRAILING_PEG


def test_anet_no_vuelve_a_salir_como_valoracion_razonable():
    """El caso que destapó el fallo: 1,52 transmite 'razonable', 2,2 'cara'."""
    peg = calcular_peg(ANET_TRAILING_PEG, ANET_PEG, ANET_TRAILING_PE, ANET_GROWTH)
    formula_vieja = ANET_FORWARD_PE / (ANET_GROWTH * 100)
    assert round(formula_vieja, 2) == 1.52, "Se reproduce la fórmula anterior para el contraste"
    assert peg > 2, f"El PEG de ANET debe quedar por encima de 2, salió {peg}"


def test_sin_dato_de_yahoo_se_calcula_con_horizontes_COHERENTES():
    """Numerador y denominador del mismo horizonte: P/E trailing con
    crecimiento trailing. Nunca el P/E forward, que ya lleva el crecimiento
    dentro."""
    peg = calcular_peg(None, None, ANET_TRAILING_PE, ANET_GROWTH)
    esperado = ANET_TRAILING_PE / (ANET_GROWTH * 100)   # 2.35
    assert peg == esperado
    assert peg > ANET_FORWARD_PE / (ANET_GROWTH * 100), (
        "El cálculo propio no puede volver a dar un valor tan bajo como la "
        "fórmula que mezclaba forward con trailing."
    )


def test_un_peg_absurdamente_bajo_no_se_muestra_como_chollo():
    """Casos MLM (0,02) e IRM (0,05): crecimiento interanual disparado desde
    una base hundida. El filtro anterior (0 < v <= 15) los dejaba pasar."""
    # Crecimiento del 900% interanual con un P/E de 30 -> PEG 0,03
    assert calcular_peg(None, None, 30.0, 9.0) is None, (
        "Un crecimiento del 900% interanual es un rebote de base baja, no algo "
        "que un PEG pueda representar."
    )
    # Y si viniera ya calculado y absurdo desde Yahoo, tampoco se acepta.
    assert calcular_peg(0.02, None, None, None) is None


def test_un_peg_absurdamente_alto_de_yahoo_cae_al_calculo_propio():
    """Caso PGR: Yahoo daba 61,8. Se descarta y se recalcula."""
    peg = calcular_peg(61.84, 61.84, 10.824457, 0.05)
    assert peg is not None and 0.1 <= peg <= 15
    assert round(peg, 2) == round(10.824457 / 5, 2)


def test_sin_ningun_dato_utilizable_devuelve_none_no_un_numero_inventado():
    assert calcular_peg(None, None, None, None) is None
    assert calcular_peg(None, None, 25.0, None) is None
    assert calcular_peg(None, None, 25.0, -0.10) is None, "Con beneficios cayendo, el PEG no significa nada"


def test_un_peg_bajo_pero_creible_si_se_muestra():
    """Que el suelo nuevo no se coma valores legítimos: un PEG de 0,5 es
    'crecimiento barato', no un artefacto."""
    peg = calcular_peg(None, None, 20.0, 0.40)   # 20 / 40 = 0.5
    assert peg == 0.5
