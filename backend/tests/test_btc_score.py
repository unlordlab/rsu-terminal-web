"""
BTC Stratum: el RSU Score deja de ser una media ponderada de cuatro cosas que
en realidad eran una y media (16/08/2026, hallazgos #2, #3, #12 y #17).

Este fichero sustituye a test_btc_origen_indicadores.py, que protegía el
etiquetado del MVRV cuando existían DOS caminos (capitalización real y un
proxy de precio). Ya no hay dos caminos: el proxy se ha eliminado, así que la
garantía que se protege aquí es más fuerte que la de entonces -- no es «cada
rama dice lo que ha comparado», es «no existe ninguna rama que estime una
métrica on-chain a partir del precio».

Lo medido que justifica el rediseño, sobre 2.953 sesiones de BTC-USD con
MA200W madura (desde 2018-07):

  - Con el MVRV en su rama de respaldo -- la única que corría en producción --
    `mvrv_score = 0,7·ma_score − 5` EXACTO. El 70% del peso era una variable
    escalada dos veces (correlación medida tras el recorte: 0,917).
  - El AHR999 valía 0 en 2.864 de 2.953 sesiones (97%).
  - El sub-score de la MA200W quedaba pegado a 0 o 100 el 63% de los días.
  - Y el resultado: el compuesto de cuatro factores ordenaba el retorno futuro
    PEOR (Spearman −0,576 a un año) que su propio ingrediente dominante a
    secas (−0,646). Con la logística, el score alcanza ese −0,646.

Uso:
    cd backend
    python -m pytest tests/test_btc_score.py -v
"""
import math
import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import services.btc_stratum_service as B  # noqa: E402

MA = 60_000.0


# ── El score depende SOLO del precio y la MA200W ─────────────────────────────

def test_el_score_solo_necesita_precio_y_media_de_200_semanas():
    """Es lo que hace imposible que el dashboard y el backtest diverjan: no hay
    ninguna fuente externa que uno pueda leer y el otro no (hallazgo #5)."""
    import inspect
    params = list(inspect.signature(B._calc_rsu_score).parameters)
    assert params == ["price", "ma200"], params


def _barrido():
    """De 0,45x a 4,5x la media de 200 semanas: cubre con margen todo lo que
    bitcoin ha hecho (histórico medido: de 0,5x a 4x)."""
    return [(paso / 1000, B._calc_rsu_score(MA * paso / 1000, MA))
            for paso in range(450, 4501, 5)]


def _rampa_anterior(ratio):
    """La fórmula que había antes: `((dev+0,5)/1,0)*100` recortada a [0,100]."""
    return max(0.0, min(100.0, ((ratio - 1) + 0.5) * 100))


def test_nunca_baja_cuando_el_precio_sube():
    anterior = -1
    for ratio, s in _barrido():
        assert s >= anterior, f"con precio/MA200W = {ratio} el score BAJA: {s} < {anterior}"
        anterior = s


def test_no_aplasta_estados_de_mercado_distintos_en_el_mismo_numero():
    """Éste es el defecto que se estaba corrigiendo. La rampa anterior dejaba el
    sub-score de la MA200W pegado a 0 o a 100 el 63% de los días reales, y ese
    aplastamiento costaba 0,21 de correlación de rango con el retorno futuro.
    Se compara contra ella con el mismo barrido para que la mejora sea medible
    y no una afirmación."""
    barrido = _barrido()
    valores_nuevos = {s for _r, s in barrido}
    valores_viejos = {round(_rampa_anterior(r), 1) for r, _s in barrido}

    pegados_viejos = sum(1 for r, _s in barrido if _rampa_anterior(r) in (0.0, 100.0))
    pegados_nuevos = sum(1 for _r, s in barrido if s in (0.1, 99.9))

    assert pegados_nuevos == 0, \
        f"{pegados_nuevos} puntos del rango real topan contra el extremo"
    assert pegados_viejos > len(barrido) * 0.5, \
        "referencia: la rampa vieja deberia saturar en mas de la mitad del rango"
    assert len(valores_nuevos) > len(valores_viejos) * 2, \
        f"el score nuevo distingue {len(valores_nuevos)} niveles y el viejo {len(valores_viejos)}"


def test_nunca_publica_un_cero_ni_un_cien_exactos():
    """Publicar 0,0 o 100,0 diría «se ha tocado el extremo» sin que se haya
    tocado -- la misma mentira que contaba la rampa recortada."""
    for precio in (1.0, 100.0, 5_000_000.0):
        s = B._calc_rsu_score(precio, MA)
        assert 0 < s < 100, f"con precio {precio} el score satura: {s}"


def test_en_la_media_de_200_semanas_el_score_cae_en_zona_de_compra():
    """Estar en la MA200W ha sido históricamente un buen sitio para comprar, y
    el score tiene que reflejarlo sin que nadie lo ajuste a mano."""
    s = B._calc_rsu_score(MA, MA)
    assert 20 < s < 35, s
    assert B._get_zone(s)["zone"] == "OPORTUNIDAD"


