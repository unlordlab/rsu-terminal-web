import yfinance as yf
import requests
import numpy as np
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from config import settings
from services.turnover_service import get_turnover_comparison, get_absorption_signal

def _safe(val, default=None):
    try:
        if val is None: return default
        v = float(val)
        return v if not np.isnan(v) and not np.isinf(v) else default
    except Exception:
        return default

def _fmt_value(val):
    if val is None: return "N/A"
    try:
        v = float(val)
        if abs(v) >= 1e12: return f"${v/1e12:.2f}T"
        if abs(v) >= 1e9:  return f"${v/1e9:.2f}B"
        if abs(v) >= 1e6:  return f"${v/1e6:.2f}M"
        return f"${v:,.2f}"
    except Exception:
        return str(val)

def _fmt_pct(val):
    if val is None: return "N/A"
    try: return f"{float(val)*100:.1f}%"
    except Exception: return "N/A"

def _get_yfinance(ticker: str) -> dict:
    try:
        stock = yf.Ticker(ticker)
        info  = {}
        try: info = stock.info or {}
        except Exception: pass

        # Fallback precio
        cp = (_safe(info.get('currentPrice')) or
              _safe(info.get('regularMarketPrice')) or
              _safe(info.get('regularMarketOpen')))

        if not cp:
            try:
                fi = stock.fast_info
                cp = _safe(getattr(fi, 'last_price', None))
                if cp: info['currentPrice'] = cp
            except Exception: pass

        if not cp:
            try:
                h = stock.history(period="5d")
                if not h.empty:
                    cp = float(h['Close'].iloc[-1])
                    info['currentPrice'] = cp
            except Exception: pass

        if not cp:
            return {"ok": False, "error": f"Sin precio para {ticker}"}

        # Recomendaciones
        recommendations = None
        recommendations_trend = []
        try:
            recs = stock.recommendations
            if recs is not None and not recs.empty:
                latest = recs.iloc[0]
                sb = int(_safe(latest.get('strongBuy')) or 0)
                b  = int(_safe(latest.get('buy')) or 0)
                h  = int(_safe(latest.get('hold')) or 0)
                s  = int(_safe(latest.get('sell')) or 0)
                ss = int(_safe(latest.get('strongSell')) or 0)
                recommendations = {"strong_buy": sb, "buy": b, "hold": h,
                                   "sell": s, "strong_sell": ss, "total": sb+b+h+s+ss}

                # Histórico de periodos (yfinance trae habitualmente 0m, -1m, -2m, -3m)
                PERIOD_LABELS = {"0m": "Actual", "-1m": "Hace 1 mes", "-2m": "Hace 2 meses", "-3m": "Hace 3 meses"}
                for _, row in recs.iterrows():
                    period = str(row.get('period', ''))
                    rsb = int(_safe(row.get('strongBuy')) or 0)
                    rb  = int(_safe(row.get('buy')) or 0)
                    rh  = int(_safe(row.get('hold')) or 0)
                    rs  = int(_safe(row.get('sell')) or 0)
                    rss = int(_safe(row.get('strongSell')) or 0)
                    rtotal = rsb + rb + rh + rs + rss
                    if rtotal == 0:
                        continue
                    buy_pct = round((rsb + rb) / rtotal * 100, 1)
                    recommendations_trend.append({
                        "period":      period,
                        "period_label": PERIOD_LABELS.get(period, period),
                        "buy_pct":     buy_pct,
                        "total":       rtotal,
                    })
        except Exception: pass

        # Precio objetivo
        tm = _safe(info.get('targetMeanPrice'))
        target_data = {
            "mean":   tm,
            "high":   _safe(info.get('targetHighPrice')),
            "low":    _safe(info.get('targetLowPrice')),
            "current": cp,
            "upside": round((tm - cp) / cp * 100, 1) if (tm and cp) else None,
        }

        # n_analysts: el campo numberOfAnalystOpinions de Yahoo a veces no coincide
        # con el recuento real que sí tenemos en `recommendations` (puede estar
        # desfasado a un periodo distinto). Usamos recommendations.total como fuente
        # de verdad cuando está disponible y difiere significativamente.
        _n_analysts_yahoo = _safe(info.get('numberOfAnalystOpinions'))
        _n_analysts_real  = recommendations['total'] if recommendations else None
        if _n_analysts_real is not None and _n_analysts_real > 0:
            n_analysts_final = _n_analysts_real
        else:
            n_analysts_final = _n_analysts_yahoo

        # Fecha del rating individual más reciente (no el agregado, que puede
        # estar desactualizado varias semanas frente al último analista que actuó).
        latest_rating_date = None
        try:
            upgrades = stock.upgrades_downgrades
            if upgrades is not None and not upgrades.empty:
                latest_rating_date = str(upgrades.index.max().date())
        except Exception:
            pass

        # Beta: igual que PEG y dividend yield, puede venir nulo o con valores
        # poco creíbles (beta negativo extremo, o >5, son casi siempre datos rotos
        # más que activos reales con esa volatilidad relativa).
        _beta_raw = _safe(info.get('beta'))
        beta_final = _beta_raw if (_beta_raw is not None and -2 <= _beta_raw <= 5) else None

        # Métricas
        _fpe = _safe(info.get('forwardPE'))
        _tpe = _safe(info.get('trailingPE'))
        _eg  = _safe(info.get('earningsGrowth'))

        # PEG manual: P/E (forward si existe, si no trailing) ÷ crecimiento earnings (%)
        # El campo pegRatio de Yahoo viene roto/desfasado con mucha frecuencia.
        _peg_calc = None
        _pe_for_peg = _fpe if (_fpe and _fpe > 0) else _tpe
        if _pe_for_peg and _eg and _eg > 0:
            _peg_calc = _pe_for_peg / (_eg * 100)

        # Sanity check: si el cálculo manual falla o sale fuera de rango razonable,
        # caemos al dato de Yahoo solo si éste también pasa el filtro; si no, N/A.
        def _peg_sane(v):
            return v is not None and 0 < v <= 15

        peg_final = _peg_calc if _peg_sane(_peg_calc) else None
        if peg_final is None:
            _peg_yahoo = _safe(info.get('pegRatio'))
            if _peg_sane(_peg_yahoo):
                peg_final = _peg_yahoo

        metrics = {
            "trailing_pe":    _tpe,
            "forward_pe":     _fpe,
            "price_to_sales": _safe(info.get('priceToSalesTrailing12Months')),
            "ev_ebitda":      _safe(info.get('enterpriseToEbitda')),
            "peg_ratio":      peg_final,
            "price_to_book":  _safe(info.get('priceToBook')),
        }

        _mktcap   = _safe(info.get('marketCap'))
        _fcf      = _safe(info.get('freeCashflow'))
        _eps_ttm  = _safe(info.get('trailingEps'))
        _div_rate_pf = _safe(info.get('dividendRate'))

        # FCF Yield: FCF / Market Cap. Más fiable que el P/E en empresas con
        # beneficios contables distorsionados (amortizaciones, partidas no-cash, etc.)
        fcf_yield = round(_fcf / _mktcap * 100, 2) if (_fcf and _mktcap) else None

        # Dividend Payout Ratio: dividendo anual / EPS. >80-100% es señal de alerta
        # de sostenibilidad, especialmente relevante cruzado con el yield ya corregido.
        payout_ratio = None
        if _div_rate_pf and _eps_ttm and _eps_ttm > 0:
            payout_ratio = round(_div_rate_pf / _eps_ttm * 100, 1)

        profitability = {
            "roe":             _safe(info.get('returnOnEquity')),
            "roa":             _safe(info.get('returnOnAssets')),
            "net_margin":      _safe(info.get('profitMargins')),
            "op_margin":       _safe(info.get('operatingMargins')),
            "gross_margin":    _safe(info.get('grossMargins')),
            "revenue_growth":  _safe(info.get('revenueGrowth')),
            "earnings_growth": _safe(info.get('earningsGrowth')),
            "debt_to_equity":  _safe(info.get('debtToEquity')),
            "free_cashflow":   _fcf,
            "fcf_yield":       fcf_yield,
            "current_ratio":   _safe(info.get('currentRatio')),
            "payout_ratio":    payout_ratio,
        }

        # Sparkline
        sparkline = []
        try:
            hist = stock.history(period="3mo", interval="1d")
            if not hist.empty:
                sparkline = [round(float(x), 2) for x in hist['Close'].dropna().tolist()]
        except Exception: pass

        prev_close = _safe(info.get('previousClose')) or _safe(info.get('regularMarketPreviousClose'))
        chg_pct    = round((cp - prev_close) / prev_close * 100, 2) if prev_close else 0

        # Dividend Yield: el campo dividendYield de Yahoo cambia de formato entre
        # versiones de yfinance — a veces fracción (0.0168) y a veces ya porcentaje
        # (1.68), sin aviso. En vez de confiar en ese formato ambiguo, lo calculamos
        # de forma fiable como dividendRate (importe $ anual, siempre consistente) / precio.
        _div_rate = _safe(info.get('dividendRate'))
        if _div_rate and cp:
            dividend_yield_pct = round(_div_rate / cp * 100, 2)
        else:
            _raw_dy = _safe(info.get('dividendYield'))
            if _raw_dy is None:
                dividend_yield_pct = None
            elif _raw_dy > 1:
                # Ya viene como porcentaje (ej. 1.68 = 1.68%), no multiplicar.
                dividend_yield_pct = round(_raw_dy, 2)
            else:
                # Viene como fracción (ej. 0.0168 = 1.68%).
                dividend_yield_pct = round(_raw_dy * 100, 2)
            # Sanity check: ningún yield real de mercado supera ~30%. Si lo supera,
            # el dato de origen es inservible — mejor N/A que un número que despista.
            if dividend_yield_pct is not None and dividend_yield_pct > 30:
                dividend_yield_pct = None

        return {
            "ok": True,
            "ticker":   ticker.upper(),
            "name":     info.get('shortName') or info.get('longName') or ticker.upper(),
            "sector":   info.get('sector', 'N/A'),
            "industry": info.get('industry', 'N/A'),
            "country":  info.get('country', 'N/A'),
            "currency": info.get('currency', 'USD'),
            "website":  info.get('website', ''),
            "description": info.get('longBusinessSummary', ''),
            "price":       round(cp, 2),
            "prev_close":  round(prev_close, 2) if prev_close else None,
            "chg_pct":     chg_pct,
            "mktcap":      _safe(info.get('marketCap')),
            "mktcap_fmt":  _fmt_value(_safe(info.get('marketCap'))),
            "week52_high": _safe(info.get('fiftyTwoWeekHigh')),
            "week52_low":  _safe(info.get('fiftyTwoWeekLow')),
            "avg_volume":  _safe(info.get('averageVolume')),
            "beta":        beta_final,
            "dividend_yield": (dividend_yield_pct / 100) if dividend_yield_pct is not None else None,
            "dividend_rate":  _div_rate,
            "n_analysts":  n_analysts_final,
            "latest_rating_date": latest_rating_date,
            "recommendations": recommendations,
            "recommendations_trend": recommendations_trend,
            "target_data":    target_data,
            "metrics":        metrics,
            "profitability":  profitability,
            "sparkline":      sparkline,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}

# Fuentes de baja sustancia que aparecen a menudo en el agregador de
# Yahoo -- clips de vídeo sin transcripción útil, o contenido tipo SEO/
# comentario automatizado. No se bloquean del todo si no hay nada mejor
# (mejor algo que nada), pero se apartan al final de la lista para que
# prioricen fuentes con más peso periodístico real.
_LOW_QUALITY_NEWS_SOURCES = {
    "yahoo finance video", "trefis", "simply wall st", "24/7 wall st.",
    "24/7 wall st", "insider monkey", "motley fool", "zacks",
    "benzinga",  # a veces es agregación automática, a veces no -- ambiguo, se aparta por precaución
}


