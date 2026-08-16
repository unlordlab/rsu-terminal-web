import math
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
            # actual (`/simple/price`) sigue siendo libre. La serie de precios
            # cae al respaldo de yfinance, que es equivalente para lo que se
            # usa aquí. (Desde el 16/08/2026 esto ya no afecta al MVRV: se lee
            # de bitcoin-data.com, que sí lo publica gratis y de verdad.)
            print(f"[BTCStratum] CoinGecko /market_chart devolvió {r.status_code} — "
                  f"se usa yfinance para la serie de precios")
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

ORIGEN_MA200 = "Precio vs media de 200 semanas"

# bitcoin-data.com publica métricas on-chain reales sin clave de API
# (verificado el 16/08/2026: MVRV Z-Score, precio realizado y Puell, con unos
# 4 años de histórico diario). Es la pieza que faltaba desde que CoinGecko dejó
# la capitalización histórica detrás de una API key: hasta hoy, el MVRV que
# veía el usuario NUNCA era on-chain, era la distancia del precio a su media de
# 200 semanas multiplicada por 3,5 -- el mismo dato que ya tenía delante.
BITCOIN_DATA_URL = "https://bitcoin-data.com/v1/{metrica}/last"


def _bitcoin_data(metrica: str, campo: str):
    """Último valor de una métrica on-chain. None si la fuente no responde --
    nunca se sustituye por una estimación de precio: es exactamente el error
    que se está corrigiendo aquí."""
    try:
        r = requests.get(BITCOIN_DATA_URL.format(metrica=metrica), timeout=8,
                         headers={"Accept": "application/json"})
        if r.status_code != 200:
            return None, None
        d = r.json()
        v = d.get(campo)
        return (round(float(v), 4) if v is not None else None), d.get("d")
    except Exception:
        return None, None


def _get_contexto_onchain(puell_data: dict, hash_data: dict) -> dict:
    """Datos on-chain REALES, al lado del score pero fuera de él.

    Antes iban dentro, con pesos (MVRV 30%, Puell 20%, AHR999 10%). Medido el
    16/08/2026, ninguno mejoraba la capacidad del score para ordenar el retorno
    futuro, y dos de ellos la empeoraban -- ver el bloque de EL SCORE. Siguen
    aquí porque informan (¿están los mineros bajo presión?, ¿cuánto se aleja el
    precio del coste medio al que se movieron las monedas?), pero un dato que
    informa no tiene por qué entrar en la fórmula.
    """
    mvrv_z, mvrv_fecha = _bitcoin_data("mvrv-zscore", "mvrvZscore")
    precio_realizado, _ = _bitcoin_data("realized-price", "realizedPrice")

    ribbon = None
    if hash_data and hash_data.get("hashrate_ehs") and hash_data.get("avg30_ehs"):
        # Hash Ribbon: el hashrate reciente frente a su media. Por debajo de 1
        # indica mineros apagando máquinas (capitulación).
        ribbon = round(hash_data["hashrate_ehs"] / hash_data["avg30_ehs"], 3)

    return {
        "mvrv_z":           mvrv_z,
        "mvrv_fecha":       mvrv_fecha,
        "precio_realizado": round(precio_realizado) if precio_realizado else None,
        "puell":            (puell_data or {}).get("puell"),
        "puell_ingresos":   (puell_data or {}).get("daily_revenue"),
        "puell_media":      (puell_data or {}).get("sma365_revenue"),
        "hashrate_ehs":     (hash_data or {}).get("hashrate_ehs"),
        "hash_ribbon":      ribbon,
        "fuentes": {
            "mvrv":     "bitcoin-data.com" if mvrv_z is not None else None,
            "puell":    (puell_data or {}).get("source"),
            "hashrate": (hash_data or {}).get("source"),
        },
    }

