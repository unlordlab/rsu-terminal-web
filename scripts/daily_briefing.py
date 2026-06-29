#!/usr/bin/env python3
"""
RSU Terminal — Daily Market Briefing
Genera análisis diario via OpenRouter (Qwen) y lo guarda en GitHub Gist
"""

import os
import json
import requests
from datetime import datetime, timedelta
import yfinance as yf
import numpy as np

OPENROUTER_KEY = os.environ.get("OPENROUTER_API_KEY", "")
GIST_TOKEN     = os.environ.get("GIST_TOKEN", "")
GIST_ID        = os.environ.get("GIST_ID", "715ee0c4e571517c11fa65c5c2376c34")
MODEL          = "qwen/qwen3-235b-a22b"

# ── RECOPILAR DATOS DE MERCADO ────────────────────────────────────────────────

def _safe(val):
    try:
        v = float(val)
        return v if not (np.isnan(v) or np.isinf(v)) else None
    except Exception:
        return None

def get_market_data() -> dict:
    """Recopila datos reales de mercado para dar contexto al LLM"""
    data = {}

    # Índices principales
    tickers = {
        "SPX":  "^GSPC",
        "NDX":  "^NDX",
        "RUT":  "^RUT",
        "VIX":  "^VIX",
        "DXY":  "DX-Y.NYB",
        "TNX":  "^TNX",   # 10Y yield
        "TYX":  "^TYX",   # 30Y yield
        "IRX":  "^IRX",   # 2Y proxy
        "GOLD": "GC=F",
        "WTI":  "CL=F",
        "BTC":  "BTC-USD",
        "ES":   "ES=F",      # futuro S&P 500 — gap pre-market
        "NQ":   "NQ=F",      # futuro Nasdaq 100 — gap pre-market
        "EURUSD": "EURUSD=X", # proxy divergencia BCE vs Fed
        "USDJPY": "USDJPY=X", # proxy divergencia BoJ vs Fed
    }

    for name, ticker in tickers.items():
        try:
            t    = yf.Ticker(ticker)
            hist = t.history(period="5d", interval="1d").dropna()
            if len(hist) < 2: continue
            prev  = float(hist["Close"].iloc[-2])
            last  = float(hist["Close"].iloc[-1])
            chg   = round((last - prev) / prev * 100, 2)
            data[name] = {"price": round(last, 2), "chg_pct": chg}
        except Exception:
            data[name] = {"price": None, "chg_pct": None}

    # Sectores S&P 500
    sectors = {
        "XLK": "Tecnología", "XLF": "Financiero", "XLV": "Salud",
        "XLE": "Energía",    "XLI": "Industrial",  "XLY": "Consumo Discr.",
        "XLP": "Consumo Bás","XLB": "Materiales",  "XLU": "Utilities",
        "XLRE":"Inmobiliario","XLC": "Comunicaciones"
    }
    sector_data = {}
    for etf, name in sectors.items():
        try:
            t    = yf.Ticker(etf)
            hist = t.history(period="5d", interval="1d").dropna()
            if len(hist) < 2: continue
            prev = float(hist["Close"].iloc[-2])
            last = float(hist["Close"].iloc[-1])
            chg  = round((last - prev) / prev * 100, 2)
            # 5 días
            chg5 = round((last - float(hist["Close"].iloc[0])) / float(hist["Close"].iloc[0]) * 100, 2)
            sector_data[etf] = {"name": name, "chg_1d": chg, "chg_5d": chg5}
        except Exception:
            pass
    data["sectors"] = sector_data

    # Niveles técnicos reales (SMA20/50/200, máx/mín 20d) — para que el LLM no se invente
    # soportes/resistencias sin datos detrás. No son niveles de "price action" discrecional,
    # son medias móviles y rangos calculados directamente del histórico real.
    tech_levels = {}
    for name, ticker in {"SPX": "^GSPC", "NDX": "^NDX"}.items():
        try:
            t    = yf.Ticker(ticker)
            hist = t.history(period="220d", interval="1d").dropna()
            if len(hist) < 50:
                tech_levels[name] = None
                continue
            closes = hist["Close"]
            last   = float(closes.iloc[-1])
            sma20  = float(closes.rolling(20).mean().iloc[-1])
            sma50  = float(closes.rolling(50).mean().iloc[-1])
            sma200 = float(closes.rolling(200).mean().iloc[-1]) if len(closes) >= 200 else None
            high20 = float(hist["High"].rolling(20).max().iloc[-1])
            low20  = float(hist["Low"].rolling(20).min().iloc[-1])
            tech_levels[name] = {
                "last": round(last, 2),
                "sma20": round(sma20, 2), "sma50": round(sma50, 2),
                "sma200": round(sma200, 2) if sma200 else None,
                "high_20d": round(high20, 2), "low_20d": round(low20, 2),
                "vs_sma200_pct": round((last - sma200) / sma200 * 100, 2) if sma200 else None,
            }
        except Exception:
            tech_levels[name] = None
    data["tech_levels"] = tech_levels

    # Proxy aproximado de expectativas de Fed Funds (NO es CME FedWatch — esa API es de
    # pago, $25+/mes). Se calcula comparando el yield a 3 meses (IRX) contra el Fed Funds
    # Rate actual: si el 3M cotiza por debajo del Fed Funds, el mercado de bonos está
    # pricing bajadas de tipos en ese horizonte; si cotiza igual o por encima, no las espera.
    try:
        irx_val = data.get("IRX", {}).get("price")
        r = requests.get(
            "https://fred.stlouisfed.org/graph/fredgraph.csv?id=FEDFUNDS",
            timeout=10, headers={"User-Agent": "RSU Terminal contact@rsu-terminal.com"}
        )
        fed_funds_now = None
        if r.status_code == 200:
            lines = r.text.strip().split("\n")
            last_line = lines[-1].split(",")
            fed_funds_now = float(last_line[1])
        if irx_val is not None and fed_funds_now is not None:
            implied_gap = round(fed_funds_now - irx_val, 2)  # positivo = mercado espera bajadas
            data["fed_funds_proxy"] = {
                "fed_funds_now": fed_funds_now,
                "yield_3m": irx_val,
                "implied_gap_pct": implied_gap,
                "interpretation": (
                    "bajadas" if implied_gap > 0.15 else
                    "subidas" if implied_gap < -0.15 else
                    "sin cambios significativos"
                ),
            }
        else:
            data["fed_funds_proxy"] = None
    except Exception:
        data["fed_funds_proxy"] = None

    # Fear & Greed
    try:
        r = requests.get(
            "https://production.dataviz.cnn.io/index/fearandgreed/graphdata",
            headers={"User-Agent": "Mozilla/5.0", "Referer": "https://edition.cnn.com"},
            timeout=8
        )
        if r.status_code == 200:
            fg = r.json()["fear_and_greed"]
            data["fear_greed"] = {
                "score":  int(fg["score"]),
                "rating": fg["rating"],
                "prev":   int(fg.get("previous_close", fg["score"])),
            }
    except Exception:
        data["fear_greed"] = None

    # VIX Term Structure
    vix_tickers = {"VIX_SPOT": "^VIX", "VIX_3M": "^VIX3M", "VIX_6M": "^VIX6M"}
    vix_data = {}
    for name, ticker in vix_tickers.items():
        try:
            t    = yf.Ticker(ticker)
            hist = t.history(period="5d").dropna()
            if len(hist) > 0:
                vix_data[name] = round(float(hist["Close"].iloc[-1]), 2)
        except Exception:
            pass
    data["vix_term"] = vix_data

    # Credit Spreads (FRED CSV)
    try:
        r = requests.get(
            "https://fred.stlouisfed.org/graph/fredgraph.csv?id=BAMLH0A0HYM2",
            timeout=10
        )
        if r.status_code == 200:
            lines = r.text.strip().split("\n")
            last_line = lines[-1].split(",")
            data["hy_spread"] = float(last_line[1])
    except Exception:
        data["hy_spread"] = None

    # Calendario económico
    try:
        r = requests.get(
            "https://nfs.faireconomy.media/ff_calendar_thisweek.json",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=8
        )
        if r.status_code == 200:
            events = []
            today  = datetime.now().strftime("%Y-%m-%d")
            for item in r.json():
                if item.get("impact") in ["High", "Medium"] and today in item.get("date", ""):
                    events.append({
                        "time":    item.get("date", "")[-8:-3],
                        "event":   item.get("title", ""),
                        "impact":  item.get("impact", ""),
                        "actual":  item.get("actual", ""),
                        "forecast":item.get("forecast", ""),
                        "previous":item.get("previous", ""),
                    })
            data["calendar"] = events[:10]
    except Exception:
        data["calendar"] = []

    data["date"] = datetime.now().strftime("%Y-%m-%d")
    data["time"] = datetime.now().strftime("%H:%M UTC")

    return data

