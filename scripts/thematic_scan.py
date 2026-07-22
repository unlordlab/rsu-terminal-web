#!/usr/bin/env python3
"""
RSU Terminal — Thematic Sector Scan
Calcula la Composición Sectorial (29 cestas temáticas: BIOTECH, SEMIS, MAG7...)
y guarda el resultado en un GitHub Gist. Pensado para ejecutarse 1x/día vía
GitHub Actions, igual que daily_briefing.py — así el backend nunca tiene que
llamar a yfinance en el camino de una petición real de un usuario, evitando
rate limits y tiempos de carga largos en la página.

Script standalone (no importa nada de backend/) para no depender del entorno
de FastAPI dentro del runner de GitHub Actions — mismo patrón que ya usa
scripts/daily_briefing.py en este repo.
"""

import os
import sys
import json
import time
import requests
import pandas as pd
from datetime import datetime, timezone
import yfinance as yf

# shared/ es sibling de scripts/ -- mismo patrón que ya usan rsrw_scan.py y
# scanner_universe.py para no depender de nada de backend/ (este script
# corre standalone en el runner de GitHub Actions).
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "shared"))
from rsrw_engine import (  # noqa: E402
    rs_smooth as _rs_smooth, rs_percentile, rs_momentum, PERIODS, WEIGHTS, EMA_SMOOTH,
)

GIST_TOKEN = os.environ.get("GIST_TOKEN", "")
GIST_ID    = os.environ.get("THEMATIC_GIST_ID", "")
GIST_FILE  = "thematic_scan.json"

BENCHMARK   = "SPY"
BATCH_SIZE  = 40
BATCH_SLEEP = 1.5

# Si editas las cestas, edita SOLO aquí — este script es la única fuente de
# verdad para el scan (el backend solo lee el resultado ya calculado del Gist).
THEMATIC_SECTORS = {
    "BIOTECH": [
        "MRNA","BNTX","REGN","VRTX","GILD","AMGN","BIIB","ALNY","SRPT","BMRN",
        "INCY","IONS","EXEL","NBIX","RARE","FOLD","BLUE","CRSP","EDIT","NTLA",
        "BEAM","VERV","ARWR","IOVA","RYTM","ACAD","HALO","PCRX","UTHR",
    ],
    "GLP-1": [
        "LLY","NVO","VKTX","AMGN","PFE","AZN","MDGL","ALT","TERN","RXRX","CRNX","ZLAB",
    ],
    "MEMORY": [
        "MU","WDC","STX","SIMO","FORM","UCTT","AEIS","ENTG","COHU",
    ],
    "CYBER": [
        "CRWD","PANW","ZS","FTNT","OKTA","CYBR","S","NET","QLYS","RPD",
        "VRNS","TENB","FFIV","CHKP","GEN",
    ],
    "FINTECH": [
        "SQ","PYPL","SOFI","AFRM","UPST","COIN","HOOD","FOUR","GPN","FI",
        "MA","V","AXP","NU","PAGS","STNE","TOST","FUTU",
    ],
    "BOOMER": [
        "KO","PEP","PG","JNJ","MO","PM","VZ","T","MMM","CL","KMB","GIS","K","CAG","CLX",
    ],
    "SEMIS": [
        "NVDA","AMD","INTC","TSM","AVGO","QCOM","TXN","MU","ASML","AMAT",
        "LRCX","KLAC","ON","MCHP","MRVL","SWKS","QRVO","ADI","NXPI","MPWR",
        "ARM","SMCI","WOLF","COHR","LSCC",
    ],
    "GAMING": [
        "RBLX","EA","TTWO","U","DKNG","PENN","SE","NTES",
    ],
    "INVERSE BETA": [
        "KO","PG","JNJ","WMT","MCD","VZ","T","SO","DUK","NEE","PEP","CL","KMB","MO",
    ],
    "DATA CENTER": [
        "EQIX","DLR","VRT","NVDA","SMCI","DELL","HPE","ANET","MOD","ETN",
        "PWR","NTAP","CSCO",
    ],
    "CRYPTO": [
        "COIN","MSTR","MARA","RIOT","CLSK","HUT","BITF","CIFR","BTBT","WULF",
    ],
    "PHOTONICS": [
        "COHR","LITE","VIAV","AAOI","INFN","NPTN",
    ],
    "AI INFRA": [
        "NVDA","AMD","SMCI","DELL","ANET","AVGO","MRVL","VRT","ETN","MU",
        "ASML","AMZN","MSFT","GOOGL",
    ],
    "ROBOTICS": [
        "ISRG","ROK","IRBT","TER","ZBRA","NVDA","PATH","EMR",
    ],
    "QUANTUM": [
        "IBM","IONQ","RGTI","QUBT","ARQQ","GOOGL","HON",
    ],
    "DEFENSE": [
        "LMT","RTX","NOC","GD","BA","LHX","HII","TXT","KTOS","AVAV",
        "LDOS","BWXT","HEI",
    ],
    "STREAMING": [
        "NFLX","DIS","WBD","PARA","ROKU","SPOT","FUBO",
    ],
    "NUCLEAR": [
        "CEG","VST","NRG","BWXT","LEU","CCJ","UEC","UUUU","SMR","OKLO","NNE","DNN",
    ],
    "STORAGE": [
        "WDC","STX","NTAP","PSTG","DBX",
    ],
    "ENERGY": [
        "XOM","CVX","COP","EOG","SLB","OXY","MPC","PSX","VLO","KMI","WMB","HAL","BKR",
    ],
    "SOFTWARE": [
        "MSFT","ORCL","CRM","ADBE","NOW","INTU","SNOW","PLTR","WDAY","DDOG",
        "TEAM","HUBS","PANW","ZS",
    ],
    "EV / AUTONOMY": [
        "TSLA","RIVN","LCID","NIO","XPEV","LI","F","GM","APTV","MBLY","QS","CHPT",
    ],
    "CHINA": [
        "BABA","PDD","JD","NIO","XPEV","LI","BIDU","NTES","TCOM","BILI","TME","YUMC",
    ],
    "DRONES": [
        "AVAV","KTOS","UMAC","RCAT","ONDS","DPRO",
    ],
    "MATERIALS": [
        "LIN","APD","SHW","ECL","NEM","FCX","DOW","DD","ALB","MOS",
    ],
    "METALS": [
        "FCX","NEM","GOLD","AA","X","CLF","STLD","NUE","SCCO","MP",
    ],
    "MAG7": [
        "AAPL","MSFT","GOOGL","AMZN","META","NVDA","TSLA",
    ],
    "SPACE": [
        "RKLB","ASTS","LUNR","RDW","IRDM","GSAT","PL",
    ],
    "SOLAR": [
        "ENPH","SEDG","FSLR","RUN","NXT","CSIQ","JKS","ARRY","SHLS",
    ],
}



