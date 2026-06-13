import json
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor
import yfinance as yf

GIST_ID     = "36afc4bd0f8e376b0f6354889bda4d52"
GIST_FILE   = "rsrw_scan.json"
BENCHMARK   = "SPY"
PERIODS     = [21, 63, 126]
WEIGHTS     = {21: 0.20, 63: 0.35, 126: 0.45}
EMA_SMOOTH  = 10
TREND_WIN   = 21
BATCH_SIZE  = 80

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

# ── GIST ──────────────────────────────────────────────────────────────────────

def _load_gist() -> dict | None:
    try:
        r = requests.get(
            f"https://api.github.com/gists/{GIST_ID}",
            timeout=10,
            headers={"Accept": "application/vnd.github.v3+json"}
        )
        r.raise_for_status()
        content = r.json()["files"][GIST_FILE]["content"]
        data    = json.loads(content)
        return data if data.get("stocks") and len(data["stocks"]) > 10 else None
    except Exception:
        return None

def _parse_gist(data: dict) -> tuple:
    meta    = data.get("meta", {})
    stocks  = data.get("stocks", {})
    sectors = data.get("sectors", {})

    if stocks:
        df = pd.DataFrame.from_dict(stocks, orient="index")
        df.index.name = "Ticker"
        rename = {
            "rs_percentile": "RS_Pct",   "rs_score_raw": "RS_Score",
            "rs_21d":        "RS_21d",   "rs_63d":       "RS_63d",
            "rs_126d":       "RS_126d",  "rs_momentum":  "RS_Mom",
            "rs_trend":      "RS_Trend", "rs_vs_sector": "RS_vs_Sector",
            "rvol":          "RVOL",     "sector":       "Sector",
            "price":         "Precio",
        }
        df = df.rename(columns=rename)
        for c in ["RS_Pct","RS_Score","RS_21d","RS_63d","RS_126d","RS_Mom","RS_Trend","RS_vs_Sector","RVOL","Precio"]:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce")
        df = df.dropna(subset=["RS_Pct"])
    else:
        df = pd.DataFrame()

    if sectors:
        sdf = pd.DataFrame.from_dict(sectors, orient="index")
        sdf.index.name = "Sector"
        for c in ["RS", "Return_63d", "RS_trend"]:
            if c in sdf.columns:
                sdf[c] = pd.to_numeric(sdf[c], errors="coerce")
    else:
        sdf = pd.DataFrame()

    return df, sdf, meta

def _freshness(meta: dict) -> str:
    try:
        ts  = meta.get("generated_at", "")
        dt  = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        ago = datetime.now(timezone.utc) - dt
        mins = int(ago.total_seconds() / 60)
        if mins < 60:   return f"Hace {mins} min"
        if mins < 1440: return f"Hace {mins//60}h"
        return f"Hace {mins//1440}d"
    except Exception:
        return "Desconocido"

# ── SCAN ON-DEMAND ────────────────────────────────────────────────────────────

def _get_sp500_tickers() -> tuple:
    try:
        df      = pd.read_html("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies", match="Symbol")[0]
        tickers = df["Symbol"].str.replace(".", "-", regex=False).tolist()
        smap    = dict(zip(df["Symbol"].str.replace(".", "-", regex=False), df["GICS Sector"]))
        if len(tickers) >= 490:
            return tickers, smap
    except Exception:
        pass
    fallback = [
        "AAPL","MSFT","NVDA","AMZN","GOOGL","META","TSLA","AVGO","JPM","LLY",
        "V","UNH","XOM","MA","JNJ","PG","HD","MRK","COST","ABBV","CVX","BAC",
        "KO","CRM","PEP","TMO","WFC","NFLX","ORCL","AMD","ACN","ADBE","LIN",
        "MCD","WMT","CSCO","IBM","GS","GE","HON","DIS","CAT","RTX","AMGN",
        "VZ","T","CMCSA","PFE","ABT","TXN","MS","NEE","BMY","SPGI","DHR","UNP",
        "LOW","BLK","ISRG","GILD","SYK","CI","BSX","ELV","ITW","DE","LMT",
        "COP","EOG","SLB","OXY","FCX","PLD","AMT","CCI","EQIX","PSA",
        "CRWD","PANW","SNOW","PLTR","NET","UBER","ABNB","DXCM","ZTS","BIIB",
        "MRNA","NKE","LULU","TGT","TJX","UPS","FDX","NSC","CSX","DAL",
        "INTC","QCOM","MU","KLAC","LRCX","AMAT","SNPS","CDNS","ADI","MCHP",
    ]
    return list(dict.fromkeys(fallback)), {}