# ── EL SCORE ──────────────────────────────────────────────────────────────────
#
# Hasta el 16/08/2026 esto era una media ponderada de cuatro sub-scores
# (MA200W 40%, MVRV 30%, Puell 20%, AHR999 10%), cada uno una rampa lineal
# recortada a [0,100]. Medido sobre 2.953 sesiones de BTC-USD con MA200W madura
# (desde 2018-07), aquel diseño tenía tres defectos que se anulaban entre sí:
#
#   1. NO ERAN CUATRO FACTORES. Con el MVRV en su rama de respaldo (la única
#      que corre en producción, porque la capitalización histórica dejó de ser
#      gratuita), `mvrv_z = 3,5·(x−1)` y `ma_score = 100·(x−1)+50` con
#      `x = precio/MA200W`, de donde `mvrv_score = 0,7·ma_score − 5` EXACTO.
#      El 70% del peso era una sola variable escalada dos veces.
#   2. EL AHR999 ERA UNA CONSTANTE. Valía 0 en 2.864 de 2.953 sesiones (97%):
#      su fórmula solo puntúa si el precio supera 5,6 veces su MA200W.
#   3. EL RECORTE TIRABA LA MITAD DE LA INFORMACIÓN. El sub-score de la MA200W
#      quedaba pegado a 0 o a 100 en el 63% de los días, con mediana 100.
#
# La prueba que zanjó el rediseño: ordenar el retorno futuro. El compuesto de
# cuatro factores daba una correlación de rango de −0,576 a un año; la simple
# distancia a la MA200W, a secas, daba −0,646. Es decir, montar el compuesto
# EMPEORABA el resultado respecto a usar solo su propio ingrediente dominante.
# Se probaron además, uno a uno, todos los candidatos a factor independiente:
# el AHR999 bien implementado (+0,939 de correlación con la distancia a la
# MA200W: redundante), el Puell real (señal propia −0,047 a un año: ninguna),
# el Hash Ribbon (−0,043) y la posición en el ciclo de halving (+0,092).
# Ninguno mejoraba la mezcla; el Puell al 25% la bajaba de −0,792 a −0,721.
#
# Así que el score es UN factor, bien transformado. Los datos on-chain reales
# (MVRV, Puell, hashrate) siguen mostrándose, pero como contexto aparte, sin
# fundirse en el número con pesos inventados.

# Logística en vez de rampa recortada: es estrictamente monótona, así que
# conserva ÍNTEGRO el orden del factor (la correlación de rango es idéntica a
# la del dato crudo), y acotada a 0-100 sin llegar nunca a saturar.
# K y C solo deciden cómo se reparte la escala en pantalla -- al ser monótona,
# no pueden alterar el poder de ordenación. Se eligieron para que los dos
# cortes que sí salen de los datos (ver ZONAS) caigan en 80 y 90 redondos.
VAL_K = 4.15
VAL_C = 0.231


def _calc_rsu_score(price: float, ma200: float) -> float:
    """RSU Score: lo lejos que está bitcoin de su media de 200 semanas, en una
    escala 0-100 donde 0 es lo más barato. Devuelve None si no hay MA200W."""
    if not price or not ma200 or price <= 0 or ma200 <= 0:
        return None
    x = math.log(price / ma200)
    s = 100 / (1 + math.exp(-VAL_K * (x - VAL_C)))
    # La logística nunca alcanza 0 ni 100, pero redondear a un decimal sí los
    # alcanza, y publicar un 0,0 o un 100,0 exactos volvería a decir «se ha
    # tocado el extremo» cuando no se ha tocado -- justo la mentira que contaba
    # la rampa recortada anterior. Los topes corresponden a un precio 4,2 veces
    # por debajo o 6,6 veces por encima de la media de 200 semanas: fuera de
    # todo lo que bitcoin ha hecho nunca, así que en la práctica no se rozan.
    return round(min(99.9, max(0.1, s)), 1)


def _score_a_precio(score: float, ma200: float) -> float:
    """La inversa: a qué precio corresponde un score. Sirve para traducir los
    cortes de zona a niveles de precio concretos, que es como se entienden."""
    if not (0 < score < 100) or not ma200:
        return None
    x = math.log(score / (100 - score)) / VAL_K + VAL_C
    return round(ma200 * math.exp(x), 0)

