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
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timezone

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

# ── UNIVERSO S&P 500 (embebido, sin dependencia de red ni de lxml) ────────────
# Lista de constituyentes con su sector GICS. Actualizar manualmente cuando el
# índice incorpore/elimine componentes (revisar 1-2 veces al año es suficiente).
# Mismo mapa que backend/services/rsrw_service.py — si se actualiza uno,
# actualizar el otro para que on-demand (fallback) y el scan nocturno usen el
# mismo universo.
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
        s["rs_momentum"]   = 1 if s["rs_21d"] > s["rs_63d"] else 0
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