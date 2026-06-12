import yfinance as yf
import requests
import numpy as np
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from config import settings

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

        # Métricas
        metrics = {
            "trailing_pe":    _safe(info.get('trailingPE')),
            "forward_pe":     _safe(info.get('forwardPE')),
            "price_to_sales": _safe(info.get('priceToSalesTrailing12Months')),
            "ev_ebitda":      _safe(info.get('enterpriseToEbitda')),
            "peg_ratio":      _safe(info.get('pegRatio')),
            "price_to_book":  _safe(info.get('priceToBook')),
        }

        profitability = {
            "roe":             _safe(info.get('returnOnEquity')),
            "roa":             _safe(info.get('returnOnAssets')),
            "net_margin":      _safe(info.get('profitMargins')),
            "op_margin":       _safe(info.get('operatingMargins')),
            "gross_margin":    _safe(info.get('grossMargins')),
            "revenue_growth":  _safe(info.get('revenueGrowth')),
            "earnings_growth": _safe(info.get('earningsGrowth')),
            "debt_to_equity":  _safe(info.get('debtToEquity')),
            "free_cashflow":   _safe(info.get('freeCashflow')),
            "current_ratio":   _safe(info.get('currentRatio')),
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
            "beta":        _safe(info.get('beta')),
            "dividend_yield": _safe(info.get('dividendYield')),
            "dividend_rate":  _safe(info.get('dividendRate')),
            "n_analysts":  _safe(info.get('numberOfAnalystOpinions')),
            "recommendations": recommendations,
            "target_data":    target_data,
            "metrics":        metrics,
            "profitability":  profitability,
            "sparkline":      sparkline,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}

def _get_finnhub(ticker: str) -> dict:
    key = settings.finnhub_api_key
    if not key:
        return {}
    try:
        session = requests.Session()
        session.headers.update({"X-Finnhub-Token": key})

        news, sentiment = [], {}
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            from datetime import timedelta
            week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
            r = session.get(
                f"https://finnhub.io/api/v1/company-news",
                params={"symbol": ticker, "from": week_ago, "to": today},
                timeout=8
            )
            if r.status_code == 200:
                items = r.json()[:8]
                news  = [{"headline": n.get('headline',''), "source": n.get('source',''),
                           "url": n.get('url',''), "datetime": n.get('datetime',0)} for n in items]
        except Exception: pass

        try:
            r = session.get(f"https://finnhub.io/api/v1/news-sentiment",
                            params={"symbol": ticker}, timeout=8)
            if r.status_code == 200:
                d = r.json()
                sentiment = {
                    "score":    _safe(d.get('companyNewsScore')),
                    "bullish":  _safe(d.get('sentiment',{}).get('bullishPercent')),
                    "bearish":  _safe(d.get('sentiment',{}).get('bearishPercent')),
                }
        except Exception: pass

        return {"news": news, "sentiment": sentiment}
    except Exception:
        return {}

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

def _compute_rsu_score(yf_data: dict) -> dict:
    score    = 0
    max_score = 100
    breakdown = []
    metrics  = yf_data.get('metrics', {})
    prof     = yf_data.get('profitability', {})
    recs     = yf_data.get('recommendations')
    target   = yf_data.get('target_data', {})

    # Crecimiento ingresos (20pts)
    rg = prof.get('revenue_growth')
    if rg is not None:
        pts = 20 if rg > 0.25 else 15 if rg > 0.15 else 10 if rg > 0.05 else 0
        score += pts
        breakdown.append({"label": "Crecimiento Ingresos", "pts": pts, "max": 20, "val": f"{rg*100:.1f}%"})

    # ROE (20pts)
    roe = prof.get('roe')
    if roe is not None:
        pts = 20 if roe > 0.25 else 15 if roe > 0.15 else 10 if roe > 0.08 else 0
        score += pts
        breakdown.append({"label": "ROE", "pts": pts, "max": 20, "val": f"{roe*100:.1f}%"})

    # Margen neto (20pts)
    nm = prof.get('net_margin')
    if nm is not None:
        pts = 20 if nm > 0.20 else 15 if nm > 0.10 else 10 if nm > 0.02 else 0
        score += pts
        breakdown.append({"label": "Margen Neto", "pts": pts, "max": 20, "val": f"{nm*100:.1f}%"})

    # Consenso analistas (20pts)
    if recs and recs['total'] > 0:
        buy_pct = (recs['strong_buy'] + recs['buy']) / recs['total'] * 100
        pts = 20 if buy_pct >= 75 else 15 if buy_pct >= 60 else 10 if buy_pct >= 40 else 0
        score += pts
        breakdown.append({"label": "Consenso Analistas", "pts": pts, "max": 20, "val": f"{buy_pct:.0f}% alcistas"})

    # Potencial precio objetivo (20pts)
    upside = target.get('upside')
    if upside is not None:
        pts = 20 if upside > 25 else 15 if upside > 15 else 10 if upside > 5 else 0
        score += pts
        breakdown.append({"label": "Potencial P.Objetivo", "pts": pts, "max": 20, "val": f"{upside:+.1f}%"})

    color = "#00ffad" if score >= 70 else "#ffb800" if score >= 50 else "#f23645"
    label = "COMPRA FUERTE" if score >= 80 else "COMPRA" if score >= 65 else "NEUTRAL" if score >= 50 else "PRECAUCIÓN" if score >= 35 else "EVITAR"

    return {"score": score, "max": max_score, "color": color, "label": label, "breakdown": breakdown}

def get_research(ticker: str) -> dict:
    ticker = ticker.upper().strip()
    with ThreadPoolExecutor(max_workers=3) as ex:
        f_yf  = ex.submit(_get_yfinance, ticker)
        f_fh  = ex.submit(_get_finnhub, ticker)
        f_av  = ex.submit(_get_alpha_vantage, ticker)
        yf_data = f_yf.result()
        fh_data = f_fh.result()
        av_data = f_av.result()

    if not yf_data.get('ok'):
        return {"ok": False, "error": yf_data.get('error', 'Sin datos')}

    suggestions = _generate_suggestions(yf_data)
    rsu_score   = _compute_rsu_score(yf_data)

    return {
        "ok":          True,
        "ticker":      yf_data['ticker'],
        "name":        yf_data['name'],
        "sector":      yf_data['sector'],
        "industry":    yf_data['industry'],
        "country":     yf_data['country'],
        "website":     yf_data['website'],
        "description": yf_data['description'],
        "price":       yf_data['price'],
        "chg_pct":     yf_data['chg_pct'],
        "mktcap_fmt":  yf_data['mktcap_fmt'],
        "week52_high": yf_data['week52_high'],
        "week52_low":  yf_data['week52_low'],
        "beta":        yf_data['beta'],
        "dividend_yield": yf_data['dividend_yield'],
        "n_analysts":  yf_data['n_analysts'],
        "recommendations": yf_data['recommendations'],
        "target_data":     yf_data['target_data'],
        "metrics":         yf_data['metrics'],
        "profitability":   yf_data['profitability'],
        "sparkline":       yf_data['sparkline'],
        "news":            fh_data.get('news', []),
        "sentiment":       fh_data.get('sentiment', {}),
        "quarterly_earnings": av_data.get('quarterly_earnings', []),
        "suggestions":     suggestions,
        "rsu_score":       rsu_score,
        "timestamp":       datetime.now().strftime('%H:%M:%S'),
    }