def test_sin_media_de_200_semanas_no_hay_score():
    assert B._calc_rsu_score(50_000.0, None) is None
    assert B._calc_rsu_score(50_000.0, 0) is None
    assert B._calc_rsu_score(None, MA) is None


def test_la_traduccion_a_precio_es_la_inversa_exacta():
    """La página enseña en qué PRECIO está cada frontera de zona; si esa
    traducción no fuera la inversa del score, enseñaría niveles falsos."""
    for objetivo in (10, 25, 50, 80, 90, 95):
        precio = B._score_a_precio(objetivo, MA)
        assert abs(B._calc_rsu_score(precio, MA) - objetivo) < 0.15, objetivo


# ── Las zonas ────────────────────────────────────────────────────────────────

def test_las_zonas_cubren_la_escala_entera_sin_huecos_ni_solapes():
    bordes = [(d, h) for d, h, *_ in B.ZONAS]
    assert bordes[0][0] == 0
    for (_, hasta), (desde, _) in zip(bordes, bordes[1:]):
        assert hasta == desde, f"hueco o solape en {hasta} / {desde}"
    assert bordes[-1][1] > 100
    for s in (0, 0.1, 49.9, 50, 79.9, 80, 89.9, 90, 99.9, 100):
        assert B._get_zone(s)["zone"], f"score {s} sin zona"


def test_cada_zona_publica_la_evidencia_en_la_que_se_apoya():
    """Los seis tramos anteriores no ordenaban el retorno futuro y nada lo
    decía. Estos cuatro sí, y el dato viaja con la zona para poder enseñarlo."""
    for _d, _h, nombre, _c, _a, _u, ev in B.ZONAS:
        assert ev["n"] > 100, nombre
        assert "retorno_1a" in ev and "pct_perdidas" in ev, nombre
    perdidas = [ev["pct_perdidas"] for *_r, ev in B.ZONAS]
    assert perdidas == sorted(perdidas), \
        f"el riesgo deberia crecer con el score, y va {perdidas}"


def test_la_asignacion_sugerida_baja_segun_sube_el_score():
    allocs = [a for _d, _h, _n, _c, a, _u, _e in B.ZONAS]
    assert allocs == sorted(allocs, reverse=True), allocs
    assert allocs[-1] == 0


# ── Nada se estima a partir del precio ───────────────────────────────────────

def test_sin_fuente_on_chain_el_mvrv_queda_vacio_y_no_se_estima():
    """LA garantía de este fichero. Antes, cuando la fuente fallaba, el MVRV se
    sustituía por `(precio − MA200W)/MA200W × 3,5` y se presentaba como una
    métrica de cadena. Ese camino ya no existe."""
    with patch("services.btc_stratum_service.requests.get", side_effect=Exception("sin red")):
        ctx = B._get_contexto_onchain({}, {})
    assert ctx["mvrv_z"] is None
    assert ctx["precio_realizado"] is None
    assert ctx["puell"] is None
    assert ctx["fuentes"]["mvrv"] is None


def test_no_queda_ninguna_funcion_que_fabrique_un_indicador_desde_el_precio():
    for muerta in ("_calc_mvrv_z_improved", "_calc_ahr999_improved", "_calc_puell_from_series"):
        assert not hasattr(B, muerta), \
            f"{muerta} sigue viva: era una estimacion de precio disfrazada de dato on-chain"


def test_el_contexto_no_influye_en_el_score():
    """MVRV, Puell y hashrate informan, pero no entran en la fórmula: dos de
    ellos la empeoraban medidos contra el retorno futuro."""
    base = B._calc_rsu_score(75_000.0, MA)
    with patch("services.btc_stratum_service.requests.get", side_effect=Exception("sin red")):
        assert B._calc_rsu_score(75_000.0, MA) == base


def test_el_hash_ribbon_sale_del_hashrate_real_o_no_sale():
    with patch("services.btc_stratum_service.requests.get", side_effect=Exception("sin red")):
        assert B._get_contexto_onchain({}, {})["hash_ribbon"] is None
        ctx = B._get_contexto_onchain({}, {"hashrate_ehs": 900.0, "avg30_ehs": 1000.0})
    assert ctx["hash_ribbon"] == 0.9


# ── Coherencia entre lo que se calcula y lo que se avisa ─────────────────────

def test_el_aviso_de_proximidad_usa_las_mismas_fronteras_que_la_tarjeta_de_zona():
    """Si el aviso dijera una frontera y la tarjeta otra, el usuario vería dos
    números incompatibles para el mismo concepto."""
    precio   = B._score_a_precio(52, MA)        # justo por encima del corte de 50
    msgs     = [a["msg"] for a in B._calc_alerts(precio, MA, 52.0)]
    objetivo = B._score_a_precio(50, MA)
    assert any(f"{objetivo:,.0f}".replace(",", ".") in m for m in msgs),         f"el aviso deberia citar el precio exacto de la frontera ({objetivo}); salio {msgs}"


def test_no_se_avisa_de_una_frontera_ya_cruzada():
    alertas = B._calc_alerts(B._score_a_precio(30, MA), MA, 30.0)
    assert not [a for a in alertas if a["icon"] == "🔥"],         [a["msg"] for a in alertas]
