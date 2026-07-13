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

GROQ_KEY   = os.environ.get("GROQ_API_KEY", "")
GIST_TOKEN = os.environ.get("GIST_TOKEN", "")
GIST_ID    = os.environ.get("GIST_ID", "715ee0c4e571517c11fa65c5c2376c34")
MODEL      = "qwen/qwen3.6-27b"

# Fichero adicional dentro del MISMO Gist (GIST_ID) — no hace falta un Gist
# nuevo, GitHub permite varios ficheros por Gist. Guarda solo un registro
# compacto por día (fecha + sesgo + objetivo), no el texto completo — eso da
# continuidad de varios días sin cargar el prompt con párrafos de días
# pasados. Se poda a los últimos BIAS_HISTORY_DAYS automáticamente, así que
# el tamaño nunca crece sin límite.
BIAS_HISTORY_FILE = "bias_history.json"
BIAS_HISTORY_DAYS = 14

# Mismo Gist que ya publica scanner_universe.py — lectura pública, sin token,
# para traer al briefing las señales de amplitud REALES de RSU (McClellan,
# % S&P sobre SMA50, NH-NL) en vez de que el briefing viva aislado del resto
# de la terminal.
SCANNER_GIST_ID = "cb9d69cbf6ca741b4fd86765a41813a7"
SCANNER_GIST_FILE = "scanner_scan.json"

FINNHUB_KEY = os.environ.get("FINNHUB_API_KEY", "")

# Insider Flow vive en SQLite dentro del backend (insider_history.db), no en
# un Gist — así que solo es alcanzable desde este script si el backend está
# desplegado y accesible por red pública. RSU_BACKEND_URL se deja vacío por
# defecto (el Action de GitHub no tiene forma de llegar a un backend que
# todavía no está en producción); el día que despliegues en Hetzner, basta
# con rellenar este secret en el repo para que el briefing empiece a incluir
# también los clusters de insiders — no hace falta tocar código de nuevo.
RSU_BACKEND_URL = os.environ.get("RSU_BACKEND_URL", "").rstrip("/")

# Tickers de mega/large-cap conocidos — para filtrar el calendario de earnings
# a solo nombres con peso real de mercado, en vez de listar cientos de small
# caps irrelevantes para un briefing macro.
NOTABLE_TICKERS = {
    "AAPL","MSFT","GOOGL","GOOG","AMZN","NVDA","META","TSLA","AVGO","BRK.B",
    "JPM","V","MA","UNH","XOM","LLY","JNJ","PG","HD","COST","ABBV","MRK",
    "CVX","BAC","WMT","KO","PEP","ADBE","CRM","AMD","NFLX","TMO","ORCL",
    "MCD","CSCO","ABT","INTC","QCOM","TXN","DIS","IBM","GE","CAT","BA",
    "MU","AMAT","LRCX","PANW","NOW","UBER","GS","MS","C","WFC","AXP",
    "SPGI","BLK","PLTR","SMCI","ARM","COIN","SNOW","SHOP",
}

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


# ── NOTICIAS REALES DEL DÍA (Finnhub) ─────────────────────────────────────────

def get_market_news(max_items: int = 8) -> list:
    """Titulares reales de mercado — sin esto el LLM no tiene ninguna forma de
    saber qué está pasando hoy en el mundo (cambios de personal en la Fed,
    geopolítica, etc.), por mucho que los números de mercado sean correctos."""
    if not FINNHUB_KEY:
        return []
    try:
        r = requests.get(
            "https://finnhub.io/api/v1/news",
            params={"category": "general", "token": FINNHUB_KEY},
            timeout=10,
        )
        if r.status_code != 200:
            return []
        items = r.json()
        if not isinstance(items, list):
            return []
        cutoff = datetime.now() - timedelta(hours=30)
        out = []
        for it in items:
            ts = it.get("datetime")
            if not ts:
                continue
            dt = datetime.utcfromtimestamp(ts)
            if dt < cutoff:
                continue
            headline = (it.get("headline") or "").strip()
            summary  = (it.get("summary") or "").strip()
            if not headline:
                continue
            out.append({
                "headline": headline[:180],
                "summary":  summary[:220],
                "source":   it.get("source", ""),
                "time":     dt.strftime("%H:%M UTC"),
            })
            if len(out) >= max_items:
                break
        return out
    except Exception as e:
        print(f"⚠️  No se pudieron obtener noticias: {e}")
        return []