def _get_yfinance_news_fallback(ticker: str) -> list:
    """Respaldo cuando Finnhub no da noticias (sin clave, cuota agotada, o
    simplemente sin cobertura esa semana) -- yfinance ya es una dependencia
    que se usa en toda la terminal, así que no hace falta ninguna clave
    nueva. El formato de .news ha cambiado entre versiones de yfinance
    (a veces plano, a veces anidado bajo 'content'), así que se comprueban
    ambas formas defensivamente. Ver conversación 18/07/2026."""
    try:
        stock = yf.Ticker(ticker)
        raw_items = stock.news or []
        news = []
        for item in raw_items[:10]:
            # yfinance >= 0.2.4x suele anidar los campos bajo 'content'
            content = item.get("content", item)
            headline = content.get("title") or item.get("title") or item.get("headline") or ""
            if not headline:
                continue
            url = (
                (content.get("clickThroughUrl") or {}).get("url")
                or (content.get("canonicalUrl") or {}).get("url")
                or item.get("link") or item.get("url") or ""
            )
            source = (content.get("provider") or {}).get("displayName") or item.get("publisher") or "Yahoo Finance"
            ts = content.get("pubDate") or item.get("providerPublishTime") or 0
            date_str = ""
            try:
                if isinstance(ts, str):
                    date_str = ts[:16].replace("T", " ")
                elif ts:
                    date_str = datetime.fromtimestamp(ts).strftime('%d/%m/%Y %H:%M')
            except Exception:
                pass
            news.append({"headline": headline, "source": source, "url": url, "datetime": 0, "date": date_str})
        # Prioriza fuentes con más peso periodístico -- las de baja calidad
        # no se descartan (mejor algo que nada), solo se van al final.
        news.sort(key=lambda n: n["source"].strip().lower() in _LOW_QUALITY_NEWS_SOURCES)
        return news
    except Exception as e:
        print(f"[Research:{ticker}] Fallback de noticias de yfinance falló: {type(e).__name__}: {e}")
        return []


def _get_finnhub(ticker: str) -> dict:
    key = settings.finnhub_api_key
    news, sentiment = [], {}

    if key:
        try:
            session = requests.Session()
            session.headers.update({"X-Finnhub-Token": key})

            try:
                from datetime import timedelta
                today = datetime.now().strftime('%Y-%m-%d')
                # Ventana ampliada de 7 a 30 días -- 7 días dejaba la sección
                # vacía para cualquier ticker sin cobertura mediática esa
                # semana concreta, aunque sí hubiera noticias recientes de
                # verdad. Ver conversación 18/07/2026.
                month_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
                r = session.get(
                    "https://finnhub.io/api/v1/company-news",
                    params={"symbol": ticker, "from": month_ago, "to": today},
                    timeout=8
                )
                if r.status_code == 200:
                    items = r.json()[:10]
                    for n in items:
                        ts = n.get('datetime', 0)
                        try:
                            date_str = datetime.fromtimestamp(ts).strftime('%d/%m/%Y %H:%M') if ts else ''
                        except Exception:
                            date_str = ''
                        news.append({
                            "headline": n.get('headline', ''),
                            "source":   n.get('source', ''),
                            "url":      n.get('url', ''),
                            "datetime": ts,
                            "date":     date_str,
                        })
                elif r.status_code == 429:
                    print(f"[Research:{ticker}] Finnhub sin cuota (429) — usando respaldo de yfinance")
            except Exception:
                pass

            try:
                r = session.get("https://finnhub.io/api/v1/news-sentiment",
                                params={"symbol": ticker}, timeout=8)
                if r.status_code == 200:
                    d = r.json()
                    sentiment = {
                        "score":    _safe(d.get('companyNewsScore')),
                        "bullish":  _safe(d.get('sentiment', {}).get('bullishPercent')),
                        "bearish":  _safe(d.get('sentiment', {}).get('bearishPercent')),
                    }
            except Exception:
                pass
        except Exception:
            pass
    else:
        print(f"[Research:{ticker}] finnhub_api_key no configurado — usando respaldo de yfinance para noticias")

    # Respaldo: si Finnhub no dio ninguna noticia (sin clave, cuota agotada,
    # o sin cobertura esa ventana), se intenta con yfinance antes de dejar
    # la sección vacía del todo.
    if not news:
        news = _get_yfinance_news_fallback(ticker)

    return {"news": news, "sentiment": sentiment}

def _get_finnhub_analyst_changes(ticker: str) -> list:
    """Antes se llamaba _get_fmp_analyst_changes — nombre engañoso, esto nunca
    ha llamado a FMP, es 100% Finnhub. Renombrado para que quede claro."""
    try:
        key = settings.finnhub_api_key
        if not key:
            print(f"[Research] finnhub_api_key no configurado — sin cambios de analistas para {ticker}")
            return []
        r = requests.get(
            f"https://finnhub.io/api/v1/stock/recommendation?symbol={ticker}&token={key}",
            timeout=8
        )
        if r.status_code != 200:
            print(f"[Research] Finnhub recommendation ({ticker}): status HTTP {r.status_code} — {r.text[:150]}")
            return []
        data = r.json()
        if not isinstance(data, list) or not data:
            print(f"[Research] Finnhub recommendation ({ticker}): respuesta vacía o inesperada — {str(data)[:150]}")
            return []

        # Finnhub devuelve recomendaciones mensuales — convertimos a cambios
        results = []
        for i, item in enumerate(data[:6]):
            period = item.get('period', '')[:10]
            buy    = int(item.get('buy', 0) or 0)
            hold   = int(item.get('hold', 0) or 0)
            sell   = int(item.get('sell', 0) or 0)
            sb     = int(item.get('strongBuy', 0) or 0)
            ss     = int(item.get('strongSell', 0) or 0)
            total  = buy + hold + sell + sb + ss
            if total == 0: continue
            buy_pct  = round((buy + sb) / total * 100)
            if buy_pct >= 70:
                action = 'ALCISTA'
                action_color = '#00ffad'
            elif buy_pct >= 50:
                action = 'NEUTRAL'
                action_color = '#ffb800'
            else:
                action = 'BAJISTA'
                action_color = '#f23645'
            results.append({
                "date":         period,
                "firm":         f"{buy+sb} compra · {hold} neutral · {sell+ss} venta",
                "action":       action,
                "action_color": action_color,
                "from_grade":   f"{buy_pct}% alcistas",
                "to_grade":     f"{total} analistas",
            })
        print(f"[Research] Finnhub recommendation ({ticker}): {len(results)} periodos recibidos")
        return results
    except Exception as e:
        print(f"[Research] Finnhub recommendation ({ticker}): error inesperado ({type(e).__name__}: {e})")
        return []

def _get_analyst_ratings_history(ticker: str) -> dict:
    """
    Histórico real de cambios de rating por firma de analistas (upgrades/downgrades),
    vía yfinance — gratuito, sin API key, sin riesgo de scraping de terceros (a
    diferencia de librerías tipo finviz/finvizfinance que sí hacen scraping no oficial).
    Distinto de _get_finnhub_analyst_changes(), que es una agregación mensual de
    sentimiento (compra/mantener/venta), no cambios de grado por firma real.
    """
    try:
        stock = yf.Ticker(ticker)
        ud = stock.upgrades_downgrades
        if ud is None or ud.empty:
            return {"ok": False, "history": []}

        ud = ud.sort_index(ascending=False).head(20)
        history = []
        for date, row in ud.iterrows():
            from_grade = str(row.get('FromGrade', '') or '')
            to_grade   = str(row.get('ToGrade', '') or '')
            action     = str(row.get('Action', '') or '').lower()
            cur_pt     = row.get('currentPriceTarget')
            prior_pt   = row.get('priorPriceTarget')

            # Clasificar visualmente la acción
            if action == 'up':
                action_label, action_color = 'UPGRADE', '#00ffad'
            elif action == 'down':
                action_label, action_color = 'DOWNGRADE', '#f23645'
            elif action == 'main':
                action_label, action_color = 'MANTIENE', '#888'
            elif action == 'init':
                action_label, action_color = 'INICIA COBERTURA', '#00d9ff'
            elif action == 'reit':
                action_label, action_color = 'REITERA', '#888'
            else:
                action_label, action_color = action.upper() or 'N/D', '#888'

            # Precio objetivo: mostrar solo si disponible
            try:
                cur_pt_fmt   = f"${float(cur_pt):.0f}" if cur_pt and not __import__('math').isnan(float(cur_pt)) else None
                prior_pt_fmt = f"${float(prior_pt):.0f}" if prior_pt and not __import__('math').isnan(float(prior_pt)) else None
            except Exception:
                cur_pt_fmt = prior_pt_fmt = None

            history.append({
                "date":            date.strftime('%Y-%m-%d'),
                "firm":            str(row.get('Firm', 'N/D')),
                "action":          action_label,
                "action_color":    action_color,
                "from_grade":      _translate_grade(from_grade) if from_grade else '—',
                "to_grade":        _translate_grade(to_grade) if to_grade else '—',
                "cur_price_target":  cur_pt_fmt,
                "prior_price_target": prior_pt_fmt,
            })

        return {"ok": True, "history": history}
    except Exception:
        return {"ok": False, "history": []}

# Traducción de grados de analistas (inglés → castellano). Distintas firmas usan
# escalas distintas entre sí; esto traduce el literal devuelto por yfinance,
# preservando el grado original como fallback si no está en el diccionario.
GRADE_TRANSLATIONS = {
    "strong buy":          "Compra Fuerte",
    "buy":                 "Comprar",
    "overweight":          "Sobreponderar",
    "outperform":          "Mejor que el Mercado",
    "market outperform":   "Mejor que el Mercado",
    "sector outperform":   "Mejor que el Sector",
    "positive":            "Positivo",
    "accumulate":          "Acumular",
    "add":                 "Añadir",
    "hold":                "Mantener",
    "neutral":             "Neutral",
    "market perform":      "Rendimiento de Mercado",
    "sector perform":      "Rendimiento del Sector",
    "equal-weight":        "Ponderación Igual",
    "equal weight":        "Ponderación Igual",
    "in-line":             "En Línea",
    "in line":             "En Línea",
    "peer perform":        "Rendimiento Comparable",
    "sector weight":       "Ponderación del Sector",
    "underweight":         "Subponderar",
    "underperform":        "Peor que el Mercado",
    "sector underperform": "Peor que el Sector",
    "reduce":              "Reducir",
    "sell":                "Vender",
    "strong sell":         "Venta Fuerte",
    "negative":            "Negativo",
}

def _translate_grade(grade) -> str:
    if not grade or not isinstance(grade, str): return grade or "—"
    return GRADE_TRANSLATIONS.get(grade.strip().lower(), grade)

def _get_alpha_vantage(ticker: str) -> dict:
    key = settings.alpha_vantage_api_key
    if not key:
        return {}
    try:
        r = requests.get(
            "https://www.alphavantage.co/query",
            params={"function": "EARNINGS", "symbol": ticker, "apikey": key},
            timeout=10
        )
        if r.status_code != 200:
            return {}
        data = r.json()
        quarterly = data.get('quarterlyEarnings', [])[:8]
        earnings  = []
        for q in quarterly:
            earnings.append({
                "date":      q.get('fiscalDateEnding', ''),
                "reported":  _safe(q.get('reportedEPS')),
                "estimated": _safe(q.get('estimatedEPS')),
                "surprise":  _safe(q.get('surprisePercentage')),
            })
        return {"quarterly_earnings": earnings}
    except Exception:
        return {}

