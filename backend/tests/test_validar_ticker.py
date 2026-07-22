"""
Test de regresión para routers/watchlist.py::_validar_ticker() -- cierra el
vector de auto-XSS de la sesión 11 (commit 2bcf259): antes solo se
limitaba la longitud (Field(max_length=15)), así que un ticker con
comillas/HTML se guardaba tal cual y se reflejaba sin escapar en
watchlist.js (onclick/data-ticker). El regex ahora es el límite real.

Uso:
    cd backend
    python -m pytest tests/test_validar_ticker.py -v
"""
import sys
import os

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from routers.watchlist import _validar_ticker  # noqa: E402


@pytest.mark.parametrize("ticker", ["AAPL", "BRK.B", "^GSPC", "EURUSD=X", "2222.SR"])
def test_validar_ticker_acepta_tickers_reales_variados(ticker):
    assert _validar_ticker(ticker) == ticker.strip().upper()


@pytest.mark.parametrize("payload", [
    "<script>alert(1)</script>",
    'AAPL"onmouseover="x"',
    "AAPL';DROP TABLE x;--",
])
def test_validar_ticker_rechaza_html_o_comillas(payload):
    with pytest.raises(ValueError):
        _validar_ticker(payload)


def test_validar_ticker_rechaza_mas_de_12_caracteres():
    """Antes el límite efectivo era 15 (Field(max_length=15)) con
    cualquier contenido; ahora el propio regex {1,12} es el límite real
    y más estricto."""
    with pytest.raises(ValueError):
        _validar_ticker("A" * 13)
