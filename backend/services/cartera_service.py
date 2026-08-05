import pandas as pd
import unicodedata
import re
import time
import math
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from concurrent.futures import ThreadPoolExecutor
from services.yf_pool import yf_executor
import pytz
from config import settings

_price_cache: dict = {}
_CACHE_TTL = 60

# Barras diarias cacheadas (precio de cierre + cierre anterior juntos, una
# sola llamada a yfinance) -- ver conversación 18/07/2026 sobre precisión
# del % diario en Cartera.
_daily_bars_cache: dict = {}
_DAILY_BARS_TTL = 6 * 3600

# Resultado completo de get_cartera(). Hasta ahora NO había ninguna caché
# aquí: cada llamada descargaba el Google Sheet entero con pd.read_csv(url).
# Eso eran 3+ descargas por carga de la página de Cartera, pero desde que los
# badges de cruce 💼 (Fase 3) llaman a get_cartera_tickers(), abrir Scanner,
# RS/RW, Insider, Research u Options Flow también se traía la hoja completa
# — más snapshots_service cada 4 min y el WebSocket cada 60 s. Ver auditoría
# de Cartera, hallazgo #B5.
#
# 60 s es exactamente el mismo TTL que ya tienen los precios (_CACHE_TTL) y
# el mismo intervalo del broadcast del WS, así que la respuesta no se queda
# más rancia de lo que ya estaba: lo único que se evita es volver a bajar la
# hoja para servir datos que no han cambiado.
_cartera_cache: dict = {}
_CARTERA_TTL = 60

# Ventana del aviso de resultados en las posiciones abiertas. Siete días
# CORRIDOS, no la semana natural: en la semana natural un viernes no avisaría
# de unos resultados del lunes siguiente, que es justo cuando más importa
# saberlo. Medido el 04/08/2026 sobre la cartera real: 14 de 46 posiciones
# caen dentro de la ventana, 6 de ellas al día siguiente.
EARNINGS_DIAS = 7


def _is_market_open() -> bool:
    """Mismo patrón que spxl_service.py::_is_market_open() -- sin llamada
    a ninguna API, solo hora/zona horaria."""
    try:
        et     = pytz.timezone("America/New_York")
        now_et = datetime.now(pytz.utc).astimezone(et)
        if now_et.weekday() >= 5: return False
        t = now_et.hour * 60 + now_et.minute
        return 9*60+30 <= t < 16*60
    except Exception:
        now_utc = datetime.now(timezone.utc)
        if now_utc.weekday() >= 5: return False
        t = now_utc.hour * 60 + now_utc.minute
        return 13*60+30 <= t < 20*60


def _get_daily_bars(tk_obj, ticker: str) -> tuple[float, float]:
    """Devuelve (ultimo_cierre, cierre_anterior) de las barras diarias,
    cacheado 6h -- una sola llamada a yfinance sirve para las dos cosas,
    y con el mercado cerrado son los dos números que de verdad importan
    (nada de mezclar con fast_info, que puede quedarse en un snapshot
    ligeramente distinto al cierre oficial)."""
    now = time.time()
    cached = _daily_bars_cache.get(ticker)
    if cached and (now - cached["updated"]) < _DAILY_BARS_TTL:
        return cached["last"], cached["prev"]
    try:
        # auto_adjust=False a propósito (auditoría de Cartera, #A2). Con el
        # valor por defecto (True) yfinance reescala las barras antiguas para
        # descontar los dividendos, así que en un día de ex-dividendo el cierre
        # anterior baja y el "HOY %" sale mejor de lo que fue: pasa a ser
        # retorno TOTAL en vez de variación de precio, y deja de cuadrar con lo
        # que enseña el bróker. Medido sobre ex-dividendos reales: NEE mostraba
        # +0,92% cuando el precio hizo +0,19%; PG +1,05% frente a +0,30%; KO
        # -1,44% frente a -2,07%. Siempre hacia el lado favorable, y una vez por
        # trimestre y posición.
        #
        # La columna `Close` con auto_adjust=False sigue estando ajustada por
        # SPLITS (convención de Yahoo), que es justo lo que hace falta: sin eso
        # un desdoblamiento aparecería como un -50%. Verificado sobre 9 splits
        # reales de 2:1 a 50:1 — porcentaje idéntico con y sin ajuste.
        hist = tk_obj.history(period="5d", interval="1d", auto_adjust=False)
        # Yahoo a veces incluye la fila más reciente con Close=NaN cuando esa
        # sesión todavía no ha asentado el dato del todo (verificado en vivo,
        # 25/07/2026: AAPL/NVDA devolvían NaN en la fila de "hoy" pese a
        # tratarse de los tickers más líquidos del mercado -- no es un
        # problema de datos raros, es un hueco normal del feed). iloc[-1]/
        # iloc[-2] ciegos propagaban ese NaN hasta la respuesta HTTP, y
        # json.dumps() no puede serializar NaN -- /api/v1/watchlist devolvía
        # un 500 en texto plano ("Internal Server Error") en vez de JSON, y
        # el mismo NaN corrompía cualquier otro consumidor de
        # fetch_live_prices() (Cartera, WebSocket, Tesis, alertas). Se
        # descartan las filas sin Close válido antes de elegir última/anterior
        # -- así "el precio de hoy" es siempre el último cierre REAL conocido.
        raw_closes = hist["Close"]
        closes = raw_closes.dropna()

        # Con el mercado cerrado (fin de semana/tras el cierre) y la fila
        # MÁS RECIENTE todavía en NaN, el dropna() de arriba salta esa sesión
        # entera -- "hoy" pasa a ser la última sesión COMPLETA (p.ej. jueves
        # en vez de viernes), desplazando actual/anterior un día entero sin
        # ningún aviso. Verificado en vivo, 25/07/2026: GOOGL mostraba el
        # cierre del jueves como "hoy" un sábado porque el viernes seguía
        # NaN. fast_info.last_price sí suele reflejar esa última sesión
        # (aunque sea un snapshot, no el cierre "oficial" -- ver docstring)
        # incluso con el mercado ya cerrado, así que se usa como relleno
        # puntual SOLO para este hueco -- un snapshot aproximado de hoy es
        # mejor que el cierre exacto de hace dos días.
        if len(raw_closes) > 0 and pd.isna(raw_closes.iloc[-1]) and len(closes) >= 1:
            try:
                fallback = float(tk_obj.fast_info.last_price or 0)
            except Exception:
                fallback = 0.0
            if fallback and math.isfinite(fallback):
                last, prev = fallback, float(closes.iloc[-1])
                _daily_bars_cache[ticker] = {"last": last, "prev": prev, "updated": now}
                return last, prev

        if len(closes) >= 2:
            last, prev = float(closes.iloc[-1]), float(closes.iloc[-2])
        elif len(closes) == 1:
            last = prev = float(closes.iloc[-1])
        else:
            return 0.0, 0.0
        _daily_bars_cache[ticker] = {"last": last, "prev": prev, "updated": now}
        return last, prev
    except Exception:
        return 0.0, 0.0

def norm_col(s):
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower().strip()

