"""
CAN SLIM Service — RSU Terminal
Universo: S&P 500 completo (ver shared/sp500_universe.py -- fuente única, sesión 19)
Fixes: NaN sanitization, RS real percentile, N+I criteria, Market widget
"""
from services.gist_client import cabeceras_gist
import json
import requests
import pandas as pd
import numpy as np
import yfinance as yf
import math
from datetime import datetime, timedelta
from concurrent.futures import as_completed
import warnings
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "shared"))
from time_utils import get_timestamp  # noqa: E402
from sp500_universe import SP500_SECTOR_MAP  # noqa: E402
from market_regime import spy_trend_snapshot  # noqa: E402
from canslim_engine import (  # noqa: E402
    perf_12m as _perf_12m,
    acc_dis_rating as _acc_dis_rating,
    trend_template as _trend_template,
    technical_score as _technical_score,
    NEAR_HIGH_PCT,
)
from services.cache import cache, TTL  # noqa: E402
warnings.filterwarnings('ignore')

# ── S&P 500 UNIVERSE ──────────────────────────────────────────────────────────
# Antes: lista propia hardcodeada, desactualizada (~30% de discrepancia
# contra el S&P500 real, ver sesión 19). Ahora deriva de la fuente única.

SP500_TICKERS = list(SP500_SECTOR_MAP.keys())

# ── SANITIZE NaN ──────────────────────────────────────────────────────────────

def _sanitize(obj):
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize(v) for v in obj]
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    return obj

def _safe(val, default=0.0):
    try:
        v = float(val)
        return v if not math.isnan(v) and not math.isinf(v) else default
    except Exception:
        return default

# ── IBD RATINGS ───────────────────────────────────────────────────────────────
# _perf_12m/_acc_dis_rating -- ver shared/canslim_engine.py (sesión 32,
# promovidas para compartirlas con scripts/canslim_scan.py, el scan nocturno).

def _rs_rating_real(perf_12m: float, universe_perfs: list):
    """RS real: percentil en el universo escaneado. Sin universo de
    referencia no hay percentil que calcular -- None, no una aproximación
    (antes `50 + perf_12m/2`) con la misma forma que un percentil real."""
    if not universe_perfs:
        return None
    rank = sum(1 for p in universe_perfs if p < perf_12m)
    return max(1, min(99, int(rank / len(universe_perfs) * 99) + 1))

def _eps_rating(eps_growth_q: float) -> int:
    if eps_growth_q >= 100: return 99
    if eps_growth_q >= 50:  return 90
    if eps_growth_q >= 25:  return 80
    if eps_growth_q >= 15:  return 70
    if eps_growth_q >= 5:   return 60
    if eps_growth_q >= 0:   return 50
    return 30

def _smr_rating(sales_g: float, roe: float, margins: float) -> str:
    score = 0
    if sales_g >= 25:   score += 3
    elif sales_g >= 15: score += 2
    elif sales_g >= 5:  score += 1
    if roe >= 20:       score += 3
    elif roe >= 15:     score += 2
    elif roe >= 10:     score += 1
    if margins >= 15:   score += 2
    elif margins >= 5:  score += 1
    if score >= 7: return 'A'
    if score >= 5: return 'B'
    if score >= 3: return 'C'
    if score >= 1: return 'D'
    return 'E'

def _registrar_scan_para_track_record(data: dict) -> None:
    """Guarda el universo del scan nocturno en canslim_history.db, una sola
    vez por scan. La fecha sale de `generated_at` del propio Gist -- la
    fecha del SCAN, no la de ejecución del backend."""
    from services.canslim_tracking_service import registrar_scan, ya_registrado

    # La fecha de la SESIÓN, no la de ejecución. En un festivo de mercado el
    # scan corre igual y descarga la sesión anterior: fechar esas filas en el
    # festivo desplazaría una sesión todos los retornos del track record.
    # `generated_at` queda como respaldo para los Gists escritos antes de que
    # el scan publicara `ultima_sesion`. Ver RS/RW #6.
    fecha = (data.get("ultima_sesion") or data.get("generated_at") or "")[:10]
    if not fecha or ya_registrado(fecha):
        return
    res = registrar_scan(data.get("candidates", []), fecha)
    if res.get("insertados"):
        print(f"[CANSLIMTracking] Scan del {fecha} registrado: {res['insertados']} tickers")


def _marcar_cartera(filas: list) -> None:
    """Marca `en_cartera` en cada fila, in-place.

    Va DENTRO del servicio (y por tanto dentro de la caché) a propósito: la
    Cartera es única y global en esta aplicación, así que el mismo valor
    sirve para todos los usuarios. `in_watchlist`, en cambio, es por usuario
    y se calcula en el router DESPUÉS de la caché -- mezclarlo aquí filtraría
    la watchlist de un usuario a la respuesta que ve el siguiente. Mismo
    reparto que scanner.py, rsrw.py e insider.py (sesión 16).

    Falla en silencio a "ningún ticker en cartera": que la hoja de Cartera no
    responda no debe tumbar el scan de CANSLIM, que no depende de ella.
    """
    try:
        from services.cartera_service import get_cartera_tickers
        tickers = get_cartera_tickers()
    except Exception:
        tickers = set()
    for fila in filas:
        fila["en_cartera"] = fila.get("ticker") in tickers