# ── TITULARES DE ALTO IMPACTO — MEDIOS INTERNACIONALES (GDELT) ───────────────

def get_major_outlet_headlines(max_items: int = 8) -> list:
    """El feed de Finnhub (get_market_news) está orientado a mercado/empresa
    y puede no recoger bien noticias de alto impacto que son ante todo
    geopolíticas (conflictos, ataques, decisiones políticas mayores) aunque
    tengan consecuencias directas en precios — el caso real que motivó esto:
    un ataque en el Estrecho de Ormuz que mueve el petróleo y añade
    volatilidad al mercado no tiene por qué aparecer en un feed financiero
    estrecho.

    En vez de intentar llamar a las APIs de Reuters/Bloomberg/FT (de pago,
    sin acceso público gratuito), se usa GDELT — proyecto respaldado por
    Google Jigsaw, gratuito, sin necesidad de API key, que monitoriza medios
    de todo el mundo actualizándose cada 15 minutos. Se le pide
    específicamente que traiga titulares recientes de esos dominios
    concretos (Reuters, Bloomberg, WSJ, AP, Financial Times), no una
    búsqueda genérica — así se acerca lo más posible a "qué llevan estos
    medios ahora mismo" sin depender de sus APIs de pago."""
    domains = ["reuters.com", "bloomberg.com", "wsj.com", "apnews.com", "ft.com"]
    query = "(" + " OR ".join(f"domain:{d}" for d in domains) + ")"
    try:
        r = requests.get(
            "https://api.gdeltproject.org/api/v2/doc/doc",
            params={
                "query": query,
                "mode": "artlist",
                "maxrecords": max_items * 2,  # margen, luego se filtra/recorta
                "timespan": "24h",
                "sort": "datedesc",
                "format": "json",
            },
            timeout=15,
            headers={"User-Agent": "RSU-Terminal-Briefing/1.0"},
        )
        if r.status_code != 200:
            return []
        data = r.json()
        articles = data.get("articles", [])
        out = []
        seen_titles = set()
        for a in articles:
            title  = (a.get("title") or "").strip()
            domain = (a.get("domain") or "").strip()
            if not title or title.lower() in seen_titles:
                continue
            seen_titles.add(title.lower())
            seendate = a.get("seendate", "")  # formato YYYYMMDDTHHMMSSZ
            time_str = ""
            try:
                time_str = datetime.strptime(seendate, "%Y%m%dT%H%M%SZ").strftime("%H:%M UTC")
            except Exception:
                pass
            out.append({
                "headline": title[:180],
                "source":   domain,
                "time":     time_str,
            })
            if len(out) >= max_items:
                break
        return out
    except Exception as e:
        print(f"⚠️  No se pudieron obtener titulares de medios internacionales (GDELT): {e}")
        return []


# ── EARNINGS NOTABLES PRÓXIMOS 2 DÍAS (Finnhub) ───────────────────────────────

def get_notable_earnings() -> list:
    """Solo large/mega-cap — un calendario de earnings sin filtrar es una lista
    de cientos de small caps irrelevantes para un briefing macro."""
    if not FINNHUB_KEY:
        return []
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        end   = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")
        r = requests.get(
            "https://finnhub.io/api/v1/calendar/earnings",
            params={"from": today, "to": end, "token": FINNHUB_KEY},
            timeout=10,
        )
        if r.status_code != 200:
            return []
        rows = r.json().get("earningsCalendar", [])
        out = []
        for row in rows:
            ticker = row.get("symbol", "")
            if ticker not in NOTABLE_TICKERS:
                continue
            out.append({
                "ticker": ticker,
                "date":   row.get("date", ""),
                "hour":   row.get("hour", ""),  # bmo=antes de apertura, amc=tras cierre
                "eps_est": row.get("epsEstimate"),
            })
        return out[:6]
    except Exception as e:
        print(f"⚠️  No se pudieron obtener earnings: {e}")
        return []


# ── SEÑALES DE AMPLITUD REALES DE RSU (mismo Gist que el Scanner) ────────────

