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
MODEL          = "qwen/qwen-2.5-72b-instruct"

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

    # Sectores
    sector_lines = ""
    for etf, sv in d.get("sectors", {}).items():
        chg1 = sv.get("chg_1d", 0) or 0
        chg5 = sv.get("chg_5d", 0) or 0
        sector_lines += f"| {etf} | {sv['name']} | {chg1:+.2f}% | {chg5:+.2f}% |\n"

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
   - Gap up/gap down en futuros
   - Divergencias SPX/NDX/RUT
   - VIX confirmando o contradiciendo

3. NARRATIVA DOMINANTE DEL MERCADO
   - ¿Qué historia cuenta el mercado hoy?
   - ¿Nueva narrativa o continuación?

4. POLÍTICA MONETARIA Y LIQUIDEZ
   - Fed Funds probabilidades (indicar si dato no disponible)
   - Balance sheet tendencia
   - Divergencias de bancos centrales globales

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
   - S&P 500: soporte, resistencia, nivel clave
   - Nasdaq 100: soporte, resistencia, nivel clave
   - Qué nivel invalida la tesis del día

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
            "max_tokens":  3000,
            "temperature": 0.3,
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
        "source": "OpenRouter + Qwen 2.5 72B",
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