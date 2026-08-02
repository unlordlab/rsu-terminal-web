"""
RS/RW Scanner — universo S&P 500 completo, corre 1x/día por GitHub Actions.

Por qué existe este script: antes NO había ningún proceso automático que
alimentara el Gist que lee /api/v1/rsrw/gist — el "scan on-demand" del
backend (backend/services/rsrw_service.py, _run_scan_engine) solo se
ejecutaba cuando un usuario pulsaba el botón "ESCANEAR AHORA" desde el
navegador, arriesgando rate limits de Yahoo en peticiones en vivo y sin
garantía de cobertura completa. Este script hace exactamente ese mismo
cálculo (misma fórmula, mismo universo embebido de 525 tickers), pero desde
un runner de GitHub Actions, una vez al día, subiendo el resultado a un Gist
— igual que ya hace scripts/scanner_universe.py para el Scanner S&P 500.

Tras esto, la sección RS/RW de la terminal deja de necesitar scan on-demand
en absoluto: siempre lee del Gist, ya con el universo completo.
"""
import json
import time
import os
import sys
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timezone

# Universo compartido -- ver shared/sp500_universe.py (Fase 2.1 del Plan
# Maestro, 20/07/2026). Antes había un diccionario embebido aquí mismo,
# idéntico al de scanner_universe.py y rsrw_service.py -- ahora una sola
# fuente de verdad. Sigue siendo standalone (sin depender de backend/),
# compatible con el runner de GitHub Actions.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "shared"))
from sp500_universe import SP500_SECTOR_MAP  # noqa: E402
from rsrw_engine import (  # noqa: E402
    rs_smooth as _rs_smooth, rs_trend_slope as _rs_trend_slope,
    rs_percentile, rs_momentum, PERIODS, WEIGHTS, EMA_SMOOTH, TREND_WIN,
    SECTOR_ETFS, GICS_MAP,
)
from yf_batch import download_batch  # noqa: E402

GIST_TOKEN = os.environ.get("GIST_TOKEN", "")
GIST_ID    = os.environ.get("RSRW_GIST_ID", "36afc4bd0f8e376b0f6354889bda4d52")
GIST_FILE  = "rsrw_scan.json"

BENCHMARK   = "SPY"
BATCH_SIZE  = 40
BATCH_SLEEP = 1.8




def _get_sp500_tickers() -> tuple:
    tickers = list(SP500_SECTOR_MAP.keys())
    print(f"[RS/RW scan] Universo S&P 500 (lista estática embebida): {len(tickers)} tickers")
    return tickers, SP500_SECTOR_MAP