# _trend_template() vivía aquí hasta el 01/08/2026. Se movió tal cual a
# shared/canslim_engine.py porque el scan usaba su propia versión de 3
# condiciones y la terminal se contradecía a sí misma: la tabla daba la
# tendencia por buena en tickers que suspendían la letra L al abrirlos.
# El porqué, con los números medidos, está en la cabecera de ese módulo.

# ── MARKET ANALYZER ───────────────────────────────────────────────────────────

def get_market_status() -> dict:
    """
    Análisis del mercado general (M en CAN SLIM).
    Usa SPY + VIX + amplitud para determinar el estado del mercado.

    Cacheado 10 min -- desde que analyze_ticker() también lo llama (para la
    letra M, ver hallazgo #2 de la auditoría CANSLIM 21/07/2026), analizar
    varios tickers seguidos ya no dispara 3 descargas (SPY/VIX/QQQ) extra
    por cada uno; el estado del mercado no cambia de un ticker a otro en la
    misma sesión de todas formas.
    """
    from services.cache import cache
    cached = cache.get("canslim:market_status")
    if cached:
        return cached
    try:
        # SPY
        spy = yf.Ticker("SPY")
        spy_hist = spy.history(period="1y")
        if spy_hist.empty:
            raise ValueError("Sin datos SPY")

        # Fuera las sesiones sin cierre antes de calcular NADA. La fila del día
        # en curso viene con Close=NaN, y `_safe()` lo convertía en 0.0 -- su
        # valor por defecto. Para un PRECIO, cero no es un respaldo prudente:
        # es un número imposible que envenena todo lo que se derive de él. El
        # 17/08/2026 dejó a SPY en "$0", con -100% en la variación del día, en
        # el 1M, en el 3M y en la distancia al máximo, y el score cayó a 20
        # anunciando "MERCADO EN CORRECCIÓN" cuando el índice estaba por encima
        # de sus dos medias. Reportado por el usuario, que vio que no cuadraba.
        spy_hist = spy_hist[spy_hist['Close'].notna()]
        if spy_hist.empty:
            raise ValueError("Sin ninguna sesión de SPY con cierre válido")

        spy_price  = _safe(spy_hist['Close'].iloc[-1])
        # iloc[-2] necesita DOS sesiones, no solo que el DataFrame no esté
        # vacío. Todas las líneas de alrededor ya llevan su `len(...) >= N`;
        # esta era la única que no, y con una sola sesión reventaría. Con SPY
        # a un año es inalcanzable en la práctica — se cierra por coherencia,
        # no por riesgo. Ver auditoría CANSLIM, hallazgo #15.
        spy_prev   = _safe(spy_hist['Close'].iloc[-2]) if len(spy_hist) >= 2 else 0.0
        spy_chg    = (spy_price - spy_prev) / spy_prev * 100 if spy_prev else 0
        spy_high52 = float(spy_hist['Close'].tail(252).max())
        spy_pct_from_high = (spy_price - spy_high52) / spy_high52 * 100

        # SMA50/SMA200 y sus "above" -- vía shared/market_regime.py, mismo
        # cálculo que ya usa market_service.py::get_market_breadth() (ver
        # auditoría CANSLIM 21/07/2026, hallazgo #10). Antes, con menos de
        # 200 sesiones, spy_ma200 se sustituía en silencio por spy_ma50
        # (sesgo optimista); ahora es None -- spy_above_ma200 también
        # queda None y sencillamente no suma los 20 puntos del score más
        # abajo (`if spy_above_ma200:` es falsy con None).
        snap = spy_trend_snapshot(spy_hist['Close'])
        spy_ma50, spy_ma200 = snap["sma50"], snap["sma200"]
        spy_above_ma50, spy_above_ma200 = snap["above_sma50"], snap["above_sma200"]

        spy_perf_3m  = _safe(((spy_price / spy_hist['Close'].iloc[-63]) - 1) * 100 if len(spy_hist) >= 63 else 0)
        spy_perf_1m  = _safe(((spy_price / spy_hist['Close'].iloc[-21]) - 1) * 100 if len(spy_hist) >= 21 else 0)
        spy_perf_1w  = _safe(((spy_price / spy_hist['Close'].iloc[-5])  - 1) * 100 if len(spy_hist) >= 5  else 0)

        # VIX
        vix_level = 0.0
        try:
            vix = yf.Ticker("^VIX")
            vix_hist = vix.history(period="5d")
            if not vix_hist.empty:
                vix_level = _safe(vix_hist['Close'].iloc[-1])
        except Exception:
            pass

        # QQQ para tech breadth
        qqq_above_ma50 = False
        try:
            qqq = yf.Ticker("QQQ")
            qqq_hist = qqq.history(period="100d")
            if not qqq_hist.empty:
                qqq_price  = _safe(qqq_hist['Close'].iloc[-1])
                qqq_ma50   = float(qqq_hist['Close'].tail(50).mean())
                qqq_above_ma50 = qqq_price > qqq_ma50
        except Exception:
            pass

        # Score del mercado 0-100
        score = 0
        if spy_above_ma50:   score += 25
        if spy_above_ma200:  score += 20
        if qqq_above_ma50:   score += 15
        if vix_level < 20:   score += 20
        elif vix_level < 30: score += 10
        if spy_perf_3m > 0:  score += 10
        if spy_perf_1m > 0:  score += 10

        # Estado del mercado
        if score >= 80:
            status = "CONFIRMED UPTREND"
            status_es = "TENDENCIA ALCISTA CONFIRMADA"
            color = "#00ffad"
            can_buy = True
        elif score >= 60:
            status = "UPTREND UNDER PRESSURE"
            status_es = "TENDENCIA ALCISTA BAJO PRESIÓN"
            color = "#ff9800"
            can_buy = True
        elif score >= 40:
            status = "RALLY ATTEMPT"
            status_es = "INTENTO DE RECUPERACIÓN"
            color = "#ffb800"
            can_buy = False
        elif score >= 20:
            status = "MARKET IN CORRECTION"
            status_es = "MERCADO EN CORRECCIÓN"
            color = "#f23645"
            can_buy = False
        else:
            status = "DISTRIBUTION PHASE"
            status_es = "FASE DE DISTRIBUCIÓN"
            color = "#f23645"
            can_buy = False

        result = _sanitize({
            "ok":            True,
            "status":        status,
            "status_es":     status_es,
            "score":         score,
            "color":         color,
            "can_buy":       can_buy,
            "spy": {
                "price":         round(spy_price, 2),
                "chg_pct":       round(spy_chg, 2),
                "above_ma50":    spy_above_ma50,
                "above_ma200":   spy_above_ma200,
                "ma50":          round(spy_ma50, 2),
                "ma200":         round(spy_ma200, 2) if spy_ma200 is not None else None,
                "pct_from_high": round(spy_pct_from_high, 1),
                "perf_1w":       round(spy_perf_1w, 2),
                "perf_1m":       round(spy_perf_1m, 2),
                "perf_3m":       round(spy_perf_3m, 2),
            },
            "vix":           round(vix_level, 2),
            "vix_risk":      "ALTO" if vix_level >= 30 else "MEDIO" if vix_level >= 20 else "BAJO",
            "timestamp":     get_timestamp(),
        })
        cache.set("canslim:market_status", result, 600)  # 10 min
        return result

    except Exception as e:
        return {"ok": False, "error": str(e)}  # sin cachear -- un fallo puntual no debe pegarse 10 min