# Sizing por nivel de conviccion: en vez de leer acciones exactas de la hoja,
# cada posicion se etiqueta Core/High/Lottery y el peso en $ sale de aplicar
# ese % fijo sobre settings.capital_total. Si una fila no tiene nivel valido,
# se cae al calculo antiguo (Cantidad/Inversion) para no romper nada.
TIER_WEIGHTS = {"CORE": 5.0, "HIGH": 3.0, "LOTTERY": 1.0}

# Fecha numérica con separador, del estilo 07/11/2025 — la forma en la que la
# ambigüedad DD/MM vs MM/DD es posible. Un formato ISO (2025-11-07) no encaja
# aquí y por tanto nunca se toca. Ver parse_dates_flexible().
_RE_FECHA_NUMERICA = re.compile(r"^\s*(\d{1,2})[/-](\d{1,2})[/-](\d{4})\s*$")

def norm_tier(value) -> str | None:
    if value is None:
        return None
    key = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode().strip().upper()
    return key if key in TIER_WEIGHTS else None

def clean_numeric(value):
    if pd.isna(value):
        return 0.0
    val_str = str(value).strip().replace("$", "").replace("%", "").replace(" ", "")
    if "," in val_str:
        val_str = val_str.replace(".", "").replace(",", ".")
    try:
        return float(val_str)
    except Exception:
        return 0.0

def _sanitize(obj):
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize(v) for v in obj]
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    return obj

def get_market_status():
    ny = pytz.timezone("America/New_York")
    now = datetime.now(ny)
    wd = now.weekday()
    h = now.hour + now.minute / 60
    if wd >= 5:
        return "CLOSED", "#f23645"
    if 9.5 <= h < 16.0:
        return "OPEN", "#00ffad"
    if 4.0 <= h < 9.5 or 16.0 <= h < 20.0:
        return "PRE/POST", "#ff9800"
    return "CLOSED", "#f23645"

def _fetch_price_single(ticker: str) -> dict | None:
    now = time.time()
    cached = _price_cache.get(ticker)
    if cached and (now - cached["updated"]) < _CACHE_TTL:
        return cached
    try:
        import yfinance as yf
        tk_obj = yf.Ticker(ticker)

        if _is_market_open():
            # Mercado abierto: precio en vivo real de fast_info, cierre
            # anterior de las barras diarias cacheadas (más fiable que
            # fast_info.previous_close, que a veces no coincide con el
            # cierre real de la sesión anterior) — ver conversación
            # 17/07/2026.
            price = 0.0
            try:
                fi    = tk_obj.fast_info
                price = float(fi.last_price or 0)
                if not math.isfinite(price):
                    price = 0.0
            except Exception:
                pass
            last_bar, prev = _get_daily_bars(tk_obj, ticker)
            if not price:
                price = last_bar
        else:
            # Mercado cerrado: usar el cierre real de las barras diarias
            # para AMBOS valores (precio y anterior) — nada de mezclar con
            # un snapshot de fast_info que puede quedarse ligeramente
            # desviado del cierre oficial que imprimió el mercado. Esto es
            # justo lo que corregía el caso de LEU (mostraba +6.59% en vez
            # de los +6.11% reales de cierre) — ver conversación 18/07/2026.
            # De propina: cero llamadas extra a fast_info con el mercado
            # cerrado, solo la de barras diarias (ya cacheada 6h).
            price, prev = _get_daily_bars(tk_obj, ticker)

        if not price or not math.isfinite(price):
            return None
        chg = (price - prev) / prev * 100 if prev and math.isfinite(prev) else 0.0
        # Guardia final defensiva -- si por cualquier otra vía no prevista
        # price/chg acaban siendo NaN/inf, se devuelve None (mismo criterio
        # de "sin dato, no se fabrica un número" del resto del proyecto) en
        # vez de dejar que un valor no serializable rompa a TODOS los
        # consumidores de fetch_live_prices() con un 500 en texto plano.
        if not math.isfinite(chg):
            return None
        entry = {"ticker": ticker, "price": round(price, 2),
                 "prev": round(prev, 2) if math.isfinite(prev) else 0.0,
                 "chg": round(chg, 2), "updated": now}
        _price_cache[ticker] = entry
        return entry
    except Exception:
        pass
    try:
        if settings.fmp_api_key:
            import requests
            # NOTA: /api/v3/quote-short/{ticker} es legacy (misma migración que
            # earnings-calendar, ver backend/services/earnings_service.py) — el
            # endpoint nuevo es /stable/quote-short?symbol=X, parámetro symbol
            # en la query en vez de en la ruta.
            r = requests.get(
                "https://financialmodelingprep.com/stable/quote-short",
                params={"symbol": ticker, "apikey": settings.fmp_api_key}, timeout=5
            )
            if r.status_code != 200:
                print(f"[Cartera] FMP quote-short ({ticker}): status HTTP {r.status_code} — {r.text[:150]}")
            data = r.json()
            if data and isinstance(data, list):
                price = float(data[0].get("price", 0))
                if price:
                    # quote-short da el precio pero NO la variación del día ni
                    # el cierre anterior. Antes se rellenaban con `prev: price,
                    # chg: 0.0`, es decir, un «sin cambios» fabricado que en
                    # pantalla es indistinguible de una sesión realmente plana.
                    # Se devuelve None en ambos: hay precio, no hay variación
                    # — mismo criterio de «sin dato, no se inventa» del resto
                    # del proyecto. Ver auditoría de Cartera, hallazgo #A3.
                    entry = {"ticker": ticker, "price": round(price, 2),
                             "prev": None, "chg": None, "updated": now}
                    _price_cache[ticker] = entry
                    return entry
    except Exception as e:
        print(f"[Cartera] FMP quote-short ({ticker}): error inesperado ({type(e).__name__}: {e})")
    return None

def fetch_live_prices(tickers: list) -> dict:
    now = time.time()
    result = {}
    stale = []
    for t in tickers:
        cached = _price_cache.get(t)
        if cached and (now - cached["updated"]) < _CACHE_TTL:
            result[t] = cached
        else:
            stale.append(t)
    if stale:
        futures = {yf_executor.submit(_fetch_price_single, t): t for t in stale}
        for fut, t in futures.items():
            try:
                r = fut.result(timeout=10)
                if r:
                    result[t] = r
            except Exception:
                pass
    return result

_sector_cache: dict = {}
_SECTOR_TTL = 6 * 3600  # el sector/industria no cambia casi nunca, cache larga

def _fetch_sector_single(ticker: str) -> dict:
    now = time.time()
    cached = _sector_cache.get(ticker)
    if cached and (now - cached["updated"]) < _SECTOR_TTL:
        return cached
    entry = {"ticker": ticker, "sector": "Sin clasificar", "industry": "", "updated": now}
    try:
        import yfinance as yf
        info = yf.Ticker(ticker).get_info()
        sector   = info.get("sector")
        industry = info.get("industry") or ""
        if not sector:
            # Los ETFs/fondos no tienen sector GICS — usamos su categoría como
            # sustituto en vez de dejarlos todos apilados en "Sin clasificar".
            quote_type = (info.get("quoteType") or "").upper()
            category   = info.get("category") or info.get("fundFamily") or ""
            if quote_type == "ETF" and category:
                sector = f"ETF · {category}"
            elif quote_type == "ETF":
                sector = "ETF (sin categoría)"
            elif quote_type == "CRYPTOCURRENCY":
                sector = "Cripto"
        entry["sector"]   = sector or "Sin clasificar"
        entry["industry"] = industry
    except Exception:
        pass
    _sector_cache[ticker] = entry
    return entry

