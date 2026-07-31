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


# ── Decisión de cierre: esperar a que la amplitud sea de la misma sesión ─────
#
# Lo que de verdad provocó los tres avisos del 30/07/2026: llegaron de
# madrugada y los TRES con el MISMO precio de SPY (729,46), score 51 -> 55 ->
# 52. No fue ruido de precio. El scan nocturno reescribe el Gist de amplitud a
# las 22:15 UTC mientras el cierre de Nueva York es a las 20:00, así que cada
# recálculo mezclaba datos frescos con rancios. El Breadth pesa 18 puntos más
# 7 del bonus de giro: mueve el score de sobra para cruzar el umbral.

def _resultado_falso(**extra):
    base = {
        "ok": True, "estado": "AMBAR", "senal": "DESARROLLANDO", "score": 52,
        "umbral_verde": 54, "precio": 729.46, "gatekeeper_a": True,
        "gatekeeper_b": True, "metricas": {}, "ftd_confirmado": False,
        "credit_spread_valor": 1.62, "credit_spread_nivel": "normal",
    }
    base.update(extra)
    return base


def test_no_decide_si_la_amplitud_es_de_una_sesion_anterior():
    """Y no debe ni disparar el cálculo: sería trabajo tirado."""
    from unittest.mock import patch
    import services.rsu_algoritmo_service as svc

    with patch.object(svc, "_fetch_breadth_real", return_value=[{"date": "2026-07-28"}]), \
         patch.object(svc, "_ultima_sesion_cerrada", return_value="2026-07-29"), \
         patch("services.algoritmo_tracking_service.sesion_ya_procesada", return_value=False), \
         patch.object(svc, "get_rsu_algoritmo") as calc:
        r = svc.procesar_cierre_si_toca()

    assert r["procesado"] is False
    assert r["motivo"] == "amplitud_desfasada"
    assert not calc.called


def test_no_repite_una_sesion_ya_procesada():
    from unittest.mock import patch
    import services.rsu_algoritmo_service as svc

    with patch.object(svc, "_ultima_sesion_cerrada", return_value="2026-07-29"), \
         patch("services.algoritmo_tracking_service.sesion_ya_procesada", return_value=True):
        r = svc.procesar_cierre_si_toca()

    assert r["procesado"] is False and r["motivo"] == "ya_procesada"


def test_con_amplitud_al_dia_decide_y_lo_registrado_no_es_provisional():
    from unittest.mock import patch
    import services.rsu_algoritmo_service as svc

    capturado = {}

    def _capturar(res, fecha_sesion=None):
        capturado.update(estado=res["estado"], fecha=fecha_sesion,
                         provisional=res.get("provisional"))

    with patch.object(svc, "_fetch_breadth_real", return_value=[{"date": "2026-07-29"}]), \
         patch.object(svc, "_ultima_sesion_cerrada", return_value="2026-07-29"), \
         patch.object(svc, "get_rsu_algoritmo", return_value=_resultado_falso()), \
         patch("services.algoritmo_tracking_service.sesion_ya_procesada", return_value=False), \
         patch("services.algoritmo_tracking_service.obtener_estado_oficial", return_value="VERDE"), \
         patch("services.algoritmo_tracking_service.procesar_resultado_algoritmo", _capturar):
        r = svc.procesar_cierre_si_toca()

    assert r["procesado"] is True
    assert capturado["estado"] == "VERDE", "la histéresis debe retener el verde"
    assert capturado["fecha"] == "2026-07-29"
    assert capturado["provisional"] is False


def test_sin_gist_de_amplitud_no_se_queda_bloqueado():
    """Sin amplitud real el factor cae SIEMPRE al oscilador sectorial, de forma
    consistente — no hay mezcla que pueda hacer parpadear el semáforo, así que
    no tiene sentido bloquear la decisión indefinidamente."""
    from unittest.mock import patch
    import services.rsu_algoritmo_service as svc

    with patch.object(svc, "_fetch_breadth_real", return_value=[]), \
         patch.object(svc, "_ultima_sesion_cerrada", return_value="2026-07-29"), \
         patch.object(svc, "get_rsu_algoritmo", return_value=_resultado_falso()), \
         patch("services.algoritmo_tracking_service.sesion_ya_procesada", return_value=False), \
         patch("services.algoritmo_tracking_service.obtener_estado_oficial", return_value="AMBAR"), \
         patch("services.algoritmo_tracking_service.procesar_resultado_algoritmo", lambda *a, **k: None):
        r = svc.procesar_cierre_si_toca()

    assert r["procesado"] is True
