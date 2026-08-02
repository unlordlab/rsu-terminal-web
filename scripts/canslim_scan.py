#!/usr/bin/env python3
"""
CANSLIM Scanner — universo S&P 500 completo, corre 1x/día (L-V) por
GitHub Actions.

Por qué existe este script (sesión 32): el scan de CANSLIM era la única
sección de scan de toda la terminal (RS/RW, Scanner técnico, Thematic,
CANSLIM) sin caché de resultado ni scan nocturno — cada clic en
"ESCANEAR S&P 500" desde el navegador recalculaba las 503 acciones desde
cero, sin importar si alguien había escaneado segundos antes. Este script
hace exactamente ese mismo cálculo técnico (misma fórmula, mismo universo
de shared/sp500_universe.py) desde un runner de GitHub Actions, una vez
al día, subiendo el resultado a un Gist — igual que ya hacen
scripts/rsrw_scan.py, scripts/scanner_universe.py y
scripts/thematic_scan.py.

Solo cubre la parte TÉCNICA del scan (precio, volumen, tendencia, RS
real, Acumulación/Distribución) — igual que ya hacía
canslim_service.py::_scan_single(). El análisis individual completo
(fundamentales vía tk.info, participación institucional) sigue siendo
on-demand en el backend (backend/services/canslim_service.py::
analyze_ticker()) — mucho más caro por ticker, no tiene sentido pagar ese
coste 503 veces cada noche solo para la vista de scan.
"""
import json
import os
import sys
from datetime import datetime, timezone

import pandas as pd
import requests

# shared/ es sibling de scripts/ -- mismo patrón que rsrw_scan.py/
# scanner_universe.py para no depender de nada de backend/ (este script
# corre standalone en el runner de GitHub Actions).
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "shared"))
from sp500_universe import SP500_SECTOR_MAP  # noqa: E402
from canslim_engine import (  # noqa: E402
    perf_12m, acc_dis_rating, trend_template, technical_score, NEAR_HIGH_PCT,
)
from yf_batch import download_batch  # noqa: E402

GIST_TOKEN = os.environ.get("GIST_TOKEN", "")
GIST_ID    = os.environ.get("CANSLIM_GIST_ID", "")
GIST_FILE  = "canslim_scan.json"

BATCH_SIZE  = 40
BATCH_SLEEP = 1.8

# 3 Weeks Tight (3WT) -- patrón de Gil Morales/Chris Kacher ("Trade Like
# an O'Neil Disciple"), refinamiento del método CAN SLIM original: 3+
# semanas consecutivas con rango de precio muy apretado tras una subida
# real, señal de acumulación silenciosa. Umbral típico citado: <=1.5% de
# rango (máximo-mínimo)/cierre por semana.
THREE_WEEKS_TIGHT_PCT = 1.5
THREE_WEEKS_TIGHT_MIN_WEEKS = 3


