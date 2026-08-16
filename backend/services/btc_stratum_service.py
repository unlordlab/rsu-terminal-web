import numpy as np
import pandas as pd
import yfinance as yf
import requests
import sys, os
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "shared"))
from time_utils import get_timestamp  # noqa: E402

# ── HELPERS ───────────────────────────────────────────────────────────────────

def _flatten(df):
    if df.empty: return df
    if isinstance(df.columns, pd.MultiIndex):
        df = df.copy()
        df.columns = df.columns.get_level_values(0)
    return df

def _safe_float(val):
    try:
        v = float(val)
        return v if not (np.isnan(v) or np.isinf(v)) else None
    except Exception:
        return None

# ── FUENTES DE DATOS ON-CHAIN GRATUITAS ──────────────────────────────────────

def _get_btc_price_coingecko() -> dict:
    """Precio BTC en tiempo real via CoinGecko"""
    try:
        r = requests.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={
                "ids": "bitcoin",
                "vs_currencies": "usd",
                "include_24hr_change": "true",
                "include_market_cap": "true",
            },
            timeout=8,
            headers={"Accept": "application/json"}
        )
        if r.status_code == 200:
            data = r.json().get("bitcoin", {})
            return {
                "price":      data.get("usd"),
                "chg_24h":    round(data.get("usd_24h_change", 0), 2),
                "market_cap": data.get("usd_market_cap"),
                "source":     "CoinGecko",
            }
    except Exception:
        pass
    return {}

def _get_btc_history_coingecko(days: int = 3650) -> pd.DataFrame:
    """Histórico de precios y market cap via CoinGecko"""
    try:
        r = requests.get(
            "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart",
            params={"vs_currency": "usd", "days": days, "interval": "daily"},
            timeout=15,
            headers={"Accept": "application/json"}
        )
        if r.status_code != 200:
            # Se LOGUEA, no se traga en silencio. Comprobado el 11/08/2026:
            # este endpoint devuelve 401 -- CoinGecko movió el histórico
            # (`/market_chart`) detrás de una API key, mientras que el precio
            # actual (`/simple/price`) sigue siendo libre. El efecto no era
            # visible: la serie cae al respaldo de yfinance y el módulo sigue
            # pintando números, pero SIN market cap histórico, que es lo único
            # con lo que se puede construir el MVRV bueno. Ese fallo mudo es lo
            # que dejó el MVRV en su proxy sin que nadie se enterara.
            print(f"[BTCStratum] CoinGecko /market_chart devolvió {r.status_code} — "
                  f"sin market cap histórico, el MVRV usará su proxy de precio")
            return pd.DataFrame()
        data = r.json()
        prices     = data.get("prices", [])
        market_cap = data.get("market_caps", [])
        if not prices:
            return pd.DataFrame()
        df = pd.DataFrame(prices, columns=["timestamp", "price"])
        df["date"] = pd.to_datetime(df["timestamp"], unit="ms")
        df.set_index("date", inplace=True)
        df.drop("timestamp", axis=1, inplace=True)
        if market_cap:
            mc_df = pd.DataFrame(market_cap, columns=["timestamp", "market_cap"])
            mc_df["date"] = pd.to_datetime(mc_df["timestamp"], unit="ms")
            mc_df.set_index("date", inplace=True)
            mc_df.drop("timestamp", axis=1, inplace=True)
            df = df.join(mc_df)
        return df.dropna()
    except Exception:
        return pd.DataFrame()

def _get_puell_multiple_real() -> dict:
    """Puell Multiple REAL via Blockchain.com — ingresos reales de mineros"""
    try:
        r = requests.get(
            "https://api.blockchain.info/charts/miners-revenue",
            params={"timespan": "2years", "format": "json", "sampled": "true"},
            timeout=10,
        )
        if r.status_code != 200:
            return {}
        data   = r.json().get("values", [])
        if len(data) < 365:
            return {}
        values = [v["y"] for v in data]
        dates  = [datetime.fromtimestamp(v["x"]) for v in data]
        series = pd.Series(values, index=dates)
        sma365 = series.rolling(365).mean()
        current_revenue = values[-1]
        current_sma     = sma365.iloc[-1]
        puell = current_revenue / current_sma if current_sma > 0 else None

        # Historia reciente para gráfico
        history = []
        for i in range(-90, 0):
            if pd.isna(sma365.iloc[i]): continue
            p = values[i] / sma365.iloc[i] if sma365.iloc[i] > 0 else None
            if p:
                history.append({
                    "date":  dates[i].strftime("%Y-%m-%d"),
                    "value": round(p, 3),
                })

        return {
            "puell":           round(puell, 3) if puell else None,
            "daily_revenue":   round(current_revenue / 1e6, 2),  # en millones USD
            "sma365_revenue":  round(current_sma / 1e6, 2),
            "history":         history,
            "source":          "Blockchain.com",
        }
    except Exception:
        return {}