# ── ANALYZE TICKER ────────────────────────────────────────────────────────────

def analyze_ticker(ticker: str, universe_perfs: list = None) -> dict:
    try:
        tk   = yf.Ticker(ticker.upper())
        hist = tk.history(period="2y")
        if len(hist) < 50:
            return {"ok": False, "error": "Histórico insuficiente"}

        info = {}
        try:
            info = tk.info or {}
        except Exception:
            pass

        price      = _safe(hist['Close'].iloc[-1])
        prev_close = _safe(hist['Close'].iloc[-2])
        chg_pct    = ((price - prev_close) / prev_close * 100) if prev_close else 0

        perf_12m = _perf_12m(hist)
        perf_6m  = _safe(((price / hist['Close'].iloc[-126]) - 1) * 100 if len(hist) >= 126 else 0)
        perf_3m  = _safe(((price / hist['Close'].iloc[-63])  - 1) * 100 if len(hist) >= 63  else 0)

        vol_today = _safe(hist['Volume'].iloc[-1])
        vol_avg   = _safe(hist['Volume'].tail(50).mean(), 1)
        vol_ratio = vol_today / vol_avg if vol_avg > 0 else 1.0

        # Fundamentales
        eps_g   = _safe(info.get('earningsGrowth',  0)) * 100
        sales_g = _safe(info.get('revenueGrowth',   0)) * 100
        roe     = _safe(info.get('returnOnEquity',  0)) * 100
        margins = _safe(info.get('profitMargins',   0)) * 100
        mktcap  = _safe(info.get('marketCap',       0))
        name    = str(info.get('shortName', ticker.upper()))
        sector  = str(info.get('sector',   'N/A'))
        industry= str(info.get('industry', 'N/A'))

        # ── Participación institucional real via major_holders ────────────────
        inst_pct        = 0.0
        inst_pct_source = "N/A"
        inst_holders    = []
        inst_data_ok    = False

        try:
            # Formato actual de yfinance (verificado con datos reales
            # 23/07/2026): major_holders es un DataFrame con índice
            # "Breakdown" (insidersPercentHeld, institutionsPercentHeld,
            # institutionsFloatPercentHeld, institutionsCount) y una única
            # columna "Value" -- los porcentajes vienen como FRACCIÓN
            # (0.665 = 66.5%), no como texto "66.50%". El parseo anterior
            # asumía el formato viejo (string con "%") y por eso nunca
            # multiplicaba por 100 -- guardaba 0.665 tal cual, un número
            # que SIEMPRE cae por debajo del umbral de 40, así que el
            # badge de sponsorship institucional salía rojo en el 100% de
            # los casos, sin importar la acción. Confirmado contra AAPL
            # (66.5%), JPM (76.1%), XOM (68.4%), TXN (94.7%) reales.
            major = tk.major_holders
            if major is not None and not major.empty and 'institutionsPercentHeld' in major.index:
                raw = _safe(major.loc['institutionsPercentHeld', 'Value'])
                if raw > 0:
                    inst_pct        = raw * 100
                    inst_pct_source = "major_holders"
                    inst_data_ok    = True
        except Exception:
            pass

        # Fallback: info['heldPercentInstitutions'] -- el nombre de campo
        # viejo, "institutionPercentHeld", ya no existe en la API actual
        # de yfinance (siempre devuelve None); el campo real hoy es
        # "heldPercentInstitutions", verificado igual que arriba.
        if not inst_data_ok:
            raw = _safe(info.get('heldPercentInstitutions', 0)) * 100
            if raw > 0:
                inst_pct        = raw
                inst_pct_source = "info"
                inst_data_ok    = True

        # Top holders institucionales
        try:
            holders_df = tk.institutional_holders
            if holders_df is not None and not holders_df.empty:
                for _, row in holders_df.head(5).iterrows():
                    holder_name = str(row.get('Holder', row.get('Name', 'N/A')))
                    shares      = _safe(row.get('Shares', 0))
                    pct_out     = _safe(row.get('% Out', row.get('pctHeld', 0))) * 100
                    inst_holders.append({
                        "name":    holder_name,
                        "shares":  int(shares),
                        "pct_out": round(pct_out, 2),
                    })
        except Exception:
            pass

        # ── RS rating ────────────────────────────────────────────────────────
        # Sin universo explícito: primero el scan nocturno (Gist, siempre
        # fresco, sesión 32 -- get_canslim_from_gist() ya deja
        # "canslim:universe_perfs" en caché al leer el Gist), si no hay
        # Gist configurado o falla, el caché de 10 min que deja
        # scan_canslim() on-demand (sesión 23) -- si ninguna de las dos
        # tiene datos, sigue sin universo y el RS Rating queda None
        # ("N/D"), igual que siempre.
        if universe_perfs is None:
            universe_perfs = cache.get("canslim:universe_perfs")
            if not universe_perfs:
                get_canslim_from_gist()
                universe_perfs = cache.get("canslim:universe_perfs") or []
        rs_r = _rs_rating_real(perf_12m, universe_perfs)

        # ── IBD Ratings ───────────────────────────────────────────────────────
        eps_r   = _eps_rating(eps_g)
        smr_r   = _smr_rating(sales_g, roe, margins)
        acc_dis = _acc_dis_rating(hist)
        trend   = _trend_template(hist, price)

        smr_num   = 100 if smr_r in ['A','B'] else 60 if smr_r == 'C' else 30
        acc_num   = 100 if acc_dis in ['A','B'] else 60 if acc_dis == 'C' else 30
        # rs_r puede ser None (sin universo de referencia -- ver
        # _rs_rating_real). Antes se rellenaba con una aproximación y
        # siempre se usaban los 4 pesos fijos; ahora, sin RS real, se
        # reescalan los 3 pesos restantes a base 100 en vez de tratar el
        # hueco como un 0 -- mismo patrón que ya usa fund_score más abajo.
        if rs_r is not None:
            composite = int(rs_r * 0.35 + eps_r * 0.30 + smr_num * 0.20 + acc_num * 0.15)
        else:
            composite = int((eps_r * 0.30 + smr_num * 0.20 + acc_num * 0.15) / 0.65)
        composite = max(1, min(99, composite))

        # ── CAN SLIM criteria ─────────────────────────────────────────────────
        pct_from_high    = trend['pct_from_high']
        near_new_high    = pct_from_high >= -15

        # I: sponsorship — solo penaliza si tenemos dato y es bajo
        # Si no hay dato (inst_data_ok=False), no penaliza
        inst_sponsorship = (inst_pct > 40) if inst_data_ok else None  # None = sin dato

        # M -- estado real del mercado (get_market_status(), cacheado 10 min),
        # no un True fijo. O'Neil consideraba esta la letra más importante:
        # ninguna compra debería hacerse con el mercado en corrección. None
        # (badge sin dato, mismo criterio que S/I arriba) solo si la propia
        # descarga de mercado falla. Ver auditoría CANSLIM 21/07/2026, #2.
        market = get_market_status()
        market_can_buy = market.get("can_buy") if market.get("ok") else None
        market_label   = market.get("status_es") if market.get("ok") else "sin datos"

        can_slim_letters = {
            "C — EPS crecimiento >25%":         bool(eps_g >= 25),
            # "revenueGrowth" de yfinance es crecimiento TRIMESTRAL interanual,
            # no anual -- la etiqueta decía "Ventas anuales" afirmando algo que
            # el dato no mide (CAN SLIM distingue C=trimestral de A=anual
            # sostenido a propósito). Renombrada para ser honesta con lo que
            # de verdad se calcula, sin inventar un cálculo anual nuevo. Ver
            # auditoría CANSLIM 21/07/2026, hallazgo #8.
            "A — Crecimiento de ventas >25%":    bool(sales_g >= 25),
            "N — Near new high (<15% del máx)":  bool(near_new_high),
            "S — RS Rating >80":                 bool(rs_r >= 80) if rs_r is not None else None,
            "L — Leader (Trend Template)":       bool(trend['passed']),
            "I — Sponsorship institucional":     bool(inst_sponsorship) if inst_sponsorship is not None else None,
            f"M — Mercado: {market_label}":      market_can_buy,
        }

        # ── Por qué cumple o falla cada letra ────────────────────────────────
        # Hasta el 01/08/2026 el badge de cada letra solo llevaba el criterio
        # en el `title`: se veía una "A" en rojo sin saber si había fallado
        # por un 24% (a un punto) o por un -3% (a años luz). El backend ya
        # tenía todos estos números calculados; solo faltaba enseñarlos. Ver
        # auditoría CANSLIM, hallazgo #21.
        #
        # `valor: None` significa SIN DATO, que no es lo mismo que incumplir
        # -- el frontend lo pinta distinto. Se usan los mismos umbrales de
        # `abs(x) > 0.1` que ya emplea el score fundamental para decidir si
        # yfinance trajo el campo o devolvió un cero por defecto.
        def _pct(v):
            return f"{v:+.1f}%"

        can_slim_detalle = [
            {"letra": "C", "criterio": "Crecimiento de EPS",
             "objetivo": "> 25%", "cumple": bool(eps_g >= 25),
             "valor": _pct(eps_g) if abs(eps_g) > 0.1 else None},
            {"letra": "A", "criterio": "Crecimiento de ventas",
             "objetivo": "> 25%", "cumple": bool(sales_g >= 25),
             "valor": _pct(sales_g) if abs(sales_g) > 0.1 else None},
            {"letra": "N", "criterio": "Distancia al máximo de 52 semanas",
             "objetivo": "dentro del 15%", "cumple": bool(near_new_high),
             "valor": _pct(pct_from_high)},
            {"letra": "S", "criterio": "RS Rating (percentil vs universo)",
             "objetivo": "> 80", "cumple": bool(rs_r >= 80) if rs_r is not None else None,
             "valor": str(rs_r) if rs_r is not None else None},
            {"letra": "L", "criterio": "Trend Template de Minervini",
             "objetivo": "5 de 7 condiciones", "cumple": bool(trend['passed']),
             "valor": f"{trend['score']}/7"},
            {"letra": "I", "criterio": "Participación institucional",
             "objetivo": "> 40%", "cumple": bool(inst_sponsorship) if inst_sponsorship is not None else None,
             "valor": f"{inst_pct:.1f}%" if inst_data_ok else None},
            {"letra": "M", "criterio": "Estado del mercado general",
             "objetivo": "permite comprar", "cumple": market_can_buy,
             "valor": market_label if market.get("ok") else None},
        ]

        # ── Score técnico (lo que puede evaluar sin fundamentales) ───────────
        # La fórmula vive en shared/canslim_engine.py desde el 01/08/2026:
        # el scan usaba antes otra distinta, con otros pesos y contando
        # perf_12m dos veces. Aquí el resultado no cambia -- es un traslado
        # literal, y el reescalado proporcional cuando falta el RS sigue
        # siendo el mismo criterio que usa fund_score justo debajo.
        tech_score = _technical_score(rs_r, trend['passed'], trend['score'],
                                      acc_dis, near_new_high, vol_ratio)

        # ── Score fundamental ─────────────────────────────────────────────────
        # Sin dato → no penaliza (tratado como ausente, no como "0% malo").
        # ROE y Márgenes antes NO comprobaban esto (a diferencia de EPS y
        # Sales, que sí) -- un ticker sin dato de ROE en yfinance (frecuente
        # fuera de EE.UU. o en salidas a bolsa recientes) se puntuaba como
        # 0% de ROE real, la peor nota posible, en vez de excluirse del
        # cálculo. Ver conversación 19/07/2026.
        eps_has_data     = abs(eps_g)   > 0.1
        sales_has_data   = abs(sales_g) > 0.1
        roe_has_data     = abs(roe)     > 0.1
        margins_has_data = abs(margins) > 0.1

        sub_scores  = []
        max_posible = 0
        if eps_has_data:
            sub_scores.append(30 if eps_g >= 25 else (15 if eps_g >= 10 else 0))
            max_posible += 30
        if sales_has_data:
            sub_scores.append(30 if sales_g >= 25 else (15 if sales_g >= 10 else 0))
            max_posible += 30
        if roe_has_data:
            sub_scores.append(20 if roe >= 15 else (10 if roe >= 8 else 0))
            max_posible += 20
        if margins_has_data:
            sub_scores.append(20 if margins >= 10 else (10 if margins >= 3 else 0))
            max_posible += 20

        # Reescalado a /100 proporcional a las submétricas realmente
        # disponibles -- mismo patrón que usa el RSU Score de Research
        # cuando faltan categorías enteras.
        fund_score = int(sum(sub_scores) / max_posible * 100) if max_posible > 0 else 0
        fund_score = min(100, fund_score)

        # Si no hay NINGÚN dato fundamental, marcar como sin dato
        fund_data_available = len(sub_scores) > 0

        # Qué componentes han entrado DE VERDAD en el score. La etiqueta del
        # frontend prometía siempre "(EPS + Sales + ROE + Margin)" aunque
        # alguno se hubiera excluido por falta de dato — caso real de VTRS,
        # que no tiene EPS y aun así anunciaba los cuatro. Se manda la lista
        # desde aquí en vez de re-deducirla en el frontend: la regla de
        # "¿hay dato?" tiene que vivir en un solo sitio.
        fund_componentes = [
            etiqueta for etiqueta, hay in (
                ("EPS", eps_has_data), ("Sales", sales_has_data),
                ("ROE", roe_has_data), ("Margin", margins_has_data),
            ) if hay
        ]

        # Score CAN SLIM unificado (60% técnico + 40% fundamental)
        # Si no hay fundamentales, usar solo técnico con disclaimer
        if fund_data_available:
            canslim_score = int(tech_score * 0.60 + fund_score * 0.40)
        else:
            canslim_score = int(tech_score * 0.80)  # sin fundamentales, reducido

        canslim_score = max(0, min(100, canslim_score))

        # ── Chart ─────────────────────────────────────────────────────────────
        hist60     = hist.tail(60)
        closes_60  = [round(_safe(c), 2) for c in hist60['Close'].tolist()]
        dates_60   = [d.strftime('%Y-%m-%d') for d in hist60.index.tolist()]
        ma50_line  = []
        ma200_line = []
        for i in range(len(hist60)):
            idx = len(hist) - len(hist60) + i
            slice50  = hist['Close'].iloc[max(0, idx-49):idx+1]
            slice200 = hist['Close'].iloc[max(0, idx-199):idx+1]
            ma50_line.append(round(float(slice50.mean()), 2) if len(slice50) >= 10 else None)
            ma200_line.append(round(float(slice200.mean()), 2) if len(slice200) >= 50 else None)

        # en_cartera aquí es seguro aunque analyze_ticker() no cachee hoy: la
        # Cartera es global, no cambia entre usuarios (ver _marcar_cartera).
        resultado = {
            "ok":        True,
            "ticker":    ticker.upper(),
            "name":      name,
            "sector":    sector,
            "industry":  industry,
            "price":     round(price, 2),
            "chg_pct":   round(chg_pct, 2),
            "mktcap":    mktcap,
            "perf": {
                "3m":  round(perf_3m, 2),
                "6m":  round(perf_6m, 2),
                "12m": round(perf_12m, 2),
            },
            "ibd": {
                "rs":        rs_r,
                "eps":       eps_r,
                "composite": composite,
                "smr":       smr_r,
                "acc_dis":   acc_dis,
            },
            "fundamentals": {
                "eps_growth":        round(eps_g, 2),
                "sales_growth":      round(sales_g, 2),
                "roe":               round(roe, 2),
                "margins":           round(margins, 2),
                "inst_pct":          round(inst_pct, 1),
                "inst_pct_source":   inst_pct_source,
                "inst_data_ok":      inst_data_ok,
                "inst_holders":      inst_holders,
                "fund_data_available": fund_data_available,
            },
            "volume": {
                "today": int(vol_today),
                "avg":   int(vol_avg),
                "ratio": round(vol_ratio, 2),
            },
            "scores": {
                "tech":         tech_score,
                "fundamental":  fund_score,
                "combined":     canslim_score,
                "fund_available": fund_data_available,
                # Componentes que de verdad entraron en fund_score, para que
                # la etiqueta no prometa más de lo que midió.
                "fund_componentes": fund_componentes,
            },
            "trend":            trend,
            "can_slim_letters": can_slim_letters,
            "can_slim_detalle": can_slim_detalle,
            "canslim_score":    canslim_score,
            "near_new_high":    near_new_high,
            "pct_from_high":    round(pct_from_high, 1),
            "chart": {
                "dates":   dates_60,
                "closes":  closes_60,
                "ma50":    ma50_line,
                "ma200":   ma200_line,
            },
            "timestamp": get_timestamp(),
        }
        _marcar_cartera([resultado])
        return _sanitize(resultado)

    except Exception as e:
        # El traceback completo va al log del servidor, nunca a la respuesta
        # -- antes se devolvía en "detail", exponiendo rutas del sistema de
        # ficheros y estructura interna a cualquier usuario autenticado (el
        # frontend nunca lo leía, era pura exposición sin uso). Ver auditoría
        # CANSLIM 21/07/2026, hallazgo #9.
        import traceback
        print(f"[CANSLIM] Error en analyze_ticker({ticker!r}): {type(e).__name__}: {e}")
        print(traceback.format_exc())
        return {"ok": False, "error": str(e)}

