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

GIST_TOKEN = os.environ.get("GIST_TOKEN", "")
GIST_ID    = os.environ.get("RSRW_GIST_ID", "36afc4bd0f8e376b0f6354889bda4d52")
GIST_FILE  = "rsrw_scan.json"

BENCHMARK   = "SPY"
PERIODS     = [21, 63, 126]
WEIGHTS     = {21: 0.20, 63: 0.35, 126: 0.45}
EMA_SMOOTH  = 10
TREND_WIN   = 21
BATCH_SIZE  = 40
BATCH_SLEEP = 1.8

SECTOR_ETFS = {
    "Tecnología":"XLK","Salud":"XLV","Financieros":"XLF",
    "Consumo Discrecional":"XLY","Consumo Básico":"XLP","Industriales":"XLI",
    "Energía":"XLE","Materiales":"XLB","Servicios Públicos":"XLU",
    "Bienes Raíces":"XLRE","Comunicaciones":"XLC",
}

GICS_MAP = {
    "Information Technology":"Tecnología","Health Care":"Salud",
    "Financials":"Financieros","Consumer Discretionary":"Consumo Discrecional",
    "Consumer Staples":"Consumo Básico","Industrials":"Industriales",
    "Energy":"Energía","Materials":"Materiales","Utilities":"Servicios Públicos",
    "Real Estate":"Bienes Raíces","Communication Services":"Comunicaciones",
}




def _get_sp500_tickers() -> tuple:
    tickers = list(SP500_SECTOR_MAP.keys())
    print(f"[RS/RW scan] Universo S&P 500 (lista estática embebida): {len(tickers)} tickers")
    return tickers, SP500_SECTOR_MAP


def _rs_smooth(prices: pd.Series, spy: pd.Series, period: int) -> pd.Series:
    rs = prices.pct_change(period) - spy.pct_change(period)
    return rs.ewm(span=EMA_SMOOTH, min_periods=3).mean()


def _rs_trend_slope(rs_series: pd.Series) -> float:
    """Pendiente normalizada de la RS — numpy puro, sin scipy."""
    recent = rs_series.dropna().iloc[-TREND_WIN:]
    if len(recent) < 5: return 0.0
    x     = np.arange(len(recent), dtype=float)
    slope = float(np.polyfit(x, recent.values, 1)[0])
    std   = float(recent.std())
    return round(slope / std if std > 0 else 0.0, 4)


def run_scan(max_tickers: int = 525) -> dict:
    tickers, smap = _get_sp500_tickers()
    tickers = tickers[:max_tickers]
    all_syms = list(dict.fromkeys([BENCHMARK] + list(SECTOR_ETFS.values()) + tickers))

    close_d, vol_d = {}, {}
    batches = [all_syms[i:i+BATCH_SIZE] for i in range(0, len(all_syms), BATCH_SIZE)]
    n_batches = len(batches)

    import yfinance as yf

    for i, batch in enumerate(batches):
        original_batch = list(batch)
        original_size  = len(original_batch)
        got_syms = set()

        for attempt in range(3):
            try:
                raw = yf.download(batch, period="260d", interval="1d",
                                   group_by="column", auto_adjust=True,
                                   threads=True, progress=False)
                if isinstance(raw.columns, pd.MultiIndex):
                    closes = raw["Close"] if "Close" in raw.columns.get_level_values(0) else pd.DataFrame()
                    vols   = raw["Volume"] if "Volume" in raw.columns.get_level_values(0) else pd.DataFrame()
                else:
                    closes = raw[["Close"]] if "Close" in raw.columns else pd.DataFrame()
                    vols   = raw[["Volume"]] if "Volume" in raw.columns else pd.DataFrame()

                for sym in batch:
                    if sym in closes.columns:
                        series = closes[sym].dropna()
                        if len(series) >= 130:
                            close_d[sym] = series
                            vol_d[sym]   = vols[sym].dropna() if sym in vols.columns else pd.Series(dtype=float)
                            got_syms.add(sym)

                missing  = [s for s in original_batch if s not in got_syms]
                coverage = len(got_syms) / original_size if original_size else 1.0

                if coverage >= 0.85 or attempt == 2:
                    if missing:
                        print(f"[RS/RW scan] Lote {i+1}/{n_batches}: {len(missing)} símbolos sin datos suficientes tras {attempt+1} intento(s): {missing[:15]}{'...' if len(missing) > 15 else ''}")
                    break

                print(f"[RS/RW scan] Lote {i+1}/{n_batches}: cobertura {coverage:.0%} tras intento {attempt+1}, reintentando {len(missing)} símbolos...")
                batch = missing
                time.sleep(2.5)
            except Exception as e:
                print(f"[RS/RW scan] Lote {i+1}/{n_batches} intento {attempt+1} falló: {e}")
                time.sleep(2.5)
                continue

        if i < n_batches - 1:
            time.sleep(BATCH_SLEEP)

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
    scores = {t: s["rs_score_raw"] for t, s in stocks.items()}
    ranked = sorted(scores.items(), key=lambda x: x[1])
    n      = len(ranked)
    pct_by_ticker = {t: round((i + 1) / n * 100, 1) for i, (t, _) in enumerate(ranked)}

    sector_scores: dict = {}
    for t, s in stocks.items():
        sector_scores.setdefault(s["sector"], []).append(pct_by_ticker[t])
    sector_avg_pct = {sec: sum(v) / len(v) for sec, v in sector_scores.items()}

    for t, s in stocks.items():
        s["rs_percentile"] = pct_by_ticker[t]
        # rs_momentum: ¿el ritmo de outperformance RECIENTE es más rápido que
        # el de medio plazo? Antes comparaba rs_21d > rs_63d directamente —
        # pero son diferenciales ACUMULADOS de ventanas de distinta longitud
        # (21 días vs 63 días), así que un ticker con outperformance ESTABLE
        # y constante tenía rs_63d > rs_21d casi siempre solo por acumular
        # más tiempo, no porque estuviera desacelerando -- el indicador
        # medía sobre todo el sesgo de longitud de ventana, no aceleración
        # real. Arreglo: normalizar cada diferencial por su nº de días
        # (ritmo diario equivalente) antes de comparar. Ver Plan Maestro
        # 3.3, auditoría RS/RW 19-20/07/2026.
        ritmo_21d = s["rs_21d"] / 21
        ritmo_63d = s["rs_63d"] / 63
        s["rs_momentum"]   = 1 if ritmo_21d > ritmo_63d else 0
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