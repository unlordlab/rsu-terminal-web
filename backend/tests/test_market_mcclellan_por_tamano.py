"""
Market #59 y el McClellan de grandes contra pequeñas.

EL CASO, 13/09/2026. El usuario preguntó si merecía la pena añadir $NYAD o
$NAMO a Market. Al mirarlo:

1. LA ETIQUETA. La amplitud de Market (McClellan, A/D, NH-NL) sale del universo
   propio del escaneo —S&P 500 + Russell 2000, ~2.400 valores—, elegido a
   propósito en lugar del NYSE. Pero el subtítulo del panel decía «A/D NYSE»,
   la ayuda decía «datos reales de avance/declive del NYSE (^ADV/^DEC)» y el
   gráfico A/D se etiquetaba «[S&P 500 REAL]» sobre S&P 500 + Russell 2000.

2. LO QUE SE AÑADE en vez del $NAMO: el McClellan de las grandes y el de las
   pequeñas por separado. Responde lo que se busca con el $NAMO —si la subida
   es de todo el mercado o de unos pocos— con datos que ya existen y con su
   nombre verdadero. AJUSTADO POR TAMAÑO, porque en bruto el Russell (≈4 veces
   más valores) daría siempre números mayores.

   CUÁNTA HISTORIA, medido con el histórico real: con 59 sesiones (lo que
   publicaba el escaneo por universo) el error medio frente a la serie completa
   fue de 34 puntos; con 110, de 1,2. Por eso el escaneo pasa a 150 y por debajo
   de 110 no se da el número.

Uso:
    cd backend
    python -m pytest tests/test_market_mcclellan_por_tamano.py -v
"""
import ast
import inspect
import io
import os
import sys

import numpy as np
import pandas as pd

AQUI = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(AQUI, '..'))
sys.path.insert(0, os.path.join(AQUI, '..', '..', 'shared'))
sys.path.insert(0, os.path.join(AQUI, '..', '..', 'scripts'))

from mcclellan import MIN_SESIONES_AJUSTADO, mcclellan_ajustado, mcclellan_series  # noqa: E402
import services.market_service as M  # noqa: E402

MARKET_JS = os.path.join(AQUI, '..', '..', 'frontend', 'pages', 'market.js')
TOOLTIP_JS = os.path.join(AQUI, '..', '..', 'frontend', 'components', 'tooltip.js')


def _leer(p):
    return io.open(p, encoding='utf-8').read()


def _historia(fracciones_netas, tamano, inicio="2026-01-02"):
    """Filas del escaneo para un universo de `tamano` valores, con la fracción
    neta (avances-descensos)/total de cada día."""
    fechas = pd.bdate_range(inicio, periods=len(fracciones_netas))
    filas = []
    for f, x in zip(fechas, fracciones_netas):
        adv = int(round(tamano * (1 + x) / 2))
        filas.append({"date": f.strftime("%Y-%m-%d"), "advances": adv, "declines": tamano - adv})
    return filas


def _mercado(n=150, semilla=7):
    rng = np.random.default_rng(semilla)
    return list(np.clip(np.cumsum(rng.normal(0, 0.05, n)) * 0.2 + rng.normal(0, 0.25, n), -0.9, 0.9))


# ── El cálculo ──────────────────────────────────────────────────────────────

def test_sin_historia_suficiente_no_hay_numero():
    assert mcclellan_ajustado(_historia(_mercado(MIN_SESIONES_AJUSTADO - 1), 500)) is None
    assert mcclellan_ajustado(_historia(_mercado(59), 500)) is None, "lo que publicaba el escaneo"
    assert mcclellan_ajustado([]) is None and mcclellan_ajustado(None) is None
    assert mcclellan_ajustado(_historia(_mercado(MIN_SESIONES_AJUSTADO), 500)) is not None


def test_el_minimo_es_el_medido():
    assert 100 <= MIN_SESIONES_AJUSTADO <= 130


def test_no_depende_del_tamano_del_universo():
    """EL test del ajuste: el mismo mercado sobre 500 y sobre 1.960 valores da
    el mismo número. En bruto, el grande sale ~4 veces mayor."""
    fr = _mercado()
    chico, grande = _historia(fr, 500), _historia(fr, 1960)
    a, b = mcclellan_ajustado(chico), mcclellan_ajustado(grande)
    assert abs(a["valor"] - b["valor"]) < 1.5, (a, b)
    bruto = lambda h: float(mcclellan_series(pd.Series([x["advances"] - x["declines"] for x in h])).iloc[-1])
    assert abs(bruto(grande)) > 3 * abs(bruto(chico)), "sin ajustar, el tamaño manda"


def test_la_escala_es_la_fraccion_neta_en_tantos_por_mil():
    # 120 días neutros y 30 de fuerte avance (60% neto): el oscilador positivo y
    # de centenas, no de unidades ni de miles.
    h = _historia([0.0] * 120 + [0.6] * 30, 500)
    r = mcclellan_ajustado(h)
    assert 50 < r["valor"] < 600, r
    assert r["sesiones"] == 150 and r["fecha"] == h[-1]["date"]


def test_signo_y_semana():
    sube = mcclellan_ajustado(_historia([0.0] * 140 + [0.5] * 10, 500))
    baja = mcclellan_ajustado(_historia([0.0] * 140 + [-0.5] * 10, 500))
    assert sube["valor"] > 0 > baja["valor"]
    serie = mcclellan_series(pd.Series([0.0] * 140 + [500.0] * 10))
    assert sube["semana"] == round(float(serie.iloc[-1] - serie.iloc[-6]), 1)


