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

MA200 = 64_000.0          # el nivel de OPORTUNIDAD MÁXIMA cae en 32.000
NEUTRO = dict(rsu=50.0, mvrv_z=0.0, puell=1.0)


def _msgs(price, ma200=MA200, **kw):
    d = {**NEUTRO, **kw}
    return [a["msg"] for a in _calc_alerts(price, ma200, d["rsu"], d["mvrv_z"], d["puell"])]


def _hay(msgs, trozo):
    return any(trozo in m for m in msgs)


# ── #6: la alerta de proximidad al nivel −50% ────────────────────────────────

def test_avisa_mientras_te_acercas_al_nivel_de_oportunidad_maxima():
    """33.000 con el nivel en 32.000: falta un 3% de caída. Este es EL caso que
    la versión anterior no cubría -- su fórmula daba negativo aquí y callaba."""
    msgs = _msgs(33_000)
    assert _hay(msgs, "OPORTUNIDAD MÁXIMA"), f"deberia avisar acercandose al nivel; salio {msgs}"


def test_no_avisa_de_que_falta_para_un_nivel_que_ya_se_ha_rebasado():
    """31.000 está POR DEBAJO de 32.000: ya se ha llegado, no queda nada que
    anunciar. Es justo el único caso en el que la versión anterior sí hablaba."""
    msgs = _msgs(31_000)
    assert not _hay(msgs, "OPORTUNIDAD MÁXIMA"), f"no deberia decir que falta para un nivel ya rebasado; salio {msgs}"


def test_no_avisa_cuando_el_nivel_esta_lejisimos():
    """A 80.000 falta un 60% de caída: anunciarlo sería ruido permanente."""
    assert not _hay(_msgs(80_000), "OPORTUNIDAD MÁXIMA")


# ── #6: la alerta de proximidad a la propia MA200W ───────────────────────────

def test_avisa_al_acercarse_a_la_ma200w_desde_arriba():
    msgs = _msgs(66_000)   # un 3% por encima de la MA200W
    assert _hay(msgs, "MA200W"), f"deberia avisar de la cercania a la MA200W; salio {msgs}"


def test_no_promete_entrar_en_una_zona_en_la_que_ya_se_esta():
    """El texto viejo decía «A X% de entrar en COMPRA FUERTE» estando ya dentro.
    Ninguna alerta debe prometer la entrada a una zona por proximidad."""
    for precio in (62_000, 66_000, 70_000):
        assert not _hay(_msgs(precio), "de entrar en COMPRA FUERTE"), \
            f"con precio {precio} se vuelve a prometer una zona en la que ya se esta"


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
