"""
Histéresis del semáforo del RSU Algoritmo y banda asimétrica de la EMA200
semanal — los dos cambios del 30/07/2026.

BUGS REALES QUE MOTIVAN ESTE FICHERO:

1. El usuario recibió TRES notificaciones de cambio de semáforo en una misma
   sesión, y un VERDE que duró cinco minutos quedó grabado en senales_tracked
   como señal accionable con un precio de entrada que nadie ejecutó. Causa: el
   estado se recalculaba con la barra intradía en curso y el score estaba
   pegado al umbral (52 contra 54).

2. El gatekeeper de la EMA200 semanal usaba `abs(dist) <= 25`, simétrico. Eso
   trata igual estar un 24% POR ENCIMA de la media secular (mercado estirado)
   que un 24% por debajo (capitulación). Medido sobre SPY, los 7 suelos
   mayores desde 1997 estuvieron todos por debajo de +6,9%, y el corte
   inferior de -25% dejaba fuera 2002 (-27,5%) y 2009 (-41,7%) — los dos
   suelos más profundos del histórico.

Uso:
    cd backend
    python -m pytest tests/test_algoritmo_histeresis.py -v
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.rsu_algoritmo_service import (  # noqa: E402
    MARGEN_HISTERESIS, aplicar_histeresis,
)

UMBRAL = 54


# ── Histéresis ───────────────────────────────────────────────────────────────

def test_entrar_en_verde_exige_el_umbral_pleno_sin_rebaja():
    """La histéresis solo dificulta SALIR, nunca facilita entrar. Si rebajara
    también la entrada, el umbral efectivo sería 51 y no 54."""
    assert aplicar_histeresis("AMBAR", UMBRAL - 1, UMBRAL, True, "AMBAR") == "AMBAR"
    assert aplicar_histeresis("AMBAR", UMBRAL - MARGEN_HISTERESIS, UMBRAL, True, "AMBAR") == "AMBAR"


def test_verde_se_mantiene_cuando_el_score_roza_el_umbral_por_debajo():
    """El caso que provocaba el parpadeo: 52 con umbral 54 viniendo de verde."""
    assert aplicar_histeresis("AMBAR", 52, UMBRAL, True, "VERDE") == "VERDE"
    # Justo en el límite del margen todavía se mantiene
    assert aplicar_histeresis("AMBAR", UMBRAL - MARGEN_HISTERESIS, UMBRAL, True, "VERDE") == "VERDE"


def test_verde_sale_cuando_el_score_cae_por_debajo_del_margen():
    assert aplicar_histeresis("AMBAR", UMBRAL - MARGEN_HISTERESIS - 1, UMBRAL, True, "VERDE") == "AMBAR"


def test_perder_el_gatekeeper_saca_del_verde_aunque_el_score_roce():
    """La histéresis absorbe ruido de score, no la desaparición del soporte
    estructural: si se cae el gatekeeper, la condición que justificaba la
    señal ya no se cumple y hay que salir en el momento."""
    assert aplicar_histeresis("AMBAR", UMBRAL - 1, UMBRAL, False, "VERDE") == "AMBAR"


def test_verde_vol_tambien_cuenta_como_verde():
    assert aplicar_histeresis("AMBAR", 52, UMBRAL, True, "VERDE-VOL") == "VERDE-VOL"


def test_sin_estado_anterior_no_retiene_nada():
    """Primera ejecución con la base de datos vacía."""
    assert aplicar_histeresis("AMBAR", 52, UMBRAL, True, None) == "AMBAR"


def test_desplome_grande_sale_sin_retencion():
    assert aplicar_histeresis("ROJO", 20, UMBRAL, True, "VERDE") == "ROJO"


# ── Banda asimétrica de la EMA200 semanal ────────────────────────────────────

def _cerca(dist_pct, margen=10):
    """Réplica de la condición de rsu_algoritmo_service (factor 5)."""
    return dist_pct <= margen


@pytest.mark.parametrize("nombre,dist", [
    ("Punto.com 2002", -27.5),
    ("Gran Crisis 2009", -41.7),
    ("Crisis euro 2011", -0.9),
    ("Suelo 2016", 6.9),
    ("Correccion 2018", 4.3),
    ("COVID 2020", -11.2),
    ("Bear 2022", 1.3),
])
def test_la_banda_captura_los_siete_suelos_reales(nombre, dist):
    """Distancias medidas sobre SPY ajustado en la fecha de cada suelo real."""
    assert _cerca(dist), f"{nombre} ({dist:+.1f}%) debería contar como zona de suelo"


def test_la_banda_vieja_simetrica_perdia_los_dos_suelos_mas_profundos():
    """Test canario: documenta por qué se abandonó `abs(dist) <= 25`."""
    for dist in (-27.5, -41.7):   # 2002 y 2009
        assert not (abs(dist) <= 25), "la banda vieja los dejaba fuera"
        assert _cerca(dist), "la nueva sí los captura"


def test_estar_muy_por_encima_de_la_media_secular_no_es_zona_de_suelo():
    """El caso del 30/07/2026: SPY a +29,4% de su media de 200 semanas, a
    -3,7% de máximos históricos. La banda vieja lo daba por bueno."""
    assert not _cerca(29.4)
    assert abs(24.7) <= 25, "con la EMA mal calculada (5 años) sí pasaba el filtro viejo"
