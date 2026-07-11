import json
import time
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

# ── UNIVERSO S&P 500 (embebido, sin dependencia de red ni de lxml) ────────────
# Lista de constituyentes con su sector GICS. Actualizar manualmente cuando el
# índice incorpore/elimine componentes (revisar 1-2 veces al año es suficiente).
SP500_SECTOR_MAP = {
    "AAPL":"Information Technology","MSFT":"Information Technology","NVDA":"Information Technology",
    "AMZN":"Consumer Discretionary","GOOGL":"Communication Services","GOOG":"Communication Services",
    "META":"Communication Services","TSLA":"Consumer Discretionary","AVGO":"Information Technology",
    "JPM":"Financials","LLY":"Health Care","V":"Financials","UNH":"Health Care","XOM":"Energy",
    "MA":"Financials","JNJ":"Health Care","PG":"Consumer Staples","HD":"Consumer Discretionary",
    "MRK":"Health Care","COST":"Consumer Staples","ABBV":"Health Care","CVX":"Energy","BAC":"Financials",
    "KO":"Consumer Staples","CRM":"Information Technology","PEP":"Consumer Staples","TMO":"Health Care",
    "WFC":"Financials","NFLX":"Communication Services","ORCL":"Information Technology","AMD":"Information Technology",
    "ACN":"Information Technology","ADBE":"Information Technology","LIN":"Materials","MCD":"Consumer Discretionary",
    "WMT":"Consumer Staples","CSCO":"Information Technology","IBM":"Information Technology","GS":"Financials",
    "GE":"Industrials","HON":"Industrials","DIS":"Communication Services","CAT":"Industrials","RTX":"Industrials",
    "AMGN":"Health Care","VZ":"Communication Services","T":"Communication Services","CMCSA":"Communication Services",
    "PFE":"Health Care","ABT":"Health Care","TXN":"Information Technology","MS":"Financials","NEE":"Utilities",
    "BMY":"Health Care","SPGI":"Financials","DHR":"Health Care","UNP":"Industrials","LOW":"Consumer Discretionary",
    "BLK":"Financials","ISRG":"Health Care","GILD":"Health Care","SYK":"Health Care","CI":"Health Care",
    "BSX":"Health Care","ELV":"Health Care","ITW":"Industrials","DE":"Industrials","LMT":"Industrials",
    "COP":"Energy","EOG":"Energy","SLB":"Energy","OXY":"Energy","FCX":"Materials","PLD":"Real Estate",
    "AMT":"Real Estate","CCI":"Real Estate","EQIX":"Real Estate","PSA":"Real Estate","CRWD":"Information Technology",
    "PANW":"Information Technology","SNOW":"Information Technology","PLTR":"Information Technology","NET":"Information Technology",
    "UBER":"Industrials","ABNB":"Consumer Discretionary","DXCM":"Health Care","ZTS":"Health Care","BIIB":"Health Care",
    "MRNA":"Health Care","NKE":"Consumer Discretionary","LULU":"Consumer Discretionary","TGT":"Consumer Staples",
    "TJX":"Consumer Discretionary","UPS":"Industrials","FDX":"Industrials","NSC":"Industrials","CSX":"Industrials",
    "DAL":"Industrials","INTC":"Information Technology","QCOM":"Information Technology","MU":"Information Technology",
    "KLAC":"Information Technology","LRCX":"Information Technology","AMAT":"Information Technology","SNPS":"Information Technology",
    "CDNS":"Information Technology","ADI":"Information Technology","MCHP":"Information Technology","AXP":"Financials",
    "C":"Financials","SCHW":"Financials","PGR":"Financials","CB":"Financials","MMC":"Financials","AON":"Financials",
    "ICE":"Financials","CME":"Financials","USB":"Financials","PNC":"Financials","TFC":"Financials","COF":"Financials",
    "AIG":"Financials","MET":"Financials","PRU":"Financials","TRV":"Financials","ALL":"Financials","AFL":"Financials",
    "AJG":"Financials","FIS":"Financials","FI":"Financials","BK":"Financials","STT":"Financials","NTRS":"Financials",
    "MTB":"Financials","HBAN":"Financials","RF":"Financials","FITB":"Financials","KEY":"Financials","CFG":"Financials",
    "WTW":"Financials","BRO":"Financials","ACGL":"Financials","CINF":"Financials","L":"Financials","GL":"Financials",
    "PFG":"Financials","RJF":"Financials","NDAQ":"Financials","MCO":"Financials","MSCI":"Financials","IVZ":"Financials",
    "BEN":"Financials","SYF":"Financials","DFS":"Financials","PYPL":"Financials","WU":"Financials","COIN":"Financials",
    "PEG":"Utilities","DUK":"Utilities","SO":"Utilities","D":"Utilities","AEP":"Utilities","EXC":"Utilities",
    "SRE":"Utilities","XEL":"Utilities","ED":"Utilities","WEC":"Utilities","ES":"Utilities","FE":"Utilities",
    "ETR":"Utilities","AEE":"Utilities","CMS":"Utilities","CNP":"Utilities","ATO":"Utilities","NI":"Utilities",
    "LNT":"Utilities","EVRG":"Utilities","PNW":"Utilities","NRG":"Utilities","AES":"Utilities","PPL":"Utilities",
    "DTE":"Utilities","AWK":"Utilities","AVB":"Real Estate","EQR":"Real Estate","AEM":"Materials","AMH":"Real Estate",
    "INVH":"Real Estate","ESS":"Real Estate","MAA":"Real Estate","UDR":"Real Estate","CPT":"Real Estate",
    "EXR":"Real Estate","DLR":"Real Estate","O":"Real Estate","WELL":"Real Estate","VTR":"Real Estate",
    "ARE":"Real Estate","BXP":"Real Estate","SPG":"Real Estate","REG":"Real Estate","FRT":"Real Estate",
    "KIM":"Real Estate","HST":"Real Estate","VICI":"Real Estate","IRM":"Real Estate","SBAC":"Real Estate",
    "WY":"Real Estate","CBRE":"Real Estate","JLL":"Real Estate","NVR":"Consumer Discretionary","PHM":"Consumer Discretionary",
    "DHI":"Consumer Discretionary","LEN":"Consumer Discretionary","KBH":"Consumer Discretionary","BLDR":"Industrials",
    "MAS":"Industrials","VMC":"Materials","MLM":"Materials","NUE":"Materials","STLD":"Materials","X":"Materials",
    "CLF":"Materials","AA":"Materials","ALB":"Materials","FMC":"Materials","CE":"Materials","DOW":"Materials",
    "DD":"Materials","LYB":"Materials","PPG":"Materials","SHW":"Materials","ECL":"Materials","IFF":"Materials",
    "APD":"Materials","CTVA":"Materials","MOS":"Materials","EMN":"Materials","AVY":"Materials","PKG":"Materials",
    "IP":"Materials","SEE":"Materials","BALL":"Materials","CCK":"Materials","WRK":"Materials","NEM":"Materials",
    "GOLD":"Materials","SCCO":"Materials","FCX2":"Materials","BG":"Consumer Staples","ADM":"Consumer Staples",
    "TSN":"Consumer Staples","HRL":"Consumer Staples","CAG":"Consumer Staples","CPB":"Consumer Staples",
    "K":"Consumer Staples","GIS":"Consumer Staples","SJM":"Consumer Staples","MKC":"Consumer Staples",
    "HSY":"Consumer Staples","MDLZ":"Consumer Staples","KHC":"Consumer Staples","STZ":"Consumer Staples",
    "BF.B":"Consumer Staples","TAP":"Consumer Staples","MNST":"Consumer Staples","KDP":"Consumer Staples",
    "PM":"Consumer Staples","MO":"Consumer Staples","CL":"Consumer Staples","KMB":"Consumer Staples",
    "CHD":"Consumer Staples","CLX":"Consumer Staples","CASY":"Consumer Staples","CHRW":"Industrials","CTAS":"Industrials",
    "EXPD":"Industrials","JBHT":"Industrials","ODFL":"Industrials","LDOS":"Industrials","HII":"Industrials",
    "GD":"Industrials","NOC":"Industrials","TXT":"Industrials","TDY":"Industrials","HWM":"Industrials",
    "PH":"Industrials","DOV":"Industrials","ROK":"Industrials","EMR":"Industrials","ETN":"Industrials",
    "AME":"Industrials","XYL":"Industrials","IEX":"Industrials","PWR":"Industrials","FAST":"Industrials",
    "PCAR":"Industrials","CMI":"Industrials","WAB":"Industrials","ALLE":"Industrials","JCI":"Industrials",
    "CARR":"Industrials","OTIS":"Industrials","SWK":"Industrials","SNA":"Industrials","GWW":"Industrials",
    "URI":"Industrials","WM":"Industrials","RSG":"Industrials","NDSN":"Industrials","IR":"Industrials",
    "GNRC":"Industrials","PAYX":"Industrials","ADP":"Industrials","BR":"Industrials","VRSK":"Industrials",
    "EFX":"Industrials","ROL":"Industrials","CTSH":"Information Technology","ACN2":"Information Technology",
    "INTU":"Information Technology","NOW":"Information Technology","ADSK":"Information Technology",
    "WDAY":"Information Technology","TEAM":"Information Technology","HUBS":"Information Technology",
    "DDOG":"Information Technology","ZS":"Information Technology","FTNT":"Information Technology",
    "GEN":"Information Technology","AKAM":"Information Technology","JNPR":"Information Technology",
    "FFIV":"Information Technology","GDDY":"Information Technology","EPAM":"Information Technology",
    "PTC":"Information Technology","ANSS":"Information Technology","KEYS":"Information Technology",
    "TER":"Information Technology","TYL":"Information Technology","TRMB":"Information Technology",
    "ZBRA":"Information Technology","NTAP":"Information Technology","WDC":"Information Technology",
    "STX":"Information Technology","HPQ":"Information Technology","DELL":"Information Technology",
    "HPE":"Information Technology","ON":"Information Technology","SWKS":"Information Technology",
    "QRVO":"Information Technology","MPWR":"Information Technology","ENPH":"Information Technology",
    "SEDG":"Information Technology","FSLR":"Information Technology","TXN2":"Information Technology",
    "APH":"Information Technology","TEL":"Information Technology","GLW":"Information Technology",
    "VRSN":"Information Technology","PAYC":"Information Technology","MSI":"Information Technology",
    "CDW":"Information Technology","JBL":"Information Technology","NXPI":"Information Technology",
    "ASML":"Information Technology","MRVL":"Information Technology","SMCI":"Information Technology",
    "ANET":"Information Technology","CSGP":"Real Estate","FDS":"Financials","MKTX":"Financials",
    "CBOE":"Financials","NWSA":"Communication Services","NWS":"Communication Services","FOXA":"Communication Services",
    "FOX":"Communication Services","PARA":"Communication Services","WBD":"Communication Services",
    "LYV":"Communication Services","TTWO":"Communication Services","EA":"Communication Services",
    "OMC":"Communication Services","IPG":"Communication Services","MTCH":"Communication Services",
    "TMUS":"Communication Services","CHTR":"Communication Services","DISH":"Communication Services",
    "EBAY":"Consumer Discretionary","ETSY":"Consumer Discretionary","BKNG":"Consumer Discretionary",
    "EXPE":"Consumer Discretionary","MAR":"Consumer Discretionary","HLT":"Consumer Discretionary",
    "RCL":"Consumer Discretionary","CCL":"Consumer Discretionary","NCLH":"Consumer Discretionary",
    "MGM":"Consumer Discretionary","WYNN":"Consumer Discretionary","LVS":"Consumer Discretionary",
    "DRI":"Consumer Discretionary","YUM":"Consumer Discretionary","CMG":"Consumer Discretionary",
    "SBUX":"Consumer Discretionary","DPZ":"Consumer Discretionary","QSR":"Consumer Discretionary",
    "ORLY":"Consumer Discretionary","AZO":"Consumer Discretionary","AAP":"Consumer Discretionary",
    "GPC":"Consumer Discretionary","BBY":"Consumer Discretionary","ULTA":"Consumer Discretionary",
    "ROST":"Consumer Discretionary","GPS":"Consumer Discretionary","TPR":"Consumer Discretionary",
    "RL":"Consumer Discretionary","VFC":"Consumer Discretionary","PVH":"Consumer Discretionary",
    "DECK":"Consumer Discretionary","CROX":"Consumer Discretionary","KMX":"Consumer Discretionary",
    "F":"Consumer Discretionary","GM":"Consumer Discretionary","APTV":"Consumer Discretionary",
    "BWA":"Consumer Discretionary","LKQ":"Consumer Discretionary","DPZ2":"Consumer Discretionary",
    "POOL":"Consumer Discretionary","WHR":"Consumer Discretionary","NWL":"Consumer Discretionary",
    "HAS":"Consumer Discretionary","MAT":"Consumer Discretionary","TPX":"Consumer Discretionary",
    "LEG":"Consumer Discretionary","CZR":"Consumer Discretionary","PENN":"Consumer Discretionary",
    "BBWI":"Consumer Discretionary","KSS":"Consumer Discretionary","M":"Consumer Discretionary",
    "JWN":"Consumer Discretionary","DG":"Consumer Discretionary","DLTR":"Consumer Discretionary",
    "BJ":"Consumer Staples","KR":"Consumer Staples","SYY":"Consumer Staples","USFD":"Consumer Staples",
    "WBA":"Consumer Staples","CVS":"Health Care","CAH":"Health Care","MCK":"Health Care","COR":"Health Care",
    "HCA":"Health Care","UHS":"Health Care","DVA":"Health Care","CNC":"Health Care","MOH":"Health Care",
    "HUM":"Health Care","CNC2":"Health Care","ALGN":"Health Care","IDXX":"Health Care","IQV":"Health Care",
    "A":"Health Care","WAT":"Health Care","MTD":"Health Care","RMD":"Health Care","ZBH":"Health Care",
    "EW":"Health Care","BAX":"Health Care","BDX":"Health Care","COO":"Health Care","HOLX":"Health Care",
    "PODD":"Health Care","DXC":"Information Technology","VTRS":"Health Care","ORG":"Health Care",
    "REGN":"Health Care","VRTX":"Health Care","INCY":"Health Care","SGEN":"Health Care","ALNY":"Health Care",
    "BMRN":"Health Care","TECH":"Health Care","CRL":"Health Care","CTLT":"Health Care","RVTY":"Health Care",
    "PFE2":"Health Care","JNJ2":"Health Care","ABC":"Health Care","XRAY":"Health Care","SOLV":"Health Care",
    "EOG2":"Energy","MPC":"Energy","PSX":"Energy","VLO":"Energy","HES":"Energy","DVN":"Energy",
    "FANG":"Energy","CTRA":"Energy","APA":"Energy","MRO":"Energy","BKR":"Energy","HAL":"Energy",
    "WMB":"Energy","KMI":"Energy","OKE":"Energy","TRGP":"Energy","EQT":"Energy","NOV":"Energy",
    "AAL":"Industrials","UAL":"Industrials","LUV":"Industrials","ALK":"Industrials","SAVE":"Industrials",
    "EXC2":"Utilities","PCG":"Utilities","EIX":"Utilities","EMN2":"Materials","DOC":"Real Estate",
    "EQH":"Financials","GEHC":"Health Care","KVUE":"Consumer Staples","VLTO":"Industrials","GEV":"Industrials",
    "SW":"Materials","SOLV2":"Health Care",
}
# Eliminar entradas placeholder erróneas (tickers duplicados por error al construir
# la lista a mano, con sufijo numérico añadido para evitar colisión de claves).
# El ticker real correspondiente ya existe en el diccionario con el sector correcto.
_PLACEHOLDER_KEYS = ["FCX2", "ACN2", "TXN2", "DPZ2", "CNC2", "PFE2", "JNJ2", "EOG2", "EXC2", "EMN2", "SOLV2",
                      "ABC"]  # ABC = ticker antiguo de Cencora, renombrado a COR en 2023
for _k in _PLACEHOLDER_KEYS:
    SP500_SECTOR_MAP.pop(_k, None)
del _PLACEHOLDER_KEYS, _k


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
            "timestamp": datetime.now().strftime('%H:%M:%S'),
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
            "timestamp": datetime.now().strftime('%H:%M:%S'),
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
            "timestamp": datetime.now().strftime('%H:%M:%S'),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}