"""
Research no puede pedir el mismo dato tres veces en la misma petición.

Contexto (29/07/2026): un research en frío tardaba ~11s y la auditoría del
módulo señalaba la causa. Verificado contra el código: `.info` de yfinance --
la llamada más pesada y más propensa a rate-limit de la librería, porque
descarga el payload completo de quoteSummary -- se pedía TRES veces por
research, cada una con su propio yf.Ticker: en el perfil (_get_yfinance), en
la participación institucional y en el interés corto. Las tres corren en
paralelo dentro del mismo request, así que ni siquiera se aprovechaban entre
ellas.

Lo mismo con el histórico de 180 días: get_turnover_comparison() y
get_absorption_signal() se piden a la vez en cada research y cada una
descargaba su propia copia del MISMO ticker.

Estos tests fijan el número de llamadas, no el tiempo. El reloj de pared no
sirve para esto: midiendo el mismo ticker en frío salían 9,3s en una pasada y
3,2s en la siguiente -- la varianza de Yahoo se come cualquier diferencia. El
número de peticiones sí es determinista y es lo que de verdad protege contra
el rate-limit.

Uso:
    cd backend
    python -m pytest tests/test_research_llamadas_red.py -v
"""
import os
import sys
from unittest.mock import MagicMock, patch

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import services.research_service as rs  # noqa: E402
import services.turnover_service as ts  # noqa: E402

INFO_FALSO = {
    "heldPercentInstitutions": 0.72,
    "shortPercentOfFloat": 0.03,
    "sharesShort": 1_000_000,
    "shortRatio": 2.5,
    "sharesOutstanding": 500_000_000,
}


class _ContadorInfo:
    """yf.Ticker falso que cuenta cada acceso a `.info`."""
    def __init__(self, ticker=None, *a, **k):
        self.ticker = ticker

    @property
    def info(self):
        _ContadorInfo.llamadas += 1
        return dict(INFO_FALSO)


_ContadorInfo.llamadas = 0


def _limpiar_cache(ticker="TEST"):
    from services.cache import cache
    cache.set(f"research:info:{ticker}", None, 1)
    ts._PV_CACHE.clear()


def test_info_se_pide_una_sola_vez_para_las_tres_funciones():
    """_get_yfinance, _get_institutional_ownership y _get_short_interest
    comparten el mismo `.info` en vez de descargarlo cada una."""
    _limpiar_cache()
    _ContadorInfo.llamadas = 0

    with patch.object(rs.yf, "Ticker", _ContadorInfo):
        rs._info_de("TEST")
        rs._info_de("TEST")
        rs._info_de("TEST")

    assert _ContadorInfo.llamadas == 1, (
        f"Se esperaba 1 descarga de .info compartida entre las tres funciones "
        f"del research, se hicieron {_ContadorInfo.llamadas}."
    )


def test_el_fallo_de_info_tampoco_se_reintenta_tres_veces():
    """Si Yahoo no responde para este ticker, las otras dos funciones del
    mismo request no van a tener más suerte insistiendo."""
    _limpiar_cache("FALLA")

    class _Explota:
        def __init__(self, *a, **k): pass
        @property
        def info(self):
            _Explota.llamadas += 1
            raise RuntimeError("Yahoo caído")
    _Explota.llamadas = 0

    with patch.object(rs.yf, "Ticker", _Explota):
        assert rs._info_de("FALLA") == {}
        assert rs._info_de("FALLA") == {}

    assert _Explota.llamadas == 1, (
        f"Un fallo de .info debe cachearse igual que un acierto, se "
        f"reintentó {_Explota.llamadas} veces."
    )


def _hist_falso(dias=200):
    idx = pd.date_range("2025-01-01", periods=dias, freq="D", tz="UTC")
    return pd.DataFrame({
        "Close":  [100.0 + i * 0.1 for i in range(dias)],
        "Volume": [1_000_000 + i * 10 for i in range(dias)],
    }, index=idx)