def _get_hashrate_mempool() -> dict:
    """Hashrate real via Mempool.space"""
    try:
        r = requests.get(
            "https://mempool.space/api/v1/mining/hashrate/1y",
            timeout=8,
            headers={"Accept": "application/json"}
        )
        if r.status_code != 200:
            return {}
        data      = r.json()
        hashrates = data.get("hashrates", [])
        if not hashrates:
            return {}
        current_hash = hashrates[-1].get("avgHashrate", 0)
        # Convertir a EH/s
        current_ehs  = round(current_hash / 1e18, 2)
        # Media 30 días
        recent = hashrates[-30:] if len(hashrates) >= 30 else hashrates
        avg30  = round(sum(h.get("avgHashrate", 0) for h in recent) / len(recent) / 1e18, 2)
        return {
            "hashrate_ehs":  current_ehs,
            "avg30_ehs":     avg30,
            "trend":         "SUBIENDO" if current_ehs > avg30 else "BAJANDO",
            "source":        "Mempool.space",
        }
    except Exception:
        return {}

def _get_difficulty_mempool() -> dict:
    """Dificultad de minería via Mempool.space"""
    try:
        r = requests.get(
            "https://mempool.space/api/v1/mining/difficulty-adjustments/1y",
            timeout=8,
        )
        if r.status_code != 200:
            return {}
        data = r.json()
        if not data:
            return {}
        latest = data[-1] if isinstance(data, list) else {}
        return {
            "difficulty":    latest.get("difficulty"),
            "change_pct":    round(latest.get("difficultyChange", 0), 2),
            "source":        "Mempool.space",
        }
    except Exception:
        return {}

# ── INDICADORES ON-CHAIN MEJORADOS ────────────────────────────────────────────

def _calc_ma200w(close: pd.Series) -> pd.Series:
    # 200 semanas = 1400 días -- antes min_periods=200 dejaba calcular la
    # media con solo el 14% de la ventana prometida, y ese valor inmaduro
    # se usaba igual que un MA200W completo (ver sesión "fallbacks
    # fabricados", 22/07/2026, mismo patrón que DXY/Yield2Y/RS CANSLIM).
    return close.rolling(window=1400, min_periods=1400).mean()

# Origen de cada indicador, tal cual lo lee el usuario bajo su tarjeta. Viven
# aquí y no incrustados en el dict de respuesta por dos motivos: el frontend
# pinta en ámbar los que empiezan por "Aproximado" (así que ese prefijo es un
# contrato, no una florritura), y un test puede comprobarlo sin salir a la red.
ORIGEN_MA200      = "Precio vs media de 200 semanas"
ORIGEN_MVRV_REAL  = "Capitalización de mercado vs su media anual"
ORIGEN_MVRV_PROXY = "Aproximado: precio vs media de 200 semanas (sin dato on-chain)"
ORIGEN_PUELL_REAL = "Ingresos reales de mineros (Blockchain.com)"
ORIGEN_PUELL_PROXY = "Aproximado: precio vs su media de 365 días"
ORIGEN_AHR999     = "Precio vs media de 200 semanas"


