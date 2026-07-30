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
from rsrw_engine import (  # noqa: E402
    rs_smooth as _rs_smooth, rs_trend_slope as _rs_trend_slope,
    rs_percentile, rs_momentum, PERIODS, WEIGHTS, EMA_SMOOTH, TREND_WIN,
    SECTOR_ETFS, GICS_MAP,
)
from yf_batch import download_batch  # noqa: E402

GIST_ID     = "36afc4bd0f8e376b0f6354889bda4d52"
GIST_FILE   = "rsrw_scan.json"
BENCHMARK   = "SPY"
BATCH_SIZE  = 40
BATCH_SLEEP = 1.8

# ── GIST ──────────────────────────────────────────────────────────────────────

def _load_gist() -> dict | None:
    """El Gist del scan nocturno, cacheado 10 min.

    Sin caché, CADA carga de la página RS/RW era una petición a la API de
    GitHub, que limita a 60 por hora y por IP a los clientes sin autenticar.
    Con ~100 usuarios eso se agota en minutos y a partir de ahí el módulo
    entero se queda sin datos -- y no solo este: Market lee otro Gist desde la
    misma IP del VPS y comparte ese presupuesto. Ver auditoría RS/RW, #2.

    10 min es de sobra: el contenido lo reescribe un scan NOCTURNO, así que
    durante la sesión de mercado no cambia nunca.
    """
    from services.cache import cache
    cacheado = cache.get("rsrw:gist")
    if cacheado is not None:
        return cacheado or None      # {} cacheado = fallo reciente, no reintentar

    try:
        r = requests.get(
            f"https://api.github.com/gists/{GIST_ID}",
            timeout=10,
            headers={"Accept": "application/vnd.github.v3+json"}
        )
        r.raise_for_status()
        content = r.json()["files"][GIST_FILE]["content"]
        data    = json.loads(content)
        bueno   = data if data.get("stocks") and len(data["stocks"]) > 10 else None
    except Exception:
        bueno = None

    # También se cachea el fallo, con TTL corto: si GitHub nos está limitando,
    # machacarlo en cada carga de página solo alarga el bloqueo.
    cache.set("rsrw:gist", bueno or {}, 600 if bueno else 60)
    return bueno

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

# _run_scan_engine() eliminado el 30/07/2026 junto con get_rsrw_scan() y el
# endpoint GET /rsrw/scan. Motivos, todos de la auditoría del módulo:
#
#   #3 -- El scan on-demand descargaba ~500 tickers de Yahoo DENTRO de una
#         petición HTTP, bloqueando el event loop de FastAPI durante minutos.
#         La propia UI ya decía "Scan nocturno automático, sin scan on-demand"
#         y el frontend no lo llamaba desde hacía tiempo (verificado: cero
#         referencias a /rsrw/scan en todo frontend/).
#   #5 -- Aquí vivía `tickers[:max_tickers]` con max_tickers=500 sobre un
#         universo de 503: recortaba ALFABÉTICAMENTE, así que los percentiles
#         se calculaban sobre un universo incompleto al que siempre le
#         faltaban los mismos tres valores del final del abecedario.
#   #14 -- Y aquí se repetían los umbrales 80/20 y los límites 50/30 de
#         leaders/laggards, ya escritos en get_rsrw_from_gist().
#
# El cálculo de verdad vive en scripts/rsrw_scan.py (GitHub Actions, nocturno,
# universo completo) sobre shared/rsrw_engine.py. Si algún día hace falta un
# scan bajo demanda, el sitio correcto es disparar el workflow, no recalcular
# dentro de una petición.

# ── MAIN ENDPOINTS ────────────────────────────────────────────────────────────

def _df_to_records(df: pd.DataFrame, limit: int = 500) -> list:
    if df.empty: return []
    # El nombre del índice decide cómo se llama la clave: "Ticker" para las
    # acciones, "Sector" para la tabla sectorial. Antes se escribía "ticker"
    # SIEMPRE, así que "Tecnología" o "Energía" viajaban en un campo llamado
    # ticker -- el frontend lo tapaba con un `s.ticker || s.sector`, pero
    # cualquier consumidor que se fíe del nombre del campo (el tagging de
    # cartera/watchlist, un deep-link ?ticker=) intentaría buscar un sector
    # como si fuera un símbolo. Ver auditoría RS/RW, #12.
    clave = (df.index.name or "ticker").strip().lower()
    records = []
    for ticker, row in df.iterrows():
        r = {clave: str(ticker)}
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

def _tag_cartera(records: list) -> list:
    """Añade en_cartera a una lista de records de ticker (leaders/laggards,
    nunca a sectors, que no son tickers) -- badge 💼, Fase 3 del roadmap."""
    from services.cartera_service import get_cartera_tickers
    cartera_tickers = get_cartera_tickers()
    for r in records:
        r["en_cartera"] = r.get("ticker") in cartera_tickers
    return records

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
            "leaders":   _tag_cartera(_df_to_records(leaders, 50)),
            "laggards":  _tag_cartera(_df_to_records(laggards, 30)),
            "sectors":   _df_to_records(sdf) if not sdf.empty else [],
            "timestamp": get_timestamp(),
        }
    except Exception as e:
        return {"ok": False, "error": str(e), "mode": "gist"}

def get_rsrw_ticker(ticker: str) -> dict:
    try:
        ticker_up = ticker.upper()
        spy    = yf.Ticker(BENCHMARK).history(period="260d")["Close"]
        prices = yf.Ticker(ticker_up).history(period="260d")["Close"]
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

        # Percentil real: se busca en el scan nocturno (Gist) más reciente. Sin
        # scan disponible o ticker ausente de él, se deja sin percentil (None),
        # no se fabrica -- mismo criterio que la caché de universo de CANSLIM
        # (sesión 23).
        rs_pct = None
        try:
            gist_data = _load_gist()
            if gist_data:
                df, _, _ = _parse_gist(gist_data)
                if ticker_up in df.index:
                    val = df.loc[ticker_up, "RS_Pct"]
                    rs_pct = round(float(val), 1) if pd.notna(val) else None
        except Exception:
            pass

        return {
            "ok":       True,
            "ticker":   ticker_up,
            "rs_score": round(rs_score, 2),
            "rs_pct":   rs_pct,
            "rs_21d":   round(rs_vals_raw[21] * 100, 2),
            "rs_63d":   round(rs_vals_raw[63] * 100, 2),
            "rs_126d":  round(rs_vals_raw[126] * 100, 2),
            "rs_trend": rs_trend,
            "chart":    chart,
            "timestamp": get_timestamp(),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}