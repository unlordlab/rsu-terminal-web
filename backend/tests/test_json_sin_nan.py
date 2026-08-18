"""
Un NaN suelto no puede volver a borrar un módulo entero de la pantalla.

Ha pasado tres veces, siempre por lo mismo -- yfinance devuelve NaN en la barra
en curso o en una semana de festivo -- pero con DOS síntomas distintos según por
dónde salga el dato, y por eso costó reconocerlo como un solo problema:

  · Por HTTP: Starlette serializa con `allow_nan=False`, así que lanza y FastAPI
    devuelve "Internal Server Error" en TEXTO PLANO. El navegador intenta
    parsearlo como JSON y enseña «Unexpected token 'I', "Internal S"...».
    Visto en /api/v1/watchlist (25/07) y en /api/v1/market/liquidity (17/08).

  · Por WebSocket: `json.dumps` SÍ acepta NaN y escribe el literal `NaN`, que no
    es JSON válido. El navegador falla al parsear, el `catch` del onmessage se lo
    traga con un console.warn, y NO se emite ningún evento. El ticker del topbar
    se quedó en «Conectando...» para siempre. Medido el 17/08: 10 de los 12
    precios de la carga venían NaN.

Uso:
    cd backend
    python -m pytest tests/test_json_sin_nan.py -v
"""
import json
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from json_seguro import sanear, JSONSeguro  # noqa: E402


def test_los_no_finitos_salen_como_null():
    """`null` es lo que de verdad significan: no hay dato. El frontend ya lo
    sabe tratar; un NaN, en cambio, tumba la respuesta entera."""
    assert sanear(float("nan")) is None
    assert sanear(float("inf")) is None
    assert sanear(float("-inf")) is None


def test_no_toca_los_valores_buenos():
    for v in (0.0, -1.5, 42, "texto", True, False, None):
        assert sanear(v) == v


def test_entra_en_listas_y_diccionarios_anidados():
    sucio = {"serie": [{"value": float("nan")}, {"value": 3.0}],
             "meta": {"corr": float("inf"), "n": 2}}
    limpio = sanear(sucio)
    assert limpio["serie"][0]["value"] is None
    assert limpio["serie"][1]["value"] == 3.0
    assert limpio["meta"]["corr"] is None
    assert limpio["meta"]["n"] == 2


def test_lo_saneado_sobrevive_al_serializador_de_starlette():
    """Ésta es la garantía de verdad: `allow_nan=False` es lo que usa Starlette,
    y es lo que lanzaba el 500 en texto plano."""
    sucio = {"spx": [{"date": "2026-08-17", "value": float("nan")}]}
    try:
        json.dumps(sucio, allow_nan=False)
        raise AssertionError("referencia: sin sanear deberia lanzar")
    except ValueError:
        pass
    json.dumps(sanear(sucio), allow_nan=False)   # no debe lanzar


def test_lo_saneado_no_escribe_el_literal_NaN_que_el_navegador_rechaza():
    """Para el WebSocket: `json.dumps` por defecto acepta NaN y escribe `NaN`,
    que JSON.parse rechaza. El mensaje se descartaba sin que nada lo dijera."""
    sucio = {"prices": [{"name": "GOLD", "price": float("nan")}]}
    assert "NaN" in json.dumps(sucio), "referencia: sin sanear se cuela el literal"
    assert "NaN" not in json.dumps(sanear(sucio))


def test_la_respuesta_de_la_app_sanea_al_renderizar():
    cuerpo = JSONSeguro(content={"ok": True, "v": float("nan")}).body
    assert b"NaN" not in cuerpo
    assert json.loads(cuerpo)["v"] is None