def fetch_sectors(tickers: list) -> dict:
    now = time.time()
    result = {}
    stale = []
    for t in tickers:
        cached = _sector_cache.get(t)
        if cached and (now - cached["updated"]) < _SECTOR_TTL:
            result[t] = cached
        else:
            stale.append(t)
    if stale:
        futures = {yf_executor.submit(_fetch_sector_single, t): t for t in stale}
        for fut, t in futures.items():
            try:
                result[t] = fut.result(timeout=10)
            except Exception:
                pass
    return result


_sparkline_cache: dict = {}
_SPARKLINE_TTL = 900  # 15 min

def _fetch_sparkline_single(ticker: str, days: int) -> dict | None:
    key = f"{ticker}:{days}"
    now = time.time()
    cached = _sparkline_cache.get(key)
    if cached and (now - cached["updated"]) < _SPARKLINE_TTL:
        return cached
    try:
        import yfinance as yf
        # auto_adjust=False por el mismo motivo que en _get_daily_bars (#A2):
        # el sparkline dibuja el precio que el usuario ve en su bróker, no una
        # serie reescalada por dividendos. Sigue ajustado por splits.
        hist = yf.Ticker(ticker).history(period=f"{days}d", interval="1d", auto_adjust=False)
        if hist.empty:
            return None
        closes = [round(float(v), 4) for v in hist["Close"].tolist()]
        entry = {"ticker": ticker, "closes": closes, "updated": now}
        _sparkline_cache[key] = entry
        return entry
    except Exception:
        return None

def fetch_sparklines(tickers: list, days: int = 30) -> dict:
    now = time.time()
    result = {}
    stale = []
    for t in tickers:
        key = f"{t}:{days}"
        cached = _sparkline_cache.get(key)
        if cached and (now - cached["updated"]) < _SPARKLINE_TTL:
            result[t] = cached
        else:
            stale.append(t)

    if not stale:
        return result

    def _download_and_extract():
        import yfinance as yf
        df = yf.download(tickers=stale, period=f"{days}d", interval="1d",
                          group_by="ticker", threads=False, progress=False)
        out = {}
        for t in stale:
            try:
                # Con un solo ticker, yf.download no usa MultiIndex de columnas
                closes_series = df[t]["Close"] if len(stale) > 1 else df["Close"]
                closes = [round(float(v), 4) for v in closes_series.dropna().tolist()]
                if not closes:
                    continue
                entry = {"ticker": t, "closes": closes, "updated": now}
                _sparkline_cache[f"{t}:{days}"] = entry
                out[t] = entry
            except Exception:
                pass
        return out

    try:
        result.update(yf_executor.submit(_download_and_extract).result())
    except Exception as e:
        print(f"[Cartera] Batch sparklines falló ({type(e).__name__}: {e}) — usando fallback ticker a ticker")
        futures = {yf_executor.submit(_fetch_sparkline_single, t, days): t for t in stale}
        for fut, t in futures.items():
            try:
                r = fut.result(timeout=10)
                if r:
                    result[t] = r
            except Exception:
                pass

    return result


_history_cache: dict = {"updated": 0, "data": None}
_HISTORY_TTL = 900  # 15 min — reconstruir el histórico es costoso (N llamadas yfinance)

def get_portfolio_history(abiertas_rows: list, days: int = 180, cerradas_rows: list = None) -> list:
    """Curva de la cartera: patrimonio y capital aportado, día a día.

    Devuelve [{fecha, valor, invertido, retorno}] en orden cronológico, donde
    `retorno` es un índice base 100 con el retorno ponderado por tiempo.

    QUÉ ESTABA MAL (auditoría de Cartera, #B14, #B15 y el titular del gráfico):

    1. Solo entraban las posiciones ABIERTAS HOY. Todo lo cerrado durante el
       periodo —incluidas las pérdidas— era invisible: sesgo de superviviente
       de manual. Ahora entran también las cerradas, entre su fecha de compra
       y la de cierre, y al cerrarse su importe de venta pasa a caja y sigue
       contando. Esto no se podía hacer hasta que las fechas de cierre
       existieron y fueron fiables (#B13).

    2. El porcentaje que se enseñaba era (valor_final - valor_inicial) /
       valor_inicial. Con una cartera en construcción eso NO es un retorno:
       mide sobre todo el dinero nuevo que ha ido entrando. Medido con los
       datos reales: 63.366 → 147.003 = "+132%", cuando de las 47 posiciones
       solo 15 existían al principio y las otras 32 aportaron 91.424 $ nuevos.
       El resultado real contra el capital aportado era del -1%.

       Se sustituye por el retorno ponderado por tiempo (TWR): cada día se
       descuenta la aportación de ese día antes de medir la variación, y se
       encadenan. Es la forma estándar de medir rendimiento cuando hay
       entradas y salidas de capital, precisamente porque las neutraliza.
    """
    now = time.time()
    cerradas_rows = cerradas_rows or []
    positions = [r for r in abiertas_rows if r.get("shares", 0) > 0]
    cerradas  = [r for r in cerradas_rows
                 if r.get("shares", 0) > 0 and r.get("fecha_cierre") and r.get("actual", 0) > 0]
    if not positions and not cerradas:
        return []

    cache_key = tuple(sorted(
        [(r["ticker"], r["shares"], "A") for r in positions]
        + [(r["ticker"], r["shares"], r["fecha_cierre"]) for r in cerradas]
    ))
    cached = _history_cache.get("data")
    if cached and _history_cache.get("key") == cache_key and (now - _history_cache["updated"]) < _HISTORY_TTL:
        return cached

    try:
        import yfinance as yf
    except Exception:
        return []

    def _hist_for(ticker):
        try:
            # auto_adjust=False, mismo motivo que en _get_daily_bars (#A2), y
            # aquí además importa por otra razón: la curva multiplica precio
            # por número de acciones. Con las barras antiguas reescaladas hacia
            # abajo por los dividendos, el pasado parece más barato de lo que
            # fue y la curva aparenta haber crecido más. El número de acciones
            # no cambia con un dividendo; el precio de entonces tampoco debería.
            return ticker, yf.Ticker(ticker).history(
                period=f"{days}d", interval="1d", auto_adjust=False)["Close"]
        except Exception:
            return ticker, None

    tickers = list(dict.fromkeys([p["ticker"] for p in positions + cerradas]))
    series = {}
    for ticker, s in yf_executor.map(_hist_for, tickers):
        if s is not None and not s.empty:
            s.index = s.index.tz_localize(None)
            series[ticker] = s

    if not series:
        return []

    all_dates = sorted(set().union(*[s.index for s in series.values()]))
    if not all_dates:
        return []

    def _fecha(valor, por_defecto):
        try:
            return datetime.strptime(valor, "%d/%m/%Y")
        except Exception:
            return por_defecto

    # Cada operación con sus dos extremos: desde cuándo cuenta y hasta cuándo.
    # `salida` None = sigue abierta.
    ops = [{"row": p, "entrada": _fecha(p["fecha"], all_dates[0]), "salida": None}
           for p in positions]
    ops += [{"row": r, "entrada": _fecha(r["fecha"], all_dates[0]),
             "salida": _fecha(r["fecha_cierre"], all_dates[0])} for r in cerradas]

    result = []
    equity_prev = None
    inv_prev    = 0.0
    indice      = 100.0

    for d in all_dates:
        mercado = 0.0   # valor de las posiciones vivas ese día
        caja    = 0.0   # importe de las ya vendidas a esa altura
        aportado = 0.0  # capital acumulado puesto hasta esa fecha
        for op in ops:
            p = op["row"]
            if d < op["entrada"]:
                continue                      # aún no comprada
            aportado += p.get("inv", 0.0) or 0.0
            if op["salida"] is not None and d >= op["salida"]:
                caja += p["actual"] * p["shares"]   # vendida: su importe queda en caja
                continue
            s = series.get(p["ticker"])
            if s is None:
                continue
            px_series = s[s.index <= d]
            if px_series.empty:
                continue
            mercado += float(px_series.iloc[-1]) * p["shares"]

        equity = mercado + caja
        if equity <= 0:
            continue

        # TWR: se descuenta la aportación del día ANTES de medir la variación,
        # para que meter dinero nuevo no se cuente como si fuera rendimiento.
        if equity_prev and equity_prev > 0:
            aporte_dia = aportado - inv_prev
            base = equity_prev + aporte_dia
            if base > 0:
                indice *= equity / base
        equity_prev, inv_prev = equity, aportado

        result.append({
            "fecha":     d.strftime("%Y-%m-%d"),
            "valor":     round(equity, 2),
            "invertido": round(aportado, 2),
            "retorno":   round(indice, 2),
        })

    _history_cache.update({"updated": now, "key": cache_key, "data": result})
    return result