def _generate_suggestions(yf_data: dict) -> list:
    suggestions = []
    info        = {}
    metrics     = yf_data.get('metrics', {})
    prof        = yf_data.get('profitability', {})
    recs        = yf_data.get('recommendations')
    target      = yf_data.get('target_data', {})

    pe      = metrics.get('trailing_pe')
    fpe     = metrics.get('forward_pe')
    peg     = metrics.get('peg_ratio')
    upside  = target.get('upside')
    roe     = prof.get('roe')
    nm      = prof.get('net_margin')
    de      = prof.get('debt_to_equity')
    fcf     = prof.get('free_cashflow')
    rg      = prof.get('revenue_growth')
    eg      = prof.get('earnings_growth')

    if pe and fpe and pe > 0 and fpe > 0:
        if fpe < pe * 0.85:
            suggestions.append(f"📈 Forward P/E ({fpe:.1f}x) muy inferior al P/E actual ({pe:.1f}x) — fuerte crecimiento esperado.")
        elif fpe < pe:
            suggestions.append(f"📈 Forward P/E ({fpe:.1f}x) inferior al P/E actual ({pe:.1f}x) — crecimiento esperado.")
        else:
            suggestions.append(f"⚠ Forward P/E ({fpe:.1f}x) superior al actual ({pe:.1f}x) — posible contracción de márgenes.")

    if recs and recs['total'] > 0:
        buy_pct = (recs['strong_buy'] + recs['buy']) / recs['total'] * 100
        n_buy   = recs['strong_buy'] + recs['buy']
        if buy_pct >= 75:
            suggestions.append(f"✅ Fuerte consenso alcista: {n_buy}/{recs['total']} analistas recomiendan comprar ({buy_pct:.0f}%).")
        elif buy_pct >= 50:
            suggestions.append(f"⚖ Consenso mayoritariamente alcista: {buy_pct:.0f}% favorables.")
        else:
            suggestions.append(f"🔴 Consenso débil: solo {buy_pct:.0f}% recomiendan comprar.")

    if upside is not None:
        mean_p = target.get('mean')
        if upside > 25:
            suggestions.append(f"🎯 Alto potencial: +{upside:.1f}% hasta objetivo medio ${mean_p:.2f}.")
        elif upside > 10:
            suggestions.append(f"📊 Potencial moderado: +{upside:.1f}% hasta ${mean_p:.2f}.")
        elif upside < -10:
            suggestions.append(f"⚠ Cotización {abs(upside):.1f}% sobre el objetivo — posible sobrevaloración.")

    if rg is not None:
        if rg > 0.25:   suggestions.append(f"🚀 Crecimiento de ingresos excepcional: +{rg*100:.1f}% interanual.")
        elif rg > 0.10: suggestions.append(f"📈 Crecimiento de ingresos sólido: +{rg*100:.1f}%.")
        elif rg < 0:    suggestions.append(f"📉 Ingresos en contracción: {rg*100:.1f}%.")

    if roe is not None:
        if roe > 0.30:  suggestions.append(f"💎 ROE excepcional ({roe*100:.1f}%) — empresa muy eficiente.")
        elif roe > 0.15: suggestions.append(f"💚 ROE sólido ({roe*100:.1f}%).")
        elif roe < 0:   suggestions.append(f"🔴 ROE negativo ({roe*100:.1f}%) — destruyendo valor.")

    if nm is not None:
        if nm > 0.25:   suggestions.append(f"💰 Margen neto excepcional ({nm*100:.1f}%).")
        elif nm > 0.10: suggestions.append(f"✅ Margen neto sólido ({nm*100:.1f}%).")
        elif nm < 0:    suggestions.append(f"🔴 Margen neto negativo ({nm*100:.1f}%) — empresa en pérdidas.")

    if de is not None:
        if de > 150:    suggestions.append(f"💳 Endeudamiento muy elevado (D/E: {de:.0f}%) — riesgo financiero alto.")
        elif de > 80:   suggestions.append(f"⚠ Endeudamiento moderado-alto (D/E: {de:.0f}%).")
        elif de < 30:   suggestions.append(f"💪 Balance conservador (D/E: {de:.0f}%) — solidez financiera.")

    if fcf is not None:
        if fcf > 0:     suggestions.append(f"💵 Free Cash Flow positivo ({_fmt_value(fcf)}) — genera caja real.")
        else:           suggestions.append(f"⚠ Free Cash Flow negativo ({_fmt_value(fcf)}).")

    if peg and 0 < peg < 1:
        suggestions.append(f"🟢 PEG {peg:.2f} — potencialmente infravalorada respecto a su crecimiento.")
    elif peg and peg > 3:
        suggestions.append(f"🔴 PEG {peg:.2f} — valoración muy exigente respecto al crecimiento.")

    return suggestions or ["ℹ Datos insuficientes para generar sugerencias."]

def _compute_rsu_score(yf_data: dict, piotroski: dict = None, sector_comparison: dict = None,
                        insider_summary: dict = None, technical: dict = None) -> dict:
    """
    RSU Score unificado (0-100), 5 categorías de 20pts cada una.

    Antes existían dos scores independientes (RSU Score y Piotroski) que podían
    contradecirse: RSU Score miraba niveles absolutos de rentabilidad/crecimiento
    + sentimiento de analistas, mientras que Piotroski mira solo la TENDENCIA
    interanual de la salud financiera, sin importar el nivel absoluto. Una empresa
    podía tener márgenes altos (RSU Score alto) mientras su salud financiera se
    deterioraba interanualmente (Piotroski bajo) — ambos scores tenían razón a la
    vez, pero medían cosas distintas sin comunicarse entre sí.

    Esta versión integra Piotroski COMO categoría explícita (20% del total) en
    vez de mantenerlo como score separado, junto con valoración relativa al
    sector, sentimiento de mercado (analistas + insiders) y fase técnica —
    así un único número resume las 5 dimensiones relevantes sin que ninguna
    quede "escondida" generando contradicciones aparentes.
    """
    breakdown = []
    metrics  = yf_data.get('metrics', {})
    prof     = yf_data.get('profitability', {})
    recs     = yf_data.get('recommendations')
    target   = yf_data.get('target_data', {})

    # ── 1. CALIDAD FUNDAMENTAL (20pts) ──────────────────────────────────────
    # Niveles absolutos de crecimiento, ROE y margen neto, promediados.
    sub_pts, sub_max = [], 0
    rg = prof.get('revenue_growth')
    if rg is not None:
        sub_pts.append(20 if rg > 0.25 else 15 if rg > 0.15 else 10 if rg > 0.05 else 0)
        sub_max += 1
    roe = prof.get('roe')
    if roe is not None:
        sub_pts.append(20 if roe > 0.25 else 15 if roe > 0.15 else 10 if roe > 0.08 else 0)
        sub_max += 1
    nm = prof.get('net_margin')
    if nm is not None:
        sub_pts.append(20 if nm > 0.20 else 15 if nm > 0.10 else 10 if nm > 0.02 else 0)
        sub_max += 1
    fund_pts = round(sum(sub_pts) / len(sub_pts)) if sub_pts else None
    if fund_pts is not None:
        parts = []
        if rg is not None: parts.append(f"Crec. {rg*100:.0f}%")
        if roe is not None: parts.append(f"ROE {roe*100:.0f}%")
        if nm is not None: parts.append(f"Margen {nm*100:.0f}%")
        breakdown.append({"label": "Calidad Fundamental", "pts": fund_pts, "max": 20, "val": " · ".join(parts)})

    # ── 2. SALUD FINANCIERA — PIOTROSKI (20pts) ─────────────────────────────
    # Tendencia interanual real (no nivel absoluto). Folded in directamente:
    # ya no es un score aparte que pueda "contradecir" al RSU Score.
    if piotroski and piotroski.get('max'):
        pio_pts = round(piotroski['score'] / piotroski['max'] * 20)
        breakdown.append({"label": "Salud Financiera (Piotroski)", "pts": pio_pts, "max": 20,
                           "val": f"{piotroski['score']}/{piotroski['max']} criterios"})
    else:
        pio_pts = None

    # ── 3. VALORACIÓN RELATIVA AL SECTOR (20pts) ────────────────────────────
    val_keys = ['trailing_pe', 'forward_pe', 'ev_ebitda', 'peg_ratio', 'price_to_book']
    if sector_comparison and sector_comparison.get('ok') and sector_comparison.get('items'):
        items = sector_comparison['items']
        available = [items[k] for k in val_keys if k in items]
        if available:
            fav_count = sum(1 for it in available if it['favorable'])
            val_pts = round(fav_count / len(available) * 20)
            breakdown.append({"label": "Valoración vs Sector", "pts": val_pts, "max": 20,
                               "val": f"{fav_count}/{len(available)} métricas favorables"})
        else:
            val_pts = None
    else:
        # Fallback sin benchmark sectorial: PEG absoluto como proxy de valoración.
        peg = metrics.get('peg_ratio')
        if peg is not None:
            val_pts = 20 if peg < 1 else 15 if peg < 1.5 else 10 if peg < 2.5 else 0
            breakdown.append({"label": "Valoración (PEG)", "pts": val_pts, "max": 20, "val": f"PEG {peg:.2f}"})
        else:
            val_pts = None

    # ── 4. SENTIMIENTO DE MERCADO (20pts) ───────────────────────────────────
    # Consenso de analistas + potencial de precio objetivo, ajustado por
    # sentimiento de insiders (compras/ventas discrecionales reales con su
    # propio dinero, señal históricamente más informativa que las ventas).
    sent_components = []
    if recs and recs['total'] > 0:
        buy_pct = (recs['strong_buy'] + recs['buy']) / recs['total'] * 100
        sent_components.append(20 if buy_pct >= 75 else 15 if buy_pct >= 60 else 10 if buy_pct >= 40 else 0)
    upside = target.get('upside')
    if upside is not None:
        sent_components.append(20 if upside > 25 else 15 if upside > 15 else 10 if upside > 5 else 0)
    if sent_components:
        sent_pts = sum(sent_components) / len(sent_components)
        insider_note = ""
        if insider_summary and insider_summary.get('sentiment'):
            if insider_summary['sentiment'] == 'COMPRADOR':
                sent_pts += 3
                insider_note = " · Insiders comprando"
            elif insider_summary['sentiment'] == 'VENDEDOR':
                sent_pts -= 3
                insider_note = " · Insiders vendiendo"
        sent_pts = round(max(0, min(20, sent_pts)))
        val_str = (f"{buy_pct:.0f}% alcistas" if recs and recs['total'] > 0 else "") \
                   + (f" · {upside:+.0f}% objetivo" if upside is not None else "") + insider_note
        breakdown.append({"label": "Sentimiento de Mercado", "pts": sent_pts, "max": 20, "val": val_str.strip(" ·")})
    else:
        sent_pts = None

    # ── 5. FASE TÉCNICA (20pts) ─────────────────────────────────────────────
    # Usa la fase de mercado (1-4) ya calculada en Niveles Técnicos, para que
    # el componente técnico del score sea coherente con lo que se ve en esa
    # sección — no una lectura técnica distinta e inconexa.
    PHASE_PTS = {2: 20, 1: 13, 3: 7, 4: 0}
    if technical and technical.get('market_phase'):
        tech_pts = PHASE_PTS.get(technical['market_phase'], 10)
        breakdown.append({"label": "Fase Técnica", "pts": tech_pts, "max": 20,
                           "val": technical.get('phase_label', f"Fase {technical['market_phase']}")})
    else:
        tech_pts = None

    # ── TOTAL ────────────────────────────────────────────────────────────────
    # Si falta alguna categoría (datos no disponibles), se reescala sobre las
    # categorías sí disponibles para no penalizar por ausencia de datos.
    available_cats = [p for p in [fund_pts, pio_pts, val_pts, sent_pts, tech_pts] if p is not None]
    score = round(sum(available_cats) / len(available_cats) / 20 * 100) if available_cats else 0
    max_score = 100

    color = "#00ffad" if score >= 70 else "#ffb800" if score >= 50 else "#f23645"
    label = "COMPRA FUERTE" if score >= 80 else "COMPRA" if score >= 65 else "NEUTRAL" if score >= 50 else "PRECAUCIÓN" if score >= 35 else "EVITAR"

    return {"score": score, "max": max_score, "color": color, "label": label, "breakdown": breakdown}

def _translate_description(text: str) -> str:
    if not text: return text
    try:
        import requests as _req
        key = getattr(settings, 'xai_api_key', '') or getattr(settings, 'groq_api_key', '')
        if not key: return text
        
        # Intentar con Groq
        groq_key = getattr(settings, 'groq_api_key', '')
        if groq_key:
            r = _req.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"},
                json={
                    "model": "llama-3.3-70b-versatile",
                    "messages": [
                        {"role": "system", "content": "Traduce el siguiente texto del inglés al español de forma natural y profesional. Devuelve solo la traducción, sin explicaciones."},
                        {"role": "user", "content": text[:1500]}
                    ],
                    "max_tokens": 800,
                    "temperature": 0.3,
                },
                timeout=10
            )
            if r.status_code == 200:
                return r.json()['choices'][0]['message']['content'].strip()
    except Exception:
        pass
    return text

