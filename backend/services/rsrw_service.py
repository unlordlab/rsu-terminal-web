import json
import time
import os
import sys
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor
import yfinance as yf

# Universo compartido -- ver shared/sp500_universe.py (Fase 2.1 del Plan
# Maestro, 20/07/2026). Antes había un diccionario embebido aquí mismo,
# idéntico al de scripts/scanner_universe.py y scripts/rsrw_scan.py -- ahora
# una sola fuente de verdad para los tres. shared/ es sibling de backend/,
# así que se llega con "..".
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "shared"))
from sp500_universe import SP500_SECTOR_MAP  # noqa: E402
from time_utils import get_timestamp  # noqa: E402

GIST_ID     = "36afc4bd0f8e376b0f6354889bda4d52"
GIST_FILE   = "rsrw_scan.json"
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
        # Mapear sectores en inglés a español
        if "Sector" in df.columns:
            df["Sector"] = df["Sector"].map(lambda x: GICS_MAP.get(str(x), x) if pd.notna(x) else "Otros")
            df["Sector"] = df["Sector"].fillna("Otros")
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
    """
    Universo S&P 500 embebido estáticamente en el código (sin llamada de red ni
    dependencia de lxml/Wikipedia). Se actualiza manualmente cuando cambien las
    constituyentes del índice — suficientemente estable para uso entre revisiones.
    """
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

def _run_scan_engine(max_tickers: int = 500) -> tuple:
    tickers, smap = _get_sp500_tickers()
    tickers = tickers[:max_tickers]
    all_syms = list(dict.fromkeys([BENCHMARK] + list(SECTOR_ETFS.values()) + tickers))

    close_d, vol_d = {}, {}
    batches = [all_syms[i:i+BATCH_SIZE] for i in range(0, len(all_syms), BATCH_SIZE)]
    n_batches = len(batches)

    for i, batch in enumerate(batches):
        original_batch = list(batch)
        original_size  = len(original_batch)
        got_syms = set()
        for attempt in range(3):  # hasta 3 intentos si el lote vuelve incompleto
            try:
                raw = yf.download(batch, period="260d", auto_adjust=True, progress=False, threads=True)
                if isinstance(raw.columns, pd.MultiIndex):
                    closes = raw["Close"] if "Close" in raw.columns.get_level_values(0) else pd.DataFrame()
                    vols   = raw["Volume"] if "Volume" in raw.columns.get_level_values(0) else pd.DataFrame()
                else:
                    closes = raw[["Close"]] if "Close" in raw.columns else pd.DataFrame()
                    vols   = raw[["Volume"]] if "Volume" in raw.columns else pd.DataFrame()

                for sym in batch:
                    if sym in closes.columns:
                        series = closes[sym].dropna()
                        # Yahoo a veces devuelve la columna presente pero vacía/NaN
                        # cuando el rate-limit es "suave" (sin lanzar excepción).
                        if len(series) >= 130:
                            close_d[sym] = series
                            vol_d[sym]   = vols[sym].dropna() if sym in vols.columns else pd.Series(dtype=float)
                            got_syms.add(sym)

                missing  = [s for s in original_batch if s not in got_syms]
                coverage = len(got_syms) / original_size if original_size else 1.0

                # Si llegó casi todo, aceptamos el lote tal cual.
                if coverage >= 0.85 or attempt == 2:
                    if missing:
                        print(f"[RS/RW scan] Lote {i+1}/{n_batches}: {len(missing)} símbolos sin datos suficientes tras {attempt+1} intento(s): {missing[:15]}{'...' if len(missing) > 15 else ''}")
                    break

                # Cobertura pobre y aún quedan intentos: reintentamos SOLO los que faltan
                print(f"[RS/RW scan] Lote {i+1}/{n_batches}: cobertura {coverage:.0%} tras intento {attempt+1}, reintentando {len(missing)} símbolos...")
                batch = missing
                time.sleep(2.5)
            except Exception as e:
                print(f"[RS/RW scan] Lote {i+1}/{n_batches} intento {attempt+1} falló: {e}")
                time.sleep(2.5)
                continue

        # Pausa entre lotes para evitar "Too many requests" en scans grandes (S&P 500 completo)
        if i < n_batches - 1:
            time.sleep(BATCH_SLEEP)

    print(f"[RS/RW scan] Total con histórico suficiente: {len(close_d)}/{len(all_syms)} símbolos solicitados")

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
            # Blend de 3 ventanas (21/63/126, mismos pesos que las acciones
            # individuales) en vez de una única ventana fija de 63 días —
            # antes había una asimetría metodológica entre esta parte del
            # módulo y el resto (acciones sí usaban blend, sectores no).
            sec_rs_raw = {}
            for pp in PERIODS:
                sm = _rs_smooth(p, sp, pp)
                sec_rs_raw[pp] = float(sm.iloc[-1]) if not sm.empty else 0.0
            rs_v  = sum(sec_rs_raw[pp] * WEIGHTS[pp] for pp in PERIODS) * 100
            ret63 = float((p.iloc[-1] / p.iloc[-63] - 1) * 100) if len(p) >= 63 else 0
            # La tendencia (flecha) se calcula sobre la componente de 63d
            # específicamente — igual que se hace para acciones individuales,
            # por coherencia entre ambas partes del módulo.
            slope = _rs_trend_slope(_rs_smooth(p, sp, 63))
            sector_rows.append({"Sector": sec, "RS": round(rs_v, 2),
                                 "Return_63d": round(ret63, 2), "RS_trend": slope})

    sdf  = pd.DataFrame(sector_rows).set_index("Sector") if sector_rows else pd.DataFrame()
    meta = {"generated_at": datetime.now(timezone.utc).isoformat(),
            "mode": "on_demand", "n_stocks": len(df), "n_requested": len(tickers)}

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
                elif isinstance(val, str): val = val.strip()
            except Exception: pass
            r[col.lower()] = val
        # Asegurar que sector nunca sea vacío
        if not r.get('sector') or str(r.get('sector', '')).strip() in ('', 'nan', 'None'):
            r['sector'] = 'Otros'
        records.append(r)
    return records[:limit]