def simulate_tier_capital(df, col_fecha, col_estado, col_compra, col_actual, col_venta, col_tier, capital_total, col_cierre=None):
    """Recorre TODAS las operaciones (abiertas + cerradas) en orden cronológico y
    dimensiona cada posición Core/High/Lottery como % de un capital que:
      - empieza en `capital_total`,
      - se incrementa/reduce con el P&L REALIZADO de cada posición al cerrarse,
      - nunca permite que el capital comprometido en posiciones abiertas supere
        el capital disponible en ese momento (si el tamaño objetivo del nivel no
        cabe, se recorta al disponible).
    Devuelve {indice_fila_df: inversion_real} — None si la fila no tiene nivel
    válido o no se puede dimensionar (para que el llamador caiga al cálculo
    antiguo Cantidad/Inversión en ese caso).

    SIMULACIÓN POR EVENTOS, no por filas (auditoría de Cartera, #B4). Antes se
    recorría `df.sort_values(col_fecha)` —la fecha de APERTURA— y una posición
    cerrada se abría Y se cerraba dentro de la misma iteración. Es decir: una
    posición abierta en enero y cerrada en diciembre devolvía su capital y
    apuntaba su P&L en ENERO, antes de que existieran las de febrero a
    noviembre. El capital disponible que veían todas esas posiciones
    intermedias era falso, y con él el recorte por falta de capital.

    Ahora cada fila genera hasta dos eventos —apertura en `col_fecha`, cierre
    en `col_cierre`— y se procesan todos en orden real. En una misma fecha las
    aperturas van antes que los cierres (criterio conservador: el capital no se
    da por liberado hasta después de haber comprometido lo de ese día). Si una
    fila cerrada no tiene fecha de cierre fiable —columna ausente, vacía, o
    anterior a la de apertura— se cierra el mismo día que se abre, que es
    exactamente el comportamiento antiguo: sin dato no se inventa una fecha.
    """
    if capital_total <= 0 or not col_tier:
        return {}

    filas = {idx: row for idx, row in df.iterrows()}

    eventos = []
    for idx, row in filas.items():
        f_apertura = row[col_fecha]
        eventos.append((f_apertura, 0, "abrir", idx))
        estado = str(row[col_estado]).upper()
        if "CERRADA" in estado or "CLOSED" in estado:
            f_cierre = row.get(col_cierre) if col_cierre else None
            if f_cierre is None or pd.isna(f_cierre) or f_cierre < f_apertura:
                f_cierre = f_apertura
            eventos.append((f_cierre, 1, "cerrar", idx))
    eventos.sort(key=lambda e: (e[0], e[1]))

    equity = capital_total
    open_committed = 0.0
    inv_by_idx = {}

    for _fecha, _orden, tipo, idx in eventos:
        row    = filas[idx]
        compra = float(row[col_compra]) if row[col_compra] else 0.0

        if tipo == "abrir":
            tier = norm_tier(row.get(col_tier))
            if not tier or compra <= 0:
                inv_by_idx[idx] = None
                continue
            desired    = capital_total * TIER_WEIGHTS[tier] / 100
            available  = max(0.0, equity - open_committed)
            actual_inv = round(min(desired, available), 2)
            # Sin capital para dimensionar: None, NO 0.0. Es lo que el
            # docstring de esta función promete desde el principio ("None si
            # ... no se puede dimensionar, para que el llamador caiga al
            # cálculo antiguo Cantidad/Inversión"), pero el código devolvía
            # 0.0, que sí es un valor y por tanto se usaba tal cual.
            #
            # Con la hoja de HOY esto no cambia ningún número, y conviene
            # decirlo: las columnas Cantidad e Inversión están vacías en las
            # 53 filas abiertas, así que no hay ningún cálculo alternativo al
            # que caer. El valor de devolver None es que el llamador puede
            # distinguir «no se pudo dimensionar» de «vale cero», y marcar la
            # fila en consecuencia en vez de pintarla como una posición de $0.
            if actual_inv <= 0:
                inv_by_idx[idx] = None
                continue
            inv_by_idx[idx] = actual_inv
            open_committed += actual_inv
        else:
            actual_inv = inv_by_idx.get(idx)
            if not actual_inv:
                continue  # fila sin nivel válido: nunca comprometió capital
            venta = float(row.get(col_venta, 0) or 0) if col_venta else 0.0
            actual_px = venta if venta > 0 else (float(row.get(col_actual, 0) or 0) if col_actual else 0.0) or compra
            pnl_dollar = (actual_px - compra) / compra * actual_inv if compra > 0 else 0.0
            equity += pnl_dollar
            open_committed -= actual_inv  # libera el capital comprometido al cerrar

    # ── SEGUNDA PASADA: repartir el capital que se fue liberando ─────────────
    #
    # La pasada de arriba dimensiona cada posición con el capital que había EL
    # DÍA que se abrió, y no vuelve a mirarla nunca. Cuando más tarde se cierra
    # otra posición, ese capital vuelve a estar libre pero ya no se ofrece a
    # nadie: las que se abrieron en un momento apretado se quedan pequeñas —o a
    # cero— para siempre.
    #
    # Medido sobre la cartera real el 04/08/2026: seis posiciones a cero y
    # cuatro por debajo de su peso (tres de ellas HIGH), mientras la pantalla
    # declaraba $22.676,55 de capital disponible. Dimensionar las seis costaba
    # $22.000. Es decir, la pantalla decía a la vez que sobraba dinero y que no
    # había con qué dimensionar.
    #
    # SOLO SE TOCAN LAS ABIERTAS. Reasignar una cerrada cambiaría el P&L
    # realizado que ya generó al venderse, y eso es reescribir la historia: el
    # capital de esa operación se comprometió y se liberó en su día, con el
    # tamaño que tuvo entonces.
    #
    # ORDEN: primero por peso de nivel (CORE antes que HIGH antes que LOTTERY)
    # y, dentro del mismo nivel, la más antigua primero. Cuando el capital no
    # llega para todas hace falta un criterio, y este es explicable: se
    # completa antes lo de mayor convicción.
    abiertas_idx = [
        idx for idx, row in filas.items()
        if "CERRADA" not in str(row[col_estado]).upper()
        and "CLOSED" not in str(row[col_estado]).upper()
        and norm_tier(row.get(col_tier))
    ]
    abiertas_idx.sort(key=lambda i: (-TIER_WEIGHTS[norm_tier(filas[i].get(col_tier))],
                                     filas[i][col_fecha]))

    reasignado = 0.0
    for idx in abiertas_idx:
        disponible = round(equity - open_committed, 2)
        if disponible <= 0:
            break
        tier    = norm_tier(filas[idx].get(col_tier))
        deseado = capital_total * TIER_WEIGHTS[tier] / 100
        actual  = inv_by_idx.get(idx) or 0.0
        falta   = round(deseado - actual, 2)
        if falta <= 0:
            continue
        anadir = round(min(falta, disponible), 2)
        if anadir <= 0:
            continue
        inv_by_idx[idx] = round(actual + anadir, 2)
        open_committed += anadir
        reasignado     += anadir

    return {
        "inv_by_idx": inv_by_idx,
        "equity_final":     round(equity, 2),
        "open_committed":   round(open_committed, 2),
        "pnl_realizado":    round(equity - capital_total, 2),
        "capital_disponible": round(max(0.0, equity - open_committed), 2),
        "reasignado":       round(reasignado, 2),
    }