def run_scan() -> dict:
    tickers = list(SP500_SECTOR_MAP.keys())
    print(f"🔍 CANSLIM scan — universo S&P 500: {len(tickers)} tickers")

    close_d, vol_d, hl_d = download_batch(
        tickers, period="2y", batch_size=BATCH_SIZE, batch_sleep=BATCH_SLEEP,
        max_retries=3, coverage_threshold=0.85, min_history=100,
        include_hl=True, log_prefix="[CANSLIM scan] ",
    )
    print(f"✅ Con histórico suficiente: {len(close_d)}/{len(tickers)} tickers")

    raw_results = []
    for t in tickers:
        if t not in close_d or t not in hl_d:
            continue
        closes = close_d[t]
        vols   = vol_d.get(t)
        price  = float(closes.iloc[-1])
        if price < 5:
            continue
        vol_avg = float(vols.tail(50).mean()) if vols is not None and len(vols) else 0.0
        if vol_avg < 100_000:
            continue

        hist = pd.DataFrame({
            "Close":  closes,
            "High":   hl_d[t]["High"],
            "Low":    hl_d[t]["Low"],
            "Volume": vols,
        }).dropna()
        if len(hist) < 20:
            continue

        # Trend Template de 7 condiciones, el MISMO que la letra L del
        # análisis individual. Hasta el 01/08/2026 esto era un chequeo de 3
        # condiciones propio de este script, y las dos definiciones
        # discrepaban en el 23,8% del universo: había tickers que salían con
        # la tendencia en verde en la tabla y suspendían al abrirlos. Cuesta
        # 157 ms más para 500 tickers, frente a los ~35 s de la descarga.
        trend = trend_template(hist, price)

        vol_today = float(vols.iloc[-1])
        vol_ratio = vol_today / vol_avg if vol_avg > 0 else 1.0
        acc_dis   = acc_dis_rating(hist)

        pct_from_high = trend["pct_from_high"]

        # 3 Weeks Tight: agrega Close/High/Low diarios a semanal (cierre =
        # último de la semana, high/low = máximo/mínimo de la semana) y
        # comprueba si las últimas THREE_WEEKS_TIGHT_MIN_WEEKS semanas
        # tienen todas un rango (high-low)/close por debajo del umbral.
        is_3wt = False
        weekly = hist[["Close", "High", "Low"]].resample("W-FRI").agg(
            {"Close": "last", "High": "max", "Low": "min"}
        ).dropna()
        if len(weekly) >= THREE_WEEKS_TIGHT_MIN_WEEKS:
            last_weeks = weekly.tail(THREE_WEEKS_TIGHT_MIN_WEEKS)
            weekly_range_pct = (last_weeks["High"] - last_weeks["Low"]) / last_weeks["Close"] * 100
            is_3wt = bool((weekly_range_pct <= THREE_WEEKS_TIGHT_PCT).all())

        raw_results.append({
            "ticker":        t,
            "price":         round(price, 2),
            "perf_12m":      round(perf_12m(hist), 2),
            "acc_dis":       acc_dis,
            "vol_ratio":     round(vol_ratio, 2),
            "trend":         trend["passed"],
            # Cuántas de las 7 condiciones se cumplen: la tabla lo pinta como
            # "5/7" en vez de un tick, para que el umbral (5 de 7) deje de ser
            # invisible y se distinga un aprobado raspado de uno perfecto.
            "trend_score":   trend["score"],
            "pct_from_high": round(pct_from_high, 1),
            "is_3wt":        is_3wt,
        })

    print(f"📊 {len(raw_results)}/{len(tickers)} tickers con datos completos (precio ≥$5, volumen ≥100k)")
    if not raw_results:
        raise ValueError("Sin resultados calculados para ningún ticker")

    # RS real = percentil dentro del universo escaneado -- misma fórmula
    # que scan_canslim() en el backend (sesión 12/23), aquí calculada una
    # sola vez para los 503 en vez de recalcularla en cada request.
    perfs = [r["perf_12m"] for r in raw_results]
    for r in raw_results:
        rank = sum(1 for p in perfs if p < r["perf_12m"])
        r["rs"] = max(1, min(99, int(rank / len(perfs) * 99) + 1)) if perfs else 50

    # Score técnico: MISMA fórmula que el análisis individual del backend
    # (shared/canslim_engine.py). La anterior era propia de aquí, con otros
    # pesos, sin crédito parcial y sumando +10 por «perf_12m >= 20%» cuando
    # el RS ya ES el percentil de perf_12m -- el mismo dato contaba dos veces.
    candidates = []
    for r in raw_results:
        near_new_high = r["pct_from_high"] >= NEAR_HIGH_PCT
        r["score"]         = technical_score(r["rs"], r["trend"], r["trend_score"],
                                             r["acc_dis"], near_new_high, r["vol_ratio"])
        r["near_new_high"] = near_new_high
        candidates.append(r)

    candidates.sort(key=lambda x: -x["score"])

    # Fecha de la SESIÓN que describen los datos, no la de ejecución. El cron
    # corre de lunes a viernes, así que en un festivo de mercado el scan se
    # ejecuta igual y descarga lo mismo que la víspera. Sin este campo, el
    # tracking de candidatos guardaría los precios de la sesión anterior
    # fechados en el festivo, y los retornos saldrían desplazados una sesión.
    # Se toma del propio índice descargado -- por definición es una sesión
    # real, así que no hace falta calendario de festivos. Ver RS/RW #6.
    ultima_sesion = max(s.index[-1].date() for s in close_d.values())

    return {
        "ok":         True,
        "candidates": candidates,
        "perfs":      perfs,   # universo completo -- lo usa analyze_ticker() para el percentil real
        "scanned":    len(tickers),
        "total":      len(candidates),
        "ultima_sesion": str(ultima_sesion),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def save_to_gist(result: dict):
    if not GIST_TOKEN:
        raise ValueError("GIST_TOKEN no configurado")
    if not GIST_ID:
        raise ValueError("CANSLIM_GIST_ID no configurado")

    r = requests.patch(
        f"https://api.github.com/gists/{GIST_ID}",
        headers={"Authorization": f"token {GIST_TOKEN}", "Accept": "application/vnd.github+json"},
        json={"files": {GIST_FILE: {"content": json.dumps(result, ensure_ascii=False, indent=2)}}},
        timeout=30,
    )
    if r.status_code not in (200, 201):
        raise ValueError(f"Gist error {r.status_code}: {r.text[:300]}")
    print(f"✅ CANSLIM scan guardado en Gist: {r.json()['html_url']}")


def main():
    print(f"🕐 CANSLIM Scanner — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    result = run_scan()
    print(f"📊 {result['total']} candidatos de {result['scanned']} escaneados")
    print("💾 Guardando en GitHub Gist...")
    save_to_gist(result)
    print("✅ Scan completado")


if __name__ == "__main__":
    main()