# ── SCAN NOCTURNO (GIST) ──────────────────────────────────────────────────────
# scripts/canslim_scan.py corre 1x/día (L-V) vía GitHub Actions y sube el
# resultado aquí -- mismo patrón que rsrw_service.py::_load_gist() (sesión
# 32). El ID es público (solo el token de escritura es secreto) -- rellenar
# tras crear el Gist la primera vez.
CANSLIM_GIST_ID   = "5925708e930b8074e753d353bcdd4bc9"
CANSLIM_GIST_FILE = "canslim_scan.json"


def _load_canslim_gist() -> dict | None:
    if not CANSLIM_GIST_ID:
        return None
    try:
        r = requests.get(
            f"https://api.github.com/gists/{CANSLIM_GIST_ID}",
            timeout=10,
            headers=cabeceras_gist(),
        )
        r.raise_for_status()
        content = r.json()["files"][CANSLIM_GIST_FILE]["content"]
        data    = json.loads(content)
        return data if data.get("candidates") else None
    except Exception:
        return None


def get_canslim_from_gist() -> dict:
    """Lee el scan nocturno ya calculado -- reemplaza a scan_canslim() como
    camino principal del frontend (mismo criterio que
    rsrw_service.py::get_rsrw_from_gist(), sesión 32). Sin Gist configurado
    o sin datos todavía, cae a un resultado vacío honesto (ok:False), no a
    un scan on-demand automático -- si se quiere forzar un cálculo fresco,
    scan_canslim()/GET /api/v1/canslim/scan sigue disponible tal cual."""
    from services.cache import cache
    cache_key = "canslim:gist"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached


    data = _load_canslim_gist()
    if not data:
        result = {"ok": False, "error": "Scan nocturno no disponible todavía", "candidates": [], "timestamp": get_timestamp()}
    else:
        candidatos = data.get("candidates", [])
        _marcar_cartera(candidatos)
        result = {
            "ok":         True,
            "candidates": candidatos,
            "total":      data.get("total", len(candidatos)),
            "scanned":    data.get("scanned", 0),
            "timestamp":  get_timestamp(),
        }
        # El universo completo de percentiles se cachea aparte (10 min,
        # mismo TTL/clave que ya usaba scan_canslim() para
        # analyze_ticker() -- sesión 23) para no tener que releer el Gist
        # completo en cada análisis individual.
        perfs = data.get("perfs")
        if perfs:
            cache.set("canslim:universe_perfs", perfs, TTL["canslim"])

        # Registrar el scan para el track record (hallazgo #22). Se hace
        # aquí, en la lectura del Gist, y no con un bucle propio de 24h:
        # ese patrón ancla la hora a cuándo se reinició el contenedor -- el
        # mismo error que ya se corrigió en Options Flow (sesión 35). Aquí
        # la fecha del SCAN decide, así que da igual cuántas veces se llame.
        # En try/except propio: que el tracking falle no puede dejar sin
        # scanner a quien solo quería mirar la tabla.
        try:
            _registrar_scan_para_track_record(data)
        except Exception as e:
            print(f"[CANSLIMTracking] No se pudo registrar el scan: {type(e).__name__}: {e}")
    cache.set(cache_key, result, 600)  # 10 min -- el dato en sí solo cambia 1x/día
    return result


