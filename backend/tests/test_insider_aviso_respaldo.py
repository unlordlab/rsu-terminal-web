"""
Insider Flow: cuando la SEC no responde, la pantalla tiene que decirlo.

EL FALLO, encontrado el 14/08/2026 al revisar cuántas formas distintas tenía el
proyecto de avisar de que un dato no es lo que aparenta. `get_insider_ticker()`
ya hacía lo correcto en el backend: si EDGAR falla y hay histórico en disco,
sirve lo guardado en vez de un error, y devuelve la advertencia redactada:

    "source":  "Histórico guardado en la terminal — SEC EDGAR no respondió,
                puede faltar lo más reciente"
    "parcial": True

El frontend no leía ninguno de los dos. Y era peor que callar: el subtítulo de
la tarjeta estaba clavado a 'SEC EDGAR Form 4 · Últimos 6 meses', así que
durante una caída de la SEC la pantalla AFIRMABA un origen que no era el suyo.

LO QUE FIJA ESTE FICHERO:
1. El camino de respaldo emite `avisos` en el formato que pinta el envoltorio
   compartido, no solo un texto suelto que nadie recoge.
2. El camino normal NO trae aviso -- si apareciera siempre, dejaría de mirarse.
3. Sin histórico en disco no se sirve una tabla vacía disfrazada: se devuelve
   un error de verdad.

Uso:
    cd backend
    python -m pytest tests/test_insider_aviso_respaldo.py -v
"""
import sys, os
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import services.insider_service as I  # noqa: E402


TX = [{
    "ticker": "AAPL", "insider_name": "Tim Cook", "title": "CEO",
    "type": "Compra", "type_code": "P", "shares": 1000, "value": 250000,
    "tx_date": "2026-08-01", "date": "2026-08-01",
}]


@pytest.fixture(autouse=True)
def _sin_cache():
    from services.cache import cache
    cache.delete("insider:ticker:AAPL")
    yield
    cache.delete("insider:ticker:AAPL")


def _con_edgar_caido(locales):
    """EDGAR lanza; en disco hay lo que se le pase."""
    return (
        patch.object(I, "_sec_get", side_effect=Exception("503 desde EDGAR")),
        patch.object(I, "_transacciones_locales", return_value=locales),
        patch("services.cartera_service.get_cartera_tickers", return_value=set()),
    )


def test_si_la_sec_no_responde_el_aviso_viaja_en_la_respuesta():
    a, b, c = _con_edgar_caido(TX)
    with a, b, c:
        r = I.get_insider_ticker("AAPL")
    assert r["ok"] is True, "con histórico en disco se sirve lo que hay"
    assert r["parcial"] is True
    assert r["avisos"], "el aviso tiene que llegar al frontend, no quedarse en el log"
    aviso = r["avisos"][0]
    assert aviso["tipo"] == "parcial"
    assert "SEC" in aviso["mensaje"] and "puede faltar" in aviso["mensaje"]


def test_el_aviso_dice_de_donde_sale_el_dato_de_verdad():
    """No basta con «hubo un problema»: lo que el usuario necesita saber es que
    está mirando el histórico local, no lo que la SEC tiene ahora mismo."""
    a, b, c = _con_edgar_caido(TX)
    with a, b, c:
        r = I.get_insider_ticker("AAPL")
    assert "terminal" in r["avisos"][0]["mensaje"].lower()


def test_el_camino_normal_no_trae_aviso():
    """Un aviso que sale siempre deja de leerse a los dos días.

    Hay que llegar de verdad al camino bueno, no dar por hecho que se llega: la
    primera versión de este test mockeaba EDGAR con un 404, caía en el respaldo
    y el `assert` quedaba dentro de un `if` que nunca se cumplía -- pasaba en
    verde sin comprobar nada. Lo cazó el sabotaje. Un feed Atom válido y vacío
    sí recorre el camino normal hasta el final."""
    feed = type("R", (), {
        "status_code": 200,
        "content": b'<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"></feed>',
        "text": "",
    })()
    with patch.object(I, "_transacciones_locales", return_value=TX), \
         patch.object(I, "_sec_get", return_value=feed), \
         patch("services.cartera_service.get_cartera_tickers", return_value=set()):
        r = I.get_insider_ticker("AAPL")
    assert r["ok"] is True and not r.get("parcial"), "esto tiene que ser el camino bueno"
    assert r["source"] == "SEC EDGAR Form 4"
    assert not r.get("avisos"), "sin incidencia no debe haber banda"


def test_sin_histórico_en_disco_no_se_finge_una_respuesta():
    a, b, c = _con_edgar_caido([])
    with a, b, c:
        r = I.get_insider_ticker("AAPL")
    assert r["ok"] is False
    assert "error" in r


def test_la_respuesta_de_respaldo_no_se_cachea():
    """Si se cacheara, la versión incompleta se serviría una hora entera aunque
    la SEC ya hubiera vuelto."""
    from services.cache import cache
    a, b, c = _con_edgar_caido(TX)
    with a, b, c:
        I.get_insider_ticker("AAPL")
    assert cache.get("insider:ticker:AAPL") is None
