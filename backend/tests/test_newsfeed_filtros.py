"""
Test de los filtros y los tickers del Newsfeed (11/08/2026, hallazgos #17,
#18 y #19 de la auditoría).

Lo que más importa aquí no es que los filtros filtren, sino DÓNDE filtran: el
backend recorta a `limit` DESPUÉS de filtrar, así que un filtro implementado
en el navegador sobre lo ya descargado deja fuera noticias que sí existen. Es
el error que ya se pagó con el filtro de impacto (auditoría #7: pedir HIGH
enseñaba 9 de las 22 que había), y `source` y `q` se han añadido por el mismo
camino para no repetirlo.

Uso:
    cd backend
    python -m pytest tests/test_newsfeed_filtros.py -v
"""
import os
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import services.newsfeed_service as N  # noqa: E402


def _item(titulo, sid="cnbc", desc="", impacto="LOW", tickers=None):
    return {"title": titulo, "desc": desc, "url": f"https://x.test/{titulo[:8]}",
            "source": sid.upper(), "source_id": sid, "source_url": "",
            "impact": impacto, "sentiment": "neutral", "sector": "GENERAL",
            "mins_ago": 5, "pub": "", "tickers": tickers or []}


def _feed(items):
    """Salta el fetch: estos tests son sobre el filtrado, no sobre la red."""
    return patch.object(N, "_fetch_all_items",
                        return_value=(items, {"cnbc": True, "ft": True}, []))


# ── #18: filtro por fuente ───────────────────────────────────────────────────

def test_el_filtro_de_fuente_devuelve_solo_esa_fuente():
    items = [_item("A", "cnbc"), _item("B", "ft"), _item("C", "cnbc")]
    with _feed(items):
        r = N.get_newsfeed(source="cnbc")
    assert {i["source_id"] for i in r["items"]} == {"cnbc"}
    assert r["filtrados"] == 2


def test_una_fuente_inexistente_no_devuelve_todo_por_error():
    """El fallo silencioso que se acaba de quitar (#13) era exactamente este:
    un filtro que no filtra y devuelve el feed entero como si lo hubiera
    aplicado."""
    with _feed([_item("A", "cnbc"), _item("B", "ft")]):
        r = N.get_newsfeed(source="noexiste")
    assert r["items"] == [] and r["filtrados"] == 0


# ── #19: búsqueda por texto ──────────────────────────────────────────────────

def test_la_busqueda_mira_titular_descripcion_y_tickers():
    items = [
        _item("Nada que ver", "cnbc"),
        _item("Un titular sobre Tesla", "cnbc"),
        _item("Otro", "ft", desc="menciona Tesla en el resumen"),
        _item("Tercero", "ft", tickers=["TSLA"]),
    ]
    with _feed(items):
        assert N.get_newsfeed(q="tesla")["filtrados"] == 2
        assert N.get_newsfeed(q="TSLA")["filtrados"] == 1


def test_la_busqueda_ignora_mayusculas_y_espacios_sobrantes():
    with _feed([_item("La Reserva Federal sube tipos")]):
        for termino in ("federal", "FEDERAL", "  Federal  "):
            assert N.get_newsfeed(q=termino)["filtrados"] == 1


def test_una_busqueda_vacia_no_filtra_nada():
    with _feed([_item("A"), _item("B")]):
        for vacio in ("", "   ", None):
            assert N.get_newsfeed(q=vacio)["filtrados"] == 2


# ── El punto de todo esto: filtrar ANTES de recortar ─────────────────────────

def test_los_filtros_se_aplican_antes_del_limite_no_despues():
    """90 noticias de cnbc y 10 de ft. Pidiendo ft con limit=5, si el filtro
    se aplicara después del recorte saldrían 0 (las 5 primeras son de cnbc).
    Es el mismo fallo que tenía el filtro de impacto (#7)."""
    items = [_item(f"cnbc {n}", "cnbc") for n in range(90)] + \
            [_item(f"ft {n}", "ft") for n in range(10)]
    with _feed(items):
        r = N.get_newsfeed(source="ft", limit=5)
    assert r["filtrados"] == 10, "hay 10 de ft en el ciclo completo"
    assert len(r["items"]) == 5, "la página muestra 5"
    assert all(i["source_id"] == "ft" for i in r["items"])


def test_filtrados_cuenta_coincidencias_no_lo_que_cabe_en_la_pagina():
    """La UI dice «N de M». Sin este campo solo podría decir cuántas caben,
    que es otra cosa."""
    items = [_item(f"x {n}", "ft") for n in range(30)]
    with _feed(items):
        r = N.get_newsfeed(source="ft", limit=5)
    assert (r["filtrados"], len(r["items"]), r["total"]) == (30, 5, 30)


# ── #17: tickers en los titulares ────────────────────────────────────────────

def test_un_cashtag_se_acepta_aunque_no_este_en_el_sp500():
    """La intención es explícita: quien escribe $OUST está nombrando un
    ticker, aunque sea una small cap fuera del índice."""
    assert N._extraer_tickers("Thinking about investing in $OUST") == ["OUST"]


def test_un_simbolo_del_sp500_en_mayusculas_se_reconoce():
    assert "CME" in N._extraer_tickers("CME to debut hockey futures")


def test_una_palabra_en_mayusculas_que_no_es_ticker_no_cuela():
    """Sin la comprobación contra el S&P 500, cualquier sigla del titular se
    convertiría en un enlace a una página de Research vacía."""
    assert N._extraer_tickers("BREAKING NEWS FROM THE ECB TODAY") == []


def test_las_palabras_inglesas_corrientes_no_se_toman_por_tickers():
    """LOW es Lowe's y FAST es Fastenal, pero en un titular casi nunca lo son.
    Se prefiere perder la mención antes que fabricar un enlace falso."""
    assert N._extraer_tickers("Shares hit a new LOW after a FAST selloff") == []


def test_un_cashtag_si_recupera_esas_palabras():
    """Si de verdad se habla de Lowe's, el cashtag lo deja claro."""
    assert N._extraer_tickers("$LOW beats estimates") == ["LOW"]


def test_los_related_de_finnhub_van_primero_y_no_se_adivinan():
    r = N._extraer_tickers("Un titular cualquiera", related=[{"symbol": "NVDA"}])
    assert r == ["NVDA"]


def test_como_mucho_tres_tickers_por_titular():
    """Un titular con seis enlaces deja de ser un titular."""
    r = N._extraer_tickers("x", related=[{"symbol": s} for s in
                                         ("AAPL", "MSFT", "NVDA", "AMZN", "META")])
    assert len(r) == 3


def test_no_se_repiten_si_llegan_por_dos_caminos():
    r = N._extraer_tickers("$NVDA sube", related=[{"symbol": "NVDA"}])
    assert r == ["NVDA"]