def get_universe_dataframe():
    """
    Devuelve (df, meta) con el DataFrame COMPLETO del universo (todas las
    acciones, no solo líderes/laggards) tal como lo deja el último scan
    guardado en el Gist. Pensado para que otros módulos (ej. Composición
    Sectorial en Market) puedan agregar métricas por sector reutilizando este
    mismo dato, sin repetir la carga del Gist ni hacer llamadas nuevas a APIs.
    Devuelve None si el Gist no está disponible o no tiene datos válidos.
    """
    data = _load_gist()
    if not data:
        return None
    df, sdf, meta = _parse_gist(data)
    if df.empty:
        return None
    return df, meta

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
            "timestamp": get_timestamp(),
        }
    except Exception as e:
        return {"ok": False, "error": str(e), "mode": "gist"}

def get_rsrw_scan(max_tickers: int = 500) -> dict:
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
            "timestamp": get_timestamp(),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}

def get_rsrw_ticker(ticker: str) -> dict:
    try:
        spy    = yf.Ticker(BENCHMARK).history(period="260d")["Close"]
        prices = yf.Ticker(ticker.upper()).history(period="260d")["Close"]
        if len(prices) < 63:
            return {"ok": False, "error": "Histórico insuficiente"}

        spy_r = spy.reindex(prices.index).ffill()
        # rs_vals guarda el diferencial RAW (sin escalar) de cada periodo —
        # igual que _run_scan_engine(), para que el RS Score de esta función
        # sea comparable con el del scan nocturno, no una escala distinta.
        rs_vals_raw = {}
        for p in PERIODS:
            sm = _rs_smooth(prices, spy_r, p)
            rs_vals_raw[p] = float(sm.iloc[-1]) if not sm.empty else 0.0

        # Antes: cada rs_vals ya se multiplicaba por 100 aquí Y el rs_score
        # se volvía a multiplicar por 100 sobre esos valores ya escalados —
        # doble escalado que inflaba el RS Score ~100x (13125.8 en vez de
        # ~131.3 para INTC). Ahora: los componentes RAW se pesan y se
        # escalan una única vez, igual que en _run_scan_engine().
        rs_score = sum(rs_vals_raw[p] * WEIGHTS[p] for p in PERIODS) * 100
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
            "rs_21d":   round(rs_vals_raw[21] * 100, 2),
            "rs_63d":   round(rs_vals_raw[63] * 100, 2),
            "rs_126d":  round(rs_vals_raw[126] * 100, 2),
            "rs_trend": rs_trend,
            "chart":    chart,
            "timestamp": get_timestamp(),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}