# Los colores viajan como expresiones CSS con tokens del tema, no como hex.
# Antes esta escalera inventaba seis verdes propios (#006b1b, #009627, #28a745,
# #78a832, #aa8c28) que no existían en ningún otro módulo de la terminal y que
# se quedaban clavados con cualquier tema que no fuera el oscuro por defecto.
# La rampa se construye ahora mezclando los dos tokens semánticos que ya
# definen los extremos -- así el degradado sigue leyéndose igual en los nueve
# temas. `color-mix` ya se usa en components/sidebar.js.
def _mezcla(pct_accent: int) -> str:
    return f"color-mix(in srgb, var(--color-accent) {pct_accent}%, var(--color-warning))"

# Las zonas eran seis, con cortes en 20/40/60/70/85 heredados sin respaldo.
# Medido el 16/08/2026, esos seis tramos NO ordenaban el retorno futuro: el de
# «BUENA COMPRA» rendía más a tres meses (+30,5%) que el de «OPORTUNIDAD
# MÁXIMA» (+28,1%). Estas cuatro sí, y además aguantan la prueba de partir la
# muestra por la mitad y repetirla en cada trozo por separado:
#
#   tramo    precio vs MA200W    n     +1 año   % en pérdidas   1ª mitad   2ª mitad
#   <50      hasta +26%         675   +143,6%       0,1%         +276,3%    +103,4%
#   50-80    +26% a +76%        580   +183,8%       7,8%         +273,0%     +84,9%
#   80-90    +76% a +114%       427    +69,5%      34,9%         +163,7%      +8,4%
#   >=90     más de +114%       906     −6,4%      67,8%           +0,3%     −24,6%
#
# El orden se mantiene entero en las dos mitades, y el porcentaje de casos que
# acaban en pérdidas crece de forma monótona en ambas. Muestra: 2.588 sesiones
# de 2018-07 a 2025-08 con retorno a un año disponible -- unos dos ciclos de
# halving, que es poco en lo que de verdad cuenta. Los números viajan con la
# zona (`evidencia`) para que la página pueda enseñar en qué se apoya cada
# consejo en vez de darlo por bueno.
ZONAS = [
    (0,  50,  "OPORTUNIDAD",  "var(--color-accent)",  25, "ALTA",
     {"n": 675, "retorno_1a": 143.6, "pct_perdidas": 0.1}),
    (50, 80,  "ACUMULACIÓN",  _mezcla(60),            15, "MEDIA",
     {"n": 580, "retorno_1a": 183.8, "pct_perdidas": 7.8}),
    (80, 90,  "PRECAUCIÓN",   "var(--color-warning)",  5, "BAJA",
     {"n": 427, "retorno_1a": 69.5,  "pct_perdidas": 34.9}),
    (90, 101, "RIESGO ALTO",  "var(--color-danger)",   0, "ESPERAR",
     {"n": 906, "retorno_1a": -6.4,  "pct_perdidas": 67.8}),
]
CORTES_ZONA = [desde for desde, *_ in ZONAS if desde > 0]
ZONAS_MUESTRA = "lo que pasó cada día entre julio de 2018 y agosto de 2025"


def _get_zone(rsu: float) -> dict:
    for desde, hasta, nombre, color, alloc, urgencia, ev in ZONAS:
        if desde <= rsu < hasta:
            return {"zone": nombre, "color": color, "allocation": alloc,
                    "urgency": urgencia, "desde": desde, "hasta": hasta,
                    "evidencia": ev, "muestra": ZONAS_MUESTRA}
    return {"zone": "RIESGO ALTO", "color": "var(--color-danger)", "allocation": 0,
            "urgency": "ESPERAR", "desde": 90, "hasta": 101,
            "evidencia": ZONAS[-1][6], "muestra": ZONAS_MUESTRA}


