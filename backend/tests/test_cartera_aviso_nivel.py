"""
Test del nivel y el tamaño en los avisos de Telegram de Cartera (11/08/2026,
pedido por el usuario).

Hasta ahora el aviso de entrada decía ticker, precio y fecha — un LOTTERY y un
CORE llegaban al móvil exactamente iguales, y el nivel es justo lo que dice
cuánto pesa la operación.

Va el nivel con su peso objetivo, y deliberadamente NO el importe en $: el
`inv` de la fila es lo que la simulación de niveles asigna sobre
`capital_total`, no lo ejecutado en el bróker, y suelto en un aviso se leería
como una cifra real.

Uso:
    cd backend
    python -m pytest tests/test_cartera_aviso_nivel.py -v
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.cartera_tracking_service import (  # noqa: E402
    _mensaje_apertura, _mensaje_cierre, _linea_nivel,
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
    # No se pierde nada de lo que ya decía
    assert "NVDA" in msg and "$123.45" in msg and "11/08/2026" in msg


def test_el_cierre_tambien_dice_el_nivel():
    msg = _mensaje_cierre(_fila(tier="LOTTERY"))
    assert "Nivel: LOTTERY (1% objetivo)" in msg
    assert "+12.3%" in msg


def test_los_tres_niveles_llevan_su_porcentaje_real():
    """El % sale de TIER_WEIGHTS de cartera_service, no de una copia local:
    si allí se recalibran los pesos, el aviso los sigue."""
    esperado = {"CORE": "5%", "HIGH": "3%", "LOTTERY": "1%"}
    for tier, pct in esperado.items():
        assert f"Nivel: {tier} ({pct} objetivo)" in _linea_nivel(_fila(tier=tier))


def test_sin_nivel_valido_no_se_inventa_uno():
    """La hoja puede traer la columna vacía o con un valor que norm_tier() no
    reconoce. El aviso lo dice en vez de suponer CORE."""
    msg = _mensaje_apertura(_fila(tier=None))
    assert "Nivel: sin clasificar" in msg
    assert "CORE" not in msg and "objetivo" not in msg


def test_el_aviso_no_lleva_importes_en_dolares_del_sizing():
    """`inv` es el tamaño que ASIGNA la simulación de niveles sobre
    capital_total, no lo ejecutado en el bróker — en un aviso suelto se leería
    como una cifra real, así que no entra. El único $ es el precio."""
    for msg in (_mensaje_apertura(_fila()), _mensaje_cierre(_fila())):
        assert "Tamaño" not in msg
        assert "5,000" not in msg and "5000" not in msg
    # ...y el precio de compra sí sigue ahí
    assert "$123.45" in _mensaje_apertura(_fila())
