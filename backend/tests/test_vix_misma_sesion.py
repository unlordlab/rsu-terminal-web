"""
Newsfeed #66: la curva del VIX solo se calcula con las dos patas del MISMO día,
y el hueco del histórico de VIX3M se rellena con CBOE.

EL CASO, medido el 14/09/2026. `^VIX3M` no tiene barras diarias en yfinance
desde el 17/07/2026: la serie salta de esa fecha a una única fila suelta con la
cotización de hoy. Esa fila es buena —en sesión es el precio en vivo—, así que
Market y el Algoritmo en vivo, que piden 5 días y cogen el último valor, estaban
bien. Lo que fallaba:

  · El BACKTEST del Algoritmo recorta el histórico por fecha y comparaba el VIX
    de cada día entre el 18/07 y el 11/09 con el VIX3M del 17/07: 39 sesiones,
    1,7 puntos de error medio, y el 29/07 puntuó «pánico agudo» (+7) cuando era
    «curva tensa» (+3).
  · El BRIEFING publicaba «Estructura: CONTANGO» sin escala —el contango es lo
    normal— y sin mirar de qué día era cada pata.

CBOE publica el histórico oficial y cuadra al céntimo con yfinance en los 86
días de VIX3M en que los dos tienen dato.

Uso:
    cd backend
    python -m pytest tests/test_vix_misma_sesion.py -v
"""
import inspect
import os
import sys
from datetime import date

import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'shared'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'scripts'))

import vix_curve as V  # noqa: E402

TZ = "America/Chicago"


def _df(fechas, valores, tz=TZ):
    idx = pd.DatetimeIndex(pd.to_datetime(fechas)).tz_localize(tz)
    return pd.DataFrame({"Close": valores}, index=idx)


# ── misma_sesion ────────────────────────────────────────────────────────────

def test_misma_sesion_con_su_margen():
    assert V.misma_sesion(date(2026, 9, 14), date(2026, 9, 14))
    assert V.misma_sesion(date(2026, 9, 14), date(2026, 9, 11)), "viernes y lunes"
    assert V.misma_sesion(date(2026, 9, 8), date(2026, 9, 4)), "fin de semana con festivo"
    assert not V.misma_sesion(date(2026, 9, 14), date(2026, 7, 17)), "EL caso"
    assert not V.misma_sesion(None, date(2026, 9, 14))
    assert V.misma_sesion(pd.Timestamp("2026-09-14", tz=TZ), pd.Timestamp("2026-09-14"))


# ── completar_con_cboe ──────────────────────────────────────────────────────

def test_rellena_el_hueco_sin_tocar_lo_que_habia():
    yf_df = _df(["2026-07-16", "2026-07-17", "2026-09-14"], [19.50, 20.54, 19.39])
    cboe = pd.Series([19.50, 20.54, 21.50, 18.60, 99.0],
                     index=pd.to_datetime(["2026-07-16", "2026-07-17", "2026-07-29", "2026-09-11", "2026-09-14"]))
    completo, n = V.completar_con_cboe(yf_df, cboe)
    assert n == 2
    assert completo.index.tz is not None, "misma zona horaria que yfinance, o fallan las comparaciones"
    fechas = [d.strftime("%Y-%m-%d") for d in completo.index]
    assert fechas == ["2026-07-16", "2026-07-17", "2026-07-29", "2026-09-11", "2026-09-14"]
    assert completo["Close"].iloc[-1] == 19.39, "no se pisa el valor de yfinance"


def test_sin_cboe_no_cambia_nada():
    yf_df = _df(["2026-07-17", "2026-09-14"], [20.54, 19.39])
    completo, n = V.completar_con_cboe(yf_df, pd.Series(dtype=float))
    assert n == 0 and completo is yf_df


def test_historico_cboe_nunca_levanta(monkeypatch):
    import requests

    def caido(*a, **k):
        raise requests.ConnectionError("sin red")
    monkeypatch.setattr(requests, "get", caido)
    assert len(V.historico_cboe("VIX3M")) == 0


def test_historico_cboe_lee_el_formato_de_cboe(monkeypatch):
    import requests

    class R:
        text = "DATE,OPEN,HIGH,LOW,CLOSE\n09/10/2026,19.57,19.85,19.17,19.73\n09/11/2026,18.88,18.92,18.54,18.60\n"

        def raise_for_status(self):
            pass
    monkeypatch.setattr(requests, "get", lambda *a, **k: R())
    s = V.historico_cboe("VIX3M")
    assert list(s.round(2)) == [19.73, 18.60]
    assert s.index[-1] == pd.Timestamp("2026-09-11")