def _get_signal_label(rsu: float) -> dict:
    if rsu < 30:   return {"label": "MUY BARATO PARA LO QUE SUELE VALER", "color": "var(--color-accent)"}
    elif rsu < 50: return {"label": "BARATO PARA LO QUE SUELE VALER",     "color": "var(--color-accent)"}
    elif rsu < 80: return {"label": "EN PRECIOS NORMALES",               "color": _mezcla(40)}
    elif rsu < 90: return {"label": "CARO PARA LO QUE SUELE VALER",      "color": "var(--color-warning)"}
    else:          return {"label": "MUY CARO PARA LO QUE SUELE VALER",  "color": "var(--color-danger)"}

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

    if progress < 0.2:   phase = "RECIÉN EMPEZADO"
    elif progress < 0.4: phase = "SUBIDA TEMPRANA"
    elif progress < 0.6: phase = "SUBIDA AVANZADA"
    elif progress < 0.8: phase = "TRAMO FINAL"
    else:                phase = "ESPERANDO EL SIGUIENTE"

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

def _calc_alerts(price: float, ma200: float, rsu: float, contexto: dict = None) -> list:
    """Avisos de proximidad y de extremo. Todos anclados a los cortes de zona
    ya calibrados (ver ZONAS), no a umbrales sueltos: si un aviso dice que
    faltan tres puntos para entrar en PRECAUCIÓN, es la misma frontera que
    pinta la tarjeta de zona, no otra distinta escrita en otro sitio."""
    alerts   = []
    contexto = contexto or {}

    # Cuánto tiene que MOVERSE el precio para cruzar la frontera de zona más
    # cercana. La versión anterior calculaba `(ma200*0,5 − price)/price`, que
    # solo sale positivo cuando el precio ya está por debajo del nivel: avisaba
    # de lo que "faltaba" para llegar a un sitio en el que ya estabas, y callaba
    # durante todo el trayecto, que es cuando el aviso sirve.
    for desde, hasta, nombre, _c, _a, _u, _e in ZONAS:
        if rsu >= hasta:                       # frontera por debajo: hay que caer
            objetivo = _score_a_precio(hasta, ma200)
            if objetivo and price > objetivo:
                caida = (price - objetivo) / price * 100
                if caida <= 15:
                    alerts.append({"icon": "🔥", "color": "var(--color-accent)",
                                   "msg": f"Si bitcoin baja un {caida:.1f}% (hasta ${objetivo:,.0f}) pasa a zona {nombre}".replace(",", ".")})
                break

    if rsu < 50:
        alerts.append({"icon": "🚨", "color": "var(--color-accent)",
                       "msg": "Bitcoin cotiza barato para lo que ha valido de media estos últimos cuatro años"})
    elif rsu >= 90:
        alerts.append({"icon": "⚠️", "color": "var(--color-danger)",
                       "msg": "Bitcoin está caro: cuando ha estado así de caro, un año después el precio era más bajo en 68 de cada 100 casos"})

    # Contexto on-chain: informa, pero NO entra en el score (ver EL SCORE).
    # Cada aviso dice de dónde sale su número; ninguno se estima desde el precio.
    mvrv = contexto.get("mvrv_z")
    if mvrv is not None and mvrv < 0:
        alerts.append({"icon": "💎", "color": "var(--color-secondary)",
                       "msg": "De media, quien ya tiene bitcoins los compró más caros de lo que valen ahora"})

    puell = contexto.get("puell")
    if puell is not None and puell < 0.6:
        # El porcentaje sale del propio dato: decir "la mitad" con un Puell de
        # 0,40 sería redondear a la baja una cifra que ya tenemos exacta.
        alerts.append({"icon": "⛏️", "color": "var(--color-warning)",
                       "msg": f"Los mineros están ingresando un {puell * 100:.0f}% de lo que ingresan "
                              f"en un año normal: muchos apagan máquinas y les queda menos que vender"})

    ribbon = contexto.get("hash_ribbon")
    if ribbon is not None and ribbon < 0.97:
        alerts.append({"icon": "🔌", "color": "var(--color-warning)",
                       "msg": "Hay mineros apagando máquinas: la potencia de la red baja frente a su media del último mes"})

    return alerts

