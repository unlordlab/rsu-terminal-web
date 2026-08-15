"""
Reddit Pulse: acreditar la fuente, y sobrevivir al bloqueo de StockTwits.

DOS FALLOS, LOS DOS VISTOS EN PRODUCCIÓN EL 15/08/2026, en la misma captura.

1. LA COLUMNA FUENTE SALÍA ENTERA CON GUIONES y la cabecera decía «Reddit».
   La vía del RSS -- la ÚNICA que corre en producción, porque las credenciales
   de OAuth nunca se aprobaron -- sumaba la mención pero no hacía
   `reddit_tickers.add(ticker)`. Eso solo pasaba en la rama de OAuth. Así que
   ninguna fila quedaba acreditada, y la cabecera mentía gracias al respaldo
   `or list(set(sources))`, que enmascaraba justo eso.

   Es el mismo fallo que se «arregló» el 14/08 (entonces la etiqueta miraba el
   puesto en el ranking en vez de la fuente). Aquel arreglo se verificó sobre
   el camino de OAuth, que no se ejecuta.

2. LA COLUMNA SENT SALÍA VACÍA EN LAS QUINCE FILAS. StockTwits está tras un
   challenge de Cloudflare desde la IP del VPS -- documentado en el propio
   fichero desde el 28/07/2026, y confirmado midiendo: 200 desde una IP
   doméstica, nada desde producción. La capa de sentimiento se construyó el
   14/08 sobre esa fuente y se verificó solo en local.

   Ahora el trabajo lo hace un runner de GitHub Actions y el backend lee el
   Gist, con la llamada directa como primera opción por si se desbloquea.

Uso:
    cd backend
    python -m pytest tests/test_reddit_fuentes_y_gist.py -v
"""
import sys, os
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import services.market_service as M  # noqa: E402
from services.cache import cache      # noqa: E402


@pytest.fixture(autouse=True)
def _sin_cache():
    def limpiar():
        for k in ("market:reddit", "market:st_gist"):
            cache.delete(k)
        for t in ("AAPL", "NVDA", "SPY", "CHWY", "ZZZZ"):
            cache.delete(f"market:st_sent:{t}")
    limpiar()
    yield
    limpiar()


# ── 1. La fuente se acredita por donde SALE el ticker ───────────────────────

def _pulso(titulos, trending=(), gist=None):
    """Ejecuta get_reddit_pulse con Reddit vía RSS y StockTwits controlados."""
    fi = MagicMock(); fi.last_price = 10.0; fi.previous_close = 10.0
    with patch.object(M, "_get_reddit_token", return_value=None), \
         patch.object(M, "_fetch_reddit_titles_via_rss", return_value=list(titulos)), \
         patch.object(M, "fetch_trending", return_value=list(trending)), \
         patch.object(M, "_stocktwits_gist", return_value=gist or {}), \
         patch.object(M, "fetch_sentimiento", return_value=None), \
         patch.object(M, "_datos_squeeze", return_value=None), \
         patch.object(M, "_presion_corto_map", return_value={}), \
         patch.object(M, "download_batch", return_value=({}, {})), \
         patch.object(M.yf, "Ticker", return_value=MagicMock(fast_info=fi)):
        return M.get_reddit_pulse()


def test_un_ticker_que_solo_sale_del_rss_se_acredita_a_reddit():
    """El fallo exacto: en producción la vía es el RSS, y no acreditaba nada."""
    r = _pulso(["$NVDA subiendo fuerte hoy", "más sobre $NVDA"])
    fila = next(d for d in r["data"] if d["ticker"] == "NVDA")
    assert fila["fuentes"] == "Reddit"


def test_la_cabecera_solo_dice_lo_que_las_filas_confirman():
    r = _pulso(["$NVDA al alza"])
    fuentes_filas = {f for d in r["data"] for f in (d.get("fuentes") or "").split(" + ") if f}
    assert set(r["sources"]) == fuentes_filas
    assert r["sources"] == ["Reddit"]


def test_si_ninguna_fila_lleva_fuente_la_cabecera_se_queda_vacia():
    """El respaldo `or list(set(sources))` era lo que permitía que la cabecera
    dijera «Reddit» con las quince filas en guiones.

    Solo se nota cuando NINGUNA fila lleva fuente, que es lo que pasa si el
    enriquecimiento falla (yfinance caído): esas filas salen por la rama de
    excepción, sin el campo. Comprobar el caso normal no distingue -- la
    primera versión de este test lo hacía y el sabotaje la cazó."""
    with patch.object(M, "_get_reddit_token", return_value=None), \
         patch.object(M, "_fetch_reddit_titles_via_rss", return_value=["$NVDA al alza"]), \
         patch.object(M, "fetch_trending", return_value=[]), \
         patch.object(M, "_stocktwits_gist", return_value={}), \
         patch.object(M, "_presion_corto_map", return_value={}), \
         patch.object(M, "download_batch", return_value=({}, {})), \
         patch.object(M.yf, "Ticker", side_effect=Exception("yfinance caído")):
        r = M.get_reddit_pulse()
    assert r["data"], "sigue habiendo filas, solo que sin enriquecer"
    assert all(not d.get("fuentes") for d in r["data"])
    assert r["sources"] == [], "sin fila acreditada, la cabecera no puede anunciar nada"