def _rs_smooth(prices: pd.Series, spy: pd.Series, period: int) -> pd.Series:
    rs = prices.pct_change(period) - spy.pct_change(period)
    return rs.ewm(span=EMA_SMOOTH, min_periods=3).mean()

def _rs_trend_slope(rs_series: pd.Series) -> float:
    from scipy import stats as scipy_stats
    recent = rs_series.dropna().iloc[-TREND_WIN:]
    if len(recent) < 5: return 0.0
    x = np.arange(len(recent))
    slope, *_ = scipy_stats.linregress(x, recent.values)
    std = recent.std()
    return round(float(slope / std) if std > 0 else 0.0, 4)

def _run_scan_engine(max_tickers: int = 150) -> tuple:
    tickers, smap = _get_sp500_tickers()
    tickers = tickers[:max_tickers]
    all_syms = list(dict.fromkeys([BENCHMARK] + list(SECTOR_ETFS.values()) + tickers))

    close_d, vol_d = {}, {}
    batches = [all_syms[i:i+BATCH_SIZE] for i in range(0, len(all_syms), BATCH_SIZE)]

    for batch in batches:
        try:
            raw = yf.download(batch, period="200d", auto_adjust=True, progress=False, threads=True)
            if isinstance(raw.columns, pd.MultiIndex):
                closes = raw["Close"] if "Close" in raw.columns.get_level_values(0) else pd.DataFrame()
                vols   = raw["Volume"] if "Volume" in raw.columns.get_level_values(0) else pd.DataFrame()
            else:
                closes = raw[["Close"]] if "Close" in raw.columns else pd.DataFrame()
                vols   = raw[["Volume"]] if "Volume" in raw.columns else pd.DataFrame()
            for sym in batch:
                if sym in closes.columns:
                    close_d[sym] = closes[sym].dropna()
                    vol_d[sym]   = vols[sym].dropna() if sym in vols.columns else pd.Series(dtype=float)
        except Exception:
            continue

    if BENCHMARK not in close_d:
        return pd.DataFrame(), pd.DataFrame(), {}

    spy   = close_d[BENCHMARK]
    rows  = []

    for ticker in tickers:
        if ticker not in close_d: continue
        prices = close_d[ticker]
        if len(prices) < 130: continue
        aligned_spy = spy.reindex(prices.index).ffill()

        try:
            rs_vals = {}
            for p in PERIODS:
                sm = _rs_smooth(prices, aligned_spy, p)
                rs_vals[p] = float(sm.iloc[-1]) if not sm.empty else 0.0

            rs_score_raw = sum(rs_vals[p] * WEIGHTS[p] for p in PERIODS)
            rs_trend     = _rs_trend_slope(_rs_smooth(prices, aligned_spy, 63))

            vol_today = float(vol_d[ticker].iloc[-1]) if ticker in vol_d and len(vol_d[ticker]) > 0 else 0
            vol_avg   = float(vol_d[ticker].tail(20).mean()) if ticker in vol_d and len(vol_d[ticker]) >= 20 else 1
            rvol      = round(vol_today / vol_avg, 2) if vol_avg > 0 else 1.0

            price = float(prices.iloc[-1])
            sector_raw = smap.get(ticker, "")
            sector     = GICS_MAP.get(sector_raw, sector_raw or "Otros")

            rows.append({
                "Ticker":      ticker,
                "RS_Score":    round(rs_score_raw * 100, 2),
                "RS_21d":      round(rs_vals[21] * 100, 2),
                "RS_63d":      round(rs_vals[63] * 100, 2),
                "RS_126d":     round(rs_vals[126] * 100, 2),
                "RS_Trend":    rs_trend,
                "RVOL":        rvol,
                "Precio":      round(price, 2),
                "Sector":      sector,
            })
        except Exception:
            continue

    if not rows:
        return pd.DataFrame(), pd.DataFrame(), {}

    df          = pd.DataFrame(rows).set_index("Ticker")
    df["RS_Pct"] = df["RS_Score"].rank(pct=True).mul(100).round(1)
    df["RS_Mom"] = (df["RS_21d"] > df["RS_63d"]).astype(int)

    sector_rs = df.groupby("Sector")["RS_Pct"].mean().to_dict()
    df["RS_vs_Sector"] = df.apply(
        lambda r: round(r["RS_Pct"] - sector_rs.get(r["Sector"], 50), 1), axis=1
    )

    sector_rows = []
    for sec, etf in SECTOR_ETFS.items():
        if etf in close_d:
            p     = close_d[etf]
            sp    = spy.reindex(p.index).ffill()
            sm63  = _rs_smooth(p, sp, 63)
            rs_v  = float(sm63.iloc[-1]) * 100 if not sm63.empty else 0
            ret63 = float((p.iloc[-1] / p.iloc[-63] - 1) * 100) if len(p) >= 63 else 0
            slope = _rs_trend_slope(sm63)
            sector_rows.append({"Sector": sec, "RS": round(rs_v, 2),
                                 "Return_63d": round(ret63, 2), "RS_trend": slope})

    sdf  = pd.DataFrame(sector_rows).set_index("Sector") if sector_rows else pd.DataFrame()
    meta = {"generated_at": datetime.now(timezone.utc).isoformat(),
            "mode": "on_demand", "n_stocks": len(df)}

    return df, sdf, meta