# ── Algoritmo ───────────────────────────────────────────────────────────────

import services.rsu_algoritmo_service as A  # noqa: E402


def test_el_ratio_del_algoritmo_no_mezcla_dias():
    vix = _df(["2026-07-28", "2026-07-29"], [19.0, 20.66])
    vix3m_viejo = _df(["2026-07-16", "2026-07-17"], [19.50, 20.54])
    assert A._vix_vix3m_ratio(vix, vix3m_viejo) is None, "el 29/07 contra el 17/07"
    vix3m_bueno = _df(["2026-07-28", "2026-07-29"], [21.0, 21.50])
    assert A._vix_vix3m_ratio(vix, vix3m_bueno) == round(20.66 / 21.50, 3)


def test_el_backtest_rellena_el_hueco_antes_de_recortar_por_fecha():
    fuente = inspect.getsource(A.get_rsu_algoritmo_backtest)
    i_relleno = fuente.index("completar_con_cboe(df_vix3m_full")
    i_recorte = fuente.index("vix3m_slice = df_vix3m_full[")
    assert i_relleno < i_recorte
    assert 'historico_cboe("VIX3M")' in fuente


# ── Market ──────────────────────────────────────────────────────────────────

import services.market_service as M  # noqa: E402


def _vix_widget(monkeypatch, fecha_3m):
    from services import cache as C
    monkeypatch.setattr(C.cache, "get", lambda *a, **k: None)
    monkeypatch.setattr(C.cache, "set", lambda *a, **k: None)
    cols = pd.MultiIndex.from_product([["^VIX", "^VIX3M", "^VIX6M", "^VIX1Y"], ["Close"]])
    idx = pd.DatetimeIndex(pd.to_datetime(["2026-07-17", "2026-09-11", "2026-09-14"]))
    datos = {("^VIX", "Close"): [16.0, 15.84, 17.21],
             ("^VIX6M", "Close"): [None, None, 20.83],
             ("^VIX1Y", "Close"): [None, None, 22.04]}
    datos[("^VIX3M", "Close")] = [20.54, None, None] if fecha_3m == "2026-07-17" else [None, None, 19.39]
    df = pd.DataFrame(datos, index=idx)[cols]
    monkeypatch.setattr(M.yf, "download", lambda *a, **k: df)
    return M.get_vix_term_structure()


def test_market_con_las_dos_patas_de_hoy_calcula_la_curva(monkeypatch):
    r = _vix_widget(monkeypatch, "2026-09-14")
    assert r["ok"] and r["ratio"] == round(17.21 / 19.39, 3) and r["structure"] == "contango"


def test_market_con_un_VIX3M_de_otro_dia_no_calcula_la_curva(monkeypatch):
    r = _vix_widget(monkeypatch, "2026-07-17")
    assert r["ok"], "el resto del panel se sigue pintando"
    assert r["ratio"] is None and r["contango"] is None and r["structure"] is None


# ── Briefing ────────────────────────────────────────────────────────────────

import daily_briefing as D  # noqa: E402

HOY = {"VIX_SPOT": "2026-09-14", "VIX_3M": "2026-09-14"}


def test_el_briefing_da_la_escala_no_solo_la_palabra():
    normal = D.linea_curva_vix(17.21, 19.39, HOY)
    assert "0.888" in normal and "NORMAL" in normal and "HABITUAL" in normal
    assert "no es una señal" in normal
    assert "TENSA" in D.linea_curva_vix(19.0, 19.5, HOY)
    assert "INVERTIDA" in D.linea_curva_vix(25.0, 22.0, HOY)


def test_el_briefing_usa_los_mismos_umbrales_que_el_algoritmo(monkeypatch):
    monkeypatch.setattr(D, "zona_curva", lambda r: "tensa")
    assert "TENSA" in D.linea_curva_vix(17.21, 19.39, HOY), "tiene que salir de shared/vix_curve"


def test_el_briefing_no_compara_patas_de_dias_distintos():
    linea = D.linea_curva_vix(17.21, 20.54, {"VIX_SPOT": "2026-09-14", "VIX_3M": "2026-07-17"})
    assert "NO DISPONIBLE" in linea and "2026-07-17" in linea
    assert "Ratio" not in linea


def test_el_prompt_usa_la_linea_nueva_y_guarda_las_fechas():
    fuente = inspect.getsource(D.build_prompt)
    assert 'linea_curva_vix(vix_spot, vix_3m, d.get("vix_term_fechas")' in fuente
    assert '"CONTANGO" if' not in inspect.getsource(D)
    assert 'data["vix_term_fechas"] = vix_fechas' in inspect.getsource(D)
