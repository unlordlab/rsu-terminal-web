"""
Reddit Pulse: sentimiento real y señales de estrangulamiento de cortos.

EL FALLO QUE LO ORIGINÓ, reportado por el usuario («creo que stocktwits no
funciona»): funcionaba, y de hecho era la ÚNICA fuente que aportaba tickers ese
día -- pero todas las filas salían rotuladas «Reddit Top». La etiqueta no
miraba la fuente, miraba el puesto en el ranking:

    hype_suffix = " Reddit Top" if hype_raw > 0.5 else (" StockTwits" if in_st else "")

Cualquier valor en la mitad alta se anunciaba como Reddit. Y la cabecera decía
«Reddit + StockTwits» porque a Reddit le bastaba con responder, aunque no se
extrajera de sus titulares ni un solo ticker.

LO QUE SE AÑADE ENCIMA: el reparto alcista/bajista real (la etiqueta que el
propio autor pone a su mensaje, no sentimiento adivinado del texto) y un
recuento de señales de estrangulamiento con sus ingredientes explicables.

LO QUE FIJA ESTE FICHERO:
1. La etiqueta de fuente dice de dónde SALE el ticker.
2. Sin mensajes etiquetados no se fabrica un 50/50.
3. Una señal que no se puede evaluar baja el denominador en vez de contar como
   incumplida -- un fondo cotizado no tiene posiciones prestadas y no puede
   aparentar «0 de 5» cuando en realidad son «0 de 2».

Uso:
    cd backend
    python -m pytest tests/test_reddit_pulse_sentimiento.py -v
"""
import sys, os
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import services.market_service as M  # noqa: E402


# ── 1. La etiqueta dice la FUENTE, no el puesto ─────────────────────────────

def _enriquecer(ticker, menciones, maximo, st, rd):
    fi = MagicMock(); fi.last_price = 10.0; fi.previous_close = 10.0
    with patch.object(M.yf, "Ticker", return_value=MagicMock(fast_info=fi)), \
         patch.object(M, "_sentimiento_stocktwits", return_value=None), \
         patch.object(M, "_datos_squeeze", return_value=None):
        return M._enrich_ticker(ticker, menciones, maximo, st, None, rd)


def test_un_ticker_solo_de_stocktwits_no_se_rotula_como_reddit():
    """El caso exacto del fallo: va primero del ranking (hype alto) pero viene
    entero de StockTwits."""
    r = _enriquecer("AVGO", 20, 20, st=["AVGO"], rd=set())
    assert r["fuentes"] == "StockTwits"
    assert "Reddit" not in r["social_hype"]


def test_un_ticker_solo_de_reddit_se_rotula_como_reddit():
    r = _enriquecer("GME", 20, 20, st=[], rd={"GME"})
    assert r["fuentes"] == "Reddit"


def test_un_ticker_de_las_dos_fuentes_las_nombra_a_las_dos():
    r = _enriquecer("NVDA", 20, 20, st=["NVDA"], rd={"NVDA"})
    assert r["fuentes"] == "Reddit + StockTwits"


def test_el_puesto_en_el_ranking_no_decide_la_etiqueta():
    """Mismo origen, distinto puesto: la etiqueta no puede cambiar. Con el
    código viejo, el de arriba decía Reddit y el de abajo StockTwits."""
    arriba = _enriquecer("AAA", 20, 20, st=["AAA"], rd=set())
    abajo  = _enriquecer("BBB", 1, 20, st=["BBB"], rd=set())
    assert arriba["fuentes"] == abajo["fuentes"] == "StockTwits"


# ── 2. El sentimiento no se fabrica ─────────────────────────────────────────

def _respuesta_st(etiquetas):
    r = MagicMock(); r.status_code = 200
    r.json.return_value = {"messages": [
        {"entities": {"sentiment": {"basic": e} if e else None}} for e in etiquetas]}
    return r


@pytest.fixture(autouse=True)
def sin_cache():
    from services.cache import cache
    for t in ("GME", "AAA", "BBB", "NVDA", "AVGO", "XYZ"):
        cache.delete(f"market:st_sent:{t}")
        cache.delete(f"market:squeeze:{t}")
    yield


def test_cuenta_las_etiquetas_que_pone_cada_autor():
    with patch.object(M.requests, "get", return_value=_respuesta_st(
            ["Bullish"] * 22 + ["Bearish"] * 2 + [None] * 6)):
        s = M._sentimiento_stocktwits("GME")
    assert s["alcistas"] == 22 and s["bajistas"] == 2
    assert s["mensajes"] == 24
    assert s["pct_alcista"] == 92
    assert s["muestra"] == 30, "la muestra tiene que incluir los no etiquetados"


def test_sin_mensajes_etiquetados_devuelve_none_y_no_un_cincuenta_por_ciento():
    """Un 50/50 de relleno sería indistinguible de un valor realmente
    dividido, que es el patrón de dato fabricado que el proyecto evita."""
    with patch.object(M.requests, "get", return_value=_respuesta_st([None] * 30)):
        assert M._sentimiento_stocktwits("XYZ") is None


def test_si_la_fuente_falla_no_se_inventa_sentimiento():
    fallo = MagicMock(); fallo.status_code = 404
    with patch.object(M.requests, "get", return_value=fallo):
        assert M._sentimiento_stocktwits("XYZ") is None


# ── 3. Lo que no se puede evaluar no suspende ──────────────────────────────

def test_lo_que_no_se_puede_medir_baja_el_denominador():
    """Un fondo cotizado no tiene posiciones prestadas ni float. Sin esto
    aparentaría «0 de 5» cuando en realidad no se le pueden medir tres."""
    n = M._senales_squeeze(None, 1.0, None)
    assert n["de"] == 1, "solo el volumen es evaluable"
    assert n["n"] == 0


def test_un_caso_de_libro_las_cumple_todas():
    """Números reales de UMAC medidos el 14/08/2026."""
    sq = {"pct_float_corto": 20.1, "dias_para_cubrir": 2.5, "float": 30_000_000}
    n = M._senales_squeeze(sq, 3.0, {"pct_alcista": 88})
    assert n["n"] == n["de"] == 5
    assert any("float en corto" in c for c in n["cumplidas"])


def test_cada_senal_cumplida_se_puede_nombrar():
    """El recuento tiene que ser desglosable: es lo que lo separa de una
    puntuación opaca."""
    sq = {"pct_float_corto": 47.4, "dias_para_cubrir": 2.2, "float": 500_000_000}
    n = M._senales_squeeze(sq, 1.0, {"pct_alcista": 81})
    assert len(n["cumplidas"]) == n["n"]
    assert all(isinstance(c, str) and c for c in n["cumplidas"])


def test_un_valor_muy_corto_pero_dificil_de_estrangular_no_las_cumple_todas():
    """GME el 14/08/2026: 13,1% del float en corto pero 16 días para cubrir.
    Mucho corto no es lo mismo que un estrangulamiento fácil."""
    sq = {"pct_float_corto": 13.1, "dias_para_cubrir": 16.2, "float": 409_000_000}
    n = M._senales_squeeze(sq, 1.0, {"pct_alcista": 60})
    assert n["n"] == 0 and n["de"] == 5