# ── SCANNER S&P 500 COMPLETO (on-demand, ya no es el camino principal del
# frontend -- se mantiene disponible, mismo criterio que
# rsrw_service.py::get_rsrw_scan()) ────────────────────────────────────────────

def _scan_single(ticker: str) -> dict | None:
    try:
        tk   = yf.Ticker(ticker)
        hist = tk.history(period="2y")  # antes "1y" -- necesario para iloc[-252] real, ver _perf_12m

        # Con el mercado ABIERTO, Yahoo devuelve la fila del día en curso con
        # Close=NaN (la sesión aún no ha cerrado). Como _safe() convierte NaN
        # en 0.0, `price` salía 0.0 y el `if price < 5` de abajo descartaba el
        # ticker EN SILENCIO -- y le pasaba a todos a la vez, así que el scan
        # se vaciaba entero durante toda la sesión sin ningún error. Mismo
        # patrón de fondo ya corregido en cartera_service._get_daily_bars()
        # (25/07/2026); aquí se limpia la fila una sola vez, al principio, en
        # vez de parchear cada uso: `price`, `perf_12m`, `vol_today` y
        # `acc_dis_rating` leen todos iloc[-1] y se arreglan de golpe.
        #
        # Para un screener basado en cierres (medias de 50/150/200, RS a 12
        # meses) el último cierre REAL es además el dato correcto -- no hace
        # falta el relleno con fast_info que sí necesita Cartera, donde el
        # precio intradía de hoy sí importa para el P&L en vivo.
        hist = hist[hist['Close'].notna()]
        if len(hist) < 100:
            return None

        price = _safe(hist['Close'].iloc[-1])
        if price < 5:
            return None

        vol_avg = _safe(hist['Volume'].tail(50).mean(), 1)
        if vol_avg < 100_000:
            return None

        perf_12m = _perf_12m(hist)

        try:
            fi     = tk.fast_info
            mktcap = _safe(getattr(fi, 'market_cap', 0))
        except Exception:
            mktcap = 0

        # Trend Template de 7 condiciones, el MISMO que la letra L del
        # análisis individual. Antes esto era un chequeo de 3 condiciones
        # aparte (`price > ma50 and price > ma150 and ma50 > ma150`), y las
        # dos definiciones discrepaban en el 23,8% del universo -- ver
        # shared/canslim_engine.py.
        trend = _trend_template(hist, price)

        vol_today = _safe(hist['Volume'].iloc[-1])
        vol_ratio = vol_today / vol_avg if vol_avg > 0 else 1.0
        acc_dis   = _acc_dis_rating(hist)

        return {
            "ticker":      ticker,
            "price":       round(price, 2),
            "perf_12m":    round(perf_12m, 2),
            "acc_dis":     acc_dis,
            "vol_ratio":   round(vol_ratio, 2),
            "trend":       trend["passed"],
            # Cuántas de las 7 condiciones se cumplen. La tabla lo pinta como
            # "5/7" en vez de un tick: un aprobado raspado y uno perfecto no
            # son lo mismo, y el umbral (5 de 7) deja de ser invisible.
            "trend_score": trend["score"],
            "ma50":        trend["ma50"],
            "ma150":       trend["ma150"],
            "ma200":       trend["ma200"],
            "high_52w":    trend["high_52w"],
            "low_52w":     trend["low_52w"],
            "pct_from_high": trend["pct_from_high"],
            "mktcap":      mktcap,
        }
    except Exception:
        return None