def _classify_insider_tx(code: str, is_buy: bool) -> dict:
    """Clasifica el tipo de transacción insider según el código SEC Form 4."""
    code = (code or '').strip().upper()
    if code == 'P':
        return {"nature": "Compra discrecional en mercado abierto", "scheduled": False,
                "flag": "Señal de confianza", "flag_color": "#00ffad"}
    if code == 'S':
        return {"nature": "Venta discrecional en mercado abierto", "scheduled": False,
                "flag": "Posible cautela", "flag_color": "#f23645"}
    if code == 'A':
        return {"nature": "Adjudicación / concesión (compensación)", "scheduled": True,
                "flag": "Rutinaria", "flag_color": "#888"}
    if code == 'M':
        return {"nature": "Ejercicio de opciones", "scheduled": True,
                "flag": "Rutinaria", "flag_color": "#888"}
    if code == 'F':
        return {"nature": "Liquidación de impuestos (in-kind)", "scheduled": True,
                "flag": "Rutinaria", "flag_color": "#888"}
    if code == 'G':
        return {"nature": "Donación", "scheduled": True,
                "flag": "No discrecional", "flag_color": "#888"}
    if code == 'C':
        return {"nature": "Conversión de valores", "scheduled": True,
                "flag": "Rutinaria", "flag_color": "#888"}
    return {"nature": "Compra" if is_buy else "Venta",
            "scheduled": None, "flag": "Sin clasificar", "flag_color": "#888"}

def _get_insider_trading(ticker: str) -> dict:
    try:
        key = settings.finnhub_api_key
        if not key: return {"transactions": [], "summary": None, "monthly_volume": []}
        r = requests.get(
            f"https://finnhub.io/api/v1/stock/insider-transactions?symbol={ticker}&token={key}",
            timeout=8
        )
        if r.status_code != 200: return {"transactions": [], "summary": None, "monthly_volume": []}
        data = r.json().get('data', [])
        if not isinstance(data, list): return {"transactions": [], "summary": None, "monthly_volume": []}

        from datetime import datetime, timedelta
        cutoff = datetime.now() - timedelta(days=182)
        vol_cutoff = datetime.now() - timedelta(days=365)

        results = []
        buy_count = sell_count = 0
        buy_value = sell_value = 0.0

        # Volumen mensual (acciones) de los últimos 12 meses, para el gráfico
        # de barras Compras vs Ventas. Se construye sobre TODAS las
        # transacciones devueltas por Finnhub (no solo las 10 que se listan
        # en la tabla), agrupando por mes calendario.
        monthly = {}

        for item in data:
            change = _safe(item.get('change', 0)) or 0
            value  = _safe(item.get('transactionPrice', 0)) or 0
            total  = abs(change * value)
            is_buy = change > 0
            cls    = _classify_insider_tx(item.get('transactionCode', ''), is_buy)
            tx_date_str = item.get('transactionDate', '')[:10]

            try:
                tx_date = datetime.strptime(tx_date_str, "%Y-%m-%d")
            except Exception:
                tx_date = None

            # Resumen 6 meses: solo transacciones discrecionales reales de mercado
            # (excluye donaciones/conversiones/liquidaciones fiscales rutinarias,
            # que no reflejan una decisión de compra/venta del insider).
            if tx_date and tx_date >= cutoff and cls["scheduled"] is not True:
                if is_buy:
                    buy_count += 1
                    buy_value += total
                else:
                    sell_count += 1
                    sell_value += total

            # Volumen mensual: 12 meses, mismas reglas de "discrecional" que el
            # resumen, para que el gráfico cuente lo mismo que el sentimiento.
            if tx_date and tx_date >= vol_cutoff and cls["scheduled"] is not True:
                month_key = tx_date.strftime('%Y-%m')
                if month_key not in monthly:
                    monthly[month_key] = {"buy_shares": 0, "sell_shares": 0}
                if is_buy:
                    monthly[month_key]["buy_shares"] += int(abs(change))
                else:
                    monthly[month_key]["sell_shares"] += int(abs(change))

            if len(results) < 10:
                results.append({
                    "date":     tx_date_str,
                    "name":     item.get('name', ''),
                    "title":    item.get('position', ''),
                    "type":     'COMPRA' if is_buy else 'VENTA',
                    "type_color": '#00ffad' if is_buy else '#f23645',
                    "shares":   int(abs(change)),
                    "price":    round(value, 2),
                    "value":    _fmt_value(total),
                    "code":     (item.get('transactionCode') or '').strip().upper(),
                    "nature":   cls["nature"],
                    "scheduled": cls["scheduled"],
                    "flag":      cls["flag"],
                    "flag_color": cls["flag_color"],
                })

        summary = None
        if buy_count or sell_count:
            net_value = buy_value - sell_value
            total_value = buy_value + sell_value
            sentiment = "NEUTRAL"
            sentiment_color = "var(--color-muted)"
            if total_value > 0:
                net_ratio = net_value / total_value
                if net_ratio > 0.3:
                    sentiment, sentiment_color = "COMPRADOR", "#00ffad"
                elif net_ratio < -0.3:
                    sentiment, sentiment_color = "VENDEDOR", "#f23645"
            summary = {
                "buy_count":   buy_count,
                "sell_count":  sell_count,
                "buy_value":   _fmt_value(buy_value),
                "sell_value":  _fmt_value(sell_value),
                "net_value":   _fmt_value(abs(net_value)),
                "net_is_buy":  net_value >= 0,
                "sentiment":   sentiment,
                "sentiment_color": sentiment_color,
                "months":      6,
            }

        # Ordenar cronológicamente y rellenar meses sin actividad con 0, para
        # que el eje del gráfico no tenga huecos irregulares.
        monthly_volume = []
        if monthly:
            cursor = vol_cutoff.replace(day=1)
            end    = datetime.now().replace(day=1)
            while cursor <= end:
                key = cursor.strftime('%Y-%m')
                m   = monthly.get(key, {"buy_shares": 0, "sell_shares": 0})
                monthly_volume.append({
                    "month":       key,
                    "buy_shares":  m["buy_shares"],
                    "sell_shares": m["sell_shares"],
                })
                # Avanza al primer día del mes siguiente
                if cursor.month == 12:
                    cursor = cursor.replace(year=cursor.year + 1, month=1)
                else:
                    cursor = cursor.replace(month=cursor.month + 1)

        return {"transactions": results, "summary": summary, "monthly_volume": monthly_volume}
    except Exception:
        return {"transactions": [], "summary": None, "monthly_volume": []}

def _row_get(row, *names):
    """Busca un valor en una fila de DataFrame yfinance probando varios nombres posibles
    (los nombres de columnas de yfinance varían entre versiones)."""
    for n in names:
        if n in row.index:
            return row[n]
    lower_map = {str(k).lower().replace(' ', '').replace('%', ''): k for k in row.index}
    for n in names:
        key = n.lower().replace(' ', '').replace('%', '')
        if key in lower_map:
            return row[lower_map[key]]
    return None

def _get_piotroski_score(ticker: str) -> dict:
    """Piotroski F-Score (0-9): salud financiera fundamental vs. el ejercicio anterior."""
    try:
        stock = yf.Ticker(ticker)
        bs  = stock.balance_sheet
        fin = stock.financials
        cf  = stock.cashflow
        if bs is None or bs.empty or fin is None or fin.empty or cf is None or cf.empty:
            return {}
        if bs.shape[1] < 2 or fin.shape[1] < 2 or cf.shape[1] < 2:
            return {}

        missing_lines = []

        def line(df, *names):
            for n in names:
                if n in df.index:
                    return df.loc[n]
            missing_lines.append(names[0])
            return None

        total_assets   = line(bs, 'Total Assets')
        net_income     = line(fin, 'Net Income')
        op_cf          = line(cf, 'Operating Cash Flow', 'Total Cash From Operating Activities')
        lt_debt        = line(bs, 'Long Term Debt', 'Long Term Debt And Capital Lease Obligation')
        current_assets = line(bs, 'Current Assets', 'Total Current Assets')
        current_liab   = line(bs, 'Current Liabilities', 'Total Current Liabilities')
        shares_out     = line(bs, 'Ordinary Shares Number', 'Share Issued')
        revenue        = line(fin, 'Total Revenue')
        gross_profit   = line(fin, 'Gross Profit')

        if missing_lines:
            print(f"[Piotroski:{ticker}] Líneas contables no encontradas (criterio(s) afectado(s) marcado(s) como 'sin datos'): {missing_lines}")

        if total_assets is None or net_income is None or op_cf is None:
            print(f"[Piotroski:{ticker}] Cancelado — faltan líneas base imprescindibles (Total Assets / Net Income / Operating Cash Flow)")
            return {}

        ta0, ta1 = _safe(total_assets.iloc[0]), _safe(total_assets.iloc[1])
        ni0, ni1 = _safe(net_income.iloc[0]), _safe(net_income.iloc[1])
        cfo0     = _safe(op_cf.iloc[0])

        roa0 = (ni0 / ta0) if (ta0 and ni0 is not None) else None
        roa1 = (ni1 / ta1) if (ta1 and ni1 is not None) else None

        criteria = []
        score = 0

        def add_criterion(pass_value, label_true, label_false, label_unknown):
            """
            pass_value puede ser True, False, o None (dato no disponible).
            La etiqueta mostrada describe siempre el HECHO real ocurrido, nunca
            la condición ideal — así el icono (✓/✗) nunca obliga a invertir
            mentalmente el texto. 'None' se puntúa como 0 (igual que el Piotroski
            original trata cualquier dato no disponible), pero se muestra distinto
            (— gris) para no afirmar que pasó algo negativo cuando en realidad
            no tenemos el dato.
            """
            nonlocal score
            if pass_value is None:
                criteria.append({"label": label_unknown, "pass": None})
            elif pass_value:
                criteria.append({"label": label_true, "pass": True})
                score += 1
            else:
                criteria.append({"label": label_false, "pass": False})

        # 1. ROA positivo
        c1 = (roa0 > 0) if roa0 is not None else None
        add_criterion(c1, "ROA positivo", "ROA negativo (pérdidas)", "ROA no disponible")

        # 2. CFO positivo
        c2 = (cfo0 > 0) if cfo0 is not None else None
        add_criterion(c2, "Flujo de caja operativo positivo", "Flujo de caja operativo negativo", "Flujo de caja operativo no disponible")

        # 3. ROA en mejora interanual
        c3 = (roa0 > roa1) if (roa0 is not None and roa1 is not None) else None
        add_criterion(c3, "ROA mejoró respecto al año anterior", "ROA empeoró respecto al año anterior", "Comparación de ROA no disponible")

        # 4. Calidad del beneficio: CFO > Net Income
        c4 = (cfo0 > ni0) if (cfo0 is not None and ni0 is not None) else None
        add_criterion(c4, "Beneficio de buena calidad (CFO > Bº Neto)", "Beneficio de baja calidad (CFO < Bº Neto)", "Calidad del beneficio no disponible")

        # 5. Apalancamiento estable o decreciente
        c5 = None
        if lt_debt is not None and ta0 and ta1:
            ld0 = _safe(lt_debt.iloc[0])
            ld1 = _safe(lt_debt.iloc[1])
            if ld0 is not None and ld1 is not None:
                c5 = (ld0 / ta0) <= (ld1 / ta1)
        add_criterion(c5, "Apalancamiento estable o ha bajado", "El apalancamiento ha aumentado", "Apalancamiento no disponible")

        # 6. Liquidez (current ratio) en mejora
        c6 = None
        if current_assets is not None and current_liab is not None:
            ca0, ca1 = _safe(current_assets.iloc[0]), _safe(current_assets.iloc[1])
            cl0, cl1 = _safe(current_liab.iloc[0]), _safe(current_liab.iloc[1])
            if ca0 and cl0 and ca1 and cl1:
                c6 = (ca0 / cl0) > (ca1 / cl1)
        add_criterion(c6, "Liquidez (current ratio) mejoró", "Liquidez (current ratio) empeoró", "Liquidez no disponible")

        # 7. Sin dilución de acciones
        c7 = None
        if shares_out is not None:
            s0, s1 = _safe(shares_out.iloc[0]), _safe(shares_out.iloc[1])
            if s0 is not None and s1 is not None:
                c7 = s0 <= s1
        add_criterion(c7, "Sin dilución de acciones (nº de acciones estable o ha bajado)", "Hubo dilución de acciones (emisión de nuevas acciones)", "Nº de acciones no disponible")

        # 8. Margen bruto en mejora
        c8 = None
        if gross_profit is not None and revenue is not None:
            gp0, gp1 = _safe(gross_profit.iloc[0]), _safe(gross_profit.iloc[1])
            rv0, rv1 = _safe(revenue.iloc[0]), _safe(revenue.iloc[1])
            if gp0 is not None and rv0 and gp1 is not None and rv1:
                c8 = (gp0 / rv0) > (gp1 / rv1)
        add_criterion(c8, "Margen bruto mejoró", "Margen bruto empeoró", "Margen bruto no disponible")

        # 9. Rotación de activos en mejora
        c9 = None
        if revenue is not None and ta0 and ta1:
            rv0, rv1 = _safe(revenue.iloc[0]), _safe(revenue.iloc[1])
            if rv0 and rv1:
                c9 = (rv0 / ta0) > (rv1 / ta1)
        add_criterion(c9, "Rotación de activos mejoró", "Rotación de activos empeoró", "Rotación de activos no disponible")

        if score >= 8:    label, color = "EXCELENTE", "#00ffad"
        elif score >= 6:  label, color = "SÓLIDO", "#90ee90"
        elif score >= 4:  label, color = "NEUTRAL", "#ffb800"
        else:             label, color = "DÉBIL", "#f23645"

        return {"score": score, "max": 9, "label": label, "color": color, "criteria": criteria, "missing_lines": missing_lines}
    except Exception as e:
        print(f"[Piotroski:{ticker}] Error inesperado al calcular: {e}")
        return {}

