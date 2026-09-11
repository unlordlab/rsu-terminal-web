"""
Piotroski F-Score con la definición original, y la caché de Research ligada
al código desplegado.

EL CASO, 11/09/2026, auditando OSS con el usuario. El 5/9 salía bien por
casualidad: dos criterios equivocados que se compensaban.

  1. «ROA positivo» con un beneficio neto de +5,09M, de los que 8,19M venían
     de operaciones discontinuadas (vender o cerrar un negocio): su negocio
     perdía 3,1M. Piotroski usa el beneficio ANTES de partidas
     extraordinarias, el de las operaciones que continúan.
  2. La rotación de activos y la rentabilidad se dividían por el activo al
     CIERRE del año; Piotroski usa el del INICIO (y el apalancamiento, el
     MEDIO). OSS subió su activo un 43% en 2025: con el del cierre la rotación
     «empeoraba» (0,66 → 0,61), con el del inicio mejora (0,51 → 0,87).

Medido en 151 valores (OSS y 150 del S&P 500, mismas cuentas en las dos
versiones): 71 cambian algún criterio y 63 de nota, casi siempre ±1; la
rotación cambia en 60 (comprobado a mano en CL e IEX: son las cuentas).

Y la caché: vive en disco y sobrevive a los despliegues. Tras desplegar el
panel técnico nuevo, OSS siguió saliendo con la respuesta de la versión
anterior hasta que caducó. Ahora la clave lleva el commit desplegado.

Uso:
    cd backend
    python -m pytest tests/test_piotroski_definicion.py -v
"""
import io
import os

import pandas as pd
import pytest

import despliegue
from services import research_service as R

AÑOS = pd.to_datetime(["2025-12-31", "2024-12-31", "2023-12-31"])


def _df(filas):
    return pd.DataFrame({k: v for k, v in filas.items()}, index=AÑOS).T


# Las cuentas de OSS tal como las da Yahoo (millones), 2025 / 2024 / 2023.
OSS_BS = _df({
    "Total Assets": [52.82, 36.93, 48.27], "Current Assets": [50.82, 32.20, 42.44],
    "Current Liabilities": [5.57, 8.20, 6.87],
    "Long Term Debt And Capital Lease Obligation": [1.25, 1.47, 1.77], "Total Debt": [1.47, 1.70, 4.23],
    "Ordinary Shares Number": [24.58, 21.15, 20.66],
})
OSS_FIN = _df({
    "Total Revenue": [32.22, 24.56, 60.90], "Gross Profit": [15.98, 0.62, 17.95],
    "Net Income": [5.09, -13.63, -6.72],
    "Net Income From Continuing Operation Net Minority Interest": [-3.10, -15.17, -6.72],
})
OSS_CF = _df({"Operating Cash Flow": [-6.55, -2.60, -0.44]})


class _Ticker:
    def __init__(self, bs, fin, cf):
        self.balance_sheet, self.financials, self.cashflow = bs, fin, cf


def _piotroski(monkeypatch, bs=OSS_BS, fin=OSS_FIN, cf=OSS_CF):
    monkeypatch.setattr(R.yf, "Ticker", lambda t: _Ticker(bs, fin, cf))
    return R._get_piotroski_score("OSS")


def _criterio(r, n):
    return r["criteria"][n - 1]


def test_OSS_da_5_por_los_motivos_correctos(monkeypatch):
    r = _piotroski(monkeypatch)
    assert r["score"] == 5
    assert [c["pass"] for c in r["criteria"]] == [False, False, True, False, True, True, False, True, True]


def test_vender_un_negocio_no_cuenta_como_rentabilidad(monkeypatch):
    """EL test del criterio 1: beneficio neto positivo solo por la venta."""
    c = _criterio(_piotroski(monkeypatch), 1)
    assert c["pass"] is False
    assert "vender o cerrar un negocio" in c["label"]


def test_la_rotacion_usa_el_activo_al_inicio_del_ano(monkeypatch):
    assert _criterio(_piotroski(monkeypatch), 9)["pass"] is True


