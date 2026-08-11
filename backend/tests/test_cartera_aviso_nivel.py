"""
Test del nivel y el tamaño en los avisos de Telegram de Cartera (11/08/2026,
pedido por el usuario).

Hasta ahora el aviso de entrada decía ticker, precio y fecha — un LOTTERY del
1% y un CORE del 5% llegaban al móvil exactamente iguales, y el tamaño de la
operación es justo lo que decide si merece la pena mirarla.

Lo que cubren estos tests, además del caso normal, son los dos casos en los
que NO hay dato y no se puede rellenar con un número:
  - fila sin nivel válido en la hoja (`norm_tier()` devuelve None),
  - `sin_dimensionar`: posición abierta real cuyo `inv` es 0 porque la
    simulación de niveles está saturada — «Tamaño: $0» ahí sería
    indistinguible de una posición que no existe.

Uso:
    cd backend
    python -m pytest tests/test_cartera_aviso_nivel.py -v
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.cartera_tracking_service import (  # noqa: E402
    _mensaje_apertura, _mensaje_cierre, _lineas_sizing,
)


def _fila(**extra):
    base = {
        "ticker": "NVDA", "compra": 123.45, "fecha": "11/08/2026",
        "pnl": 12.3, "tier": "CORE", "inv": 5000.0, "sin_dimensionar": False,
    }
    base.update(extra)
    return base


def test_la_entrada_dice_el_nivel_con_su_peso_objetivo():
    msg = _mensaje_apertura(_fila())
    assert "Nivel: CORE (5% objetivo)" in msg
    assert "Tamaño: $5,000" in msg
    # No se pierde nada de lo que ya decía
    assert "NVDA" in msg and "$123.45" in msg and "11/08/2026" in msg


def test_el_cierre_tambien_dice_nivel_y_tamano():
    msg = _mensaje_cierre(_fila(tier="LOTTERY", inv=1000.0))
    assert "Nivel: LOTTERY (1% objetivo)" in msg
    assert "Tamaño: $1,000" in msg
    assert "+12.3%" in msg


def test_los_tres_niveles_llevan_su_porcentaje_real():
    """El % sale de TIER_WEIGHTS de cartera_service, no de una copia local:
    si allí se recalibran los pesos, el aviso los sigue."""
    esperado = {"CORE": "5%", "HIGH": "3%", "LOTTERY": "1%"}
    for tier, pct in esperado.items():
        assert f"Nivel: {tier} ({pct} objetivo)" in _lineas_sizing(_fila(tier=tier))


def test_sin_nivel_valido_no_se_inventa_uno():
    """La hoja puede traer la columna vacía o con un valor no reconocido;
    norm_tier() devuelve None y el sizing cae al cálculo antiguo. El aviso lo
    dice en vez de suponer CORE."""
    msg = _mensaje_apertura(_fila(tier=None))
    assert "Nivel: sin clasificar" in msg
    assert "CORE" not in msg and "objetivo" not in msg
    # El tamaño real sí se conoce (viene de Cantidad/Inversión), así que va
    assert "Tamaño: $5,000" in msg


def test_posicion_sin_dimensionar_no_dice_cero_dolares():
    """inv=0 aquí no significa «no ha invertido nada», significa «no se le
    pudo asignar capital». Ver el mismo criterio en la tabla de Cartera."""
    msg = _mensaje_apertura(_fila(inv=0.0, sin_dimensionar=True))
    assert "sin asignar" in msg
    assert "$0" not in msg


def test_sin_tamano_conocido_se_omite_la_linea_en_vez_de_poner_cero():
    """Cerrada antigua sin Cantidad ni Inversión en la hoja: no hay tamaño
    que dar y `sin_dimensionar` solo aplica a abiertas."""
    msg = _mensaje_cierre(_fila(inv=0.0, sin_dimensionar=False))
    assert "Tamaño" not in msg
    assert "$0" not in msg
    assert "Nivel: CORE" in msg