def _get_income_statement(ticker: str) -> list:
    """Income statement trimestral (Revenue, Gross Profit, Operating Income,
    Net Income) para el gráfico de evolución financiera. Usa
    quarterly_income_stmt (yfinance >= 0.2.x) con fallback a
    quarterly_financials para compatibilidad con versiones antiguas."""
    try:
        stock = yf.Ticker(ticker)
        df = None
        try:
            df = stock.quarterly_income_stmt
        except Exception:
            df = None
        if df is None or df.empty:
            try:
                df = stock.quarterly_financials
            except Exception:
                df = None
        if df is None or df.empty:
            return []

        # Columnas = fechas trimestrales (más reciente primero), filas = conceptos
        cols = list(df.columns)
        cols = sorted(cols)  # cronológico ascendente para el gráfico

        out = []
        for col in cols:
            def pick(*names):
                for n in names:
                    try:
                        if n in df.index:
                            v = df.loc[n, col]
                            v = _safe(v)
                            if v is not None:
                                return v
                    except Exception:
                        continue
                return None

            revenue          = pick('Total Revenue', 'TotalRevenue')
            gross_profit     = pick('Gross Profit', 'GrossProfit')
            operating_income = pick('Operating Income', 'OperatingIncome')
            net_income       = pick('Net Income', 'NetIncome', 'Net Income Common Stockholders')

            if revenue is None and gross_profit is None and operating_income is None and net_income is None:
                continue

            try:
                date_str = col.strftime('%Y-%m-%d') if hasattr(col, 'strftime') else str(col)[:10]
            except Exception:
                date_str = str(col)[:10]

            out.append({
                "date":             date_str,
                "revenue":          revenue,
                "gross_profit":     gross_profit,
                "operating_income": operating_income,
                "net_income":       net_income,
            })

        return out
    except Exception as e:
        print(f"[IncomeStatement:{ticker}] Error: {e}")
        return []

def _get_institutional_ownership(ticker: str) -> dict:
    """% del capital en manos de institucionales y principales accionistas."""
    try:
        stock = yf.Ticker(ticker)
        info = {}
        try: info = stock.info or {}
        except Exception: pass
        pct = _safe(info.get('heldPercentInstitutions'))

        holders = []
        try:
            df = stock.institutional_holders
            if df is not None and not df.empty:
                df = df.head(8)

                # FIX: la columna "Value" de yfinance NO es el valor reportado
                # en el 13F — en versiones recientes yfinance la recalcula como
                # acciones × precio ACTUAL, así que Valor/Acciones siempre da el
                # precio de hoy (igual para todas las filas). Para obtener un
                # precio de referencia real por institución, descargamos el
                # histórico de precios y usamos el cierre en la fecha de reporte
                # de cada una (una sola descarga para todas, no una por fila).
                raw_dates = []
                for _, r in df.iterrows():
                    d = _row_get(r, 'Date Reported', 'dateReported')
                    if d is not None:
                        raw_dates.append(d if hasattr(d, 'to_pydatetime') else d)

                price_hist = None
                if raw_dates:
                    try:
                        min_d = min(raw_dates)
                        from datetime import timedelta as _td
                        start = (min_d.to_pydatetime() if hasattr(min_d, 'to_pydatetime') else min_d) - _td(days=7)
                        price_hist = stock.history(start=start.strftime('%Y-%m-%d'), end=datetime.now().strftime('%Y-%m-%d'))
                    except Exception:
                        price_hist = None

                def _price_on(date_val):
                    """Cierre real más cercano (mismo día o anterior) a date_val."""
                    if price_hist is None or price_hist.empty or date_val is None:
                        return None
                    try:
                        ts = date_val.to_pydatetime() if hasattr(date_val, 'to_pydatetime') else date_val
                        ts = ts.replace(tzinfo=None)
                        idx = price_hist.index.tz_localize(None) if price_hist.index.tz is not None else price_hist.index
                        eligible = price_hist.loc[idx <= ts]
                        if eligible.empty:
                            eligible = price_hist
                        return round(float(eligible['Close'].iloc[-1]), 2)
                    except Exception:
                        return None

                for _, r in df.iterrows():
                    holder_name = _row_get(r, 'Holder', 'holder')
                    shares      = _safe(_row_get(r, 'Shares', 'shares')) or 0
                    pct_held    = _safe(_row_get(r, 'pctHeld', '% Out', 'pctOut', 'Percentage'))
                    value       = _safe(_row_get(r, 'Value', 'value'))
                    date_rep    = _row_get(r, 'Date Reported', 'dateReported')
                    try:
                        date_str = date_rep.strftime('%Y-%m-%d') if hasattr(date_rep, 'strftime') else str(date_rep)[:10]
                    except Exception:
                        date_str = str(date_rep)[:10] if date_rep else ''

                    ref_price = _price_on(date_rep)

                    holders.append({
                        "holder":   holder_name or 'N/D',
                        "shares":   int(shares),
                        "pct_out":  round(pct_held * 100, 2) if pct_held and pct_held < 1 else (round(pct_held, 2) if pct_held else None),
                        "value":    _fmt_value(value),
                        "date":     date_str,
                        "ref_price": ref_price,
                    })
        except Exception:
            pass

        return {
            "pct_institutions": round(pct * 100, 2) if pct is not None else None,
            "holders": holders,
        }
    except Exception:
        return {}

def _get_short_interest(ticker: str) -> dict:
    try:
        stock     = yf.Ticker(ticker)
        info      = stock.info or {}
        short_pct = _safe(info.get('shortPercentOfFloat'))
        short_int = _safe(info.get('sharesShort'))
        short_ratio = _safe(info.get('shortRatio'))  # días para cubrir
        if short_pct is None and short_int is None:
            return {}

        short_pct_fmt = round(short_pct * 100, 2) if short_pct else None

        # Squeeze score 0-100: combina % del float en corto (peso 60) y
        # días para cubrir (peso 40). Umbrales calibrados sobre referencias
        # históricas de squeezes conocidos (GME, AMC, etc. > 20% float / >5 DTC).
        squeeze_score = None
        if short_pct_fmt is not None or short_ratio is not None:
            pct_component   = min((short_pct_fmt or 0) / 30 * 60, 60)
            ratio_component = min((short_ratio or 0) / 10 * 40, 40)
            squeeze_score = round(pct_component + ratio_component, 1)

        if squeeze_score is None:
            squeeze_label = None
        elif squeeze_score >= 75:
            squeeze_label = "EXTREMO"
        elif squeeze_score >= 50:
            squeeze_label = "ALTO"
        elif squeeze_score >= 25:
            squeeze_label = "MODERADO"
        else:
            squeeze_label = "BAJO"

        return {
            "short_pct":      short_pct_fmt,
            "short_int":      short_int,
            "short_ratio":    round(short_ratio, 1) if short_ratio else None,  # days to cover
            "squeeze_score":  squeeze_score,
            "squeeze_label":  squeeze_label,
            "date":           "",
        }
    except Exception:
        return {}

def _get_next_earnings(ticker: str) -> dict:
    try:
        key = settings.finnhub_api_key
        if not key: return {}
        from datetime import datetime, timedelta
        now     = datetime.now()
        to_date = (now + timedelta(days=90)).strftime('%Y-%m-%d')
        from_date = now.strftime('%Y-%m-%d')
        r = requests.get(
            f"https://finnhub.io/api/v1/calendar/earnings?symbol={ticker}&from={from_date}&to={to_date}&token={key}",
            timeout=8
        )
        if r.status_code != 200: return {}
        items = r.json().get('earningsCalendar', [])
        if not items: return {}
        next_e = items[0]
        return {
            "date":     next_e.get('date', ''),
            "eps_est":  _safe(next_e.get('epsEstimate')),
            "hour":     next_e.get('hour', ''),
        }
    except Exception:
        return {}

def _get_seasonality(ticker: str) -> list:
    try:
        import yfinance as yf
        stock = yf.Ticker(ticker)
        hist  = stock.history(period="5y", interval="1mo")
        if hist.empty or len(hist) < 12: return []
        hist['month']  = hist.index.month
        hist['return'] = hist['Close'].pct_change() * 100
        monthly = hist.groupby('month')['return'].mean()
        months  = ['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic']
        results = []
        for m in range(1, 13):
            val = round(float(monthly.get(m, 0)), 2)
            results.append({
                "month": months[m-1],
                "avg":   val,
                "color": '#00ffad' if val > 1 else '#90ee90' if val > 0 else '#f23645' if val < -1 else '#ff8c00',
            })
        return results
    except Exception:
        return []

def _ema_slope(series, lookback: int, threshold: float):
    """Calcula la pendiente de una EMA comparando valor actual vs hace `lookback` sesiones.
    threshold es el % mínimo de variación para considerarla inclinada (si no, 'plana')."""
    if len(series) <= lookback:
        return None, None
    now  = float(series.iloc[-1])
    prev = float(series.iloc[-1 - lookback])
    if prev == 0:
        return None, None
    pct = round((now - prev) / prev * 100, 2)
    if pct > threshold:
        return "alcista", pct
    if pct < -threshold:
        return "bajista", pct
    return "plana", pct