def test_sin_la_linea_de_operaciones_continuas_usa_el_beneficio_neto(monkeypatch):
    fin = OSS_FIN.drop(index="Net Income From Continuing Operation Net Minority Interest")
    c = _criterio(_piotroski(monkeypatch, fin=fin), 1)
    assert c["pass"] is True and c["label"] == "ROA positivo"


def test_con_solo_dos_balances_compara_cierre_con_cierre(monkeypatch):
    """Sin el balance de hace dos años no hay activo inicial para el año
    anterior: se usan los dos cierres, como antes, en vez de mezclar."""
    bs = OSS_BS.iloc[:, :2]
    r = _piotroski(monkeypatch, bs=bs, fin=OSS_FIN.iloc[:, :2], cf=OSS_CF.iloc[:, :2])
    assert _criterio(r, 9)["pass"] is False    # 32,22/52,82 = 0,61 frente a 24,56/36,93 = 0,66


def test_el_apalancamiento_usa_el_activo_medio(monkeypatch):
    """Un caso en que cierre y medio discrepan: la deuda baja poco y el activo
    del cierre salta. Con el activo del cierre «baja»; con el medio, sube."""
    bs = OSS_BS.copy()
    bs.loc["Total Assets"] = [80.0, 40.0, 30.0]
    bs.loc["Long Term Debt And Capital Lease Obligation"] = [3.0, 2.0, 1.0]
    # cierre: 3/80 = 3,8% frente a 2/40 = 5,0% (baja) · medio: 3/60 = 5,0% frente a 2/35 = 5,7% (baja)
    assert _criterio(_piotroski(monkeypatch, bs=bs), 5)["pass"] is True
    bs.loc["Long Term Debt And Capital Lease Obligation"] = [3.3, 2.0, 1.0]
    # cierre: 3,3/80 = 4,1% (baja) · medio: 3,3/60 = 5,5% frente a 5,7% (baja)
    bs.loc["Total Assets"] = [80.0, 40.0, 50.0]
    # cierre: 4,1% frente a 5,0% (baja) · medio: 5,5% frente a 2/45 = 4,4% (SUBE)
    assert _criterio(_piotroski(monkeypatch, bs=bs), 5)["pass"] is False


def test_dice_que_ejercicios_compara(monkeypatch):
    r = _piotroski(monkeypatch)
    assert r["ejercicio"] == "2025-12-31" and r["ejercicio_anterior"] == "2024-12-31"
    js = io.open(os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "pages", "research.js"),
                 encoding="utf-8").read()
    assert "p.ejercicio && p.ejercicio_anterior" in js and "Cuentas anuales" in js


# ── La caché de Research sigue al código desplegado ──────────────────────────

def test_la_clave_lleva_el_commit_desplegado(monkeypatch):
    monkeypatch.setattr(despliegue, "COMMIT", "aaaaaaa")
    antes = R._clave_research("OSS")
    monkeypatch.setattr(despliegue, "COMMIT", "bbbbbbb")
    assert antes != R._clave_research("OSS") and "bbbbbbb" in R._clave_research("OSS")


def test_tras_un_despliegue_no_se_sirve_la_respuesta_vieja(monkeypatch):
    from services.cache import cache
    monkeypatch.setattr(despliegue, "COMMIT", "viejo00")
    cache.set(R._clave_research("ZZOSS"), {"ok": True, "version": "vieja"}, 60)
    assert R.get_research("ZZOSS") == {"ok": True, "version": "vieja"}
    monkeypatch.setattr(despliegue, "COMMIT", "nuevo00")
    monkeypatch.setattr(R, "_get_yfinance", lambda t: {"ok": False, "error": "recalculado"})
    assert R.get_research("ZZOSS")["error"] == "recalculado"
    for commit in ("viejo00", "nuevo00"):
        monkeypatch.setattr(despliegue, "COMMIT", commit)
        cache.set(R._clave_research("ZZOSS"), None, 1)


def test_ninguna_escritura_de_la_ficha_usa_la_clave_sin_version():
    rs = io.open(R.__file__, encoding="utf-8").read()
    assert 'f"research:{ticker}"' not in rs
    assert rs.count("_clave_research(ticker)") >= 5