def test_turnover_y_absorcion_comparten_una_sola_descarga():
    """Las dos se piden en paralelo en cada research sobre el MISMO ticker."""
    ts._PV_CACHE.clear()
    descargas = {"n": 0}

    class _TickerHist:
        def __init__(self, *a, **k): pass
        @property
        def fast_info(self):
            m = MagicMock()
            m.shares_outstanding = 500_000_000
            return m
        def history(self, *a, **k):
            descargas["n"] += 1
            return _hist_falso()

    with patch.object(ts.yf, "Ticker", _TickerHist):
        ts.get_absorption_signal("TEST")
        ts._get_daily_turnover("TEST")

    assert descargas["n"] == 1, (
        f"Absorción y rotación deben compartir la descarga de 180 días del "
        f"mismo ticker, se hicieron {descargas['n']}."
    )


def test_la_traduccion_no_se_vuelve_a_pagar_en_cada_research():
    """Era una llamada SÍNCRONA a un LLM (hasta 10s de timeout) en el camino
    principal, sin caché propia, para una descripción que no cambia nunca."""
    from services.cache import cache
    import hashlib
    texto = "Adobe Inc. operates as a diversified software company worldwide."
    clave = "research:desc_es:" + hashlib.sha1(texto[:1500].encode("utf-8")).hexdigest()
    cache.set(clave, None, 1)

    llamadas = {"n": 0}

    def _fake_llm(t):
        llamadas["n"] += 1
        return "Adobe Inc. opera como una empresa de software diversificada."

    with patch.object(rs, "_traducir_con_llm", _fake_llm):
        primera = rs._translate_description(texto)
        segunda = rs._translate_description(texto)

    assert primera == segunda
    assert llamadas["n"] == 1, (
        f"La traducción debe pedirse una sola vez, se pidió {llamadas['n']}."
    )


def test_una_traduccion_fallida_no_se_cachea_como_buena():
    """Si el LLM falla devuelve el texto original en inglés. Guardarlo dejaría
    la ficha en inglés durante 30 días por un fallo puntual de red."""
    from services.cache import cache
    import hashlib
    texto = "Some company profile that will fail to translate."
    clave = "research:desc_es:" + hashlib.sha1(texto[:1500].encode("utf-8")).hexdigest()
    cache.set(clave, None, 1)

    llamadas = {"n": 0}

    def _fake_llm_roto(t):
        llamadas["n"] += 1
        return t   # el original, sin traducir

    with patch.object(rs, "_traducir_con_llm", _fake_llm_roto):
        rs._translate_description(texto)
        rs._translate_description(texto)

    assert llamadas["n"] == 2, (
        "Un fallo de traducción debe reintentarse en el siguiente research, "
        "no quedarse cacheado 30 días."
    )


def test_un_ticker_invalido_no_repite_el_pipeline_entero_en_cada_peticion():
    """Antes solo se cacheaba el ÉXITO, así que un ticker inexistente o
    retirado volvía a disparar las ~14 descargas en paralelo en cada
    petición -- y es de los casos que más se repiten: alguien tecleando mal,
    o un enlace viejo a algo que ya no cotiza."""
    from services.cache import cache
    cache.set("research:NOEXISTE", None, 1)

    llamadas = {"n": 0}

    def _yf_falla(ticker):
        llamadas["n"] += 1
        return {"ok": False, "error": "Sin precio para NOEXISTE"}

    with patch.object(rs, "_get_yfinance", _yf_falla):
        primera = rs.get_research("NOEXISTE")
        segunda = rs.get_research("NOEXISTE")

    assert primera["ok"] is False and segunda["ok"] is False
    assert primera["error"] == segunda["error"]
    assert llamadas["n"] == 1, (
        f"El fallo debe servirse de caché en la segunda petición, se "
        f"reconstruyó {llamadas['n']} veces."
    )
    cache.set("research:NOEXISTE", None, 1)