def _fetch_batch(all_syms: list) -> dict:
    close_d = {}
    batches = [all_syms[i:i + BATCH_SIZE] for i in range(0, len(all_syms), BATCH_SIZE)]
    n = len(batches)
    for i, batch in enumerate(batches):
        print(f"📦 Lote {i+1}/{n} ({len(batch)} símbolos)...")
        try:
            raw = yf.download(batch, period="200d", auto_adjust=True, progress=False, threads=True)
            if isinstance(raw.columns, pd.MultiIndex):
                closes = raw["Close"] if "Close" in raw.columns.get_level_values(0) else pd.DataFrame()
            else:
                closes = raw[["Close"]] if "Close" in raw.columns else pd.DataFrame()
            for sym in batch:
                if sym in closes.columns:
                    series = closes[sym].dropna()
                    if len(series) >= 130:
                        close_d[sym] = series
        except Exception as e:
            print(f"⚠️  Lote {i+1}/{n} falló: {e}")
        if i < n - 1:
            time.sleep(BATCH_SLEEP)
    return close_d


def run_scan() -> dict:
    all_tickers = sorted(set(t for lst in THEMATIC_SECTORS.values() for t in lst))
    all_syms = [BENCHMARK] + [t for t in all_tickers if t != BENCHMARK]
    print(f"🔍 Universo temático: {len(all_tickers)} tickers únicos en {len(THEMATIC_SECTORS)} cestas")

    close_d = _fetch_batch(all_syms)
    if BENCHMARK not in close_d:
        raise ValueError("Sin datos de SPY — cancelado")

    spy  = close_d[BENCHMARK]
    rows = []
    for ticker in all_tickers:
        if ticker not in close_d:
            continue
        prices = close_d[ticker]
        if len(prices) < 130:
            continue
        aligned_spy = spy.reindex(prices.index).ffill()
        try:
            rs_vals = {}
            for p in PERIODS:
                sm = _rs_smooth(prices, aligned_spy, p)
                rs_vals[p] = float(sm.iloc[-1]) if not sm.empty else 0.0
            rs_score = sum(rs_vals[p] * WEIGHTS[p] for p in PERIODS)
            rows.append({
                "ticker":   ticker,
                "rs_score": round(rs_score * 100, 2),
                "rs_21d":   round(rs_vals[21] * 100, 2),
                "rs_63d":   round(rs_vals[63] * 100, 2),
                "precio":   round(float(prices.iloc[-1]), 2),
            })
        except Exception:
            continue

    print(f"✅ {len(rows)}/{len(all_tickers)} tickers con histórico suficiente")
    if not rows:
        raise ValueError("Sin filas calculadas")

    df = pd.DataFrame(rows).set_index("ticker")
    df["rs_pct"] = rs_percentile(df["rs_score"])
    df["rs_mom"] = df.apply(lambda r: rs_momentum(r["rs_21d"], r["rs_63d"]), axis=1)

    grouped = []
    for theme, tickers in THEMATIC_SECTORS.items():
        sub = df[df.index.isin(tickers)]
        basket = len(sub)
        if basket == 0:
            grouped.append({
                "sector": theme, "basket": 0, "leaders": 0,
                "leaders_pct": 0, "avg_score": None, "avg_momentum": None,
            })
            continue
        leaders = int((sub["rs_pct"] >= 80).sum())
        grouped.append({
            "sector":       theme,
            "basket":       basket,
            "leaders":      leaders,
            "leaders_pct":  round(leaders / basket * 100, 0),
            "avg_score":    round(float(sub["rs_pct"].mean()), 1),
            "avg_momentum": round(float(sub["rs_mom"].mean()), 2),
        })

    scored = [g for g in grouped if g["avg_score"] is not None]
    empty  = [g for g in grouped if g["avg_score"] is None]
    scored.sort(key=lambda r: r["avg_score"], reverse=True)
    for i, r in enumerate(scored):
        r["rank"] = i + 1
    for r in empty:
        r["rank"] = None

    # Desempate: cuando varios sectores empatan en avg_momentum (frecuente en
    # el extremo +1/0, ya que es la fracción de la cesta acelerando — varios
    # sectores pueden tener el 100% de sus nombres acelerando a la vez), se
    # usa avg_score como segundo criterio. En "acelerando" gana el de mayor
    # score (momentum fuerte + fortaleza real, no solo una cesta pequeña con
    # ruido). En "desacelerando" gana el de menor score (debilidad real, no
    # solo una pausa dentro de un sector que sigue siendo fuerte).
    accelerating = sorted(scored, key=lambda r: (r["avg_momentum"], r["avg_score"]), reverse=True)[:5]
    decelerating = sorted(scored, key=lambda r: (r["avg_momentum"], r["avg_score"]))[:5]

    return {
        "ok":              True,
        "sectors":         scored + empty,
        "strongest":       scored[0] if scored else None,
        "weakest":         scored[-1] if scored else None,
        "sectors_tracked": len(scored),
        "sectors_empty":   len(empty),
        "universe_size":   int(len(df)),
        "accelerating":    accelerating,
        "decelerating":    decelerating,
        "generated_at":    datetime.now(timezone.utc).isoformat(),
    }


def save_to_gist(result: dict):
    if not GIST_TOKEN:
        raise ValueError("GIST_TOKEN no configurado")
    if not GIST_ID:
        raise ValueError("THEMATIC_GIST_ID no configurado")

    r = requests.patch(
        f"https://api.github.com/gists/{GIST_ID}",
        headers={
            "Authorization": f"token {GIST_TOKEN}",
            "Accept":        "application/vnd.github+json",
        },
        json={
            "files": {
                GIST_FILE: {
                    "content": json.dumps(result, ensure_ascii=False, indent=2)
                }
            }
        },
        timeout=30,
    )
    if r.status_code not in (200, 201):
        raise ValueError(f"Gist error {r.status_code}: {r.text[:300]}")
    print(f"✅ Composición sectorial guardada en Gist: {r.json()['html_url']}")


def main():
    print(f"🕐 Thematic scan — {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}")
    result = run_scan()
    print("💾 Guardando en GitHub Gist...")
    save_to_gist(result)
    print("✅ Scan completado")


if __name__ == "__main__":
    main()