def _classify_phase_from_close(close) -> dict:
    """Fase Weinstein (1-4) a partir de una serie de cierres — idéntica
    metodología que scripts/scanner_universe.py:_classify_phase (mismos
    umbrales, mismo orden de comprobaciones), factorizada aquí como función
    reutilizable para poder aplicar debounce y la versión semanal sin
    duplicar la lógica de clasificación en sí."""
    if len(close) < 50:
        return {"phase": None, "phase_label": "Sin datos suficientes", "trend": None}

    price    = float(close.iloc[-1])
    ema10_s  = close.ewm(span=10,  adjust=False).mean()
    ema20_s  = close.ewm(span=20,  adjust=False).mean()
    ema50_s  = close.ewm(span=50,  adjust=False).mean()
    ema200_s = close.ewm(span=200, adjust=False).mean() if len(close) >= 200 else None

    ema20  = float(ema20_s.iloc[-1])
    ema50  = float(ema50_s.iloc[-1])
    ema200 = float(ema200_s.iloc[-1]) if ema200_s is not None else None

    slope10_dir,  _ = _ema_slope(ema10_s,  3,  0.4)
    slope20_dir,  _ = _ema_slope(ema20_s,  5,  0.4)
    slope50_dir,  _ = _ema_slope(ema50_s,  10, 0.6)
    slope200_dir, _ = _ema_slope(ema200_s, 20, 0.8) if ema200_s is not None else (None, None)

    bull_conditions = [
        price > ema20,
        ema20 > ema50,
        (ema50 > ema200) if ema200 else True,
        slope50_dir == "alcista",
        (slope200_dir in ("alcista", "plana")) if slope200_dir else True,
    ]
    bull_score = sum(1 for c in bull_conditions if c)

    early_reversal  = (slope10_dir == "alcista" and slope20_dir == "alcista" and price > ema20)
    early_breakdown = (slope10_dir == "bajista" and slope20_dir == "bajista" and price < ema20)

    if bull_score >= 4:
        trend = "ALCISTA"
    elif bull_score <= 1 and not early_reversal:
        trend = "BAJISTA"
    else:
        trend = "RANGO"

    if trend == "ALCISTA":
        phase, label = 2, "Fase 2 · Avance (Markup)"
    elif trend == "BAJISTA":
        phase, label = 4, "Fase 4 · Declive / Corrección"
    elif early_reversal and bull_score <= 1:
        phase, label = 1, "Fase 1 · Posible Giro Temprano"
    elif early_breakdown:
        phase, label = 3, "Fase 3 · Posible Giro Bajista Temprano"
    elif ema200 and price >= ema200:
        phase, label = 3, "Fase 3 · Distribución"
    else:
        phase, label = 1, "Fase 1 · Acumulación"

    return {"phase": phase, "phase_label": label, "trend": trend}


def _classify_phase_debounced(close, confirm_sessions: int = 3) -> dict:
    """Exige que la fase se mantenga `confirm_sessions` sesiones seguidas
    antes de darla por "confirmada" — mismo mecanismo que
    scripts/scanner_universe.py:_classify_phase_debounced. Reduce el parpadeo
    entre fases por ruido de un solo día sin tocar la fórmula en sí."""
    today_result = _classify_phase_from_close(close)
    if today_result["phase"] is None:
        today_result["phase_confirmed"] = None
        return today_result

    recent_phases = [today_result["phase"]]
    for i in range(1, confirm_sessions):
        cutoff = len(close) - i
        if cutoff < 50:
            break
        sub = _classify_phase_from_close(close.iloc[:cutoff])
        if sub["phase"] is None:
            break
        recent_phases.append(sub["phase"])

    if len(recent_phases) < confirm_sessions:
        today_result["phase_confirmed"] = None
        return today_result

    confirmed = len(set(recent_phases)) == 1
    result = dict(today_result)
    result["phase_confirmed"] = confirmed
    if not confirmed:
        result["phase_label"] = result["phase_label"] + " (sin confirmar)"
    return result


def _resample_weekly_close(close):
    """Reagrupa cierres diarios en cierres semanales (viernes) — misma
    técnica que rsu_algoritmo_service._resample_semanal, aplicada aquí solo
    a la serie de cierre."""
    if len(close) < 14:
        return None
    try:
        weekly = close.resample('W-FRI').last().dropna()
        return weekly if len(weekly) >= 10 else None
    except Exception:
        return None


def _classify_phase_weekly(close_daily) -> dict:
    """Fase Weinstein sobre velas SEMANALES — la temporalidad original del
    método (el libro de Weinstein usa gráficos semanales, no diarios).
    Pensada como CONFIRMACIÓN estructural junto a la fase diaria (más rápida
    y táctica), no como sustituta — ver tooltip "market-phase" para más
    contexto. Misma implementación que scripts/scanner_universe.py para que
    ambos módulos sigan siendo coherentes entre sí."""
    weekly = _resample_weekly_close(close_daily)
    if weekly is None or len(weekly) < 30:
        return {"phase": None, "phase_label": "Sin histórico semanal suficiente", "trend": None}

    price    = float(weekly.iloc[-1])
    ema10_s  = weekly.ewm(span=10,  adjust=False, min_periods=5).mean()
    ema20_s  = weekly.ewm(span=20,  adjust=False, min_periods=10).mean()
    ema50_s  = weekly.ewm(span=50,  adjust=False, min_periods=20).mean()
    ema200_s = weekly.ewm(span=200, adjust=False, min_periods=20).mean() if len(weekly) >= 20 else None

    ema20  = float(ema20_s.iloc[-1])
    ema50  = float(ema50_s.iloc[-1])
    ema200 = float(ema200_s.iloc[-1]) if ema200_s is not None else None

    slope10_dir,  _ = _ema_slope(ema10_s,  1, 0.4)
    slope20_dir,  _ = _ema_slope(ema20_s,  2, 0.4)
    slope50_dir,  _ = _ema_slope(ema50_s,  3, 0.6)
    slope200_dir, _ = _ema_slope(ema200_s, 4, 0.8) if ema200_s is not None else (None, None)

    bull_conditions = [
        price > ema20,
        ema20 > ema50,
        (ema50 > ema200) if ema200 else True,
        slope50_dir == "alcista",
        (slope200_dir in ("alcista", "plana")) if slope200_dir else True,
    ]
    bull_score = sum(1 for c in bull_conditions if c)

    early_reversal  = (slope10_dir == "alcista" and slope20_dir == "alcista" and price > ema20)
    early_breakdown = (slope10_dir == "bajista" and slope20_dir == "bajista" and price < ema20)

    if bull_score >= 4:
        trend = "ALCISTA"
    elif bull_score <= 1 and not early_reversal:
        trend = "BAJISTA"
    else:
        trend = "RANGO"

    if trend == "ALCISTA":
        phase, label = 2, "Fase 2 · Avance (Markup)"
    elif trend == "BAJISTA":
        phase, label = 4, "Fase 4 · Declive / Corrección"
    elif early_reversal and bull_score <= 1:
        phase, label = 1, "Fase 1 · Posible Giro Temprano"
    elif early_breakdown:
        phase, label = 3, "Fase 3 · Posible Giro Bajista Temprano"
    elif ema200 and price >= ema200:
        phase, label = 3, "Fase 3 · Distribución"
    else:
        phase, label = 1, "Fase 1 · Acumulación"

    return {"phase": phase, "phase_label": label, "trend": trend}


def _get_technical_levels(ticker: str) -> dict:
    try:
        import yfinance as yf
        stock = yf.Ticker(ticker)
        # 2 años para que las EMAs largas (200) tengan recorrido suficiente de cálculo,
        # no solo de visualización.
        hist  = stock.history(period="2y", interval="1d").dropna()
        if len(hist) < 50: return {}
        close  = hist['Close']
        price  = float(close.iloc[-1])

        sma50  = round(float(close.tail(50).mean()), 2)
        sma200 = round(float(close.tail(200).mean()), 2) if len(close) >= 200 else None
        sma20  = round(float(close.tail(20).mean()), 2)
        high52 = round(float(close.tail(252).max()), 2) if len(close) >= 252 else round(float(close.max()), 2)
        low52  = round(float(close.tail(252).min()), 2) if len(close) >= 252 else round(float(close.min()), 2)

        # ── EMAs ──────────────────────────────────────────────────────────────
        ema10_s  = close.ewm(span=10,  adjust=False).mean()
        ema20_s  = close.ewm(span=20,  adjust=False).mean()
        ema50_s  = close.ewm(span=50,  adjust=False).mean()
        ema200_s = close.ewm(span=200, adjust=False).mean() if len(close) >= 200 else None

        ema10  = round(float(ema10_s.iloc[-1]), 2)
        ema20  = round(float(ema20_s.iloc[-1]), 2)
        ema50  = round(float(ema50_s.iloc[-1]), 2)
        ema200 = round(float(ema200_s.iloc[-1]), 2) if ema200_s is not None else None

        # Pendientes: lookback y umbral más amplios para EMAs más lentas.
        slope10_dir,  slope10_pct  = _ema_slope(ema10_s,  3,  0.4)
        slope20_dir,  slope20_pct  = _ema_slope(ema20_s,  5,  0.4)
        slope50_dir,  slope50_pct  = _ema_slope(ema50_s,  10, 0.6)
        slope200_dir, slope200_pct = _ema_slope(ema200_s, 20, 0.8) if ema200_s is not None else (None, None)

        # ── Clasificación de tendencia y fase (diaria, con debounce, + semanal) ──
        # La lógica de clasificación en sí vive ahora en funciones reutilizables
        # (_classify_phase_debounced / _classify_phase_weekly) — misma
        # metodología exacta que scripts/scanner_universe.py, así que Research
        # y Scanner siguen siendo coherentes entre sí. Las EMAs/pendientes de
        # arriba se mantienen aparte porque alimentan las tarjetas visuales
        # ("emas" en el return de abajo), no la decisión de fase en sí.
        phase_info        = _classify_phase_debounced(close)
        phase_weekly_info = _classify_phase_weekly(close)

        trend        = phase_info["trend"]
        phase        = phase_info["phase"]
        phase_label  = phase_info["phase_label"]
        early_reversal = (slope10_dir == "alcista" and slope20_dir == "alcista" and price > ema20)

        return {
            "sma20":         sma20,
            "sma50":         sma50,
            "sma200":        sma200,
            "vs_sma20":      round((price - sma20)  / sma20  * 100, 1),
            "vs_sma50":      round((price - sma50)  / sma50  * 100, 1),
            "vs_sma200":     round((price - sma200) / sma200 * 100, 1) if sma200 else None,
            "vs_52h":        round((price - high52) / high52 * 100, 1),
            "vs_52l":        round((price - low52)  / low52  * 100, 1),
            "above_sma50":   price > sma50,
            "above_sma200":  price > sma200 if sma200 else None,

            "emas": {
                "ema10":  {"value": ema10,  "slope": slope10_dir,  "slope_pct": slope10_pct,
                           "vs_price": round((price - ema10) / ema10 * 100, 1)},
                "ema20":  {"value": ema20,  "slope": slope20_dir,  "slope_pct": slope20_pct,
                           "vs_price": round((price - ema20) / ema20 * 100, 1)},
                "ema50":  {"value": ema50,  "slope": slope50_dir,  "slope_pct": slope50_pct,
                           "vs_price": round((price - ema50) / ema50 * 100, 1)},
                "ema200": {"value": ema200, "slope": slope200_dir, "slope_pct": slope200_pct,
                           "vs_price": round((price - ema200) / ema200 * 100, 1) if ema200 else None},
            },
            "trend":               trend,
            "market_phase":        phase,
            "phase_label":         phase_label,
            "phase_confirmed":     phase_info.get("phase_confirmed"),
            "phase_weekly":        phase_weekly_info["phase"],
            "phase_weekly_label":  phase_weekly_info["phase_label"],
            "early_reversal":      early_reversal,
        }
    except Exception:
        return {}

# ETF de referencia por sector GICS, usado como FALLBACK cuando no hay un
# ETF de industria más específico disponible (ver INDUSTRY_ETF_MAP abajo).
SECTOR_ETF_MAP = {
    "Technology":             "XLK",
    "Financial Services":     "XLF",
    "Healthcare":             "XLV",
    "Consumer Cyclical":      "XLY",
    "Consumer Defensive":     "XLP",
    "Industrials":            "XLI",
    "Energy":                 "XLE",
    "Basic Materials":        "XLB",
    "Utilities":              "XLU",
    "Real Estate":            "XLRE",
    "Communication Services": "XLC",
}