def get_rsu_breadth_signals() -> dict:
    """Lee directamente el Gist que publica scripts/scanner_universe.py cada
    noche — el mismo dato que alimenta Market Breadth en la terminal — para
    que el briefing hable con las señales propias de RSU (McClellan real,
    % del S&P sobre SMA50, NH-NL) en vez de vivir aislado del resto de la
    herramienta. Lectura pública, sin necesidad de token."""
    try:
        r = requests.get(
            f"https://api.github.com/gists/{SCANNER_GIST_ID}",
            timeout=10,
            headers={"Accept": "application/vnd.github.v3+json"},
        )
        if r.status_code != 200:
            return {}
        content = r.json()["files"][SCANNER_GIST_FILE]["content"]
        gist = json.loads(content)
        stocks = gist.get("stocks", {})
        if not stocks:
            return {}

        flagged = [v for v in stocks.values() if v.get("above_sma50") is not None]
        pct_above_sma50 = round(sum(1 for v in flagged if v["above_sma50"]) / len(flagged) * 100, 1) if flagged else None
        new_highs = sum(1 for v in stocks.values() if v.get("new_high"))
        new_lows  = sum(1 for v in stocks.values() if v.get("new_low"))

        mcclellan = None
        breadth_hist = gist.get("breadth_history", [])
        if len(breadth_hist) >= 40:
            net = [h["advances"] - h["declines"] for h in breadth_hist]
            # EMA simple sin pandas — el script no depende de pandas para esto
            def ema(vals, span):
                k = 2 / (span + 1)
                e = vals[0]
                for v in vals[1:]:
                    e = v * k + e * (1 - k)
                return e
            mcclellan = round(ema(net, 19) - ema(net, 39), 1)

        return {
            "pct_above_sma50": pct_above_sma50,
            "new_highs": new_highs,
            "new_lows": new_lows,
            "nh_nl": new_highs - new_lows,
            "mcclellan": mcclellan,
            "universe_size": gist.get("universe_size"),
        }
    except Exception as e:
        print(f"⚠️  No se pudieron leer las señales de amplitud de RSU: {e}")
        return {}


# ── CLUSTERS DE INSIDERS (solo si el backend ya está desplegado) ─────────────

def get_insider_clusters() -> list:
    """Insider Flow vive en SQLite dentro del backend, no en un Gist — así que
    esto solo funciona si RSU_BACKEND_URL apunta a un backend desplegado y
    accesible por red pública. Mientras la terminal no esté en el servidor,
    devuelve vacío sin romper el resto del briefing."""
    if not RSU_BACKEND_URL:
        return []
    try:
        r = requests.get(f"{RSU_BACKEND_URL}/api/v1/insider/clusters", timeout=10)
        if r.status_code != 200:
            return []
        return r.json().get("clusters", [])[:5]
    except Exception as e:
        print(f"⚠️  No se pudo leer Insider Flow del backend: {e}")
        return []


# ── POSTURA DE AYER (memoria entre días, no un caché de rendimiento) ─────────

def get_yesterday_stance() -> str:
    """Lee el propio Gist de salida ANTES de sobrescribirlo con el briefing de
    hoy. Esto es lo que da continuidad narrativa real ("ayer cerramos las
    coberturas...") — no un caché que acelera respuestas, sino memoria de la
    postura del día anterior para que el briefing de hoy pueda construir
    sobre ella en vez de escribirse en el vacío cada mañana."""
    if not GIST_TOKEN:
        return ""
    try:
        r = requests.get(
            f"https://api.github.com/gists/{GIST_ID}",
            headers={"Authorization": f"token {GIST_TOKEN}", "Accept": "application/vnd.github+json"},
            timeout=10,
        )
        if r.status_code != 200:
            return ""
        content = r.json()["files"].get("briefing.json", {}).get("content", "")
        if not content:
            return ""
        payload = json.loads(content)
        prev_date = payload.get("date", "")
        today     = datetime.now().strftime("%Y-%m-%d")
        if prev_date == today:
            return ""  # ya se generó hoy, no hay "ayer" que aportar
        text = payload.get("text", "")
        # Nos quedamos con un extracto corto (no todo el briefing de ayer) —
        # solo lo suficiente para que el modelo sepa cuál fue su postura.
        return text[:1200]
    except Exception as e:
        print(f"⚠️  No se pudo leer la postura de ayer: {e}")
        return ""


# ── CONSTRUIR PROMPT ──────────────────────────────────────────────────────────

