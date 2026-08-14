"""
Media de 150 sesiones sobre el gráfico de precio del indicador RSU.

Es la media de 30 semanas de Weinstein, la misma que el clasificador de fases
usa para decidir si un valor está en avance o en declive, así que sirve de
referencia común entre el panel y el resto de la terminal.

LO QUE FIJA ESTE FICHERO, que es un solo punto pero se rompe con facilidad:

    la media se calcula sobre el histórico COMPLETO y se recorta después,
    NO sobre el año que se pinta.

Al revés, las primeras 150 velas del gráfico se quedarían sin línea -- y son
justo el tramo donde interesa ver por dónde venía el precio. Es el mismo error
que ya se corrigió una vez en el feed de noticias: filtrar (o recortar) antes
de calcular deja fuera datos que sí existen.

Y los días sin media se OMITEN en vez de mandarse a 0: un cero arrastraría la
escala del panel de precio hasta abajo y aplastaría las velas contra el techo.

Uso:
    cd backend
    python -m pytest tests/test_research_sma150.py -v
"""
import sys, os
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import services.research_service as rs  # noqa: E402


def _historico(n_sesiones, precio_inicial=100.0):
    """OHLCV sintético con tendencia suave, suficiente para que el oscilador
    y la media tengan valores reales."""
    idx = pd.bdate_range(end="2026-08-13", periods=n_sesiones)
    close = pd.Series(np.linspace(precio_inicial, precio_inicial * 1.6, n_sesiones), index=idx)
    return pd.DataFrame({
        "Open":   close * 0.995,
        "High":   close * 1.01,
        "Low":    close * 0.99,
        "Close":  close,
        "Volume": pd.Series(1_000_000.0, index=idx),
    })


def _rsu_flow_con(hist):
    """Ejecuta _get_technical_levels() con ese histórico y devuelve el bloque
    del indicador."""
    tk = MagicMock()
    tk.history.return_value = hist
    tk.info = {}
    with patch.object(rs.yf, "Ticker", return_value=tk):
        niveles = rs._get_technical_levels("TEST")
    return niveles.get("rsu_flow", {})


# ── El punto central ────────────────────────────────────────────────────────

def test_la_media_cubre_todas_las_velas_que_se_pintan():
    """Con dos años descargados y un año pintado, hay 250+ sesiones previas a
    la primera vela visible: la media tiene que existir desde la primera."""
    f = _rsu_flow_con(_historico(504))
    assert f.get("ok") is True, f.get("error")
    assert len(f["sma150"]) == len(f["velas"]), (
        "la media no cubre todas las velas: se ha calculado sobre el recorte, "
        "no sobre el histórico completo")
    assert f["sma150"][0]["time"] == f["velas"][0]["time"]


def test_el_valor_de_la_media_es_el_de_150_sesiones_no_otro():
    """Comprobación de que es una media de 150 y no de 50 o de 200: se
    contrasta el último punto contra el cálculo directo."""
    hist = _historico(504)
    f = _rsu_flow_con(hist)
    esperado = float(hist["Close"].rolling(150).mean().iloc[-1])
    assert f["sma150"][-1]["value"] == pytest.approx(round(esperado, 2), abs=0.02)


# ── Histórico corto: se omite, no se rellena ────────────────────────────────

def test_los_dias_sin_media_se_omiten_en_vez_de_mandarse_a_cero():
    """Con menos histórico que el año que se pinta, las primeras velas no
    tienen media. Un 0 ahí hundiría la escala del panel."""
    f = _rsu_flow_con(_historico(200))
    assert f.get("ok") is True, f.get("error")
    valores = [p["value"] for p in f["sma150"]]
    assert valores, "debería haber al menos algunos puntos con media"
    assert all(v > 0 for v in valores), "ningún punto puede valer 0"
    assert len(f["sma150"]) < len(f["velas"]), (
        "con 200 sesiones no puede haber media para todas las velas pintadas")


def test_la_media_empieza_mas_tarde_pero_termina_con_las_velas():
    """La línea arranca donde de verdad hay dato y llega hasta hoy."""
    f = _rsu_flow_con(_historico(200))
    assert f["sma150"][-1]["time"] == f["velas"][-1]["time"]
    assert f["sma150"][0]["time"] > f["velas"][0]["time"]


def test_sin_histórico_para_la_media_el_indicador_no_se_cae():
    """Menos de 150 sesiones: no hay media en ninguna vela. El resto del
    indicador tiene que seguir funcionando -- la media es un añadido, no un
    requisito."""
    f = _rsu_flow_con(_historico(120))
    assert f.get("ok") is True, f.get("error")
    assert f["sma150"] == []
    assert len(f["osc"]) > 0 and len(f["velas"]) > 0