# ── MAIN ENDPOINTS ────────────────────────────────────────────────────────────

def _df_to_records(df: pd.DataFrame, limit: int = 500) -> list:
    if df.empty: return []
    records = []
    for ticker, row in df.iterrows():
        r = {"ticker": str(ticker)}
        for col in df.columns:
            val = row[col]
            try:
                if pd.isna(val): val = None
                elif isinstance(val, (np.integer,)): val = int(val)
                elif isinstance(val, (np.floating,)): val = round(float(val), 4)
            except Exception: pass
            r[col.lower()] = val
        records.append(r)
    return records[:limit]

def get_rsrw_from_gist() -> dict:
    try:
        data = _load_gist()
        if not data:
            return {"ok": False, "error": "Gist vacío o no disponible", "mode": "gist"}

        df, sdf, meta = _parse_gist(data)
        if df.empty:
            return {"ok": False, "error": "Sin datos en el Gist", "mode": "gist"}

        leaders = df[df["RS_Pct"] >= 80].sort_values("RS_Pct", ascending=False)
        laggards = df[df["RS_Pct"] <= 20].sort_values("RS_Pct", ascending=True)

        return {
            "ok":        True,
            "mode":      "gist",
            "freshness": _freshness(meta),
            "meta":      meta,
            "total":     len(df),
            "leaders":   _df_to_records(leaders, 50),
            "laggards":  _df_to_records(laggards, 30),
            "sectors":   _df_to_records(sdf) if not sdf.empty else [],
            "timestamp": datetime.now().strftime('%H:%M:%S'),
        }
    except Exception as e:
        return {"ok": False, "error": str(e), "mode": "gist"}

def get_rsrw_scan(max_tickers: int = 150) -> dict:
    try:
        df, sdf, meta = _run_scan_engine(max_tickers)
        if df.empty:
            return {"ok": False, "error": "Sin resultados del scan"}

        leaders  = df[df["RS_Pct"] >= 80].sort_values("RS_Pct", ascending=False)
        laggards = df[df["RS_Pct"] <= 20].sort_values("RS_Pct", ascending=True)

        return {
            "ok":       True,
            "mode":     "on_demand",
            "meta":     meta,
            "total":    len(df),
            "leaders":  _df_to_records(leaders, 50),
            "laggards": _df_to_records(laggards, 30),
            "sectors":  _df_to_records(sdf) if not sdf.empty else [],
            "timestamp": datetime.now().strftime('%H:%M:%S'),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}

def get_rsrw_ticker(ticker: str) -> dict:
    try:
        spy    = yf.Ticker(BENCHMARK).history(period="200d")["Close"]
        prices = yf.Ticker(ticker.upper()).history(period="200d")["Close"]
        if len(prices) < 63:
            return {"ok": False, "error": "Histórico insuficiente"}

        spy_r = spy.reindex(prices.index).ffill()
        rs_vals = {}
        for p in PERIODS:
            sm = _rs_smooth(prices, spy_r, p)
            rs_vals[p] = float(sm.iloc[-1]) * 100 if not sm.empty else 0.0

        rs_score = sum(rs_vals[p] * WEIGHTS[p] for p in PERIODS) * 100
        rs_trend = _rs_trend_slope(_rs_smooth(prices, spy_r, 63))

        hist_rs = _rs_smooth(prices, spy_r, 63).tail(60)
        chart   = {
            "dates":  [d.strftime('%Y-%m-%d') for d in hist_rs.index],
            "values": [round(float(v) * 100, 2) for v in hist_rs.values],
        }

        return {
            "ok":       True,
            "ticker":   ticker.upper(),
            "rs_score": round(rs_score, 2),
            "rs_pct":   None,
            "rs_21d":   round(rs_vals[21], 2),
            "rs_63d":   round(rs_vals[63], 2),
            "rs_126d":  round(rs_vals[126], 2),
            "rs_trend": rs_trend,
            "chart":    chart,
            "timestamp": datetime.now().strftime('%H:%M:%S'),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}