# ── CONSTRUIR PROMPT ──────────────────────────────────────────────────────────

def build_prompt(market_data: dict) -> str:
    d = market_data

    # Formatear índices
    def fmt(name):
        v = d.get(name, {})
        if not v or v.get("price") is None:
            return "Dato no disponible"
        chg = v.get("chg_pct", 0) or 0
        arrow = "▲" if chg >= 0 else "▼"
        return f"{v['price']:,.2f} ({arrow}{abs(chg):.2f}%)"

    # Formatear pares de divisas (más decimales que índices — 1.0856 no 1.09)
    def fmt_fx(name):
        v = d.get(name, {})
        if not v or v.get("price") is None:
            return "Dato no disponible"
        chg = v.get("chg_pct", 0) or 0
        arrow = "▲" if chg >= 0 else "▼"
        return f"{v['price']:,.4f} ({arrow}{abs(chg):.2f}%)"

    # Sectores
    sector_lines = ""
    for etf, sv in d.get("sectors", {}).items():
        chg1 = sv.get("chg_1d", 0) or 0
        chg5 = sv.get("chg_5d", 0) or 0
        sector_lines += f"| {etf} | {sv['name']} | {chg1:+.2f}% | {chg5:+.2f}% |\n"

    # Futuros (gap pre-market real, no inventado)
    es = d.get("ES", {})
    nq = d.get("NQ", {})
    futures_str = "Dato no disponible"
    if es.get("price") is not None and nq.get("price") is not None:
        futures_str = f"ES (S&P): {fmt('ES')} | NQ (Nasdaq): {fmt('NQ')}"

    # Niveles técnicos reales (SMA20/50/200, rango 20d) — calculados, no inventados
    def fmt_tech(name):
        tl = d.get("tech_levels", {}).get(name)
        if not tl:
            return "Dato no disponible"
        sma200_str = f"{tl['sma200']:,.2f}" if tl.get('sma200') else "N/D (histórico insuficiente)"
        vs200_str  = f" ({tl['vs_sma200_pct']:+.2f}% vs SMA200)" if tl.get('vs_sma200_pct') is not None else ""
        return (f"Último: {tl['last']:,.2f}{vs200_str} | SMA20: {tl['sma20']:,.2f} | "
                f"SMA50: {tl['sma50']:,.2f} | SMA200: {sma200_str} | "
                f"Rango 20d: {tl['low_20d']:,.2f} – {tl['high_20d']:,.2f}")

    spx_tech_str = fmt_tech("SPX")
    ndx_tech_str = fmt_tech("NDX")

    # Proxy de Fed Funds (aproximado, NO es CME FedWatch — ver nota en el propio dato)
    ffp = d.get("fed_funds_proxy")
    if ffp:
        fed_proxy_str = (
            f"Fed Funds actual: {ffp['fed_funds_now']:.2f}% | Yield 3M: {ffp['yield_3m']:.2f}% | "
            f"Gap implícito: {ffp['implied_gap_pct']:+.2f}pp → el mercado de bonos a corto plazo "
            f"sugiere expectativa de {ffp['interpretation']} en el horizonte de 3 meses "
            f"(PROXY APROXIMADO basado en yields, no es la probabilidad exacta de CME FedWatch)"
        )
    else:
        fed_proxy_str = "Dato no disponible"

    # Proxy de divergencia de bancos centrales globales (vía pares de divisas, no hay
    # acceso gratuito a decisiones/probabilidades de BCE o BoJ específicamente)
    eurusd_str = fmt_fx('EURUSD') if d.get('EURUSD', {}).get('price') is not None else "Dato no disponible"
    usdjpy_str = fmt_fx('USDJPY') if d.get('USDJPY', {}).get('price') is not None else "Dato no disponible"

    # Calendario
    calendar_lines = ""
    for ev in d.get("calendar", []):
        calendar_lines += f"| {ev['time']} ET | {ev['event']} | {ev.get('forecast','N/D')} | {ev.get('previous','N/D')} | {ev['impact']} |\n"
    if not calendar_lines:
        calendar_lines = "| — | Sin eventos de alto impacto hoy | — | — | — |\n"

    # Fear & Greed
    fg = d.get("fear_greed")
    fg_str = f"{fg['score']}/100 — {fg['rating']} (ayer: {fg['prev']})" if fg else "Dato no disponible"

    # VIX Term Structure
    vix = d.get("vix_term", {})
    vix_spot = vix.get("VIX_SPOT", "N/D")
    vix_3m   = vix.get("VIX_3M", "N/D")
    vix_str  = f"Spot: {vix_spot} | 3M: {vix_3m}"
    if vix_spot and vix_3m and isinstance(vix_spot, float) and isinstance(vix_3m, float):
        structure = "CONTANGO" if vix_3m > vix_spot else "BACKWARDATION"
        vix_str += f" | Estructura: {structure}"

    hy = d.get("hy_spread")
    hy_str = f"{hy:.2f}%" if hy else "Dato no disponible"

    prompt = f"""Eres el Jefe de Estrategia Macro de un hedge fund quant-macro con $2B bajo gestión. 
Tu trabajo es publicar cada mañana (pre-market) un informe de mercado que determine el sesgo direccional del día, 
la asignación sectorial táctica y los niveles de riesgo a vigilar. 
El público objetivo son Portfolio Managers y traders de prop que toman decisiones en los primeros 30 minutos de sesión.

IDIOMA: Español castellano. Traduce los conceptos anglosajones cuando sea posible. Mantén términos técnicos financieros en inglés cuando no tengan traducción natural.

NORMA ANTI-ALUCINACIÓN: No inventes datos. Si no tienes acceso a un dato concreto, indícalo explícitamente como "Dato no disponible o pendiente de verificación". Para cada precio o dato macro, indica la fuente.

DATOS REALES DE MERCADO HOY ({d['date']} — {d['time']}):

ÍNDICES:
- S&P 500: {fmt('SPX')}
- Nasdaq 100: {fmt('NDX')}
- Russell 2000: {fmt('RUT')}
- VIX: {fmt('VIX')}
- Dólar Index (DXY): {fmt('DXY')}
- Yield 10Y: {fmt('TNX')}%
- Yield 30Y: {fmt('TYX')}%
- Oro: {fmt('GOLD')}
- Petróleo WTI: {fmt('WTI')}
- Bitcoin: {fmt('BTC')}

FUTUROS PRE-MARKET (gap real vs cierre anterior):
{futures_str}

NIVELES TÉCNICOS CALCULADOS (medias móviles y rango — NO inventes otros niveles, usa solo estos):
- S&P 500: {spx_tech_str}
- Nasdaq 100: {ndx_tech_str}

POLÍTICA MONETARIA — DATOS DISPONIBLES (usa solo esto, no inventes probabilidades exactas de FedWatch):
- Proxy de expectativas Fed Funds: {fed_proxy_str}
- EUR/USD: {eurusd_str} (proxy indirecto de divergencia BCE vs Fed)
- USD/JPY: {usdjpy_str} (proxy indirecto de divergencia BoJ vs Fed)

SECTORES S&P 500 (1D / 5D):
| ETF | Sector | 1D | 5D |
|-----|--------|----|----|
{sector_lines}

SENTIMIENTO:
- Fear & Greed Index: {fg_str}
- VIX Term Structure: {vix_str}
- High Yield Spread (OAS): {hy_str}

CALENDARIO ECONÓMICO HOY:
| Hora | Evento | Consenso | Previo | Impacto |
|------|--------|----------|--------|---------|
{calendar_lines}

---

Genera el informe completo siguiendo esta estructura:

1. RESUMEN EJECUTIVO (60 SEGUNDOS)
   - 3-4 bullets: sesgo direccional, catalizador principal, riesgo número 1, recomendación de acción
   - Analogía memorable del setup actual

2. ESTADO DE LOS MERCADOS
   - Análisis de los datos proporcionados arriba
   - Gap pre-market real usando los datos de FUTUROS PRE-MARKET proporcionados (no inventes el gap)
   - Divergencias SPX/NDX/RUT
   - VIX confirmando o contradiciendo

3. NARRATIVA DOMINANTE DEL MERCADO
   - ¿Qué historia cuenta el mercado hoy?
   - ¿Nueva narrativa o continuación?

4. POLÍTICA MONETARIA Y LIQUIDEZ
   - Usa el "Proxy de expectativas Fed Funds" proporcionado arriba. Deja explícito que es una aproximación
     basada en yields (3M vs Fed Funds actual), NO la probabilidad exacta de CME FedWatch
   - Usa EUR/USD y USD/JPY proporcionados como lectura indirecta de divergencia de bancos centrales —
     no inventes decisiones o probabilidades específicas de BCE/BoJ que no se te han dado
   - Si quieres comentar el balance de la Fed, indica que ese detalle está disponible en el módulo
     FED & MACRO de la terminal, no lo inventes aquí

5. CALENDARIO ECONÓMICO
   - Análisis de los eventos del día
   - Qué escenario (beat/miss) es bullish/bearish

6. ROTACIÓN SECTORIAL
   - Basado en los datos de sectores proporcionados
   - Líderes y rezagados
   - Factor performance (Growth vs Value, Large vs Small)

7. SENTIMIENTO Y POSICIONAMIENTO
   - Fear & Greed análisis
   - VIX term structure interpretación
   - Credit spreads señal

8. NIVELES TÁCTICOS
   - Usa EXCLUSIVAMENTE los "NIVELES TÉCNICOS CALCULADOS" proporcionados arriba (SMA20/50/200, rango 20d)
   - S&P 500 y Nasdaq 100: interpreta esos niveles reales, no inventes soportes/resistencias adicionales
   - Qué nivel de los proporcionados (SMA20, SMA50, SMA200, máximo o mínimo de 20d) invalidaría la tesis del día

9. TESIS DEL DÍA
   Bull Case (3 puntos)
   Bear Case (3 puntos)
   Escenario más probable con probabilidad asignada

10. SECTORES Y ACTIVOS A VIGILAR
    Tabla con sector, sesgo, catalizador, nivel de entrada/salida

11. CONCLUSIÓN TÁCTICA
    - Sesgo direccional: Alcista / Bajista / Neutral
    - Tamaño de posición recomendado
    - Hedge recomendado
    - Horas clave a vigilar
    - Qué confirmaría / invalidaría la tesis

Termina con: "¿Por qué hoy puede ser un día de movimiento importante?" (3-5 puntos)

FORMATO: Usa tablas Markdown para comparativas. Veredicto en negrita al inicio de cada sección. Tono frío, cuantitativo, sin hype. Límite 2000 palabras."""

    return prompt