def comprobar_coherencia_fechas(df, col_fecha, col_cierre, col_estado, col_ticker) -> list:
    """Incoherencias entre las dos fechas y el estado de cada operación.

    Estas comprobaciones no se podían hacer antes: mientras la hoja mezclaba
    DD/MM y MM/DD, comparar dos fechas entre sí no significaba nada, porque
    cualquiera de las dos podía estar leída al revés. Con el formato ya
    resuelto (ver parse_dates_flexible) sí tienen sentido, y de hecho la
    primera pasada sobre los datos reales sacó cinco filas: una compra
    fechada en el futuro, tres cierres anteriores a su propia compra y una
    posición marcada como abierta con fecha de cierre puesta.

    Son condiciones binarias y baratas: nada que interpretar, o la fila es
    imposible o no lo es. Se informan; no se corrige nada por nuestra cuenta,
    porque el dato correcto solo lo sabe quien hizo la operación."""
    hoy = pd.Timestamp(datetime.now(ZoneInfo("Europe/Madrid")).date())
    avisos = []

    def _apunta(fila_idx, tipo, detalle):
        avisos.append({
            "fila":    int(fila_idx) + 2,   # +2 = cabecera + índice base 0, para que cuadre con el Excel
            "ticker":  str(df.loc[fila_idx, col_ticker]),
            "tipo":    tipo,
            "detalle": detalle,
        })

    cerrada = df[col_estado].astype(str).str.upper().str.contains("CERRADA|CLOSED", na=False)
    cierres = df[col_cierre] if col_cierre else None

    for idx in df.index:
        f_compra = df.loc[idx, col_fecha]
        f_cierre = cierres.loc[idx] if cierres is not None else None

        if pd.notna(f_compra) and f_compra > hoy:
            _apunta(idx, "compra_futura", f"fecha de compra {f_compra:%d/%m/%Y}, posterior a hoy")
        if f_cierre is not None and pd.notna(f_cierre):
            if f_cierre > hoy:
                _apunta(idx, "cierre_futuro", f"fecha de cierre {f_cierre:%d/%m/%Y}, posterior a hoy")
            if pd.notna(f_compra) and f_cierre < f_compra:
                _apunta(idx, "cierre_antes_de_compra",
                        f"cerrada el {f_cierre:%d/%m/%Y} pero comprada el {f_compra:%d/%m/%Y}")
            if not cerrada.loc[idx]:
                _apunta(idx, "abierta_con_cierre",
                        f"marcada como abierta pero con fecha de cierre {f_cierre:%d/%m/%Y}")
        elif cerrada.loc[idx] and cierres is not None:
            _apunta(idx, "cerrada_sin_cierre", "marcada como cerrada pero sin fecha de cierre")

    return avisos


def get_cartera_tickers() -> set:
    """Tickers actualmente en posición abierta en Cartera -- para los
    badges de cruce 💼 en Scanner/RS-RW/Insider/Research/Options Flow
    (Fase 3 del roadmap). Cartera es única/global en esta app (no por
    usuario), así que este set es seguro de usar dentro de cachés
    compartidas entre usuarios -- a diferencia de Watchlist, que sí es por
    usuario. Falla en silencio a conjunto vacío si Cartera no está
    disponible por lo que sea; no debe tumbar otro módulo por un problema
    puntual de Cartera. (Antes vivía como _obtener_tickers_cartera() solo
    dentro de options_service.py -- promovido aquí para que los demás
    módulos no dupliquen la misma lógica.)"""
    try:
        data = get_cartera()
        return {r["ticker"] for r in data.get("abiertas", [])}
    except Exception as e:
        print(f"[Cartera] No se pudo leer Cartera para un cruce de tickers: {e}")
        return set()