# ETF de referencia por INDUSTRIA (campo info['industry'] de yfinance, más
# granular que info['sector']). Un sector GICS como "Industrials" agrupa
# negocios tan distintos como aeroespacial/defensa, maquinaria pesada,
# transporte o construcción — comparar una empresa de defensa contra XLI
# (todo el sector industrial) diluye la comparación frente a comparar contra
# ITA (específico de Aerospace & Defense). Se usa esta tabla PRIMERO; si la
# industria exacta del ticker no está aquí, se cae al ETF de sector general.
# Cobertura no exhaustiva — los casos más comunes donde sector ≠ industria real.
INDUSTRY_ETF_MAP = {
    "Aerospace & Defense":            "ITA",
    "Semiconductors":                 "SOXX",
    "Semiconductor Equipment & Materials": "SOXX",
    "Software—Application":           "IGV",
    "Software—Infrastructure":        "IGV",
    "Biotechnology":                  "IBB",
    "Drug Manufacturers—General":     "XPH",
    "Drug Manufacturers—Specialty & Generic": "XPH",
    "Oil & Gas E&P":                  "XOP",
    "Oil & Gas Equipment & Services": "XOP",
    "Banks—Regional":                 "KRE",
    "Homebuilding":                   "ITB",
    "Internet Retail":                "ONLN",
    "Airlines":                       "JETS",
    "Gold":                           "GDX",
    "Silver":                         "SIL",
    "REIT—Residential":               "XLRE",
    "Insurance—Life":                 "KIE",
    "Insurance—Property & Casualty":  "KIE",
    "Asset Management":               "KCE",
    "Capital Markets":                "KCE",
    "Utilities—Renewable":            "ICLN",
    "Solar":                          "TAN",
}

def _get_relative_strength(ticker: str, sector: str, industry: str = None) -> dict:
    """
    Fuerza relativa del activo vs SPY (mercado) y vs su benchmark sectorial,
    en 3 marcos temporales (1m/3m/6m) ponderados — misma lógica de
    weighting por periodo que el módulo RS/RW Scanner, aplicada aquí a
    un solo ticker en vez de a todo el universo.

    El benchmark "sectorial" usa, cuando está disponible, un ETF de
    INDUSTRIA específica (más preciso) en vez del ETF de sector GICS
    genérico — ver INDUSTRY_ETF_MAP.
    """
    try:
        industry_etf = INDUSTRY_ETF_MAP.get(industry) if industry else None
        sector_etf   = industry_etf or SECTOR_ETF_MAP.get(sector)
        benchmark_label = (industry if industry_etf else sector) or "Sector"

        def _closes(sym):
            try:
                h = yf.Ticker(sym).history(period="7mo", interval="1d")
                return h['Close'].dropna() if (h is not None and not h.empty) else None
            except Exception:
                return None

        close_t   = _closes(ticker)
        close_spy = _closes('SPY')
        close_sec = _closes(sector_etf) if sector_etf else None

        if close_t is None or close_spy is None or len(close_t) < 21:
            return {}

        # (días, etiqueta, peso) — mismo esquema de ponderación que RS/RW:
        # más peso al corto plazo, sin ignorar el medio plazo.
        PERIODS = [(21, '1m', 0.5), (63, '3m', 0.3), (126, '6m', 0.2)]

        def _ret(close, days):
            if close is None or len(close) <= days: return None
            return round((float(close.iloc[-1]) / float(close.iloc[-1 - days]) - 1) * 100, 2)

        periods_data = []
        w_spy_sum = w_spy_w = 0.0
        w_sec_sum = w_sec_w = 0.0

        for days, label, weight in PERIODS:
            t_ret   = _ret(close_t, days)
            spy_ret = _ret(close_spy, days)
            sec_ret = _ret(close_sec, days) if close_sec is not None else None
            if t_ret is None or spy_ret is None:
                continue
            rs_spy = round(t_ret - spy_ret, 2)
            rs_sec = round(t_ret - sec_ret, 2) if sec_ret is not None else None
            w_spy_sum += rs_spy * weight
            w_spy_w   += weight
            if rs_sec is not None:
                w_sec_sum += rs_sec * weight
                w_sec_w   += weight
            periods_data.append({
                "label": label, "ticker_ret": t_ret, "spy_ret": spy_ret,
                "sector_ret": sec_ret, "rs_vs_spy": rs_spy, "rs_vs_sector": rs_sec,
            })

        if not periods_data:
            return {}

        rs_vs_spy_score    = round(w_spy_sum / w_spy_w, 2) if w_spy_w else None
        rs_vs_sector_score = round(w_sec_sum / w_sec_w, 2) if w_sec_w else None

        def _classify(score):
            if score is None: return None, None
            if score > 5:    return "FUERTE", "#00ffad"
            if score > 1.5:  return "LIGERAMENTE FUERTE", "#90ee90"
            if score < -5:   return "DÉBIL", "#f23645"
            if score < -1.5: return "LIGERAMENTE DÉBIL", "#ff8c00"
            return "NEUTRAL", "#ffb800"

        spy_label, spy_color       = _classify(rs_vs_spy_score)
        sector_label, sector_color = _classify(rs_vs_sector_score)

        return {
            "sector_etf":         sector_etf,
            "benchmark_label":    benchmark_label,
            "is_industry_level":  industry_etf is not None,
            "rs_vs_spy":          rs_vs_spy_score,
            "rs_vs_spy_label":    spy_label,
            "rs_vs_spy_color":    spy_color,
            "rs_vs_sector":       rs_vs_sector_score,
            "rs_vs_sector_label": sector_label,
            "rs_vs_sector_color": sector_color,
            "periods":            periods_data,
        }
    except Exception:
        return {}

# ── CRIPTO — perfil temático vía CoinGecko (misma API que ya usa BTC Stratum) ──
#
# CoinGecko requiere su propio "id" interno (p.ej. "bitcoin"), no el símbolo
# del ticker — y varias criptos distintas pueden compartir símbolo (hay
# decenas de tokens "ETH" o "SOL" de proyectos menores). Para los ~20 nombres
# más habituales se usa un mapeo fijo (cero ambigüedad, cero llamada extra);
# para el resto se resuelve con /search, que ordena resultados por relevancia
# de capitalización — el primer resultado exacto de símbolo es, en la
# práctica, casi siempre el proyecto "real" y no un token menor homónimo.
_CRYPTO_ID_OVERRIDES = {
    "BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana", "XRP": "ripple",
    "ADA": "cardano", "DOGE": "dogecoin", "AVAX": "avalanche-2", "DOT": "polkadot",
    "MATIC": "matic-network", "LINK": "chainlink", "LTC": "litecoin",
    "BNB": "binancecoin", "SHIB": "shiba-inu", "TRX": "tron", "UNI": "uniswap",
    "ATOM": "cosmos", "XLM": "stellar", "BCH": "bitcoin-cash", "NEAR": "near",
    "APT": "aptos", "ARB": "arbitrum", "OP": "optimism", "SUI": "sui",
    "ICP": "internet-computer", "FIL": "filecoin", "ETC": "ethereum-classic",
}

def _resolve_coingecko_id(symbol: str):
    symbol = symbol.upper()
    if symbol in _CRYPTO_ID_OVERRIDES:
        return _CRYPTO_ID_OVERRIDES[symbol]
    try:
        r = requests.get(
            "https://api.coingecko.com/api/v3/search",
            params={"query": symbol},
            timeout=8,
        )
        if r.status_code == 200:
            coins = r.json().get("coins", [])
            for c in coins:
                if (c.get("symbol") or "").upper() == symbol:
                    return c.get("id")
            if coins:
                return coins[0].get("id")
    except Exception:
        pass
    return None