def scan_canslim(min_score: int = 40, max_results: int = 50) -> dict:
    """Escanea el S&P 500 completo con RS real calculado contra el universo."""
    tickers = list(dict.fromkeys(SP500_TICKERS))   # sin duplicados (ya vienen únicos de shared/sp500_universe.py)

    # Paso 1: datos básicos en paralelo -- pool compartido de yfinance (ver
    # services/yf_pool.py), no uno propio: este scan puede coincidir en el
    # tiempo con otros módulos que también golpean yfinance.
    from services.yf_pool import yf_executor
    raw_results = []
    futures = {yf_executor.submit(_scan_single, t): t for t in tickers}
    # as_completed() en vez de iterar el dict (orden de envío) -- así se
    # recogen los resultados según van terminando, no bloqueado esperando
    # al primer ticker enviado si resulta ser uno lento mientras otros
    # posteriores ya han acabado.
    for future in as_completed(futures):
        result = future.result()
        if result:
            raw_results.append(result)

    # Paso 2: RS real = percentil dentro del universo escaneado
    perfs = [r['perf_12m'] for r in raw_results]
    if perfs:
        # Se cachea el universo completo para que analyze_ticker() pueda
        # dar un RS Rating real sin haber corrido su propio scan --
        # TTL["canslim"]=600 ya existía definido y sin usar. Ver sesión 23.
        cache.set("canslim:universe_perfs", perfs, TTL["canslim"])
    for r in raw_results:
        rank = sum(1 for p in perfs if p < r['perf_12m'])
        r['rs'] = max(1, min(99, int(rank / len(perfs) * 99) + 1)) if perfs else 50

    # Paso 3: Score con RS real -- MISMA fórmula que el análisis individual
    # (shared/canslim_engine.py). La versión anterior era propia de aquí, con
    # otros pesos, sin crédito parcial y sumando +10 por «perf_12m >= 20%»
    # cuando el RS ya ES el percentil de perf_12m: el mismo dato puntuaba dos
    # veces. Ver la cabecera de canslim_engine.py.
    candidates = []
    for r in raw_results:
        near_new_high = r['pct_from_high'] >= NEAR_HIGH_PCT
        score = _technical_score(r['rs'], r['trend'], r['trend_score'],
                                 r['acc_dis'], near_new_high, r['vol_ratio'])

        if score >= min_score:
            r['score'] = score
            r['near_new_high'] = near_new_high
            candidates.append(r)

    candidates.sort(key=lambda x: -x['score'])
    _marcar_cartera(candidates)

    return _sanitize({
        "ok":         True,
        "candidates": candidates[:max_results],
        "total":      len(candidates),
        "scanned":    len(tickers),
        "timestamp":  get_timestamp(),
    })