def build_prompt(market_data: dict, news: list, major_headlines: list, earnings: list, breadth: dict,
                  insider_clusters: list, yesterday_stance: str, bias_history: list) -> str:
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

    # Noticias reales del día — sin esto el modelo no tiene ni idea de qué
    # está pasando en el mundo, por muy correctos que sean los números
    news_lines = ""
    for n in news:
        news_lines += f"- [{n['time']}, {n['source']}] {n['headline']}"
        if n.get("summary"):
            news_lines += f" — {n['summary']}"
        news_lines += "\n"
    if not news_lines:
        news_lines = "Sin titulares disponibles hoy — no menciones catalizadores de noticias que no estén aquí.\n"

    # Titulares de alto impacto de medios internacionales (Reuters/Bloomberg/
    # WSJ/AP/FT vía GDELT) — complementa el feed de mercado de arriba con
    # eventos de gran impacto que pueden ser ante todo geopolíticos (conflictos,
    # ataques, decisiones políticas mayores) y no aparecer bien en un feed
    # financiero estrecho, aunque tengan consecuencias directas en precios
    # (petróleo, defensa, refugio como oro/USD, volatilidad general vía VIX).
    major_headlines_lines = ""
    for n in major_headlines:
        major_headlines_lines += f"- [{n['time']}, {n['source']}] {n['headline']}\n"
    if not major_headlines_lines:
        major_headlines_lines = "Sin titulares de medios internacionales disponibles hoy — no inventes eventos geopolíticos que no estén aquí.\n"

    # Earnings notables próximos 1-2 días
    earnings_lines = ""
    hour_label = {"bmo": "antes de apertura", "amc": "tras cierre", "": "hora no especificada"}
    for e in earnings:
        earnings_lines += f"- {e['ticker']}: {e['date']} ({hour_label.get(e['hour'], e['hour'])})"
        if e.get("eps_est") is not None:
            earnings_lines += f" — EPS estimado: {e['eps_est']}"
        earnings_lines += "\n"
    if not earnings_lines:
        earnings_lines = "Sin earnings de peso en las próximas 48h.\n"

    # Señales de amplitud propias de RSU (McClellan real, % sobre SMA50, NH-NL)
    # — calculadas sobre el propio universo de 500 tickers del Scanner, no
    # sobre una fuente externa genérica
    if breadth:
        pct_s = f"{breadth['pct_above_sma50']}%" if breadth.get('pct_above_sma50') is not None else "N/D"
        mc_s  = f"{breadth['mcclellan']:+.1f}" if breadth.get('mcclellan') is not None else "N/D (histórico insuficiente todavía)"
        rsu_breadth_str = (
            f"% S&P 500 sobre SMA50: {pct_s} | Oscilador McClellan RSU (real, sobre vuestro propio universo): {mc_s} | "
            f"New Highs−New Lows: {breadth.get('nh_nl', 'N/D')} "
            f"({breadth.get('new_highs', '?')} nuevos máximos de 52 sem. vs {breadth.get('new_lows', '?')} nuevos mínimos)"
        )
    else:
        rsu_breadth_str = "Dato no disponible (Scanner sin datos frescos)"

    # Clusters de insiders (solo si el backend está desplegado — ver nota en get_insider_clusters)
    insider_lines = ""
    for c in insider_clusters:
        insider_lines += f"- {c.get('ticker','?')}: {c.get('n_insiders','?')} insiders comprando, ${c.get('total_value',0):,.0f} total, señal {c.get('signal','')}\n"
    if not insider_lines:
        insider_lines = "Sin datos de Insider Flow disponibles en este ciclo.\n"

    # Postura de ayer — memoria entre días para dar continuidad narrativa real
    yesterday_block = (
        f"TU PROPIO BRIEFING DE AYER (para dar continuidad — di explícitamente si mantienes, "
        f"reduces o cambias esta postura, y por qué. Si el mercado te dio la razón o te la quitó, dilo con "
        f"naturalidad — \"ayer funcionó\" o \"me equivoqué con el timing, esto es lo que cambio\" son frases "
        f"legítimas, no debilidad):\n{yesterday_stance}\n"
        if yesterday_stance else
        "No hay briefing de ayer disponible (primera ejecución, o el de ayer no se generó) — escribe sin referencias al día anterior.\n"
    )

    bias_history_str = format_bias_history(bias_history)

    prompt = f"""Eres un trader macro-discrecional escribiendo tu propia nota de mercado de cada mañana, para tu comunidad de trading. No es un informe institucional de un banco — es tu lectura personal, en primera persona, con tu propio posicionamiento incluido ("mi cartera", "he cerrado las coberturas", "mantengo el objetivo de..."). El tono es directo, seguro, con opiniones claras — no un informe neutro que evita mojarse.

IDIOMA: Español castellano, natural. Nada de emojis. Nada de listas interminables — prosa conectada, con algún bullet solo donde de verdad ayude a la lectura rápida.

VARIEDAD: Esto se publica todos los días. No repitas la misma fórmula de apertura ni las mismas frases hechas cada vez — varía cómo empiezas y cómo conectas las ideas, como lo haría una persona real escribiendo día tras día, no una plantilla rellenada.

PROHIBIDO SONAR A TEXTO GENERADO: Nunca uses coletillas típicas de IA como "es importante destacar que", "cabe mencionar que", "en resumen", "cabe señalar", "es fundamental tener en cuenta", "no debemos olvidar que". Ningún trader real las usa escribiendo rápido por la mañana — si se cuela alguna de estas, reescribe la frase.

CUANTIFICA, NO GENERALICES: Cada afirmación cualitativa debe ir atada a un número concreto de los datos proporcionados abajo. No "el VIX está tranquilo" — "el VIX cotiza en 14,2, por debajo del rango reciente". No "el mercado ha recuperado terreno" — el nivel exacto de dónde a dónde. Tienes los datos, úsalos en vez de quedarte en adjetivos vagos.

NIVEL DE INVALIDACIÓN CONCRETO: La conclusión debe incluir un precio exacto que invalidaría la tesis del día — usa uno de los niveles técnicos reales ya proporcionados (SMA20, SMA50, SMA200 o el rango de 20 días), nunca un nivel inventado. Un análisis serio siempre dice qué número exacto le haría cambiar de opinión, no solo "si el mercado se pone feo".

SIN CIERRE DE ASISTENTE: No termines con nada tipo "espero que esta información te sea útil", "cualquier duda me dices" o similar. El briefing termina con tu conclusión y la etiqueta SESGO, nada más — no es una respuesta de chatbot despidiéndose.

CONVICCIÓN CALIBRADA: Evita tanto las afirmaciones categóricas ("esto va a pasar") como la vaguedad que no compromete a nada ("podría pasar cualquier cosa"). El registro correcto es: "lo más probable es X, y esto se invalida si pasa Y" — una lectura de probabilidades con un punto de invalidación claro, no una predicción ni un texto que no dice nada.

NORMA ANTI-ALUCINACIÓN: No inventes datos, precios, ni titulares que no estén en los bloques de abajo. Si falta un dato, dilo o simplemente no lo menciones — no rellenes el hueco con algo inventado. No inventes noticias que no estén en la lista de titulares proporcionada. De los titulares recibidos, ignora cualquiera que no tenga impacto financiero/económico/geopolítico real — un feed de noticias generalista trae de todo, tu criterio es filtrar lo irrelevante, no mencionarlo por completar espacio.

LONGITUD: 500-700 palabras. Esto no es un informe de 2000 palabras con 11 secciones — es una nota que se lee en 3-4 minutos.

{yesterday_block}

TU SESGO DE LOS ÚLTIMOS DÍAS (para dar contexto de tendencia, p.ej. "llevamos N sesiones en el mismo sesgo" si aplica — no lo fuerces si no aporta nada hoy):
{bias_history_str}

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

SEÑALES PROPIAS DE RSU (amplitud calculada sobre vuestro propio universo de 500 tickers — dales protagonismo, es lo que os diferencia de cualquier newsletter macro genérica):
{rsu_breadth_str}

INSIDER FLOW — CLUSTERS DE COMPRA RECIENTES:
{insider_lines}

CALENDARIO ECONÓMICO HOY:
| Hora | Evento | Consenso | Previo | Impacto |
|------|--------|----------|--------|---------|
{calendar_lines}

EARNINGS NOTABLES PRÓXIMAS 48H:
{earnings_lines}

TITULARES REALES DE MERCADO (últimas ~24-30h — usa 2-3 de los más relevantes para el mercado, no los enumeres todos, teje solo los que de verdad importan para el sesgo de hoy):
{news_lines}

TITULARES DE ALTO IMPACTO — MEDIOS INTERNACIONALES (Reuters/Bloomberg/WSJ/AP/FT, últimas 24h): estos pueden ser noticias GEOPOLÍTICAS o de otro tipo (conflictos, ataques, decisiones políticas mayores) que no son "económicas" en sentido estricto pero SÍ mueven mercado (petróleo, defensa, refugio, volatilidad general). Si hay algo aquí con impacto real de mercado hoy — aunque no sea una noticia financiera clásica — mencionalo explícitamente y conecta por qué le importa a un trader (qué activo concreto mueve, por qué):
{major_headlines_lines}

---

Escribe la nota de hoy. Estructura sugerida (adapta libremente, esto no es una plantilla rígida de secciones obligatorias):

- Un título con la fecha.
- Cómo está el mercado ahora mismo y cuál es tu lectura de la situación — en primera persona, con tu propio posicionamiento si aplica (¿mantienes, reduces o cambias la postura de ayer?).
- Los 1-2 catalizadores reales del día (de los titulares y earnings proporcionados) que de verdad mueven la aguja hoy — no un resumen de todos los titulares, solo los que importan.
- Objetivo técnico y zona de seguridad — usa los niveles técnicos reales proporcionados (SMA20/50/200, rango 20d), no inventes soportes/resistencias adicionales.
- Un repaso corto del panorama macro (tipos, VIX, amplitud propia de RSU, spreads) — solo lo que aporte a la tesis del día, no una lista exhaustiva de todos los datos.
- Qué vigilar — riesgos concretos, no genéricos ("cuidado con la volatilidad" no vale; di qué exactamente y por qué).
- Cierra con tu recomendación clara para hoy.

FORMATO: Prosa en primera persona, con algún encabezado en negrita para las 2-3 secciones principales si ayuda a la lectura, no una tabla por sección. Sin emojis. Tono de trader real hablando a su comunidad, no de banco de inversión.

ÚLTIMA LÍNEA OBLIGATORIA: Termina el briefing con una línea aparte, exactamente en este formato (sin nada más en esa línea, sin negrita, sin explicación adicional):
SESGO: ALCISTA
(o BAJISTA, o NEUTRAL — el que corresponda a tu conclusión de hoy). Esta línea se procesa automáticamente, tiene que estar en ese formato exacto o se pierde el registro de sesgo del día."""

    return prompt