def _get_crypto_profile(coin_id: str) -> dict:
    try:
        r = requests.get(
            f"https://api.coingecko.com/api/v3/coins/{coin_id}",
            params={
                "localization": "false", "tickers": "false", "market_data": "true",
                "community_data": "false", "developer_data": "false", "sparkline": "false",
            },
            timeout=10,
        )
        if r.status_code != 200:
            return {"ok": False, "error": f"CoinGecko error {r.status_code}"}
        data = r.json()
        md = data.get("market_data") or {}

        # La descripción de CoinGecko puede ser larga (varios párrafos) — nos
        # quedamos con el primero, que suele ser el resumen del proyecto, y
        # se traduce con el mismo motor que ya usáis para descripciones de
        # empresas (_translate_description, Groq) en vez de dejarla en inglés.
        desc_en   = (data.get("description") or {}).get("en", "") or ""
        desc_short = desc_en.split("\n\n")[0][:900].strip()
        desc_es   = _translate_description(desc_short) if desc_short else ""

        links     = data.get("links") or {}
        homepage  = next((h for h in (links.get("homepage") or []) if h), None)
        github_ls = (links.get("repos_url") or {}).get("github") or []

        return {
            "ok":                 True,
            "name":               data.get("name"),
            "symbol":             (data.get("symbol") or "").upper(),
            "categories":         [c for c in (data.get("categories") or []) if c],
            "description":        desc_es,
            "market_cap_rank":    data.get("market_cap_rank"),
            "circulating_supply": md.get("circulating_supply"),
            "total_supply":       md.get("total_supply"),
            "max_supply":         md.get("max_supply"),
            "ath":                (md.get("ath") or {}).get("usd"),
            "ath_change_pct":     (md.get("ath_change_percentage") or {}).get("usd"),
            "ath_date":           ((md.get("ath_date") or {}).get("usd") or "")[:10],
            "atl":                (md.get("atl") or {}).get("usd"),
            "atl_change_pct":     (md.get("atl_change_percentage") or {}).get("usd"),
            "links": {
                "homepage":  homepage,
                "whitepaper": links.get("whitepaper") or None,
                "github":    github_ls[0] if github_ls else None,
                "subreddit": links.get("subreddit_url") or None,
                "twitter":   ("https://twitter.com/" + links["twitter_screen_name"]) if links.get("twitter_screen_name") else None,
            },
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _get_crypto_chart(coin_id: str, days: int = 365) -> list:
    """Histórico de precio diario vía CoinGecko (/coins/{id}/market_chart) —
    se usa para el gráfico en vez de TradingView porque TradingView solo
    tiene datos de las criptos listadas en el exchange concreto que le
    pidamos (Coinbase, Binance...), y muchas monedas más pequeñas no están en
    ninguno de ellos aunque sí tengan ficha en CoinGecko. Con esto el gráfico
    funciona para cualquier moneda que ya aparezca en el perfil temático,
    sin depender de en qué exchange cotice."""
    try:
        r = requests.get(
            f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart",
            params={"vs_currency": "usd", "days": str(days), "interval": "daily"},
            timeout=12,
        )
        if r.status_code != 200:
            return []
        prices = r.json().get("prices", [])
        out = []
        for ts_ms, price in prices:
            out.append({
                "date":  datetime.utcfromtimestamp(ts_ms / 1000).strftime('%Y-%m-%d'),
                "price": round(float(price), 6),
            })
        return out
    except Exception:
        return []


def _get_research_crypto(ticker: str) -> dict:
    from services.cache import cache, TTL
    yf_data = _get_yfinance(ticker)
    if not yf_data.get('ok'):
        return {"ok": False, "error": yf_data.get('error', 'Sin datos')}

    symbol  = ticker.replace("-USD", "").upper()
    coin_id = _resolve_coingecko_id(symbol)

    crypto_profile = _get_crypto_profile(coin_id) if coin_id else {"ok": False, "error": f"No se encontró {symbol} en CoinGecko"}
    crypto_chart   = _get_crypto_chart(coin_id) if coin_id else []

    result = {
        "ok":             True,
        "is_crypto":      True,
        "ticker":         yf_data['ticker'],
        "name":           (crypto_profile.get('name') if crypto_profile.get('ok') else None) or yf_data['name'] or ticker,
        "price":          yf_data['price'],
        "chg_pct":        yf_data['chg_pct'],
        "mktcap_fmt":     yf_data['mktcap_fmt'],
        "week52_high":    yf_data['week52_high'],
        "week52_low":     yf_data['week52_low'],
        "sparkline":      yf_data['sparkline'],
        "description":    crypto_profile.get('description', '') if crypto_profile.get('ok') else '',
        "crypto_profile": crypto_profile,
        "crypto_chart":   crypto_chart,
        "timestamp":      datetime.now().strftime('%H:%M:%S'),
    }
    cache.set(f"research:{ticker}", result, TTL["research"])
    return result


def get_research(ticker: str) -> dict:
    ticker = ticker.upper().strip()
    from services.cache import cache, TTL
    cached = cache.get(f"research:{ticker}")
    if cached: return cached

    # Cripto (convención de yfinance: sufijo -USD, p.ej. BTC-USD, ETH-USD) usa
    # una ruta completamente distinta — nada de lo fundamental de una acción
    # (Piotroski, insider trading, titularidad institucional, estado de
    # resultados, rating de analistas...) tiene sentido para una cripto, así
    # que ni se piden esos 10 fetches (antes se hacían igual y volvían vacíos).
    # En su lugar se trae un perfil temático de CoinGecko.
    if ticker.endswith('-USD'):
        return _get_research_crypto(ticker)

    with ThreadPoolExecutor(max_workers=10) as ex:
        f_yf      = ex.submit(_get_yfinance, ticker)
        f_fh      = ex.submit(_get_finnhub, ticker)
        f_av      = ex.submit(_get_alpha_vantage, ticker)
        f_analyst_chg = ex.submit(_get_finnhub_analyst_changes, ticker)
        f_insider = ex.submit(_get_insider_trading, ticker)
        f_short   = ex.submit(_get_short_interest, ticker)
        f_season  = ex.submit(_get_seasonality, ticker)
        f_ratings = ex.submit(_get_analyst_ratings_history, ticker)
        f_piotro  = ex.submit(_get_piotroski_score, ticker)
        f_inst    = ex.submit(_get_institutional_ownership, ticker)
        f_tech    = ex.submit(_get_technical_levels, ticker)
        f_income  = ex.submit(_get_income_statement, ticker)
        f_turnover = ex.submit(get_turnover_comparison, ticker)
        f_absorption = ex.submit(get_absorption_signal, ticker)
        yf_data   = f_yf.result()
        fh_data   = f_fh.result()
        av_data   = f_av.result()
        analyst_chg_data = f_analyst_chg.result()
        insider   = f_insider.result()
        short     = f_short.result()
        season    = f_season.result()
        ratings_history = f_ratings.result()
        piotroski = f_piotro.result()
        instit    = f_inst.result()
        technical = f_tech.result()
        income_stmt = f_income.result()
        turnover  = f_turnover.result()
        absorption = f_absorption.result()

    if not yf_data.get('ok'):
        return {"ok": False, "error": yf_data.get('error', 'Sin datos')}

    sector_comparison = _get_sector_comparison(yf_data['sector'], yf_data['metrics'], yf_data['profitability'])

    # Fuerza relativa requiere el sector (de yf_data, ya resuelto), por eso se
    # calcula después — son solo 2-3 descargas de histórico de precio
    # (ticker, SPY, ETF del sector).
    relative_strength = _get_relative_strength(ticker, yf_data['sector'], yf_data['industry'])

    suggestions = _generate_suggestions(yf_data)
    rsu_score   = _compute_rsu_score(yf_data, piotroski, sector_comparison, insider.get("summary"), technical)

    result = {
        "ok":                 True,
        "ticker":             yf_data['ticker'],
        "name":               yf_data['name'],
        "sector":             yf_data['sector'],
        "industry":           yf_data['industry'],
        "country":            yf_data['country'],
        "website":            yf_data['website'],
        "description":        _translate_description(yf_data['description']),
        "turnover":           turnover,
        "absorption":         absorption,
        "price":              yf_data['price'],
        "chg_pct":            yf_data['chg_pct'],
        "mktcap_fmt":         yf_data['mktcap_fmt'],
        "week52_high":        yf_data['week52_high'],
        "week52_low":         yf_data['week52_low'],
        "beta":               yf_data['beta'],
        "dividend_yield":     yf_data['dividend_yield'],
        "n_analysts":         yf_data['n_analysts'],
        "recommendations":    yf_data['recommendations'],
        "recommendations_trend": yf_data['recommendations_trend'],
        "target_data":        yf_data['target_data'],
        "metrics":            yf_data['metrics'],
        "profitability":      yf_data['profitability'],
        "sparkline":          yf_data['sparkline'],
        "news":               fh_data.get('news', []),
        "sentiment":          fh_data.get('sentiment', {}),
        "quarterly_earnings": av_data.get('quarterly_earnings', []),
        "suggestions":        suggestions,
        "rsu_score":          rsu_score,
        "piotroski":          piotroski,
        "institutional":      instit,
        "analyst_changes":    analyst_chg_data,
        "ratings_history":    ratings_history,
        "insider_trading":    insider.get("transactions", []),
        "insider_summary":    insider.get("summary"),
        "insider_monthly_volume": insider.get("monthly_volume", []),
        "income_statement":   income_stmt,
        "short_interest":     short,
        "seasonality":        season,
        "next_earnings":      _get_next_earnings(ticker),
        "technical_levels":   technical,
        "sector_comparison":  sector_comparison,
        "relative_strength":  relative_strength,
        "timestamp":          datetime.now().strftime('%H:%M:%S'),
    }
    cache.set(f"research:{ticker}", result, TTL["research"])
    return result
# ── COMPARATIVA SECTORIAL (valoración, rentabilidad, crecimiento vs sector) ────

# Medianas sectoriales de referencia. Basadas en rangos históricos típicos del
# mercado US por sector (categorías tal como las devuelve yfinance en info['sector']).
# Se usan como benchmark relativo, no como datos de un proveedor en tiempo real,
# para poder colorear cada métrica como favorable/desfavorable frente a su sector.
SECTOR_BENCHMARKS = {
    "Technology": {
        "trailing_pe": 28.0, "forward_pe": 24.0, "price_to_sales": 6.5, "ev_ebitda": 18.0,
        "peg_ratio": 1.8, "price_to_book": 7.0,
        "roe": 0.22, "roa": 0.10, "net_margin": 0.18, "op_margin": 0.22, "gross_margin": 0.55,
        "revenue_growth": 0.12, "earnings_growth": 0.14, "debt_to_equity": 60.0,
    },
    "Financial Services": {
        "trailing_pe": 13.0, "forward_pe": 11.5, "price_to_sales": 3.0, "ev_ebitda": 12.0,
        "peg_ratio": 1.3, "price_to_book": 1.4,
        "roe": 0.13, "roa": 0.012, "net_margin": 0.22, "op_margin": 0.30, "gross_margin": 0.65,
        "revenue_growth": 0.06, "earnings_growth": 0.08, "debt_to_equity": 150.0,
    },
    "Healthcare": {
        "trailing_pe": 22.0, "forward_pe": 18.0, "price_to_sales": 4.0, "ev_ebitda": 15.0,
        "peg_ratio": 1.7, "price_to_book": 4.5,
        "roe": 0.16, "roa": 0.07, "net_margin": 0.12, "op_margin": 0.16, "gross_margin": 0.60,
        "revenue_growth": 0.08, "earnings_growth": 0.10, "debt_to_equity": 70.0,
    },
    "Consumer Cyclical": {
        "trailing_pe": 20.0, "forward_pe": 17.0, "price_to_sales": 1.8, "ev_ebitda": 12.0,
        "peg_ratio": 1.6, "price_to_book": 5.0,
        "roe": 0.18, "roa": 0.06, "net_margin": 0.07, "op_margin": 0.09, "gross_margin": 0.35,
        "revenue_growth": 0.07, "earnings_growth": 0.10, "debt_to_equity": 90.0,
    },
    "Consumer Defensive": {
        "trailing_pe": 21.0, "forward_pe": 19.0, "price_to_sales": 1.5, "ev_ebitda": 13.0,
        "peg_ratio": 2.2, "price_to_book": 5.5,
        "roe": 0.20, "roa": 0.07, "net_margin": 0.07, "op_margin": 0.11, "gross_margin": 0.34,
        "revenue_growth": 0.04, "earnings_growth": 0.06, "debt_to_equity": 90.0,
    },
    "Industrials": {
        "trailing_pe": 21.0, "forward_pe": 18.5, "price_to_sales": 2.0, "ev_ebitda": 13.5,
        "peg_ratio": 1.8, "price_to_book": 4.5,
        "roe": 0.17, "roa": 0.06, "net_margin": 0.08, "op_margin": 0.12, "gross_margin": 0.30,
        "revenue_growth": 0.06, "earnings_growth": 0.09, "debt_to_equity": 80.0,
    },
    "Energy": {
        "trailing_pe": 11.0, "forward_pe": 10.5, "price_to_sales": 1.1, "ev_ebitda": 5.5,
        "peg_ratio": 1.2, "price_to_book": 1.8,
        "roe": 0.14, "roa": 0.07, "net_margin": 0.09, "op_margin": 0.13, "gross_margin": 0.35,
        "revenue_growth": 0.03, "earnings_growth": 0.05, "debt_to_equity": 45.0,
    },
    "Basic Materials": {
        "trailing_pe": 16.0, "forward_pe": 14.0, "price_to_sales": 1.4, "ev_ebitda": 8.5,
        "peg_ratio": 1.4, "price_to_book": 2.2,
        "roe": 0.14, "roa": 0.06, "net_margin": 0.08, "op_margin": 0.13, "gross_margin": 0.30,
        "revenue_growth": 0.04, "earnings_growth": 0.07, "debt_to_equity": 55.0,
    },
    "Utilities": {
        "trailing_pe": 18.0, "forward_pe": 17.0, "price_to_sales": 2.2, "ev_ebitda": 11.0,
        "peg_ratio": 3.0, "price_to_book": 2.0,
        "roe": 0.10, "roa": 0.03, "net_margin": 0.11, "op_margin": 0.20, "gross_margin": 0.40,
        "revenue_growth": 0.03, "earnings_growth": 0.05, "debt_to_equity": 140.0,
    },
    "Real Estate": {
        "trailing_pe": 35.0, "forward_pe": 30.0, "price_to_sales": 6.0, "ev_ebitda": 16.0,
        "peg_ratio": 2.5, "price_to_book": 2.2,
        "roe": 0.07, "roa": 0.03, "net_margin": 0.20, "op_margin": 0.35, "gross_margin": 0.55,
        "revenue_growth": 0.04, "earnings_growth": 0.05, "debt_to_equity": 110.0,
    },
    "Communication Services": {
        "trailing_pe": 19.0, "forward_pe": 17.0, "price_to_sales": 3.5, "ev_ebitda": 11.0,
        "peg_ratio": 1.5, "price_to_book": 3.5,
        "roe": 0.15, "roa": 0.06, "net_margin": 0.13, "op_margin": 0.18, "gross_margin": 0.55,
        "revenue_growth": 0.06, "earnings_growth": 0.09, "debt_to_equity": 85.0,
    },
}

# Para cada métrica, ¿un valor MÁS ALTO es mejor (True) o MÁS BAJO es mejor (False)?
# Esto determina si comparado con el sector el color es verde u rojo.
METRIC_HIGHER_IS_BETTER = {
    "trailing_pe":     False,  # más barato = mejor
    "forward_pe":      False,
    "price_to_sales":  False,
    "ev_ebitda":       False,
    "peg_ratio":       False,
    "price_to_book":   False,
    "debt_to_equity":  False,  # menos deuda = mejor
    "roe":             True,
    "roa":             True,
    "net_margin":      True,
    "op_margin":       True,
    "gross_margin":    True,
    "revenue_growth":  True,
    "earnings_growth": True,
}

def _get_sector_comparison(sector: str, metrics: dict, profitability: dict) -> dict:
    """
    Compara cada métrica de valoración/rentabilidad/crecimiento contra la
    mediana de referencia de su sector. Devuelve, por métrica, el valor del
    benchmark y si la empresa está por encima o por debajo (favorable/desfavorable).
    No sustituye ningún dato existente — es información adicional.
    """
    bench = SECTOR_BENCHMARKS.get(sector)
    if not bench:
        return {"ok": False, "sector": sector, "items": {}}

    combined = {**metrics, **profitability}
    items = {}
    for key, bench_val in bench.items():
        val = combined.get(key)
        if val is None or bench_val is None:
            continue
        higher_is_better = METRIC_HIGHER_IS_BETTER.get(key, True)
        diff_pct = round((val - bench_val) / abs(bench_val) * 100, 1) if bench_val else None
        is_favorable = (val >= bench_val) if higher_is_better else (val <= bench_val)
        items[key] = {
            "value":        round(val, 4) if isinstance(val, float) else val,
            "sector_avg":   bench_val,
            "diff_pct":     diff_pct,
            "favorable":    is_favorable,
        }

    return {"ok": True, "sector": sector, "items": items}