def _run_stress_tests(price: float, allocation: float) -> list:
    return [
        {"name": "Quiebra de una plataforma grande", "description": "Como pasó con FTX en 2022: una casa de cambio importante cae y arrastra al mercado durante meses",
         "drop_pct": 50, "target": round(price * 0.5, 0),
         "severity": "high",
         "hedge": "Guardar la mayor parte en una cartera propia, no en la plataforma donde compras"},
        {"name": "Prohibición en los países ricos", "description": "Estados Unidos, Europa y Japón se ponen de acuerdo para prohibirlo",
         "drop_pct": 35, "target": round(price * 0.65, 0),
         "severity": "high",
         "hedge": "No tenerlo todo en plataformas de un solo país, y guardarlo tú mismo"},
        {"name": "Crisis económica larga", "description": "Años de inflación alta con la economía parada: el dinero se va a refugios más tradicionales",
         "drop_pct": 60, "target": round(price * 0.4, 0),
         "severity": "moderate",
         "hedge": "Tener también cosas que aguantan mejor la inflación, como oro o vivienda"},
        {"name": "Se rompe el cifrado que lo protege", "description": "Alguien encuentra la forma de falsificar transacciones. Es lo único de esta lista que acabaría con bitcoin",
         "drop_pct": 90, "target": round(price * 0.1, 0),
         "severity": "extreme",
         "hedge": "No hay forma de protegerse: es el riesgo que se asume al tener bitcoin"},
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

        # El backtest usa EXACTAMENTE el mismo score que el dashboard. Hasta el
        # 16/08/2026 no era así: el dashboard puntuaba con el Puell real
        # (ingresos de mineros de Blockchain.com) y aquí se usaba
        # `close/close.rolling(365).mean()`, un cociente de precio -- dos
        # magnitudes distintas alimentando la misma fórmula, de modo que lo que
        # se validaba no era lo que se enseñaba (hallazgo #5 de la auditoría).
        # Al quedarse el score en un único factor derivado del precio y la
        # MA200W, esa divergencia desaparece de raíz: no hay nada que el
        # dashboard pueda leer de una fuente y el backtest de otra.
        def rsu_point(i):
            try:
                p = float(close.iloc[i])
                m = float(ma200.iloc[i])
                if np.isnan(p) or np.isnan(m) or np.isinf(p) or np.isinf(m):
                    return None
                return _calc_rsu_score(p, m)
            except Exception:
                return None

        # Umbrales sobre la escala nueva, alineados con los cortes de zona ya
        # calibrados (50 = frontera de OPORTUNIDAD, 80 = de PRECAUCIÓN).
        thresholds   = [50, 65, 80]
        VENTA_UMBRAL = 90   # la frontera de RIESGO ALTO, la misma que ve el usuario
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

                elif score > VENTA_UMBRAL and in_position and btc_held > 0:
                    capital    += btc_held * price
                    trades.append({"date": date, "type": "SELL", "price": round(price, 0), "rsu": round(score, 1)})
                    btc_held    = 0.0
                    in_position = False

            final_value  = capital + btc_held * float(close.iloc[-1])
            total_return = (final_value - 10000) / 10000 * 100

            results.append({
                "threshold":    threshold,
                "label":        f"Comprar con RSU < {threshold}",
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
            "venta_umbral": VENTA_UMBRAL,
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

        # El score: un solo factor, la distancia del precio a su media de 200
        # semanas, transformado con una logística que conserva el orden entero
        # y no satura. Ver el bloque EL SCORE para por qué dejó de ser una
        # media ponderada de cuatro cosas que en realidad eran una y media.
        rsu       = _calc_rsu_score(price, ma_val)
        deviation = (price - ma_val) / ma_val * 100

        # Datos on-chain REALES, al lado del score y fuera de él.
        contexto = _get_contexto_onchain(puell_data, hash_data)

        zone     = _get_zone(rsu)
        signal   = _get_signal_label(rsu)
        halving  = _get_halving_cycle()
        alerts   = _calc_alerts(price, ma_val, rsu, contexto)
        stress   = _run_stress_tests(price, zone["allocation"])

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
            # Las bandas son las FRONTERAS DE ZONA, recalculadas sobre la
            # MA200W de cada día. Antes eran ±25% y ±50% de la media: unos
            # múltiplos redondos que, tras calibrar las zonas, ya no marcaban
            # ninguna frontera -- el gráfico dibujaba un juego de líneas y las
            # tablas de al lado otro distinto.
            punto = {
                "date":  close_3y.index[i].strftime("%Y-%m-%d"),
                "price": round(float(close_3y.iloc[i]), 0),
                "ma200": round(float(mv), 0),
            }
            for corte in CORTES_ZONA:
                punto[f"z{corte}"] = _score_a_precio(corte, float(mv))
            chart_data.append(punto)

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
        # Se redactan aquí, donde se sabe qué camino tomó cada dato.
        avisos = []
        if contexto.get("mvrv_z") is None:
            avisos.append({"tipo": "parcial", "mensaje":
                "El MVRV Z-Score no está disponible ahora mismo. Aparece vacío en vez de estimarse "
                "con el precio: esa estimación era, punto por punto, el mismo dato que ya muestra el "
                "RSU Score, y presentarla como una medida on-chain independiente era engañoso."})
        if contexto.get("puell") is None:
            avisos.append({"tipo": "parcial", "mensaje":
                "No ha llegado el dato de ingresos de mineros, así que el Puell Multiple aparece vacío."})
        if macro_data.get("dxy") is None:
            avisos.append({"tipo": "parcial", "mensaje":
                "Sin datos macro en este momento (dólar y liquidez): las tarjetas de entorno aparecen vacías "
                "en vez de con un valor supuesto."})
        avisos.append({"tipo": "antiguo", "mensaje":
            f"El máximo que se muestra es el más alto desde {ath_desde}, que es hasta donde llegan los datos "
            f"que usamos. No es necesariamente el máximo de toda la historia de bitcoin."})

        sources = {
            "price":    cg_price.get("source", "yfinance"),
            "puell":    contexto["fuentes"].get("puell") or "sin dato",
            "mvrv":     contexto["fuentes"].get("mvrv") or "sin dato",
            "hashrate": contexto["fuentes"].get("hashrate") or "sin dato",
        }

        # Los cortes de zona traducidos a precio: es como de verdad se entiende
        # un score. "80" no dice nada; "$112.000" sí.
        fronteras = [
            {"score": desde, "zona": nombre, "precio": _score_a_precio(desde, ma_val)}
            for desde, _h, nombre, _c, _a, _u, _e in ZONAS if desde > 0
        ]

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
            # El score dejó de ser una media ponderada de cuatro sub-scores.
            # `score_detalle` explica de qué está hecho el único número que hay,
            # y `contexto` trae los datos on-chain reales que antes se fundían
            # dentro de él con pesos que no se sostenían. Ver el bloque EL SCORE.
            "score_detalle": {
                "origen":     ORIGEN_MA200,
                "ma200":      round(ma_val, 0),
                "desviacion": round(deviation, 1),
                "fronteras":  fronteras,
                "muestra":    ZONAS_MUESTRA,
            },
            "contexto":    contexto,
            "halving":     halving,
            "macro":       macro_data,
            "alerts":      alerts,
            "stress":      stress,
            "chart_data":  chart_data,
            "puell_data":  puell_data,
            "hash_data":   hash_data,
            "sources":     sources,
            "timestamp":   get_timestamp(),
        }
        cache.set("btc:dashboard", result, TTL.get("market", 300))
        return result

    except Exception as e:
        return {"ok": False, "error": str(e)}