# ── LLAMAR A GROQ ─────────────────────────────────────────────────────────────

def generate_briefing(prompt: str) -> str:
    if not GROQ_KEY:
        raise ValueError("GROQ_API_KEY no configurada")

    r = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {GROQ_KEY}",
            "Content-Type":  "application/json",
        },
        json={
            "model":            MODEL,
            "messages":         [{"role": "user", "content": prompt}],
            "max_tokens":       2500,
            "temperature":      0.45,
            # Qwen3.6-27B es un modelo "razonador" — antes de la respuesta
            # final genera un bloque de pensamiento interno que casi siempre
            # sale en inglés, aunque el idioma pedido en el prompt sea
            # español (comportamiento habitual en modelos de este tipo, no
            # un fallo del prompt). Sin este parámetro, ese razonamiento se
            # devolvía mezclado dentro del propio texto de la respuesta —
            # "hidden" hace que Groq solo devuelva la respuesta final limpia,
            # sin tocar la calidad del razonamiento en sí (sigue pensando
            # igual por dentro, solo no se cuela en el texto final).
            "reasoning_format": "hidden",
        },
        timeout=120,
    )

    if r.status_code != 200:
        raise ValueError(f"Groq error {r.status_code}: {r.text[:200]}")

    return r.json()["choices"][0]["message"]["content"]