def get_cartera():
    # Caché de 60 s (ver _CARTERA_TTL). Se devuelve una copia profunda: el
    # resultado lo consumen la página de Cartera, el WS, los badges de otros
    # cinco módulos, snapshots y las notificaciones, y basta con que uno de
    # ellos mute una fila para contaminar a todos los demás — es el mismo
    # fallo que ya ocurrió con `in_watchlist` en las cachés compartidas.
    now_ts = time.time()
    cacheado = _cartera_cache.get("data")
    if cacheado and (now_ts - _cartera_cache.get("updated", 0)) < _CARTERA_TTL:
        import copy
        return copy.deepcopy(cacheado)
    try:
        url = settings.url_cartera
        if not url:
            raise ValueError("URL_CARTERA no configurada")

        df_raw = pd.read_csv(url).dropna(how="all")
        df_raw.columns = [c.strip() for c in df_raw.columns]

        col_map = {norm_col(c): c for c in df_raw.columns}

        def find_col(*candidates):
            for c in candidates:
                key = norm_col(c)
                if key in col_map:
                    return col_map[key]
            return None

        col_fecha    = find_col("Fecha")
        col_ticker   = find_col("Ticker", "Symbol")
        col_estado   = find_col("Estado")
        col_cantidad = find_col("Cantidad", "Shares", "Acciones", "Qty")
        col_compra   = find_col("Precio Compra", "Compra", "Precio de Compra")
        col_actual   = find_col("Precio Actual", "Actual", "Current Price", "Precio")
        col_venta    = find_col("Precio Venta", "Venta", "Precio de Venta")
        col_inversion = find_col("Inversión", "Inversion", "Capital")
        col_valor    = find_col("Valor Actual", "Valor", "Market Value")
        col_comis    = find_col("Comisiones", "Comision", "Fees")
        col_comment  = find_col("Comentarios", "Comentario", "Notes")
        col_tier     = find_col("Nivel", "Tamaño", "Tamano", "Tier", "Categoria", "Conviccion", "Convicción")
        col_cierre   = find_col("Fecha Cierre", "Fecha Venta", "Fecha Salida", "Close Date", "Fecha Cerrada")

        if not col_fecha or not col_ticker or not col_estado or not col_compra:
            raise ValueError(f"Columnas mínimas no encontradas. Disponibles: {list(df_raw.columns)}")

        df = df_raw.copy()

        for col in [c for c in [col_compra, col_actual, col_venta, col_inversion,
                                  col_valor, col_comis, col_cantidad] if c]:
            df[col] = df[col].apply(clean_numeric)

        df[col_estado] = df[col_estado].astype(str).str.strip().str.upper()
        df[col_ticker] = df[col_ticker].astype(str).str.strip()

        def formato_de_columna(raw):
            """Deduce si una columna está escrita día-primero o mes-primero
            usando solo los valores que NO admiten dos lecturas: si el primer
            campo supera 12 tiene que ser un día, y si lo supera el segundo
            tiene que serlo también.

            La gracia es que esto convierte la ambigüedad en un problema de
            columna y no de valor: en una columna coherente, `07-11-2025` deja
            de ser ambiguo en cuanto otra fila dice `29-10-2025`, porque esa
            prueba que la columna escribe el día delante. No es una
            preferencia ni una heurística, es evidencia del propio dato.

            Devuelve "dia", "mes", "mezcla" (hay pruebas de ambos formatos, que
            es el caso peor y no se puede resolver) o "sin evidencia" (todos
            los valores son ambiguos y no hay nada en qué apoyarse)."""
            dmy = mdy = 0
            for valor in raw:
                if not isinstance(valor, str):
                    continue
                m = _RE_FECHA_NUMERICA.match(valor)
                if not m:
                    continue
                a, b = int(m.group(1)), int(m.group(2))
                if a > 12 and b <= 12:
                    dmy += 1
                elif b > 12 and a <= 12:
                    mdy += 1
            if dmy and not mdy:
                return "dia"
            if mdy and not dmy:
                return "mes"
            if dmy and mdy:
                return "mezcla"
            return "sin evidencia"

        def parse_dates_flexible(series, diag):
            """La hoja mezcla fechas DD/MM/AAAA y MM/DD/AAAA. Se prueba primero
            día-primero; para las que resulten inválidas ("06/29/2026" → día=06,
            mes=29 no existe) se reintenta mes-primero antes de descartar.

            Eso deja fuera el caso peligroso, que es el que NO falla: cuando los
            dos números son ≤ 12, ambas lecturas son fechas válidas y la
            elección es silenciosa. En esta hoja son 53 de 86 valores. Ver
            auditoría de Cartera, hallazgo #B13.

            Lo que sí se puede resolver con certeza, y es lo que hace este
            bloque: una fecha de operación NO puede estar en el futuro. Si una
            de las dos lecturas cae después de hoy y la otra no, la del futuro
            es imposible y se descarta. No es una heurística ni una preferencia
            de formato — es eliminar lo que no puede ser. Con los datos reales
            había 3 posiciones fechadas en octubre y noviembre de 2026, ya
            cerradas, por elegir mal la lectura.

            Para el resto no hay forma de decidir desde el código: la
            ambigüedad está en el dato, no en el parseo. Se cuentan y se
            informan para que se puedan normalizar en origen (AAAA-MM-DD la
            elimina por completo)."""
            raw     = series.astype(str)
            formato = formato_de_columna(raw)
            diag["formatos"].append(formato)

            parsed = pd.to_datetime(raw, dayfirst=(formato != "mes"), errors="coerce")
            need_retry = parsed.isna() & series.notna()
            if need_retry.any():
                retry = pd.to_datetime(raw[need_retry], dayfirst=(formato == "mes"), errors="coerce")
                parsed.loc[need_retry] = retry

            hoy = pd.Timestamp(datetime.now(ZoneInfo("Europe/Madrid")).date())

            if formato in ("dia", "mes"):
                # Columna coherente: el formato está probado por sus propios
                # valores, así que no queda ambigüedad que contar. Lo único que
                # se comprueba es que no salga ninguna fecha futura — con el
                # formato ya resuelto, eso ya no sería una lectura equivocada
                # sino un error de tecleo en la hoja, y se avisa como tal.
                diag["futuras"] += int((parsed > hoy).sum())
                return parsed

            for idx, valor in raw.items():
                # pandas 3 ya no convierte los NaN al literal "nan" en
                # astype(str): los deja como faltantes, así que `valor` puede
                # ser un float. La columna de fecha de cierre está casi
                # entera vacía, con lo que este caso es el habitual, no el raro.
                if not isinstance(valor, str):
                    continue
                m = _RE_FECHA_NUMERICA.match(valor)
                if not m:
                    continue
                a, b, anio = int(m.group(1)), int(m.group(2)), int(m.group(3))
                if a > 12 or b > 12 or a == b:
                    continue          # sin ambigüedad posible
                try:
                    dia_primero = pd.Timestamp(anio, b, a)
                    mes_primero = pd.Timestamp(anio, a, b)
                except ValueError:
                    continue
                if dia_primero > hoy and mes_primero <= hoy:
                    parsed.loc[idx] = mes_primero
                    diag["corregidas"] += 1
                elif mes_primero > hoy and dia_primero <= hoy:
                    parsed.loc[idx] = dia_primero
                    diag["corregidas"] += 1
                else:
                    diag["ambiguas"] += 1
            return parsed

        diag_fechas = {"ambiguas": 0, "corregidas": 0, "futuras": 0, "formatos": []}
        df[col_fecha] = parse_dates_flexible(df[col_fecha], diag_fechas)
        if col_cierre:
            df[col_cierre] = parse_dates_flexible(df[col_cierre], diag_fechas)
        print(f"[Cartera] Formato de fechas deducido por columna: {diag_fechas['formatos']}")
        if diag_fechas["corregidas"]:
            print(f"[Cartera] {diag_fechas['corregidas']} fecha(s) reinterpretada(s): la lectura día-primero caía en el futuro")
        if diag_fechas["ambiguas"]:
            print(f"[Cartera] {diag_fechas['ambiguas']} fecha(s) ambigua(s) DD/MM vs MM/DD sin forma de resolver — normalizar el formato de la hoja")
        if diag_fechas["futuras"]:
            print(f"[Cartera] {diag_fechas['futuras']} fecha(s) posteriores a hoy con el formato ya resuelto — revisar esas filas en la hoja")

        incoherencias = comprobar_coherencia_fechas(df, col_fecha, col_cierre, col_estado, col_ticker)
        if incoherencias:
            print(f"[Cartera] {len(incoherencias)} incoherencia(s) de fechas: "
                  + "; ".join(f"fila {a['fila']} {a['ticker']} ({a['tipo']})" for a in incoherencias))

        n_before = len(df)
        df = df.dropna(subset=[col_fecha, col_ticker])
        n_after = len(df)
        if n_before != n_after:
            print(f"[Cartera] {n_before - n_after} fila(s) descartada(s) por fecha o ticker inválido tras ambos intentos de parseo")
        df = df[~df[col_ticker].str.upper().isin(["NAN", "NONE", ""])]

        sim = simulate_tier_capital(df, col_fecha, col_estado, col_compra, col_actual,
                                     col_venta, col_tier, settings.capital_total,
                                     col_cierre=col_cierre)
        inv_by_idx = sim.get("inv_by_idx", {}) if sim else {}

        abiertas = df[df[col_estado].str.contains("ABIERTA|OPEN", case=False, na=False)].copy()
        cerradas = df[df[col_estado].str.contains("CERRADA|CLOSED", case=False, na=False)].copy()

        # Enriquecer abiertas con precios live + sector
        live_prices = {}
        sectors = {}
        earnings = {}
        if not abiertas.empty:
            tickers_open = abiertas[col_ticker].unique().tolist()
            live_prices = fetch_live_prices(tickers_open)
            sectors = fetch_sectors(tickers_open)
            # Resultados en los próximos 7 días. Tiene caché diaria propia
            # (ver earnings_service.earnings_proximos) porque get_cartera()
            # solo cachea 60 s: sin ella esto consultaría un ticker por
            # segundo. Falla a diccionario vacío — si la fuente no responde,
            # la tabla se pinta igual, solo sin el aviso.
            try:
                from services.earnings_service import earnings_proximos
                earnings = earnings_proximos(tickers_open, EARNINGS_DIAS)
            except Exception as e:
                print(f"[Cartera] No se pudieron consultar los earnings próximos: {type(e).__name__}: {e}")

        def calc_pnl(compra, actual):
            if compra and compra > 0 and actual and actual > 0:
                return round((actual - compra) / compra * 100, 2)
            return 0.0

        def df_to_rows(d, total_inv_ref=1, is_open=False):
            rows = []
            for idx, row in d.sort_values(col_fecha, ascending=False).iterrows():
                ticker  = row[col_ticker]
                compra  = float(row[col_compra]) if row[col_compra] else 0.0
                cantidad = float(row[col_cantidad]) if col_cantidad and row.get(col_cantidad) else 0.0

                tier = norm_tier(row.get(col_tier)) if col_tier else None

                # Inversión: prioridad = simulación cronológica Core/High/Lottery
                # (capital real disponible, ver simulate_tier_capital) > columna
                # Inversión > Cantidad*compra.
                sim_inv = inv_by_idx.get(idx)
                if sim_inv is not None:
                    inv = sim_inv
                else:
                    inv = float(row[col_inversion]) if col_inversion and row.get(col_inversion) else 0.0
                    if inv == 0 and cantidad > 0 and compra > 0:
                        inv = round(cantidad * compra, 2)

                # Shares: si viene de nivel o inversión, se derivan del precio de compra;
                # si la hoja ya trae Cantidad explícita, esa manda (más precisa).
                shares = cantidad if cantidad > 0 else (round(inv / compra, 4) if compra > 0 else 0.0)

                # Precio actual: live > sheet > compra
                live = live_prices.get(ticker, {}) if is_open else {}
                live_px = live.get("price", 0.0)

                sheet_px = float(row[col_actual]) if col_actual and row.get(col_actual) else 0.0

                # Para cerradas, usar precio de venta si existe
                if not is_open and col_venta:
                    venta_px = float(row.get(col_venta, 0) or 0)
                    actual = venta_px if venta_px > 0 else (sheet_px if sheet_px > 0 else compra)
                else:
                    actual = live_px if live_px > 0 else (sheet_px if sheet_px > 0 else compra)

                actual = round(actual, 2)

                # Valor actual y P&L
                val_act = round(shares * actual, 2) if shares > 0 and actual > 0 else inv
                pnl = calc_pnl(compra, actual)
                pnl_usd = round(val_act - inv, 2)

                peso = round(inv / total_inv_ref * 100, 1) if total_inv_ref > 0 else 0.0

                # Posición abierta real a la que no se le pudo asignar capital:
                # la simulación de niveles está saturada (comprometido ≈ equity)
                # y la hoja no trae Cantidad ni Inversión para esa fila. Hasta
                # ahora se pintaba como «$0 invertidos, 0 acciones, 0% de peso»,
                # indistinguible de una posición inexistente. Se marca para que
                # la tabla pueda decir que existe pero está sin dimensionar, en
                # vez de enseñar un cero que parece un dato.
                sin_dimensionar = bool(is_open and inv == 0 and compra > 0)

                # Días en posición: desde la compra hasta hoy si sigue abierta,
                # o hasta el cierre si ya salió. Es el dato que falta para saber
                # si un +12% se consiguió en tres semanas o en año y medio — dos
                # operaciones muy distintas que hasta ahora se veían igual.
                # Ver auditoría de Cartera, #22.
                dias = None
                try:
                    f_ini = row[col_fecha]
                    f_fin = (row[col_cierre] if (not is_open and col_cierre and pd.notna(row.get(col_cierre)))
                             else pd.Timestamp(datetime.now(ZoneInfo("Europe/Madrid")).date()))
                    if pd.notna(f_ini):
                        dias = max(0, int((f_fin - f_ini).days))
                except Exception:
                    dias = None

                comment = str(row[col_comment])[:60] if col_comment and col_comment in row.index else ""
                if comment.lower() in ("nan", "none", ""):
                    comment = ""

                sec = sectors.get(ticker, {}) if is_open else {}

                # Fecha de cierre real (si la hoja la tiene y está rellenada);
                # si no, cae a la fecha de apertura para no romper filas antiguas.
                fecha_cierre = None
                if not is_open and col_cierre and pd.notna(row.get(col_cierre)):
                    fecha_cierre = row[col_cierre].strftime("%d/%m/%Y")
                fecha_display = fecha_cierre if fecha_cierre else row[col_fecha].strftime("%d/%m/%Y")

                rows.append({
                    # Identificador único por fila (no por ticker) — imprescindible
                    # para no confundir operaciones duplicadas del mismo ticker
                    # (varios lotes abiertos/cerrados) al actualizar precios live.
                    "id":       f"{ticker}-{idx}",
                    "ticker":   ticker,
                    "fecha":    row[col_fecha].strftime("%d/%m/%Y"),
                    "fecha_cierre":  fecha_cierre,
                    "fecha_display": fecha_display,
                    "compra":   round(compra, 2),
                    "actual":   actual,
                    "pnl":      pnl,
                    "pnl_usd":  pnl_usd,
                    "inv":      inv,
                    "val_act":  val_act,
                    "shares":   round(shares, 4),
                    "peso":     peso,
                    "chg_hoy":    live.get("chg"),
                    "prev_close": live.get("prev"),
                    "estado":   row[col_estado],
                    "comment":  comment,
                    "sector":   sec.get("sector", "Sin clasificar"),
                    "industry": sec.get("industry", ""),
                    "tier":     tier,
                    "sin_dimensionar": sin_dimensionar,
                    "dias":     dias,
                    # {fecha, dias} si presenta resultados dentro de la
                    # ventana; None si no, o si no hay dato. Solo para
                    # posiciones abiertas: en una cerrada da igual.
                    "earnings": earnings.get(ticker) if is_open else None,
                })
            return rows

        # Calcular totales para métricas
        abiertas_rows = df_to_rows(abiertas, 1, is_open=True)
        total_inv = sum(r["inv"] for r in abiertas_rows)
        # Recalcular con total_inv correcto
        abiertas_rows = df_to_rows(abiertas, total_inv or 1, is_open=True)

        cerradas_rows = df_to_rows(cerradas, total_inv or 1, is_open=False)

        # Para "Últimas salidas" ordenamos por fecha de CIERRE real (fecha_display
        # ya cae a la fecha de apertura si no hay fecha de cierre en la hoja),
        # no por fecha de apertura como el resto de la tabla de cerradas.
        def _parse_dmy(s):
            try:
                return datetime.strptime(s, "%d/%m/%Y")
            except Exception:
                return datetime.min
        recent_closed = sorted(cerradas_rows, key=lambda r: _parse_dmy(r["fecha_display"]), reverse=True)[:5]

        # Métricas
        metrics = {}
        if abiertas_rows:
            total_val   = sum(r["val_act"] for r in abiertas_rows)
            total_comis = df[col_comis].apply(clean_numeric).sum() if col_comis else 0
            pnl_neto    = (total_val - total_inv) - total_comis
            pnl_pct     = (pnl_neto / total_inv * 100) if total_inv > 0 else 0
            val_pct     = ((total_val - total_inv) / total_inv * 100) if total_inv > 0 else 0
            metrics = {
                "total_inv":   round(total_inv, 2),
                "total_val":   round(total_val, 2),
                "pnl_neto":    round(pnl_neto, 2),
                "pnl_pct":     round(pnl_pct, 2),
                "val_pct":     round(val_pct, 2),
                "total_comis": round(total_comis, 2),
            }

            # P&L del día agregado -- solo sobre posiciones con cierre de ayer
            # disponible (si el precio en vivo falló para un ticker, se
            # excluye de ambos lados en vez de fabricar un dato).
            rows_con_chg = [r for r in abiertas_rows if r.get("prev_close") and r["shares"]]
            if rows_con_chg:
                val_hoy_chg  = sum(r["shares"] * r["actual"] for r in rows_con_chg)
                val_ayer_chg = sum(r["shares"] * r["prev_close"] for r in rows_con_chg)
                if val_ayer_chg > 0:
                    metrics["pnl_dia_usd"] = round(val_hoy_chg - val_ayer_chg, 2)
                    metrics["pnl_dia_pct"] = round((val_hoy_chg - val_ayer_chg) / val_ayer_chg * 100, 2)

            if sim and sim.get("inv_by_idx"):
                metrics["capital_inicial"]     = round(settings.capital_total, 2)
                metrics["pnl_realizado_acum"]  = sim["pnl_realizado"]
                metrics["capital_disponible"]  = sim["capital_disponible"]

        # ── ASIGNACIÓN OBJETIVO VS REAL ──────────────────────────────────────
        # Cuánto capital pedirían las reglas de nivel si TODAS las posiciones
        # abiertas tuvieran su tamaño completo, frente a cuánto hay de verdad.
        # Es la cuenta que hace falta para ver de un vistazo si el número de
        # posiciones abiertas cabe en las propias reglas de tamaño: 5% × 13
        # CORE + 3% × 37 HIGH + 1% × 3 LOTTERY = 179% del capital, que
        # obviamente no cabe, y por eso hay posiciones sin dimensionar. Sin
        # esta tabla, lo único que se veía era un «0%» silencioso en cinco
        # filas. Ver auditoría de Cartera, #20 (y #B19, que es su síntoma).
        asignacion = {}
        if abiertas_rows and sim and sim.get("inv_by_idx") and settings.capital_total > 0:
            equity = round(settings.capital_total + sim["pnl_realizado"], 2)
            por_nivel = []
            deseado_total = 0.0
            for nivel, peso in TIER_WEIGHTS.items():
                filas_nivel = [r for r in abiertas_rows if r["tier"] == nivel]
                if not filas_nivel:
                    continue
                deseado = round(settings.capital_total * peso / 100 * len(filas_nivel), 2)
                deseado_total += deseado
                por_nivel.append({
                    "nivel":         nivel,
                    "peso_unitario": peso,
                    "n":             len(filas_nivel),
                    "deseado":       deseado,
                    "asignado":      round(sum(r["inv"] for r in filas_nivel), 2),
                    "sin_asignar":   sum(1 for r in filas_nivel if r["sin_dimensionar"]),
                })
            por_nivel.sort(key=lambda x: -x["deseado"])
            sin_nivel = [r for r in abiertas_rows if not r["tier"]]
            asignacion = {
                "capital_base":   round(settings.capital_total, 2),
                "equity_modelo":  equity,
                "comprometido":   round(total_inv, 2),
                "deseado_total":  round(deseado_total, 2),
                # Positivo = falta capital para dar tamaño completo a todo lo abierto.
                "deficit":        round(deseado_total - equity, 2),
                "pct_del_capital": round(deseado_total / settings.capital_total * 100, 1),
                "por_nivel":      por_nivel,
                "sin_nivel":      len(sin_nivel),
            }

        closed_stats = {}
        if cerradas_rows:
            ganadas  = len([r for r in cerradas_rows if r["pnl"] > 0])
            perdidas = len([r for r in cerradas_rows if r["pnl"] <= 0])
            win_rate = ganadas / len(cerradas_rows) * 100
            # Media ponderada por capital invertido en cada operación --
            # sumar los % de retorno sin ponderar (versión anterior) mezclaba
            # operaciones de tamaños muy distintos como si pesaran igual
            # (+50% de $200 y -10% de $5.000 sumaban +40%, sin sentido
            # económico). Ver auditoría de Cartera, hallazgo #B3.
            inv_cerradas = sum(r["inv"] for r in cerradas_rows)
            avg_pnl = (
                sum(r["pnl"] * r["inv"] for r in cerradas_rows) / inv_cerradas
                if inv_cerradas > 0 else 0.0
            )
            closed_stats = {
                "total":    len(cerradas_rows),
                "ganadas":  ganadas,
                "perdidas": perdidas,
                "win_rate": round(win_rate, 1),
                "avg_pnl":  round(avg_pnl, 2),
            }

        mkt_status, mkt_color = get_market_status()

        history = []
        try:
            history = get_portfolio_history(abiertas_rows, cerradas_rows=cerradas_rows)
        except Exception:
            history = []

        resultado = _sanitize({
            "ok":           True,
            "metrics":      metrics,
            "asignacion":   asignacion,
            "diag_fechas":  diag_fechas,
            "incoherencias": incoherencias,
            "closed_stats": closed_stats,
            "abiertas":     abiertas_rows,
            "cerradas":     cerradas_rows,
            "recent":       abiertas_rows[:5],
            "recent_closed": recent_closed,
            "history":      history,
            "mkt_status":   mkt_status,
            "mkt_color":    mkt_color,
            "last_update":  datetime.now(ZoneInfo("Europe/Madrid")).strftime("%d/%m/%Y %H:%M:%S"),
        })
        # Solo se cachea un resultado bueno -- un fallo de red o de formato de
        # la hoja no debe quedarse pegado 60 s, mismo criterio que el resto
        # del proyecto con los `ok: False`.
        _cartera_cache["data"]    = resultado
        _cartera_cache["updated"] = time.time()
        import copy
        return copy.deepcopy(resultado)

    except Exception as e:
        import traceback
        return {"ok": False, "error": str(e), "detail": traceback.format_exc()}


def get_live_prices_for_ws(tickers: list) -> list:
    prices = fetch_live_prices(tickers)
    return list(prices.values())