def run_scan(max_tickers: int = 525) -> dict:
    tickers, smap = _get_sp500_tickers()
    tickers = tickers[:max_tickers]
    all_syms = list(dict.fromkeys([BENCHMARK] + list(SECTOR_ETFS.values()) + tickers))

    close_d, vol_d = download_batch(
        all_syms, period="260d", batch_size=BATCH_SIZE, batch_sleep=BATCH_SLEEP,
        max_retries=3, coverage_threshold=0.85, log_prefix="[RS/RW scan] ",
    )
    print(f"[RS/RW scan] Total con histórico suficiente: {len(close_d)}/{len(all_syms)} símbolos solicitados")

    if BENCHMARK not in close_d:
        raise ValueError("Sin datos de SPY (benchmark) — no se puede calcular RS/RW")

    spy   = close_d[BENCHMARK]
    stocks = {}

    for ticker in tickers:
        if ticker not in close_d: continue
        prices = close_d[ticker]
        if len(prices) < 130: continue
        aligned_spy = spy.reindex(prices.index).ffill()

        try:
            rs_vals_raw = {}
            for p in PERIODS:
                sm = _rs_smooth(prices, aligned_spy, p)
                rs_vals_raw[p] = float(sm.iloc[-1]) if not sm.empty else 0.0

            # Escalado ÚNICO — el mismo bug de doble *100 que se corrigió en
            # get_rsrw_ticker() del backend no existía aquí, pero se deja el
            # comentario para que quede explícito que es intencional: los
            # componentes se pesan en crudo y se escalan una sola vez.
            rs_score_raw = sum(rs_vals_raw[p] * WEIGHTS[p] for p in PERIODS)
            rs_trend     = _rs_trend_slope(_rs_smooth(prices, aligned_spy, 63))

            vol_today = float(vol_d[ticker].iloc[-1]) if ticker in vol_d and len(vol_d[ticker]) > 0 else 0
            vol_avg   = float(vol_d[ticker].tail(20).mean()) if ticker in vol_d and len(vol_d[ticker]) >= 20 else 1
            rvol      = round(vol_today / vol_avg, 2) if vol_avg > 0 else 1.0

            price = float(prices.iloc[-1])
            sector_raw = smap.get(ticker, "")
            sector     = GICS_MAP.get(sector_raw, sector_raw or "Otros")

            stocks[ticker] = {
                "rs_score_raw": round(rs_score_raw * 100, 2),
                "rs_21d":       round(rs_vals_raw[21] * 100, 2),
                "rs_63d":       round(rs_vals_raw[63] * 100, 2),
                "rs_126d":      round(rs_vals_raw[126] * 100, 2),
                "rs_trend":     rs_trend,
                "rvol":         rvol,
                "price":        round(price, 2),
                "sector":       sector,
            }
        except Exception:
            continue

    if not stocks:
        raise ValueError("Sin resultados calculados para ningún ticker")

    # RS_Pct (percentil dentro del universo) y RS_vs_Sector se calculan sobre
    # el conjunto completo ya construido — necesitan verse todos entre sí.
    # rs_percentile() usa pandas rank(pct=True) (promedia rangos empatados)
    # -- antes este fichero era el único de los 4 con un ranking manual por
    # posición, que da un número distinto en cuanto hay un empate exacto.
    scores = pd.Series({t: s["rs_score_raw"] for t, s in stocks.items()})
    pct_by_ticker = rs_percentile(scores).to_dict()

    sector_scores: dict = {}
    for t, s in stocks.items():
        sector_scores.setdefault(s["sector"], []).append(pct_by_ticker[t])
    sector_avg_pct = {sec: sum(v) / len(v) for sec, v in sector_scores.items()}

    for t, s in stocks.items():
        s["rs_percentile"] = pct_by_ticker[t]
        s["rs_momentum"]   = rs_momentum(s["rs_21d"], s["rs_63d"])
        s["rs_vs_sector"]  = round(pct_by_ticker[t] - sector_avg_pct.get(s["sector"], 50), 1)

    # Rotación sectorial — blend de 3 ventanas (21/63/126, mismos pesos que
    # las acciones individuales) de cada ETF sectorial vs SPY. Antes era una
    # única ventana fija de 63d, distinta de cómo se calculan las acciones
    # individuales en este mismo módulo — ahora coherente entre ambas partes.
    sectors = {}
    for sec, etf in SECTOR_ETFS.items():
        if etf in close_d:
            p     = close_d[etf]
            sp    = spy.reindex(p.index).ffill()
            sec_rs_raw = {}
            for pp in PERIODS:
                sm = _rs_smooth(p, sp, pp)
                sec_rs_raw[pp] = float(sm.iloc[-1]) if not sm.empty else 0.0
            rs_v  = sum(sec_rs_raw[pp] * WEIGHTS[pp] for pp in PERIODS) * 100
            ret63 = float((p.iloc[-1] / p.iloc[-63] - 1) * 100) if len(p) >= 63 else 0
            # La flecha de tendencia sigue basada en la componente de 63d,
            # igual que para acciones individuales.
            slope = _rs_trend_slope(_rs_smooth(p, sp, 63))
            sectors[sec] = {"RS": round(rs_v, 2), "Return_63d": round(ret63, 2), "RS_trend": slope}

    return {
        "ok":           True,
        "stocks":       stocks,
        "sectors":      sectors,
        "universe_size": len(stocks),
        "meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            # Fecha de la SESIÓN que describen estos datos, no la de ejecución.
            # El cron corre de lunes a viernes, así que en un festivo de
            # mercado el scan se ejecuta igual, descarga lo mismo que ayer y
            # reescribe el Gist -- y `generated_at` decía "hace 20 minutos",
            # presentando datos de la sesión anterior como recién salidos.
            #
            # No hace falta un calendario de festivos: el último índice del
            # benchmark ES, por definición, una sesión real de mercado. El
            # dato se saca de lo ya descargado y no puede desincronizarse.
            # Ver auditoría RS/RW, hallazgo #6.
            "ultima_sesion": str(close_d[BENCHMARK].index[-1].date()),
            "mode":         "nightly_scan",
            "n_stocks":     len(stocks),
            "n_requested":  len(tickers),
            "sector_timeframe": "blend 21/63/126d (20/35/45%) — igual que acciones individuales",
        },
    }


def save_to_gist(result: dict):
    if not GIST_TOKEN:
        raise ValueError("GIST_TOKEN no configurado")
    if not GIST_ID:
        raise ValueError("RSRW_GIST_ID no configurado")

    r = requests.patch(
        f"https://api.github.com/gists/{GIST_ID}",
        headers={"Authorization": f"token {GIST_TOKEN}", "Accept": "application/vnd.github+json"},
        json={"files": {GIST_FILE: {"content": json.dumps(result, ensure_ascii=False, indent=2)}}},
        timeout=30,
    )
    if r.status_code not in (200, 201):
        raise ValueError(f"Gist error {r.status_code}: {r.text[:300]}")
    print(f"✅ RS/RW scan guardado en Gist: {r.json()['html_url']}")


def main():
    print(f"🕐 RS/RW Scanner — {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}")
    result = run_scan()
    print(f"📊 {result['universe_size']} tickers calculados")
    print("💾 Guardando en GitHub Gist...")
    save_to_gist(result)
    print("✅ Scan completado")


if __name__ == "__main__":
    main()