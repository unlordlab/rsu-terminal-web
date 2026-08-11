"""
Test del presupuesto de tiempo y la deduplicación del Newsfeed (11/08/2026,
hallazgos #13, #14, #15 y #16 de la auditoría).

Medido con las 14 fuentes reales antes de tocar nada: 13 respondían en menos
de 0,7s y la catorceava (benzinga) se comía los 8s enteros del timeout para
devolver CERO items. Como el bucle esperaba a todas, ESA era la latencia del
endpoint. Tras el cambio: 8,28s -> 2,62s, sin perder items.

Uso:
    cd backend
    python -m pytest tests/test_newsfeed_fuentes.py -v
"""
import os
import sys
import time
from unittest.mock import patch

import pytest
import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import services.newsfeed_service as N  # noqa: E402


# ── #13: el parámetro que prometía un filtro inexistente ─────────────────────

def test_get_newsfeed_ya_no_acepta_un_filtro_de_fuentes_que_no_aplica():
    """Aceptaba `sources` y no lo miraba: get_newsfeed(sources=['ft']) devolvía
    TODAS las fuentes como si el filtro se hubiera aplicado. Ahora falla en
    alto en vez de mentir en silencio."""
    with patch.object(N, "_fetch_all_items", return_value=([], {}, [])):
        with pytest.raises(TypeError):
            N.get_newsfeed(sources=["ft"])
        # los filtros que sí existen siguen funcionando
        assert N.get_newsfeed(impact="HIGH", limit=5)["ok"] is True


# ── #15: deduplicar también por URL ──────────────────────────────────────────

def test_la_url_canonica_ignora_esquema_www_barra_final_y_rastreo():
    a = N._url_canonica("https://www.CNBC.com/2026/08/11/x.html?utm_source=rss&id=7")
    b = N._url_canonica("http://cnbc.com/2026/08/11/x.html/?id=7")
    assert a == b == "cnbc.com/2026/08/11/x.html?id=7"


def test_la_url_canonica_conserva_los_parametros_que_no_son_rastreo():
    """Hay sitios donde el identificador del artículo viaja en la query.
    Vaciarla entera fusionaría noticias que no tienen nada que ver."""
    assert N._url_canonica("https://x.com/n?id=1") != N._url_canonica("https://x.com/n?id=2")


def test_url_vacia_no_rompe_ni_deduplica_de_mas():
    """Sin URL se cae al criterio del título, que es el de siempre. Dos items
    sin URL y con títulos distintos no pueden fusionarse."""
    assert N._url_canonica(None) == ""
    assert N._url_canonica("") == ""


def test_el_mismo_articulo_con_dos_titulares_distintos_se_deduplica():
    """Es el caso que el dedup por título solo no veía: dos fuentes sindican
    el mismo enlace con titulares ligeramente distintos."""
    def _item(titulo, url, sid):
        return {"title": titulo, "url": url, "source_id": sid, "impact": "LOW",
                "sentiment": "neutral", "sector": "GENERAL", "mins_ago": 5}
    items = [
        _item("Fed holds rates", "https://ft.com/a?utm_source=rss", "ft"),
        _item("Fed holds rates steady", "https://www.ft.com/a", "cnbc"),
    ]
    with patch.object(N, "SOURCES", []), \
         patch.object(N, "_fetch_finnhub_news", return_value=(items, True)), \
         patch.object(N.cache, "get", return_value=None), \
         patch.object(N.cache, "set"):
        unique, _estado, _defs = N._fetch_all_items()
    assert len(unique) == 1, "el mismo enlace no debe aparecer dos veces"


# ── #16: reintentar solo lo que merece la pena ───────────────────────────────

def test_un_timeout_no_se_reintenta():
    """Reintentar a un servidor lento solo suma otro timeout al reloj del
    usuario. Es lo que hace que el reintento no cueste latencia."""
    llamadas = []

    def _lento(*a, **kw):
        llamadas.append(1)
        raise requests.exceptions.Timeout()

    with patch.object(N.requests, "get", side_effect=_lento):
        items, sid, ok = N._fetch_source({"id": "x", "url": "https://x.test/rss"})
    assert llamadas == [1], f"reintentó un timeout ({len(llamadas)} intentos)"
    assert items == [] and ok is False


def test_un_fallo_de_conexion_si_se_reintenta_una_vez():
    """Un ConnectionError/DNS suele ser un tropiezo instantáneo del que se sale
    a la primera — ahí el reintento sí sale gratis."""
    llamadas = []

    def _falla_y_luego_va(*a, **kw):
        llamadas.append(1)
        if len(llamadas) == 1:
            raise requests.exceptions.ConnectionError()
        class R:
            status_code = 200
            content = b"<rss><channel></channel></rss>"
        return R()

    with patch.object(N.requests, "get", side_effect=_falla_y_luego_va), \
         patch.object(N, "FUENTE_BACKOFF", 0.01):
        _items, _sid, _ok = N._fetch_source({"id": "x", "url": "https://x.test/rss",
                                             "label": "X"})
    assert len(llamadas) == 2, "debería haber reintentado exactamente una vez"


def test_no_reintenta_indefinidamente():
    llamadas = []

    def _siempre_falla(*a, **kw):
        llamadas.append(1)
        raise requests.exceptions.ConnectionError()

    with patch.object(N.requests, "get", side_effect=_siempre_falla), \
         patch.object(N, "FUENTE_BACKOFF", 0.01):
        items, _sid, ok = N._fetch_source({"id": "x", "url": "https://x.test/rss"})
    assert len(llamadas) == 2
    assert items == [] and ok is False


# ── #14: el conjunto no espera a un rezagado ─────────────────────────────────

def test_una_fuente_colgada_no_retiene_al_resto():
    """Lo que costaba 8 segundos: el bucle esperaba a TODAS las fuentes, así
    que la latencia del endpoint era la de la más lenta aunque no aportara
    nada. Ahora se sirve lo recibido al llegar al tope."""
    rapida = {"id": "rapida", "url": "https://rapida.test/rss"}
    lenta  = {"id": "lenta",  "url": "https://lenta.test/rss"}
    item = {"title": "T", "url": "https://rapida.test/1", "source_id": "rapida",
            "impact": "LOW", "sentiment": "neutral", "sector": "GENERAL", "mins_ago": 1}

    def _fetch(src):
        if src["id"] == "lenta":
            time.sleep(5)
            return [], "lenta", True
        return [item], "rapida", True

    with patch.object(N, "SOURCES", [rapida, lenta]), \
         patch.object(N, "_fetch_source", side_effect=_fetch), \
         patch.object(N, "_fetch_finnhub_news", return_value=([], False)), \
         patch.object(N, "TANDA_DEADLINE", 0.5), \
         patch.object(N.cache, "get", return_value=None), \
         patch.object(N.cache, "set"):
        t0 = time.monotonic()
        unique, estado, _defs = N._fetch_all_items()
        transcurrido = time.monotonic() - t0

    assert transcurrido < 2.0, f"esperó {transcurrido:.1f}s a la fuente colgada"
    assert len(unique) == 1, "la fuente rápida sí debe entrar"
    assert estado["rapida"] is True
    assert estado["lenta"] is False, "la que no contestó se marca como caída"