def extract_bias_tag(text: str) -> tuple:
    """Separa la etiqueta final 'SESGO: ALCISTA/BAJISTA/NEUTRAL' del cuerpo
    del briefing. Devuelve (texto_sin_etiqueta, sesgo). Se pide al modelo en
    un formato fijo en vez de intentar adivinar el sesgo con regex sobre
    texto libre — mucho más fiable para alimentar el registro de sesgo."""
    import re
    match = re.search(r'\n*SESGO:\s*(ALCISTA|BAJISTA|NEUTRAL)\s*$', text.strip(), re.IGNORECASE)
    if not match:
        return text.strip(), None
    bias = match.group(1).upper()
    clean_text = text[:match.start()].strip()
    return clean_text, bias

# ── REGISTRO DE SESGO (memoria ligera de varios días) ─────────────────────────

def get_bias_history() -> list:
    """Lee el registro compacto de sesgo de los últimos días — fecha + sesgo,
    nada de texto completo. Vive en un fichero aparte dentro del mismo Gist."""
    if not GIST_TOKEN:
        return []
    try:
        r = requests.get(
            f"https://api.github.com/gists/{GIST_ID}",
            headers={"Authorization": f"token {GIST_TOKEN}", "Accept": "application/vnd.github+json"},
            timeout=10,
        )
        if r.status_code != 200:
            return []
        content = r.json()["files"].get(BIAS_HISTORY_FILE, {}).get("content", "")
        if not content:
            return []
        history = json.loads(content)
        return history if isinstance(history, list) else []
    except Exception as e:
        print(f"⚠️  No se pudo leer el registro de sesgo: {e}")
        return []