def test_las_dos_fuentes_se_distinguen_en_la_misma_tabla():
    r = _pulso(["$NVDA fuerte"], trending=["CHWY"])
    por_ticker = {d["ticker"]: d["fuentes"] for d in r["data"]}
    assert por_ticker["NVDA"] == "Reddit"
    assert por_ticker["CHWY"] == "StockTwits"
    assert sorted(r["sources"]) == ["Reddit", "StockTwits"]


# ── 2. El Gist cubre lo que el bloqueo impide ───────────────────────────────

def test_si_la_llamada_directa_no_pasa_el_sentimiento_sale_del_gist():
    gist = {"sentimiento": {"NVDA": {"alcistas": 20, "bajistas": 5, "mensajes": 25,
                                     "pct_alcista": 80, "muestra": 30}}}
    with patch.object(M, "fetch_sentimiento", return_value=None), \
         patch.object(M, "_stocktwits_gist", return_value=gist):
        s = M._sentimiento_stocktwits("NVDA")
    assert s["pct_alcista"] == 80


def test_la_llamada_directa_gana_al_gist_cuando_funciona():
    """Es más fresca. Desde un sitio no bloqueado tiene que seguir usándose."""
    directo = {"alcistas": 9, "bajistas": 1, "mensajes": 10, "pct_alcista": 90, "muestra": 12}
    gist    = {"sentimiento": {"NVDA": {"alcistas": 1, "bajistas": 9, "mensajes": 10,
                                        "pct_alcista": 10, "muestra": 12}}}
    with patch.object(M, "fetch_sentimiento", return_value=directo), \
         patch.object(M, "_stocktwits_gist", return_value=gist) as g:
        s = M._sentimiento_stocktwits("NVDA")
    assert s["pct_alcista"] == 90
    g.assert_not_called(), "si la directa responde, no hace falta ni leer el Gist"


def test_sin_directa_y_sin_gist_no_se_inventa_sentimiento():
    with patch.object(M, "fetch_sentimiento", return_value=None), \
         patch.object(M, "_stocktwits_gist", return_value={}):
        assert M._sentimiento_stocktwits("ZZZZ") is None


def test_el_trending_tambien_cae_al_gist():
    """Sin esto, StockTwits deja de aportar tickers Y de acreditarse, aunque el
    runner sí haya podido leerlo."""
    r = _pulso(["$NVDA"], trending=[], gist={"trending": ["CHWY", "SPY"]})
    por_ticker = {d["ticker"]: d["fuentes"] for d in r["data"]}
    assert por_ticker.get("CHWY") == "StockTwits"
    assert "StockTwits" in r["sources"]


# ── 3. El extractor compartido es el mismo para runner y backend ────────────

def test_el_backend_usa_el_extractor_compartido():
    """Si el runner y el backend extrajeran distinto, el runner pediría
    sentimiento de valores que la tabla no enseña, y al revés."""
    from social_tickers import extract_tickers
    # El texto TIENE que llevar ruido que solo el universo descarta. Con solo
    # tickers con "$" delante, el universo no interviene y la comparación no
    # distingue nada -- la primera versión de este test caía en eso y el
    # sabotaje la cazó: pasaba en verde con el universo desactivado.
    texto = "COMPRANDO $NVDA EN JULY CON CAPEX ALTO"
    universo = M._universo_tickers()
    assert "JULY" not in universo and "CAPEX" not in universo, "el ruido tiene que ser ruido"
    esperado = dict(extract_tickers(texto, universo))
    assert esperado == {"NVDA": 2}, "el universo descarta JULY y CAPEX"
    assert dict(M._extract_tickers(texto)) == esperado
    # Y sin universo entrarían: es lo que confirma que la comparación discrimina
    assert set(dict(extract_tickers(texto, None))) > set(esperado)


def test_las_palabras_corrientes_no_cuentan_como_tickers():
    encontrados = dict(M._extract_tickers("THE BEST YOLO MOON CALLS THIS YEAR"))
    assert encontrados == {}


def test_el_trending_no_cuela_cripto_ni_bolsas_extranjeras():
    """Medido el 15/08/2026 sobre el trending real: PEPE.X, LINK.X, ICP.X,
    LUNC.X y AC.TSX ocupaban CINCO de las quince filas con guiones en todas las
    columnas, porque yfinance no sabe cotizarlos. Estaban filtrados de hecho
    solo porque StockTwits no respondía desde el VPS."""
    from unittest.mock import patch, MagicMock
    import social_tickers as ST
    r = MagicMock(); r.status_code = 200
    r.json.return_value = {"symbols": [{"symbol": s} for s in
                           ["PEPE.X", "FLO", "LINK.X", "AC.TSX", "PANW", "ICP.X"]]}
    with patch.object(ST.requests, "get", return_value=r):
        assert ST.fetch_trending() == ["FLO", "PANW"]
