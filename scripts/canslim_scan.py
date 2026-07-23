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
from canslim_engine import perf_12m, acc_dis_rating  # noqa: E402
from yf_batch import download_batch  # noqa: E402

GIST_TOKEN = os.environ.get("GIST_TOKEN", "")
GIST_ID    = os.environ.get("CANSLIM_GIST_ID", "")
GIST_FILE  = "canslim_scan.json"

BATCH_SIZE  = 40
BATCH_SLEEP = 1.8


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

        ma50  = float(closes.tail(50).mean())
        ma150 = float(closes.tail(150).mean()) if len(closes) >= 150 else ma50
        trend_ok = bool(price > ma50 and price > ma150 and ma50 > ma150)

        vol_today = float(vols.iloc[-1])
        vol_ratio = vol_today / vol_avg if vol_avg > 0 else 1.0
        acc_dis   = acc_dis_rating(hist)

        high_52w = float(closes.tail(252).max())
        pct_from_high = (price - high_52w) / high_52w * 100 if high_52w > 0 else -100

        raw_results.append({
            "ticker":        t,
            "price":         round(price, 2),
            "perf_12m":      round(perf_12m(hist), 2),
            "acc_dis":       acc_dis,
            "vol_ratio":     round(vol_ratio, 2),
            "trend":         trend_ok,
            "pct_from_high": round(pct_from_high, 1),
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

    candidates = []
    for r in raw_results:
        near_new_high = r["pct_from_high"] >= -15
        score = 0
        if r["rs"] >= 80:             score += 25
        if r["trend"]:                score += 25
        if r["acc_dis"] in ["A", "B"]: score += 20
        if r["vol_ratio"] >= 1.5:     score += 15
        if r["perf_12m"] >= 20:       score += 10
        if near_new_high:             score += 5
        r["score"]         = score
        r["near_new_high"] = near_new_high
        candidates.append(r)

    candidates.sort(key=lambda x: -x["score"])

    return {
        "ok":         True,
        "candidates": candidates,
        "perfs":      perfs,   # universo completo -- lo usa analyze_ticker() para el percentil real
        "scanned":    len(tickers),
        "total":      len(candidates),
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
    print(f"🕐 CANSLIM Scanner — {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}")
    result = run_scan()
    print(f"📊 {result['total']} candidatos de {result['scanned']} escaneados")
    print("💾 Guardando en GitHub Gist...")
    save_to_gist(result)
    print("✅ Scan completado")


if __name__ == "__main__":
    main()
