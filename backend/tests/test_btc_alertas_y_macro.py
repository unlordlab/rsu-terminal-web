"""
BTC Stratum: la alerta de proximidad estaba invertida, el score de liquidez era
una constante y la fecha del halving estaba clavada a mano (16/08/2026,
hallazgos #6, #8 y #10 de su auditoría).

#6 -- `_calc_alerts` calculaba `(ma200*0,5 − price)/price` y solo emitía el
aviso si salía POSITIVO, cosa que únicamente ocurre cuando el precio ya está
POR DEBAJO del nivel −50%. Es decir: avisaba de que "faltaba" para llegar a un
sitio en el que ya estabas, y callaba durante todo el trayecto, que es cuando
el aviso sirve de algo. La rama de arriba tenía el vicio simétrico: anunciaba
"a X% de entrar en COMPRA FUERTE" con el precio hasta un 15% POR ENCIMA de la
MA200W, cuando a esa distancia el score ronda 41 y COMPRA FUERTE empieza en 60
hacia abajo -- ya se estaba dentro.

#8 -- `liquidity_score = (precio_TLT − 80)/0,6`, una recta calibrada para una
banda de precios que ya no existe. Medido el 16/08/2026 con el TLT en 82,0
daba 3,4 sobre 100, y el "entorno" derivado había sido RESTRICTIVO 1.087 de los
últimos 1.255 días (87%). Ahora es un percentil sobre la propia historia del
TLT, que no puede quedarse pegado a un extremo porque se desplace el rango.

#10 -- `next_halving` era `datetime(2028, 4, 1)` a fuego: pasada esa fecha el
progreso del ciclo superaría el 100% y la fase se quedaría encallada en
"MERCADO BAJISTA" para siempre sin que nada avisara.

Uso:
    cd backend
    python -m pytest tests/test_btc_alertas_y_macro.py -v
"""
import os
import sys
from unittest.mock import patch

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.btc_stratum_service import (  # noqa: E402
    _calc_alerts, _get_macro_data, _get_halving_cycle,
)

MA200 = 64_000.0

# Desde el rediseño del score (16/08/2026) los avisos de proximidad se anclan a
# las fronteras de ZONA, no a niveles sueltos, así que el score que se pasa
# tiene que ser el que de verdad corresponde a ese precio -- si no, se estaría
# probando una combinación imposible.
def _msgs(price, ma200=MA200):
    from services.btc_stratum_service import _calc_rsu_score
    return [a["msg"] for a in _calc_alerts(price, ma200, _calc_rsu_score(price, ma200))]


def _hay(msgs, trozo):
    return any(trozo in m for m in msgs)


# ── #6: la alerta de proximidad al nivel −50% ────────────────────────────────

def _precio_de(score, ma200=MA200):
    from services.btc_stratum_service import _score_a_precio
    return _score_a_precio(score, ma200)


def test_avisa_mientras_te_acercas_a_la_siguiente_frontera():
    """Score 52: un pelo por encima del corte de 50, falta poca caída. Éste es
    EL caso que la versión anterior no cubría -- su fórmula daba negativo
    mientras te acercabas y solo hablaba cuando ya habías llegado."""
    msgs = _msgs(_precio_de(52))
    assert _hay(msgs, "de entrar en zona"), f"deberia avisar acercandose a la frontera; salio {msgs}"


def test_no_avisa_de_una_frontera_que_ya_se_ha_rebasado():
    """Con el score en 30 ya se está dentro de OPORTUNIDAD: no queda nada que
    anunciar. Es justo el único caso en el que la versión anterior sí hablaba."""
    msgs = _msgs(_precio_de(30))
    assert not _hay(msgs, "de entrar en zona"), f"anuncia una frontera ya cruzada; salio {msgs}"


def test_no_avisa_cuando_la_frontera_esta_lejisimos():
    """Con el score en 95 falta muchísima caída para el corte de 90:
    anunciarlo sería ruido permanente."""
    assert not _hay(_msgs(_precio_de(95)), "de entrar en zona")


def test_ningun_aviso_promete_una_zona_en_la_que_ya_se_esta():
    """El texto viejo decía «A X% de entrar en COMPRA FUERTE» estando ya dentro."""
    from services.btc_stratum_service import _get_zone
    for s in (20, 40, 60, 85, 95):
        msgs   = _msgs(_precio_de(s))
        actual = _get_zone(s)["zone"]
        assert not _hay(msgs, "de entrar en zona " + actual), \
            f"con score {s} promete entrar en {actual}, donde ya se esta"


# ── #8: liquidez como percentil, no como recta con constantes mágicas ────────

def _macro_con_tlt(precios):
    """Sustituye las dos descargas de yfinance por series controladas."""
    def fake_download(ticker, *a, **kw):
        if ticker == "TLT":
            return pd.DataFrame({"Close": precios})
        # El DXY solo necesita 50 puntos para su SMA; da igual el valor.
        return pd.DataFrame({"Close": [100.0] * 60})
    with patch("services.btc_stratum_service.yf.download", side_effect=fake_download):
        return _get_macro_data()


def test_liquidez_es_un_percentil_dentro_de_su_propia_historia():
    # 100 valores de 1 a 100, el último es el 100 -> está por encima de 99 -> 99%
    r = _macro_con_tlt([float(i) for i in range(1, 101)])
    assert r["liquidity_score"] == 99.0, r["liquidity_score"]
    assert r["status"] == "EXPANSIVO"


def test_liquidez_no_se_queda_pegada_al_suelo_por_desplazarse_el_rango_de_precios():
    """La recta vieja `(precio−80)/0,6` daba ~0 con cualquier TLT por debajo de
    80, aunque dentro de su propia historia el precio estuviera arriba del todo.
    Con el percentil, ese mismo caso da una lectura alta -- que es la verdad."""
    precios = [float(i) for i in range(40, 79)] + [78.5]   # todo por debajo de 80
    r = _macro_con_tlt(precios)
    viejo = max(0, min(100, (78.5 - 80) / 0.6))
    assert viejo == 0, "referencia: la formula vieja daba 0 en este escenario"
    assert r["liquidity_score"] > 90, \
        f"el percentil deberia reflejar que el TLT esta arriba de su rango, salio {r['liquidity_score']}"


def test_liquidez_publica_sobre_cuantas_sesiones_se_calcula():
    r = _macro_con_tlt([float(i) for i in range(1, 101)])
    assert r["liquidez_base"] == 100


# ── #10: el ciclo de halving no puede desbordar ──────────────────────────────

def test_el_progreso_del_ciclo_nunca_pasa_del_100_por_cien():
    """Sin red (la estimación por altura de bloque falla), la fecha se proyecta
    desde el último halving en vez de quedarse clavada, y el progreso se acota:
    la fase no puede encallarse por haber pasado una fecha escrita a mano."""
    with patch("services.btc_stratum_service.requests.get", side_effect=Exception("sin red")):
        h = _get_halving_cycle()
    assert 0 <= h["progress_pct"] <= 100, h["progress_pct"]
    assert h["days_to_next"] >= 0
    assert "sin conexión" in h["fuente"], h["fuente"]


def test_la_fecha_del_halving_se_declara_como_estimacion():
    h = _get_halving_cycle()
    assert h.get("fuente"), "la fecha del proximo halving debe decir de donde sale"
