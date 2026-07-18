"""
Test de regresión para _get_piotroski_score() -- ver conversación
18/07/2026 sobre robustecer los cálculos críticos antes de seguir
añadiendo funciones nuevas.

No toca la red ni yfinance de verdad: se mockea yf.Ticker para inyectar
balances/estados financieros conocidos a mano, y se comprueba que el
resultado coincide con lo que se puede calcular manualmente con esos
mismos números. Si algún día un cambio en research_service.py rompe la
fórmula (aunque sea sin querer, un refactor que toque una línea), este
test falla ANTES de desplegar, no semanas después cuando alguien
pregunte por qué un Piotroski no cuadra.

Uso:
    cd backend
    pip install -r ../requirements-dev.txt --break-system-packages
    pytest tests/test_piotroski.py -v
"""
import sys
import os
from unittest.mock import patch, MagicMock

import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.research_service import _get_piotroski_score  # noqa: E402


def _build_df(rows: dict, col_recent="2025-12-31", col_prior="2024-12-31") -> pd.DataFrame:
    """Construye un DataFrame con la misma forma que devuelve yfinance
    para balance_sheet/financials/cashflow: índice = nombre de la línea
    contable, columnas = fechas (más reciente primero, igual que hace
    yfinance de verdad)."""
    return pd.DataFrame(rows, index=[col_recent, col_prior]).T


@pytest.fixture
def mock_ticker_factory():
    """Devuelve una función que crea un yf.Ticker falso con los 3
    estados financieros que le pasemos."""
    def _factory(balance_sheet: pd.DataFrame, financials: pd.DataFrame, cashflow: pd.DataFrame):
        fake = MagicMock()
        fake.balance_sheet = balance_sheet
        fake.financials = financials
        fake.cashflow = cashflow
        return fake
    return _factory


def test_piotroski_empresa_excelente(mock_ticker_factory):
    """Empresa que mejora en los 9 criterios interanualmente -> score = 9."""
    balance_sheet = _build_df({
        "Total Assets":               [120, 100],
        "Long Term Debt":             [30, 40],
        "Current Assets":             [60, 45],
        "Current Liabilities":        [30, 30],
        "Ordinary Shares Number":     [100, 105],  # menos acciones ahora = sin dilución
    })
    financials = _build_df({
        "Net Income":    [15, 8],
        "Total Revenue": [100, 80],
        "Gross Profit":  [50, 38],
    })
    cashflow = _build_df({
        "Operating Cash Flow": [20, 10],
    })

    fake_ticker = mock_ticker_factory(balance_sheet, financials, cashflow)
    with patch("services.research_service.yf.Ticker", return_value=fake_ticker):
        result = _get_piotroski_score("TESTGOOD")

    assert result["score"] == 9, f"Se esperaba score=9 (todo mejora), salió {result['score']}. Criterios: {result['criteria']}"
    assert result["label"] == "EXCELENTE"
    assert result["max"] == 9
    assert all(c["pass"] is True for c in result["criteria"]), "Los 9 criterios deberían pasar en este caso"


def test_piotroski_empresa_debil(mock_ticker_factory):
    """Empresa con pérdidas, CFO negativo, apalancamiento subiendo, dilución
    y márgenes empeorando -> solo pasa 1 de 9 criterios (calidad del
    beneficio: CFO(-2) > Net Income(-5), aunque ambos sean negativos)."""
    balance_sheet = _build_df({
        "Total Assets":               [100, 100],
        "Long Term Debt":             [60, 40],
        "Current Assets":             [40, 50],
        "Current Liabilities":        [40, 40],
        "Ordinary Shares Number":     [110, 100],  # más acciones ahora = dilución
    })
    financials = _build_df({
        "Net Income":    [-5, 3],
        "Total Revenue": [100, 100],
        "Gross Profit":  [20, 25],
    })
    cashflow = _build_df({
        "Operating Cash Flow": [-2, 5],
    })

    fake_ticker = mock_ticker_factory(balance_sheet, financials, cashflow)
    with patch("services.research_service.yf.Ticker", return_value=fake_ticker):
        result = _get_piotroski_score("TESTBAD")

    assert result["score"] == 1, f"Se esperaba score=1, salió {result['score']}. Criterios: {result['criteria']}"
    assert result["label"] == "DÉBIL"

    # El único criterio que debería pasar es "calidad del beneficio" (CFO > Net Income)
    etiquetas_pasadas = [c["label"] for c in result["criteria"] if c["pass"] is True]
    assert etiquetas_pasadas == ["Beneficio de buena calidad (CFO > Bº Neto)"], \
        f"Se esperaba que solo pasara el criterio de calidad del beneficio, pasaron: {etiquetas_pasadas}"


def test_piotroski_datos_insuficientes_devuelve_vacio(mock_ticker_factory):
    """Si faltan las líneas base imprescindibles (Total Assets/Net Income/
    Operating Cash Flow), debe devolver {} en vez de reventar o inventar
    un score con datos a medias."""
    balance_sheet = pd.DataFrame()  # vacío a propósito
    financials = pd.DataFrame()
    cashflow = pd.DataFrame()

    fake_ticker = mock_ticker_factory(balance_sheet, financials, cashflow)
    with patch("services.research_service.yf.Ticker", return_value=fake_ticker):
        result = _get_piotroski_score("TESTEMPTY")

    assert result == {}, f"Con datos vacíos se esperaba {{}}, salió {result}"