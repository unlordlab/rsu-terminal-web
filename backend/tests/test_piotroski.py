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

# ── Criterio 5 (apalancamiento) con empresas SIN deuda ───────────────────────
# Hallazgo del 29/07/2026, encontrado revisando ANET a mano en la terminal:
# el criterio salía "Apalancamiento no disponible" en empresas que
# sencillamente NO TIENEN deuda. yfinance deja la línea a NaN (o ni la
# incluye) tanto si el dato falta como si el importe es cero, y el código
# trataba los dos casos igual -- así que ANET, MNST y ERIE perdían un punto
# en silencio justo por tener el balance más sano posible (ANET: totalDebt=0
# y 12.400M en caja). No era un fallo del parser: AAPL (78.328M) y KO
# (42.119M) se leían bien, igual que 42 de 42 tickers de una muestra del
# S&P 500.
#
# Ojo con el criterio correcto: Piotroski (2000) mide la deuda a LARGO PLAZO
# sobre activos totales, NO los pasivos totales. En ANET los pasivos/activos
# sí suben (28,8% -> 36,4%), pero 2.276M de esos 3.029M son ingresos
# diferidos -- cobros por adelantado de clientes, señal de demanda y no de
# apalancamiento.

def _bs_base(extra: dict = None) -> pd.DataFrame:
    """Balance con todo lo necesario para que el resto de criterios corran,
    para poder aislar el criterio 5."""
    rows = {
        "Total Assets":           [120, 100],
        "Current Assets":         [60, 45],
        "Current Liabilities":    [30, 30],
        "Ordinary Shares Number": [100, 105],
    }
    rows.update(extra or {})
    return _build_df(rows)


_FIN_BASE = {"Net Income": [12, 8], "Total Revenue": [200, 150], "Gross Profit": [80, 55]}
_CF_BASE  = {"Operating Cash Flow": [20, 15]}


def _criterio_apalancamiento(mock_ticker_factory, balance_sheet):
    fake = mock_ticker_factory(balance_sheet, _build_df(_FIN_BASE), _build_df(_CF_BASE))
    with patch("services.research_service.yf.Ticker", return_value=fake):
        result = _get_piotroski_score("TEST")
    return result["criteria"][4], result


def test_sin_ninguna_linea_de_deuda_se_lee_como_cero_no_como_dato_ausente(mock_ticker_factory):
    """El caso ANET: ni 'Long Term Debt' ni 'Total Debt' en el balance."""
    c5, result = _criterio_apalancamiento(mock_ticker_factory, _bs_base())
    assert c5["pass"] is True, (
        "Una empresa sin deuda debe PASAR el criterio de apalancamiento: su "
        f"ratio no ha subido. Salió {c5['pass']} ({c5['label']})."
    )
    assert c5["label"] == "Sin deuda a largo plazo", (
        "Merece etiqueta propia: 'estable o ha bajado' no describe a quien "
        "nunca tuvo deuda."
    )


def test_linea_de_deuda_presente_pero_toda_a_nan_tambien_es_cero(mock_ticker_factory):
    """Forma exacta en la que yfinance devuelve ANET: la fila existe en el
    índice, con NaN en todos los ejercicios. El line() original la daba por
    buena por estar el nombre presente."""
    bs = _bs_base({
        "Long Term Debt And Capital Lease Obligation": [float("nan"), float("nan")],
        "Total Debt":                                  [float("nan"), float("nan")],
    })
    c5, _ = _criterio_apalancamiento(mock_ticker_factory, bs)
    assert c5["pass"] is True and c5["label"] == "Sin deuda a largo plazo"


def test_con_deuda_total_pero_sin_desglose_a_largo_plazo_si_es_dato_ausente(mock_ticker_factory):
    """Aquí el 'no disponible' SÍ es la respuesta honesta: la empresa tiene
    deuda, pero no sabemos cuánta es a largo plazo. No se puede asumir cero."""
    bs = _bs_base({"Total Debt": [50, 40]})
    c5, _ = _criterio_apalancamiento(mock_ticker_factory, bs)
    assert c5["pass"] is None, (
        "Con deuda total conocida y sin desglose a largo plazo no se puede "
        f"inventar un cero. Salió {c5['pass']} ({c5['label']})."
    )
    assert c5["label"] == "Apalancamiento no disponible"


def test_apalancamiento_que_sube_sigue_suspendiendo(mock_ticker_factory):
    """Que el fix no convierta en aprobado lo que debe suspender: la deuda
    crece más rápido que los activos (25% vs 20%)."""
    bs = _bs_base({"Long Term Debt": [30, 20]})
    c5, _ = _criterio_apalancamiento(mock_ticker_factory, bs)
    assert c5["pass"] is False
    assert c5["label"] == "El apalancamiento ha aumentado"


def test_deuda_que_baja_a_cero_no_se_etiqueta_como_sin_deuda(mock_ticker_factory):
    """Caso MNST: llegó a cero este año pero venía de tener deuda. Pasa el
    criterio, pero la etiqueta correcta es 'ha bajado', no 'sin deuda'."""
    bs = _bs_base({"Long Term Debt": [0, 20]})
    c5, _ = _criterio_apalancamiento(mock_ticker_factory, bs)
    assert c5["pass"] is True
    assert c5["label"] == "Apalancamiento estable o ha bajado"