def _calc_mvrv_z_improved(df: pd.DataFrame) -> dict:
    """
    MVRV Z-Score mejorado usando market cap real de CoinGecko.
    Aproximamos Realized Cap como EMA larga del market cap.
    """
    try:
        if "market_cap" not in df.columns or df["market_cap"].isna().all():
            return {"mvrv": None, "source": "proxy"}

        market_cap    = df["market_cap"].dropna()
        # Realized cap proxy: EMA 365 días del market cap
        realized_cap  = market_cap.ewm(span=365).mean()
        mvrv_ratio    = market_cap / realized_cap
        # Z-Score estandarizado
        mvrv_mean     = mvrv_ratio.rolling(365).mean()
        mvrv_std      = mvrv_ratio.rolling(365).std()
        mvrv_z        = (mvrv_ratio - mvrv_mean) / mvrv_std

        current_mvrv  = float(mvrv_ratio.iloc[-1])
        current_z     = float(mvrv_z.iloc[-1])

        # Historia para gráfico
        history = []
        step    = max(1, len(mvrv_z) // 100)
        for i in range(-min(365, len(mvrv_z)), 0, step):
            if pd.isna(mvrv_z.iloc[i]): continue
            history.append({
                "date":  mvrv_z.index[i].strftime("%Y-%m-%d"),
                "value": round(float(mvrv_z.iloc[i]), 3),
            })

        return {
            "mvrv_ratio": round(current_mvrv, 3),
            "mvrv_z":     round(current_z, 3),
            "history":    history,
            "source":     "CoinGecko market cap + EMA proxy",
        }
    except Exception:
        return {"mvrv": None, "source": "error"}

def _calc_ahr999_improved(close: pd.Series, ma200: pd.Series) -> dict:
    """AHR999 mejorado"""
    try:
        ma_safe = ma200.replace(0, np.nan)
        ahr     = (close / ma_safe) / np.log(ma_safe)
        current = float(ahr.iloc[-1])

        history = []
        step    = max(1, len(ahr) // 100)
        for i in range(-min(365, len(ahr)), 0, step):
            if pd.isna(ahr.iloc[i]): continue
            history.append({
                "date":  ahr.index[i].strftime("%Y-%m-%d"),
                "value": round(float(ahr.iloc[i]), 4),
            })

        return {
            "ahr999":  round(current, 4),
            "history": history,
            "source":  "Precio + MA200W",
        }
    except Exception:
        return {"ahr999": None, "source": "error"}

def _calc_puell_from_series(close: pd.Series) -> float:
    """Puell proxy desde precio si Blockchain.com falla"""
    try:
        sma365 = close.rolling(365).mean()
        return float(close.iloc[-1] / sma365.iloc[-1])
    except Exception:
        return 1.0

def _calc_rsu_score_improved(
    price: float, ma200: float,
    mvrv_z: float, puell: float, ahr999: float
) -> dict:
    """RSU Score con datos mejorados"""
    # MA200W score
    if ma200 > 0:
        dev      = (price - ma200) / ma200
        ma_score = max(0, min(100, ((dev + 0.5) / 1.0) * 100))
    else:
        ma_score = 50.0

    # MVRV Z-Score score (Z real, no proxy)
    # Z < -1 = extremo, Z > 3 = sobrecomprado
    mvrv_score = max(0, min(100, ((mvrv_z + 1.5) / 5.0) * 100))

    # Puell score
    puell_score = max(0, min(100, ((puell - 0.5) / 3.5) * 100))

    # AHR999 score
    ahr_score = max(0, min(100, ((ahr999 - 0.5) / 4.5) * 100))

    total = (ma_score * 0.40 + mvrv_score * 0.30 +
             puell_score * 0.20 + ahr_score * 0.10)

    return {
        "total":  round(total, 1),
        "ma200":  round(ma_score, 1),
        "mvrv":   round(mvrv_score, 1),
        "puell":  round(puell_score, 1),
        "ahr999": round(ahr_score, 1),
    }

# Los colores viajan como expresiones CSS con tokens del tema, no como hex.
# Antes esta escalera inventaba seis verdes propios (#006b1b, #009627, #28a745,
# #78a832, #aa8c28) que no existían en ningún otro módulo de la terminal y que
# se quedaban clavados con cualquier tema que no fuera el oscuro por defecto.
# La rampa se construye ahora mezclando los dos tokens semánticos que ya
# definen los extremos -- así el degradado sigue leyéndose igual en los nueve
# temas. `color-mix` ya se usa en components/sidebar.js.
def _mezcla(pct_accent: int) -> str:
    return f"color-mix(in srgb, var(--color-accent) {pct_accent}%, var(--color-warning))"

def _get_zone(rsu: float) -> dict:
    if rsu < 20:
        return {"zone": "OPORTUNIDAD MÁXIMA", "color": "var(--color-accent)", "allocation": 25, "urgency": "CRÍTICA"}
    elif rsu < 40:
        return {"zone": "COMPRA AGRESIVA",    "color": _mezcla(80), "allocation": 20, "urgency": "ALTA"}
    elif rsu < 60:
        return {"zone": "COMPRA FUERTE",      "color": _mezcla(60), "allocation": 15, "urgency": "MEDIA-ALTA"}
    elif rsu < 70:
        return {"zone": "BUENA COMPRA",       "color": _mezcla(35), "allocation": 10, "urgency": "MEDIA"}
    elif rsu < 85:
        return {"zone": "ZONA DCA",           "color": "var(--color-warning)", "allocation": 5,  "urgency": "BAJA"}
    else:
        return {"zone": "ESPERAR",            "color": "var(--color-muted)",   "allocation": 0,  "urgency": "ESPERAR"}

def _get_signal_label(rsu: float) -> dict:
    if rsu < 20:   return {"label": "OPORTUNIDAD EXTREMA",  "color": "var(--color-accent)"}
    elif rsu < 40: return {"label": "ACUMULACIÓN FUERTE",   "color": "var(--color-secondary)"}
    elif rsu < 60: return {"label": "ACUMULACIÓN MODERADA", "color": _mezcla(40)}
    elif rsu < 80: return {"label": "NEUTRAL / ESPERA",     "color": "var(--color-warning)"}
    else:          return {"label": "SOBRECOMPRA / RIESGO", "color": "var(--color-danger)"}

HALVING_BLOQUES = 210_000
HALVING_MIN_POR_BLOQUE = 10  # objetivo del protocolo; el ritmo real oscila ±5%


def _proximo_halving_por_altura():
    """Estima la fecha del próximo halving a partir de la altura de bloque
    actual, en vez de tenerla clavada. La fecha exacta NO se puede conocer de
    antemano -- depende del ritmo al que se minen los bloques que faltan --
    así que esto es una estimación, pero una que se corrige sola cada día.

    Antes era `datetime(2028, 4, 1)` a fuego: en cuanto pasara esa fecha, el
    progreso del ciclo superaría el 100% y la fase se quedaría encallada en
    "MERCADO BAJISTA" para siempre sin que nada avisara. Devuelve None si
    mempool.space no responde -- el llamador decide, no se fabrica una fecha.
    """
    try:
        r = requests.get("https://mempool.space/api/blocks/tip/height", timeout=8)
        if r.status_code != 200:
            return None
        altura = int(r.text.strip())
        if altura <= 0:
            return None
        bloque_objetivo = ((altura // HALVING_BLOQUES) + 1) * HALVING_BLOQUES
        faltan          = bloque_objetivo - altura
        return {
            "fecha":  datetime.now() + timedelta(minutes=faltan * HALVING_MIN_POR_BLOQUE),
            "altura": altura,
            "bloque": bloque_objetivo,
            "faltan": faltan,
        }
    except Exception:
        return None


def _get_halving_cycle() -> dict:
    halvings = [datetime(2012,11,28), datetime(2016,7,9),
                datetime(2020,5,11), datetime(2024,4,19)]
    now          = datetime.now()
    last_halving = max(h for h in halvings if h <= now)

    est = _proximo_halving_por_altura()
    if est:
        next_halving  = est["fecha"]
        halving_fuente = f"estimado por altura de bloque ({est['faltan']:,} bloques para el {est['bloque']:,})".replace(",", ".")
    else:
        # Sin altura de bloque no se inventa una fecha: se proyecta desde el
        # último halving con el ritmo nominal del protocolo (210.000 bloques ×
        # 10 min ≈ 1.458 días) y se dice que es eso.
        next_halving   = last_halving + timedelta(minutes=HALVING_BLOQUES * HALVING_MIN_POR_BLOQUE)
        halving_fuente = "proyectado desde el último halving (sin conexión con la red)"

    days_since   = (now - last_halving).days
    days_total   = max(1, (next_halving - last_halving).days)
    progress     = min(1.0, days_since / days_total)

    if progress < 0.2:   phase = "ACUMULACIÓN"
    elif progress < 0.4: phase = "BULL TEMPRANO"
    elif progress < 0.6: phase = "BULL AVANZADO"
    elif progress < 0.8: phase = "DISTRIBUCIÓN"
    else:                phase = "MERCADO BAJISTA"

    return {
        "phase":        phase,
        "progress_pct": round(progress * 100, 1),
        "days_since":   days_since,
        "days_to_next": max(0, (next_halving - now).days),
        "last_halving": last_halving.strftime("%Y-%m-%d"),
        "next_halving": next_halving.strftime("%Y-%m-%d"),
        "fuente":       halving_fuente,
    }

def _get_macro_data() -> dict:
    try:
        from services.yf_pool import yf_executor
        f_dxy = yf_executor.submit(lambda: yf.download(
            "DX-Y.NYB", period="1y", interval="1d", progress=False, auto_adjust=True))
        # 5 años en vez de 1: el score de liquidez es ahora un percentil sobre
        # la propia historia del TLT (ver abajo) y necesita una ventana con la
        # que comparar. El DXY solo usa su SMA50, así que le sobra.
        f_tlt = yf_executor.submit(lambda: yf.download(
            "TLT", period="5y", interval="1d", progress=False, auto_adjust=True))
        dxy_df = _flatten(f_dxy.result()).dropna()
        tlt_df = _flatten(f_tlt.result()).dropna()

        dxy_current = float(dxy_df["Close"].iloc[-1])
        dxy_ma50    = float(dxy_df["Close"].rolling(50).mean().iloc[-1])
        dxy_score   = max(0, min(100, 50 - ((dxy_current / dxy_ma50 - 1) * 500)))

        # Percentil del TLT dentro de su propia historia reciente, en vez de la
        # recta `(precio − 80)/0,6`. Aquella estaba calibrada para una banda de
        # precios que ya no existe: medido el 16/08/2026, con el TLT en 82,0
        # daba 3,4 sobre 100, y el "entorno" derivado había sido RESTRICTIVO
        # 1.087 de los últimos 1.255 días (87%) -- una etiqueta que casi nunca
        # cambia no informa de nada. El percentil no puede quedarse pegado a un
        # extremo por mucho que se desplace el rango de precios, y es el mismo
        # criterio que ya usan el McClellan del RSU Algoritmo y el RS de RS/RW.
        tlt_serie       = tlt_df["Close"].dropna()
        tlt_price       = float(tlt_serie.iloc[-1])
        liquidity_score = round(float((tlt_serie < tlt_price).sum()) / len(tlt_serie) * 100, 1)
        liquidez_base   = len(tlt_serie)

        return {
            "dxy":             round(dxy_current, 2),
            "dxy_score":       round(dxy_score, 1),
            "liquidity_score": liquidity_score,
            "liquidez_base":   liquidez_base,
            "status":          "EXPANSIVO" if liquidity_score > 60 else "NEUTRAL" if liquidity_score > 40 else "RESTRICTIVO",
        }
    except Exception:
        # Antes fabricaba un DXY=103.0/score=50/NEUTRAL fijo, indistinguible
        # de un dato real -- ante fallo real de la fuente, se admite la
        # ausencia (ver precedente ya correcto en market_service.py para el
        # DXY de forex, líneas ~201-204).
        return {"dxy": None, "dxy_score": None, "liquidity_score": None,
                "liquidez_base": None, "status": None}

def _calc_alerts(price: float, ma200: float, rsu: float,
                 mvrv_z: float, puell: float, mvrv_metodo: str = "proxy") -> list:
    alerts = []

    # Proximidad a los dos niveles de referencia. Las dos ramas estaban mal:
    #
    #   - La de abajo calculaba `(ma200*0,5 − price)/price`, que solo sale
    #     POSITIVO cuando el precio ya está por debajo del nivel −50% -- o sea,
    #     avisaba de que "faltaba" para llegar a un sitio en el que ya estabas,
    #     y callaba justo durante todo el trayecto, que es cuando sirve.
    #   - La de arriba anunciaba "a X% de entrar en COMPRA FUERTE" con el
    #     precio hasta un 15% POR ENCIMA de la MA200W, cuando a esa distancia
    #     el score ronda 41 y COMPRA FUERTE empieza en 60 hacia abajo: ya se
    #     estaba dentro.
    #
    # Ahora cada aviso mide lo que dice medir: cuánto tiene que caer el precio
    # (en %) para tocar el nivel, y solo se emite si aún no lo ha tocado.
    nivel_max = ma200 * 0.5
    if price > nivel_max:
        caida_a_max = (price - nivel_max) / price * 100
        if caida_a_max <= 20:
            alerts.append({"icon": "🔥", "msg": f"A un {caida_a_max:.1f}% de caída del nivel de OPORTUNIDAD MÁXIMA (−50% de la MA200W)",
                           "color": "var(--color-accent)"})

    if price > ma200:
        caida_a_ma = (price - ma200) / price * 100
        if caida_a_ma <= 15:
            alerts.append({"icon": "📉", "msg": f"A un {caida_a_ma:.1f}% de caída de la MA200W, el soporte de referencia del modelo",
                           "color": "var(--color-secondary)"})

    if rsu < 25:
        alerts.append({"icon": "🚨", "msg": f"RSU Score extremo ({rsu:.1f}) — zona que históricamente ha coincidido con suelos, vista en un único episodio (jun 2022 – mar 2023)",
                       "color": "var(--color-accent)"})

    if mvrv_z < -0.5:
        # El "vs realized cap" que decía antes esta alerta era falso siempre
        # que el MVRV viniera del proxy -- que en producción es SIEMPRE, porque
        # CoinGecko dejó el market cap histórico detrás de una API key y la
        # rama buena no llega a ejecutarse. Afirmar una comparación on-chain
        # que no se ha hecho es peor que no decir nada: el usuario no tiene
        # forma de saber que el número mide otra cosa. Ahora cada rama dice lo
        # que de verdad ha comparado.
        detalle = ("BTC por debajo de su capitalización media del último año"
                   if mvrv_metodo == "capmercado"
                   else "precio muy por debajo de su media de 200 semanas (aprox., sin dato on-chain)")
        alerts.append({"icon": "💎", "msg": f"MVRV Z-Score negativo ({mvrv_z:.2f}) — {detalle}", "color": "var(--color-secondary)"})

    if puell < 0.6:
        alerts.append({"icon": "⛏️", "msg": f"Puell Multiple bajo ({puell:.2f}) — mineros en stress, señal de suelo", "color": "var(--color-warning)"})

    return alerts

def _run_stress_tests(price: float, allocation: float) -> list:
    return [
        {"name": "COLAPSO EXCHANGE (FTX 2.0)", "description": "Pánico sistémico temporal",
         "drop_pct": 50, "target": round(price * 0.5, 0),
         "probability": "~15% (estimación subjetiva)", "severity": "high",
         "hedge": "Mantener 70%+ en cold wallet, limitar exposición por exchange"},
        {"name": "BAN REGULATORIO G7", "description": "Prohibición coordinada en economías desarrolladas",
         "drop_pct": 35, "target": round(price * 0.65, 0),
         "probability": "~10% (estimación subjetiva)", "severity": "high",
         "hedge": "Diversificación geográfica, auto-custodia"},
        {"name": "ESTANFLACIÓN 5+ AÑOS", "description": "DXY >120, tasas >10%, recesión global",
         "drop_pct": 60, "target": round(price * 0.4, 0),
         "probability": "~20% (estimación subjetiva)", "severity": "moderate",
         "hedge": "Oro, bienes raíces, reducir exposición risk-on"},
        {"name": "RUPTURA CRIPTOGRÁFICA", "description": "Vulnerabilidad SHA256 o ataque cuántico",
         "drop_pct": 90, "target": round(price * 0.1, 0),
         "probability": "~2% (estimación subjetiva)", "severity": "extreme",
         "hedge": "Imposible hedgear — riesgo existencial aceptado"},
    ]

# ── BACKTEST ──────────────────────────────────────────────────────────────────

def get_btc_backtest() -> dict:
    from services.cache import cache
    cached = cache.get("btc:backtest")
    if cached: return cached

    try:
        # Usar CoinGecko para datos más completos
        df = _get_btc_history_coingecko(days=3650)
        if df.empty:
            # Fallback a yfinance
            raw = yf.download("BTC-USD", period="10y", interval="1d",
                              progress=False, auto_adjust=True)
            df  = _flatten(raw).dropna()
            df.rename(columns={"Close": "price"}, inplace=True)

        close  = df["price"].squeeze()
        ma200  = _calc_ma200w(close)

        # El backtest solo es válido desde el primer día con MA200W madura
        # (1400 días reales) -- sin buffer previo como el que sí tiene el
        # RSU Algoritmo, así que se recorta la serie entera (trading +
        # baseline B&H + gráfico) al mismo punto de partida, para no
        # comparar un total_return calculado solo sobre el tramo maduro
        # contra un bh_return calculado sobre todo el histórico descargado.
        first_valid = ma200.first_valid_index()
        if first_valid is None:
            return {"ok": False, "error": "Histórico insuficiente para calcular MA200W (hacen falta 1400 días)"}
        start_pos = close.index.get_loc(first_valid)

        # Calcular MVRV si tenemos market_cap
        if "market_cap" in df.columns:
            realized_cap = df["market_cap"].ewm(span=365).mean()
            mvrv_ratio   = df["market_cap"] / realized_cap
            mvrv_mean    = mvrv_ratio.rolling(365).mean()
            mvrv_std     = mvrv_ratio.rolling(365).std()
            mvrv_z_series = (mvrv_ratio - mvrv_mean) / mvrv_std
        else:
            dev           = (close - ma200) / ma200
            mvrv_z_series = dev * 3.5

        puell_series = close / close.rolling(365).mean()
        ma_safe      = ma200.replace(0, np.nan)
        ahr_series   = (close / ma_safe) / np.log(ma_safe)

        # RSU Score serie
        def rsu_point(i):
            try:
                p   = float(close.iloc[i])
                m   = float(ma200.iloc[i])
                mz  = float(mvrv_z_series.iloc[i])
                pu  = float(puell_series.iloc[i])
                ah  = float(ahr_series.iloc[i])
                if any(np.isnan(x) or np.isinf(x) for x in [p, m, mz, pu, ah]):
                    return None
                sc = _calc_rsu_score_improved(p, m, mz, pu, ah)
                return sc["total"]
            except Exception:
                return None

        thresholds = [20, 40, 60]
        results    = []
        bh_return  = (float(close.iloc[-1]) - float(close.iloc[start_pos])) / float(close.iloc[start_pos]) * 100

        for threshold in thresholds:
            capital     = 10000.0
            btc_held    = 0.0
            trades      = []
            in_position = False

            for i in range(start_pos, len(close)):
                score = rsu_point(i)
                if score is None: continue
                price = float(close.iloc[i])
                date  = close.index[i].strftime("%Y-%m-%d")

                if score < threshold and not in_position and capital > 100:
                    invest      = capital * 0.5
                    btc_bought  = invest / price
                    btc_held   += btc_bought
                    capital    -= invest
                    in_position = True
                    trades.append({"date": date, "type": "BUY",  "price": round(price, 0), "rsu": round(score, 1)})

                elif score > 80 and in_position and btc_held > 0:
                    capital    += btc_held * price
                    trades.append({"date": date, "type": "SELL", "price": round(price, 0), "rsu": round(score, 1)})
                    btc_held    = 0.0
                    in_position = False

            final_value  = capital + btc_held * float(close.iloc[-1])
            total_return = (final_value - 10000) / 10000 * 100

            results.append({
                "threshold":    threshold,
                "label":        f"RSU < {threshold}",
                "total_return": round(total_return, 1),
                "final_value":  round(final_value, 0),
                "n_buys":       len([t for t in trades if t["type"] == "BUY"]),
                "n_sells":      len([t for t in trades if t["type"] == "SELL"]),
                "trades":       trades[-10:],
                "bh_return":    round(bh_return, 1),
                "alpha":        round(total_return - bh_return, 1),
            })

        # Series para gráfico
        rsu_series   = []
        price_series = []
        step = max(1, (len(close) - start_pos) // 200)
        for i in range(start_pos, len(close), step):
            sc = rsu_point(i)
            if sc is None: continue
            d = close.index[i].strftime("%Y-%m-%d")
            rsu_series.append({"date": d, "value": round(sc, 1)})
            price_series.append({"date": d, "value": round(float(close.iloc[i]), 0)})

        result = {
            "ok":           True,
            "results":      results,
            "rsu_series":   rsu_series,
            "price_series": price_series,
            "period_start": close.index[start_pos].strftime("%Y-%m-%d"),
            "period_days":  len(close) - start_pos,
            "timestamp":    get_timestamp(),
        }
        cache.set("btc:backtest", result, 3600)
        return result

    except Exception as e:
        return {"ok": False, "error": str(e)}

# ── DASHBOARD PRINCIPAL ───────────────────────────────────────────────────────

def get_btc_dashboard() -> dict:
    from services.cache import cache, TTL
    cached = cache.get("btc:dashboard")
    if cached: return cached

    try:
        # Datos en paralelo
        with ThreadPoolExecutor(max_workers=5) as ex:
            f_cg      = ex.submit(_get_btc_price_coingecko)
            f_hist    = ex.submit(_get_btc_history_coingecko, 3650)
            f_puell   = ex.submit(_get_puell_multiple_real)
            f_hash    = ex.submit(_get_hashrate_mempool)
            f_macro   = ex.submit(_get_macro_data)
            cg_price  = f_cg.result()
            hist_df   = f_hist.result()
            puell_data = f_puell.result()
            hash_data  = f_hash.result()
            macro_data = f_macro.result()

        # Precio
        if cg_price.get("price"):
            price   = float(cg_price["price"])
            chg_24h = cg_price["chg_24h"]
        elif not hist_df.empty:
            price   = float(hist_df["price"].iloc[-1])
            chg_24h = round((price - float(hist_df["price"].iloc[-2])) / float(hist_df["price"].iloc[-2]) * 100, 2)
        else:
            raise ValueError("Sin datos de precio BTC")

        # Serie de precios
        if hist_df.empty:
            raw   = yf.download("BTC-USD", period="10y", interval="1d", progress=False, auto_adjust=True)
            raw   = _flatten(raw).dropna()
            close = raw["Close"].squeeze()
            hist_df = pd.DataFrame({"price": close})
        else:
            close = hist_df["price"].squeeze()

        ma200 = _calc_ma200w(close)
        ma_val = float(ma200.iloc[-1])
        if np.isnan(ma_val):
            return {"ok": False, "error": "Histórico insuficiente para calcular MA200W (hacen falta 1400 días)"}

        # MVRV. Dos caminos MUY distintos, y hasta ahora nada decía cuál se
        # estaba mirando: (a) market cap real ÷ su EMA365 -- una aproximación
        # del realized cap, pero construida sobre capitalización de verdad; o
        # (b) `(precio − MA200W)/MA200W × 3,5`, que no es un Z-score de nada,
        # solo la distancia a la media reescalada por una constante elegida a
        # ojo. Los dos números no son comparables entre sí, así que el método
        # viaja en la respuesta y se usa para redactar la alerta.
        mvrv_data = _calc_mvrv_z_improved(hist_df)
        if mvrv_data.get("mvrv_z") is not None:
            mvrv_z = mvrv_data["mvrv_z"]
            mvrv_metodo = "capmercado"
        else:
            mvrv_z = float(((close - ma200) / ma200 * 3.5).iloc[-1])
            mvrv_metodo = "proxy"

        # Puell — real si disponible, proxy si no. Verificado el 11/08/2026:
        # en producción SÍ llega el real (Blockchain.com, ingresos diarios de
        # mineros contra su SMA365), pese a que la UI lo anunciaba como una
        # aproximación de precio. De ahí que ahora se declare cuál es.
        if puell_data.get("puell"):
            puell = puell_data["puell"]
            puell_metodo = "real"
        else:
            puell = _calc_puell_from_series(close)
            puell_metodo = "proxy"

        # AHR999
        ahr_data = _calc_ahr999_improved(close, ma200)
        ahr      = ahr_data.get("ahr999") or float(((close / ma200.replace(0, np.nan)) / np.log(ma200.replace(0, np.nan))).iloc[-1])

        # RSU Score
        scores   = _calc_rsu_score_improved(price, ma_val, mvrv_z, puell, ahr)
        rsu      = scores["total"]
        deviation = (price - ma_val) / ma_val * 100

        zone     = _get_zone(rsu)
        signal   = _get_signal_label(rsu)
        halving  = _get_halving_cycle()
        alerts   = _calc_alerts(price, ma_val, rsu, mvrv_z, puell, mvrv_metodo)
        stress   = _run_stress_tests(price, zone["allocation"])

        # MA curvatura
        slope     = ma200.diff(30)
        curv      = slope.diff(30)
        slope_pct = round(float(slope.iloc[-1]) / ma_val * 100, 3) if ma_val > 0 else 0
        curvature = {
            "slope":        slope_pct,
            "curvature":    round(float(curv.iloc[-1]), 6),
            "trend":        "ALCISTA FUERTE" if slope_pct > 1 else "ALCISTA" if slope_pct > 0.2 else "LATERAL" if slope_pct > -0.2 else "BAJISTA",
            "acceleration": "ACELERANDO" if float(curv.iloc[-1]) > 0 else "DESACELERANDO",
            "ma_value":     round(ma_val, 0),
        }

        # Niveles
        levels = {
            "ma200":    round(ma_val, 0),
            "minus_25": round(ma_val * 0.75, 0),
            "minus_50": round(ma_val * 0.50, 0),
            "plus_25":  round(ma_val * 1.25, 0),
            "plus_50":  round(ma_val * 1.50, 0),
        }

        # Chart data (3 años, semanal)
        cutoff   = datetime.now() - timedelta(days=3*365)
        mask     = close.index >= cutoff
        close_3y = close[mask]
        ma_3y    = ma200[mask]
        chart_data = []
        step = max(1, len(close_3y) // 150)
        for i in range(0, len(close_3y), step):
            mv = ma_3y.iloc[i]
            if pd.isna(mv): continue
            chart_data.append({
                "date":    close_3y.index[i].strftime("%Y-%m-%d"),
                "price":   round(float(close_3y.iloc[i]), 0),
                "ma200":   round(float(mv), 0),
                "minus25": round(float(mv * 0.75), 0),
                "minus50": round(float(mv * 0.50), 0),
                "plus25":  round(float(mv * 1.25), 0),
                "plus50":  round(float(mv * 1.50), 0),
            })

        # `close.max()` es el máximo de la VENTANA descargada, no el máximo
        # histórico de bitcoin. Con la ventana actual acierta por casualidad
        # (el ATH real cae dentro), pero dejaría de acertar en silencio si la
        # fuente cambiara o la ventana se acortara. Se publica junto a la fecha
        # desde la que se ha mirado, para que el número no pueda mentir sin que
        # se vea.
        ath       = round(float(close.max()), 0)
        drawdown  = round((price - ath) / ath * 100, 1)
        ath_desde = close.index[0].strftime("%Y-%m-%d")

        # Avisos para la banda compartida del frontend (core/ui.js::avisosBanda).
        # Se redactan aquí, donde se sabe qué camino tomó cada dato, en vez de
        # dejar que la página los adivine.
        avisos = []
        if mvrv_metodo != "capmercado":
            avisos.append({"tipo": "parcial", "mensaje":
                "El MVRV Z-Score de hoy no usa datos on-chain: la fuente de capitalización histórica "
                "dejó de ser gratuita, así que se estima con el precio frente a su media de 200 semanas. "
                "Eso lo convierte, de hecho, en una segunda lectura del mismo factor que ya pesa un 40%."})
        if puell_metodo != "real":
            avisos.append({"tipo": "parcial", "mensaje":
                "El Puell Multiple de hoy es una aproximación de precio: no ha llegado el dato de ingresos "
                "de mineros. Es el único de los cuatro factores que mide algo distinto del precio, así que "
                "sin él el modelo se queda apoyado en una sola señal."})
        if macro_data.get("dxy") is None:
            avisos.append({"tipo": "parcial", "mensaje":
                "Sin datos macro en este momento (dólar y liquidez): las tarjetas de entorno aparecen vacías "
                "en vez de con un valor supuesto."})
        avisos.append({"tipo": "antiguo", "mensaje":
            f"El máximo histórico y la caída desde máximos se miden sobre el histórico disponible "
            f"(desde {ath_desde}), no sobre toda la vida de bitcoin."})

        # Data sources badge
        sources = {
            "price":   cg_price.get("source", "yfinance"),
            "puell":   puell_data.get("source", "proxy precio"),
            "mvrv":    mvrv_data.get("source", "proxy precio"),
            "hashrate": hash_data.get("source", "N/A"),
        }

        result = {
            "ok":          True,
            "price":       round(price, 0),
            "chg_24h":     chg_24h,
            "ma200":       round(ma_val, 0),
            "deviation":   round(deviation, 1),
            "ath":         ath,
            "ath_desde":   ath_desde,
            "drawdown":    drawdown,
            "avisos":      avisos,
            "rsu_score":   rsu,
            "rsu_signal":  signal,
            "zone":        zone,
            # `origen` por componente. Hasta ahora la página decía en bloque
            # que los tres eran "aproximaciones basadas en precio/MA200W", y
            # eso era falso en los dos sentidos: el Puell suele ser un dato
            # on-chain REAL (ingresos de mineros vía Blockchain.com) que se
            # estaba infravendiendo, y el MVRV no tiene nada que ver con la
            # MA200W cuando corre por su rama buena. Cada tarjeta dice ahora de
            # dónde sale su número. Ver auditoría de BTC Stratum, #1.
            "components": {
                "ma200":  {"score": scores["ma200"],  "raw": round(deviation/100, 3), "weight": 40,
                           "origen": ORIGEN_MA200},
                "mvrv":   {"score": scores["mvrv"],   "raw": round(mvrv_z, 3),        "weight": 30,
                           "origen": ORIGEN_MVRV_REAL if mvrv_metodo == "capmercado" else ORIGEN_MVRV_PROXY},
                "puell":  {"score": scores["puell"],  "raw": round(puell, 3),         "weight": 20,
                           "origen": ORIGEN_PUELL_REAL if puell_metodo == "real" else ORIGEN_PUELL_PROXY},
                "ahr999": {"score": scores["ahr999"], "raw": round(ahr, 4),           "weight": 10,
                           "origen": ORIGEN_AHR999},
            },
            "curvature":   curvature,
            "halving":     halving,
            "macro":       macro_data,
            "levels":      levels,
            "alerts":      alerts,
            "stress":      stress,
            "chart_data":  chart_data,
            "puell_data":  puell_data,
            "hash_data":   hash_data,
            "mvrv_data":   mvrv_data,
            "sources":     sources,
            "timestamp":   get_timestamp(),
        }
        cache.set("btc:dashboard", result, TTL.get("market", 300))
        return result

    except Exception as e:
        return {"ok": False, "error": str(e)}