# ── LLAMAR A OPENROUTER ───────────────────────────────────────────────────────

def generate_briefing(prompt: str) -> str:
    if not OPENROUTER_KEY:
        raise ValueError("OPENROUTER_API_KEY no configurada")

    r = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization":  f"Bearer {OPENROUTER_KEY}",
            "Content-Type":   "application/json",
            "HTTP-Referer":   "https://rsu-terminal.com",
            "X-Title":        "RSU Terminal Daily Briefing",
        },
        json={
            "model":       MODEL,
            "messages":    [{"role": "user", "content": prompt}],
            "max_tokens":  6000,
            "temperature": 0.2,
        },
        timeout=120,
    )

    if r.status_code != 200:
        raise ValueError(f"OpenRouter error {r.status_code}: {r.text[:200]}")

    return r.json()["choices"][0]["message"]["content"]

# ── GUARDAR EN GIST ───────────────────────────────────────────────────────────

def save_to_gist(content: str, market_data: dict):
    if not GIST_TOKEN:
        raise ValueError("GIST_TOKEN no configurado")

    payload = {
        "text":   content,
        "date":   market_data["date"],
        "time":   market_data["time"],
        "model":  MODEL,
        "source": "OpenRouter + Qwen3 235B",
    }

    r = requests.patch(
        f"https://api.github.com/gists/{GIST_ID}",
        headers={
            "Authorization": f"token {GIST_TOKEN}",
            "Accept":        "application/vnd.github+json",
        },
        json={
            "files": {
                "briefing.json": {
                    "content": json.dumps(payload, ensure_ascii=False, indent=2)
                }
            }
        },
        timeout=30,
    )

    if r.status_code not in (200, 201):
        raise ValueError(f"Gist error {r.status_code}: {r.text[:200]}")

    print(f"✅ Briefing guardado en Gist: {r.json()['html_url']}")

# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    print(f"🕐 Generando briefing — {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}")

    print("📊 Recopilando datos de mercado...")
    market_data = get_market_data()

    print("🤖 Construyendo prompt...")
    prompt = build_prompt(market_data)

    print(f"🧠 Llamando a {MODEL} via OpenRouter...")
    briefing = generate_briefing(prompt)

    print("💾 Guardando en GitHub Gist...")
    save_to_gist(briefing, market_data)

    print("✅ Briefing completado")
    print(f"📝 Palabras generadas: {len(briefing.split())}")

if __name__ == "__main__":
    main()