def _append_bias(history: list, date: str, bias: str) -> list:
    """Añade la entrada de hoy y poda a los últimos BIAS_HISTORY_DAYS — así
    el fichero nunca crece sin límite, siempre son como mucho ~14 líneas."""
    history = [h for h in history if h.get("date") != date]  # evita duplicado si se re-ejecuta el mismo día
    history.append({"date": date, "bias": bias})
    history.sort(key=lambda h: h["date"])
    return history[-BIAS_HISTORY_DAYS:]


def format_bias_history(history: list) -> str:
    if not history:
        return "Sin registro de días anteriores todavía (primera ejecución de esta función)."
    return " | ".join(f"{h['date']}: {h['bias']}" for h in history)

# ── GUARDAR EN GIST ───────────────────────────────────────────────────────────

def save_to_gist(content: str, market_data: dict, bias: str, bias_history: list):
    if not GIST_TOKEN:
        raise ValueError("GIST_TOKEN no configurado")

    payload = {
        "text":   content,
        "date":   market_data["date"],
        "time":   market_data["time"],
        "model":  MODEL,
        "source": "Groq + Qwen3.6 27B",
        "bias":   bias,
    }

    updated_history = _append_bias(bias_history, market_data["date"], bias or "N/D")

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
                },
                BIAS_HISTORY_FILE: {
                    "content": json.dumps(updated_history, ensure_ascii=False, indent=2)
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

    print("📰 Leyendo tu postura de ayer (para continuidad narrativa)...")
    yesterday_stance = get_yesterday_stance()

    print("📊 Leyendo registro de sesgo de los últimos días...")
    bias_history = get_bias_history()

    print("📊 Recopilando datos de mercado...")
    market_data = get_market_data()

    print("📰 Recopilando titulares reales del día...")
    news = get_market_news()

    print("🌍 Recopilando titulares de alto impacto (Reuters/Bloomberg/WSJ/AP/FT vía GDELT)...")
    major_headlines = get_major_outlet_headlines()

    print("📅 Recopilando earnings notables (próximas 48h)...")
    earnings = get_notable_earnings()

    print("📈 Leyendo señales de amplitud propias de RSU (Scanner Gist)...")
    breadth = get_rsu_breadth_signals()

    print("🔍 Leyendo clusters de Insider Flow (si el backend está desplegado)...")
    insider_clusters = get_insider_clusters()

    print("🤖 Construyendo prompt...")
    prompt = build_prompt(market_data, news, major_headlines, earnings, breadth, insider_clusters, yesterday_stance, bias_history)

    print(f"🧠 Llamando a {MODEL} via Groq...")
    raw_briefing = generate_briefing(prompt)
    briefing, bias = extract_bias_tag(raw_briefing)
    print(f"📌 Sesgo detectado hoy: {bias or 'N/D (el modelo no incluyó la etiqueta)'}")

    print("💾 Guardando en GitHub Gist...")
    save_to_gist(briefing, market_data, bias, bias_history)

    print("✅ Briefing completado")
    print(f"📝 Palabras generadas: {len(briefing.split())}")

if __name__ == "__main__":
    main()