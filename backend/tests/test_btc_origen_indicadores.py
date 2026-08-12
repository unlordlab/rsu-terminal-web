"""
Test de qué dice BTC Stratum sobre el origen de sus indicadores (11/08/2026,
hallazgo #1 de su auditoría: "El MVRV Z-Score no usa Realized Cap — y la
alerta le dice al usuario que sí").

Confirmado, y peor de lo enunciado. `_calc_mvrv_z_improved()` tiene dos
caminos que producen números NO comparables entre sí:

  (a) capitalización de mercado real ÷ su EMA365, y
  (b) `(precio − MA200W) / MA200W × 3,5`, que no es un Z-score de nada.

En producción corre SIEMPRE el (b): CoinGecko movió `/coins/bitcoin/market_chart`
detrás de una API key y devuelve 401 (comprobado en vivo el 11/08/2026), así
que no hay market cap histórico con el que construir el (a). Nada lo decía —
el 401 se tragaba en silencio y la serie ca√≠a al respaldo de yfinance, que no
trae capitalización. Y encima la alerta afirmaba "BTC infravalorado vs
realized cap", una comparación on-chain que no se había hecho.

De paso, el error simétrico: el Puell SÍ suele ser un dato real (ingresos de
mineros de Blockchain.com, medido 0,674 en producción) y la página lo
anunciaba como una aproximación de precio.

Uso:
    cd backend
    python -m pytest tests/test_btc_origen_indicadores.py -v
"""
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import services.btc_stratum_service as B  # noqa: E402


# ── La alerta ya no afirma una comparación que no ha hecho ───────────────────

def _alerta_mvrv(metodo):
    alertas = B._calc_alerts(price=40_000, ma200=60_000, rsu=30,
                             mvrv_z=-1.2, puell=0.9, mvrv_metodo=metodo)
    return next((a["msg"] for a in alertas if "MVRV" in a["msg"]), "")


def test_con_el_proxy_la_alerta_no_menciona_realized_cap():
    """Es el hallazgo #1 literal: decía «infravalorado vs realized cap» con un
    número que no mira el realized cap por ningún lado."""
    msg = _alerta_mvrv("proxy")
    assert msg, "la alerta debe seguir saliendo"
    assert "realized cap" not in msg.lower()
    assert "media de 200 semanas" in msg


def test_con_capitalizacion_real_la_alerta_dice_lo_que_ha_comparado():
    msg = _alerta_mvrv("capmercado")
    assert "capitalización media" in msg
    assert "200 semanas" not in msg


def test_las_dos_ramas_no_dicen_lo_mismo():
    """Si algún día vuelven a decir lo mismo, el aviso ha dejado de informar
    de cuál de los dos cálculos se está mirando."""
    assert _alerta_mvrv("proxy") != _alerta_mvrv("capmercado")


def test_por_defecto_se_asume_el_proxy_no_el_dato_bueno():
    """Un llamador que olvide pasar el método debe caer en la versión
    conservadora. Comprobar solo que no diga «realized cap» no basta: la rama
    de capitalización tampoco lo dice, así que el test se colaba. Hay que
    exigir el texto DEL PROXY."""
    alertas = B._calc_alerts(price=40_000, ma200=60_000, rsu=30, mvrv_z=-1.2, puell=0.9)
    msg = next(a["msg"] for a in alertas if "MVRV" in a["msg"])
    assert msg == _alerta_mvrv("proxy"), "el defecto debe ser el proxy, no la capitalización"


# ── El MVRV bueno solo se usa cuando de verdad hay capitalización ────────────

def test_sin_market_cap_el_mvrv_no_finge_haberlo_calculado():
    """Devuelve source='proxy' para que el llamador sepa que tiene que caer a
    la estimación, en vez de un número que parece bueno."""
    df = pd.DataFrame({"price": [100.0] * 10})
    r = B._calc_mvrv_z_improved(df)
    assert r.get("mvrv_z") is None
    assert r.get("source") == "proxy"


def test_una_columna_de_market_cap_toda_vacia_cuenta_como_ausente():
    df = pd.DataFrame({"price": [100.0] * 10, "market_cap": [None] * 10})
    assert B._calc_mvrv_z_improved(df).get("mvrv_z") is None


def test_con_market_cap_real_si_calcula_y_lo_declara():
    import numpy as np
    n = 800
    idx = pd.date_range("2024-01-01", periods=n, freq="D")
    mc = pd.Series(np.linspace(1e11, 1.4e12, n), index=idx)
    r = B._calc_mvrv_z_improved(pd.DataFrame({"price": mc / 2e7, "market_cap": mc}))
    assert r.get("mvrv_z") is not None
    assert "market cap" in r.get("source", "").lower()


# ── Cada componente declara de dónde sale su número ──────────────────────────

def test_solo_las_estimaciones_llevan_el_prefijo_aproximado():
    """La tarjeta pinta en ámbar lo que empieza por «Aproximado», así que ese
    prefijo es un contrato con el frontend, no una florritura: marcar de más
    desconfía de un dato bueno, y marcar de menos vende una estimación como
    medición."""
    assert B.ORIGEN_MVRV_PROXY.startswith("Aproximado")
    assert B.ORIGEN_PUELL_PROXY.startswith("Aproximado")
    for real in (B.ORIGEN_MVRV_REAL, B.ORIGEN_PUELL_REAL, B.ORIGEN_MA200, B.ORIGEN_AHR999):
        assert not real.startswith("Aproximado")


def test_el_puell_real_no_se_describe_como_una_estimacion_de_precio():
    """El error simétrico del #1: el dato bueno vendido como proxy. Se mide de
    ingresos de mineros, no del precio."""
    assert "precio" not in B.ORIGEN_PUELL_REAL.lower()
    assert "mineros" in B.ORIGEN_PUELL_REAL.lower()


def test_ningun_origen_promete_realized_cap():
    """Ninguna de las dos ramas del MVRV mide el valor realizado: la buena usa
    capitalización de mercado contra su propia media, que es otra cosa."""
    for texto in (B.ORIGEN_MVRV_REAL, B.ORIGEN_MVRV_PROXY):
        assert "realized" not in texto.lower() and "realizado" not in texto.lower()