def test_un_dia_sin_valores_no_rompe_la_cuenta():
    h = _historia(_mercado(), 500)
    h.insert(80, {"date": "hueco", "advances": 0, "declines": 0})
    assert mcclellan_ajustado(h) is not None


# ── Lo que llega a Market ───────────────────────────────────────────────────

def test_market_calcula_cada_universo_con_SU_serie(monkeypatch):
    """Si se pasara la misma serie dos veces, o cruzadas, las dos lecturas
    saldrían iguales o al revés y la comparación no serviría de nada."""
    import services.scanner_service as SS
    grandes = _historia([0.0] * 140 + [0.5] * 10, 500)
    pequenas = _historia([0.0] * 140 + [-0.5] * 10, 1960)
    monkeypatch.setattr(SS, "get_amplitudes_separadas", lambda: (grandes, pequenas))
    r = M._mcclellan_por_tamano()
    assert r["grandes"]["valor"] > 0 > r["pequenas"]["valor"]
    assert r["minimo_sesiones"] == MIN_SESIONES_AJUSTADO


def test_si_el_escaneo_no_lo_trae_se_dice_no_se_inventa(monkeypatch):
    import services.scanner_service as SS
    monkeypatch.setattr(SS, "get_amplitudes_separadas", lambda: (_historia(_mercado(59), 500), []))
    r = M._mcclellan_por_tamano()
    assert r["grandes"] is None and r["pequenas"] is None

    def rota():
        raise RuntimeError("gist caído")
    monkeypatch.setattr(SS, "get_amplitudes_separadas", rota)
    r = M._mcclellan_por_tamano()
    assert r["grandes"] is None and r["pequenas"] is None


def test_el_payload_de_amplitud_lo_incluye():
    fuente = inspect.cleandoc(inspect.getsource(M.get_market_breadth))
    claves = [n for n in ast.walk(ast.parse(fuente)) if isinstance(n, ast.Dict)]
    encontrado = False
    for d in claves:
        for k, v in zip(d.keys, d.values):
            if getattr(k, "value", None) == "mcclellan_por_tamano":
                encontrado = isinstance(v, ast.Call) and getattr(v.func, "id", "") == "_mcclellan_por_tamano"
    assert encontrado


# ── El escaneo publica historia suficiente ──────────────────────────────────

def test_el_escaneo_publica_las_sesiones_que_hacen_falta():
    import scanner_universe as S
    assert S.SESIONES_AMPLITUD_SEPARADA >= MIN_SESIONES_AJUSTADO + 20
    fechas = pd.bdate_range("2025-06-02", periods=260)
    rng = np.random.default_rng(3)
    grandes = [f"G{i:02d}" for i in range(60)]
    close = {t: pd.Series(100 + np.cumsum(rng.normal(0, 1, 260)), index=fechas) for t in grandes}
    for t in S.RUSSELL2000_TICKERS[:60]:
        close[t] = pd.Series(100 + np.cumsum(rng.normal(0, 1, 260)), index=fechas)
    g, p = S._amplitudes_separadas(close, grandes)
    assert len(g) >= MIN_SESIONES_AJUSTADO and len(p) >= MIN_SESIONES_AJUSTADO
    assert mcclellan_ajustado(g) is not None and mcclellan_ajustado(p) is not None


# ── Las etiquetas (Market #59) ──────────────────────────────────────────────

def test_el_subtitulo_ya_no_dice_NYSE():
    js = _leer(MARKET_JS)
    assert "A/D NYSE" not in js
    assert js.count("NH-NL · A/D'") == 3


def test_McClellan_ABI_y_grafico_AD_usan_la_misma_funcion_de_etiqueta():
    js = _leer(MARKET_JS)
    assert "const badgeText  = etiquetaFuenteAmplitud(data.ad_source);" in js
    assert "etiquetaFuenteAmplitud(data.ad_source) + '</span>'" in js
    # Ninguna otra cadena escrita a mano que decida la etiqueta
    assert js.count("=== 'nyse_yahoo'") == 1, "solo dentro de etiquetaFuenteAmplitud"
    i = js.index("function etiquetaFuenteAmplitud")
    cuerpo = js[i:js.index("\n}", i)]
    assert "'sp500_r2k'" in cuerpo and "RUSSELL 2000" in cuerpo


def test_la_ayuda_ya_no_atribuye_al_NYSE_lo_que_no_es():
    tip = _leer(TOOLTIP_JS)
    i = tip.index('"market-breadth": {')
    bloque = tip[i:tip.index('    },', i)]
    assert "del NYSE (^ADV/^DEC)" not in bloque and "acumulado del NYSE" not in bloque
    assert "Russell 2000" in bloque


def test_el_bloque_de_grandes_y_pequenas_esta_en_el_panel():
    js = _leer(MARKET_JS)
    assert "mcclellanPorTamanoHtml(data.mcclellan_por_tamano, data.breadth_fecha)" in js
    i = js.index("function mcclellanPorTamanoHtml")
    cuerpo = js[i:js.index("\n}\n", i)]
    assert "!pt || !pt.grandes || !pt.pequenas" in cuerpo, "sin datos tiene que decirlo, no romper"
    assert "tt('mcclellan-por-tamano')" in cuerpo
    assert '"mcclellan-por-tamano": {' in _leer(TOOLTIP_JS)
