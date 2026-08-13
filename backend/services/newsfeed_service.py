import re
from functools import lru_cache
import math
import html as _html
import requests
import time
import xml.etree.ElementTree as ET
import sys, os
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturoExpirado, as_completed
import yfinance as yf
from config import settings
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "shared"))
from time_utils import get_timestamp  # noqa: E402
from sp500_universe import SP500_SECTOR_MAP  # noqa: E402
from services.cache import cache, TTL  # noqa: E402

# ── SOURCES ───────────────────────────────────────────────────────────────────

# Auditadas una a una el 28/07/2026 con criterio DOBLE: que respondan 200 Y
# que su artículo más reciente sea realmente reciente. Cuatro estaban muertas
# y se sustituyeron por equivalentes verificados vivos (<1h de antigüedad):
#   - reuters    -> feeds.reuters.com ni siquiera resuelve DNS (Reuters cerró
#                   sus RSS públicos). Sustituida por FT.
#   - wsj        -> respondía 200 con 20 artículos... el más reciente de enero
#                   de 2025, CONGELADO 547 días. Es el caso peligroso: no
#                   falla, sirve contenido plausible pero obsoleto, y solo se
#                   detecta comprobando fechas. Sustituida por Seeking Alpha.
#   - blockworks -> los 8 últimos posts agrupados hace ~202 días: feed
#                   abandonado. Sustituida por CoinDesk (misma temática cripto).
#   - gurufocus  -> HTTP 403. Sustituida por Business Insider Markets.
# NO se tocaron fed/macroalf/valuewalk aunque su último post tenga días: se
# comprobó la distribución de fechas y publican de forma regular pero
# espaciada (la Fed no saca notas a diario) -- baja frecuencia legítima, no
# congelamiento. Confundir ambas cosas habría tirado fuentes que funcionan.
#
# Re-auditadas el 13/08/2026, mismo criterio doble más un tercero que antes no
# existía: que quepan en el presupuesto de tiempo (ver FUENTE_TIMEOUT). Tres
# bajas, medidas en la misma pasada que el resto para que la comparación sea
# justa:
#   - benzinga -> viva (200, 10 items de 21h), pero tarda 4,2s contra un
#                 timeout de 2,5s: expira SIEMPRE. No aportaba ni un item y sí
#                 dos intentos de conexión por cada carga del feed.
#   - macroalf -> 31,0 días. Justo al otro lado del corte de 30. La excepción
#                 de "baja frecuencia legítima" que se le concedió en julio ya
#                 no se sostiene: el Substack dejó de publicar.
#   - valuewalk-> 44,7 días. Mismo caso, sin margen de duda.
# Las dos rancias respondían 200 con 10 artículos cada una -- exactamente el
# fallo silencioso que documenta MAX_ANTIGUEDAD_MINS. El filtro hacía su
# trabajo (los descartaba), pero se pagaba la petición igual.
SOURCES = [
    {"id":"ft",           "label":"FT",          "url":"https://www.ft.com/companies?format=rss"},
    {"id":"seekingalpha", "label":"SEEKING A.",  "url":"https://seekingalpha.com/market_currents.xml"},
    {"id":"cnbc",         "label":"CNBC",        "url":"https://www.cnbc.com/id/20910258/device/rss/rss.html"},
    {"id":"marketwatch",  "label":"MKTWATCH",    "url":"https://feeds.content.dowjones.io/public/rss/mw_topstories"},
    {"id":"yahoofinance", "label":"YAHOO FIN",   "url":"https://finance.yahoo.com/rss/topstories"},
    {"id":"zerohedge",    "label":"ZEROHEDGE",   "url":"https://feeds.feedburner.com/zerohedge/feed"},
    {"id":"investing",    "label":"INVESTING",   "url":"https://www.investing.com/rss/news.rss"},
    {"id":"reddit",       "label":"REDDIT",      "url":"https://www.reddit.com/r/investing+stocks+options/new.rss"},
    # Este feed llevaba dos bugs preexistentes encadenados, ambos silenciosos
    # (ver _parse_rss/_fetch_source): estaba declarado "fmt":"atom" siendo RSS,
    # y además empieza con BOM UTF-8, que rompía el parseo. Ya no hace falta
    # declarar formato -- se detecta solo.
    {"id":"fed",          "label":"FED",         "url":"https://www.federalreserve.gov/feeds/press_all.xml"},
    {"id":"coindesk",     "label":"COINDESK",    "url":"https://www.coindesk.com/arc/outboundfeeds/rss/"},
    {"id":"businessins",  "label":"BUS. INSIDER","url":"https://markets.businessinsider.com/rss/news"},
    # Altas del 13/08/2026 (medidas en la misma pasada que las de arriba, ver
    # el bloque de bajas). Cada una cubre una dimensión que las anteriores no
    # tenían, en vez de sumar otra cabecera generalista más:
    #   ftmarkets  - FT ya estaba, pero solo su sección de EMPRESAS; mercados
    #                es otra portada distinta (0,2s, 2,9h).
    #   bls        - fuente PRIMARIA del IPC y del informe de empleo, las dos
    #                publicaciones que el clasificador puntúa más alto. Trae un
    #                item por pasada, pero es el original, no la crónica.
    #   ecb        - había Fed y no había BCE. Baja frecuencia legítima, igual
    #                que la Fed (2 días en la medición).
    #   oilprice   - energía y materias primas: cero cobertura hasta ahora.
    #   bbcbiz     - el feed más rápido y más fresco de los 24 probados.
    #   wolfstreet - macro y crédito; ocupa el hueco que deja MACRO ALF.
    {"id":"ftmarkets",    "label":"FT MERCADOS", "url":"https://www.ft.com/markets?format=rss"},
    {"id":"bls",          "label":"BLS",         "url":"https://www.bls.gov/feed/bls_latest.rss"},
    {"id":"ecb",          "label":"BCE",         "url":"https://www.ecb.europa.eu/rss/press.html"},
    {"id":"oilprice",     "label":"OILPRICE",    "url":"https://oilprice.com/rss/main"},
    {"id":"bbcbiz",       "label":"BBC",         "url":"https://feeds.bbci.co.uk/news/business/rss.xml"},
    {"id":"wolfstreet",   "label":"WOLF STREET", "url":"https://wolfstreet.com/feed/"},
]

# Máxima antigüedad admitida para un artículo. Un feed que se congela sigue
# respondiendo 200 y sirviendo sus últimos artículos para siempre (el de WSJ
# llevaba 547 días así sin que nadie lo notara): sus items quedaban al final
# de la lista por el orden por fecha, pero ocupaban cupo y desplazaban
# noticias reales. 30 días es holgado a propósito -- las fuentes de baja
# frecuencia legítimas (Fed, Substacks) siguen entrando, y un congelamiento
# de verdad (meses) se descarta solo.
MAX_ANTIGUEDAD_MINS = 30 * 24 * 60

# Presupuesto de tiempo del feed. Los tres números salen de medir las 14
# fuentes reales el 11/08/2026, no de elegirlos a ojo:
#
#   13 de 14 respondieron por debajo de 0,7s (la más lenta que aportaba algo,
#   0,61s). La catorceava, benzinga, se comió los 8s enteros del timeout que
#   había antes para devolver CERO items -- y como el bucle esperaba a todas,
#   ESA era la latencia del endpoint: 8,15s de reloj para el usuario.
#
# FUENTE_TIMEOUT da cuatro veces el margen de la fuente útil más lenta.
# TANDA_DEADLINE es la red de seguridad del conjunto (una fuente puede
# encadenar backoff + segundo intento): pasado ese tope se sirve lo que haya
# llegado en vez de seguir esperando. Con estos valores, cortar por deadline
# no habría perdido ni uno de los 108 items medidos.
FUENTE_TIMEOUT  = 2.5
FUENTE_BACKOFF  = 0.3
TANDA_DEADLINE  = 6.0

# URL de la web de cada fuente — para hipervínculo directo al clicar el label
SOURCE_URLS = {
    "ft":           "https://www.ft.com/markets",
    "seekingalpha": "https://seekingalpha.com/market-news",
    "cnbc":         "https://www.cnbc.com/markets/",
    "marketwatch":  "https://www.marketwatch.com/",
    "yahoofinance": "https://finance.yahoo.com/",
    "zerohedge":    "https://www.zerohedge.com/",
    "investing":    "https://www.investing.com/news/",
    "reddit":       "https://www.reddit.com/r/investing/",
    "fed":          "https://www.federalreserve.gov/newsevents/pressreleases.htm",
    "coindesk":     "https://www.coindesk.com/",
    "businessins":  "https://markets.businessinsider.com/news",
    "ftmarkets":    "https://www.ft.com/markets",
    "bls":          "https://www.bls.gov/bls/newsrels.htm",
    "ecb":          "https://www.ecb.europa.eu/press/html/index.en.html",
    "oilprice":     "https://oilprice.com/",
    "bbcbiz":       "https://www.bbc.com/news/business",
    "wolfstreet":   "https://wolfstreet.com/",
    "finnhub":      "https://finnhub.io/",
}

PRICE_TICKERS = {
    "S&P 500": "^GSPC", "NASDAQ": "^IXIC", "DOW": "^DJI", "VIX": "^VIX",
    "EUR/USD": "EURUSD=X", "BTC/USD": "BTC-USD", "ETH/USD": "ETH-USD",
    "GOLD": "GC=F", "OIL WTI": "CL=F", "10Y UST": "^TNX",
}

HIGH_KW = [
    "fed","federal reserve","fomc","rate hike","rate cut","recession","crash","collapse",
    "default","bankrupt","bailout","systemic","inflation surge","cpi","ppi","nonfarm",
    "crisis","emergency","plunge","circuit breaker","black swan","contagion",
    "tariff","sanction","executive order","nuclear","war","attack",
    # El informe de empleo se colaba solo si aparecía la palabra "nonfarm", que
    # los titulares casi nunca usan: "U.S. economy unexpectedly lost 23,000
    # jobs in July" solo se cazaba por un "nonfarm" perdido en el cuerpo. Es
    # la publicación macro que más mueve el mercado cada mes, así que se
    # nombra como la nombran los titulares. Detectado al revisar el
    # clasificador contra 129 titulares reales, 13/08/2026.
    "payrolls","jobs report","jobless claims",
    # "surge" y "plunge" se tratan aparte con contexto — ver _classify_impact()
]
MED_KW = [
    "earnings","guidance","downgrade","upgrade","merger","acquisition","ipo","spac",
    "sec","investigation","layoffs","gdp","unemployment","retail sales","pmi",
    "dividend","buyback","activist","short","target price","inflation","interest rate",
]

# Palabras que anulan una keyword HIGH/MED si aparecen justo antes de ella (negación básica)
NEGATION_PREFIXES = ["no ", "not ", "avoids ", "avoid ", "no sign", "no risk", "eases ", "ease ",
                     "rules out", "denies ", "deny ", "end of ", "ends ", "survived ", "survives ",
                     "low ", "falling ", "fading ", "cooling ", "subdued "]

# Keywords de impacto que son sensibles al contexto (no clasificar como HIGH si van con
# sujetos que las anulan, p.ej. "surge in unemployment" no es bullish)
# Sin "price" a secas: lo cumple cualquier precio, y con él
# "Lettuce prices see record-setting plunge as cyclospora spooks consumers"
# entraba como impacto ALTO. Se pide un contexto que sea de MERCADO —un
# activo o un índice—, no la palabra genérica. Medido el 13/08/2026 sobre 129
# titulares reales: era el único falso positivo que sobrevivía al recuento por
# acumulación.
CONTEXT_HIGH_SURGE  = ["market","stock","share","equity","rally","s&p","nasdaq","dow","index",
                       "shares","futures","bond","yield"]
CONTEXT_HIGH_PLUNGE = ["market","stock","share","equity","s&p","nasdaq","dow","index",
                       "shares","futures","bond","yield","oil","gold","crude"]

SECTORS_MAP = {
    "TECH":    ["nvidia","apple","microsoft","google","meta","tesla","amd","chip","ai","cloud","software","semiconductor"],
    "FINANCE": ["jpmorgan","goldman","bank","federal reserve","interest rate","yield","treasury","fomc","bonds","credit"],
    "ENERGY":  ["oil","gas","opec","crude","wti","brent","energy","xom","cvx"],
    "HEALTH":  ["pharma","fda","drug","biotech","clinical","vaccine","pfizer","merck"],
    "MACRO":   ["gdp","cpi","jobs","unemployment","recession","inflation","economy","fomc"],
    "CRYPTO":  ["bitcoin","btc","ethereum","eth","crypto","blockchain","solana","defi"],
    "POLICY":  ["trump","white house","congress","tariff","sanction","executive order"],
    "DEFENSE": ["military","war","ukraine","russia","china","taiwan","missile","pentagon"],
}

# Mapeo de categorías de Finnhub a sectores RSU (Nivel 2)
FINNHUB_CATEGORY_TO_SECTOR = {
    "technology":  "TECH",
    "crypto":      "CRYPTO",
    "forex":       "FINANCE",
    "merger":      "FINANCE",
    "general":     "GENERAL",
    "top news":    "MACRO",
}

# ── HELPERS ───────────────────────────────────────────────────────────────────

def _strip_html(text: str) -> str:
    if not text: return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = _html.unescape(text)
    # 2ª pasada: un payload doblemente codificado (&amp;lt;img...) sobrevive
    # al primer strip (el parser XML aún lo ve como &lt;...&gt;) y solo se
    # convierte en HTML real tras el unescape de arriba -- sin esto, salía
    # de aquí como etiqueta viva. Defensa en profundidad; el esc() del
    # frontend (core/ui.js) es la que realmente bloquea la ejecución.
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()

# Cada keyword se busca como PALABRA, no como trozo de palabra.
#
# El clasificador usaba `kw in texto`, y con keywords de tres o cuatro letras
# eso etiquetaba mal casi la mitad del feed. Medido el 08/08 sobre 118
# titulares reales: **26 de los 57 clasificados HIGH/MED (el 46%) lo estaban
# por un fragmento**, no por la palabra. Ejemplos textuales de ese día:
#   "double dipping portfolio"      -> HIGH, por "ppi" dentro de "dipping"
#   "space agency"                  -> MED,  por "spac" dentro de "space"
#   "Citi sees growth in second quarter" -> MED, por "sec" dentro de "second"
#   "FedEx beats estimates"         -> HIGH, por "fed" dentro de "FedEx"
#   "software update"               -> HIGH, por "war" dentro de "software"
# El filtro de impacto es lo que da valor al módulo; con ese ruido, un HIGH
# no significaba nada. Ver auditoría de Newsfeed, hallazgo #2.
#
# Se compilan una vez y se cachean: son ~50 keywords por cada titular de los
# ~120 que trae un ciclo, y recompilar la expresión en cada comprobación se
# nota.
@lru_cache(maxsize=512)
def _rx_palabra(keyword: str):
    # Se admiten los sufijos habituales de plural y de verbo. Sin ellos, el
    # límite de palabra a secas se lleva por delante titulares que SÍ había
    # que clasificar: "Raymond James downgrades Arko" dejaba de ser MED
    # porque `\bdowngrade\b` no casa con "downgrades". Detectado al mirar
    # el antes/después titular a titular, no en el total.
    #
    # Los sufijos no reabren el agujero que esto viene a cerrar, porque
    # tienen que encajar ENTEROS y acabar en límite de palabra:
    #   war    -> "wars" sí, "warning" no ("ning" no es un sufijo)
    #   fed    -> "feds" sí, "federal" no
    #   sec    -> "secs" sí, "second" no
    #   short  -> "shorts"/"shorted" sí, "shortage" no
    #
    # \b no funciona si la keyword empieza o acaba en un carácter que no es
    # de palabra (p.ej. un guion), así que el límite se pone solo del lado
    # que lo admite. Con las keywords actuales siempre aplica a ambos, pero
    # añadir mañana una con símbolo no debe romper la búsqueda en silencio.
    ini = r"\b" if keyword[:1].isalnum() else ""
    fin = r"(?:s|es|ed|ing)?\b" if keyword[-1:].isalnum() else ""
    return re.compile(ini + re.escape(keyword) + fin)


def _contiene(text: str, keyword: str) -> bool:
    """¿Aparece la keyword como palabra suelta en el texto?"""
    return _rx_palabra(keyword).search(text) is not None


def _is_negated(text: str, keyword: str) -> bool:
    """
    Comprueba si una keyword aparece precedida de un prefijo de negación
    en una ventana de ~5 palabras. Cubre casos como:
      "no signs of recession", "avoids crash", "not a crisis", "rules out rate cut"
    """
    m = _rx_palabra(keyword).search(text)
    if m is None:
        return False
    window = text[max(0, m.start() - 40):m.start()]
    return any(neg in window for neg in NEGATION_PREFIXES)

# Cuánto vale una señal según dónde aparezca. Un titular es lo que el autor
# eligió destacar; la descripción es relleno donde una palabra puede aparecer
# de pasada. Antes pesaban IGUAL, y de ahí salían falsos HIGH como "Common
# Blood Pressure Drug Recalled Nationwide" -- clasificado por una palabra
# escondida en 300 caracteres de resumen.
PESO_TITULO = 2
PESO_DESC   = 1

# Umbrales de acumulación. La versión anterior era "gana la primera keyword
# que aparezca": UNA palabra en cualquier sitio decidía la etiqueta, así que
# un titular con «Fed» + «CPI» + «recession» valía lo mismo que otro con
# «attack» perdido en el resumen. Medido el 13/08 sobre 129 titulares reales:
# el 24% salía HIGH, y con una cuarta parte del feed en rojo la etiqueta deja
# de distinguir nada.
UMBRAL_HIGH = 3
UMBRAL_MED  = 1

# No todas las palabras de HIGH_KW pesan igual. "war" o "attack" aparecen en
# cualquier crónica internacional; "fomc" o "circuit breaker" no admiten duda.
# Sin esta distinción, un titular con UNA sola señal inequívoca —"Trump
# announces 50% tariff on China"— se quedaba en MED, porque una keyword en el
# titular vale 2 y el umbral son 3. Estas llegan solas.
CRITICO_KW = [
    "fomc", "rate hike", "rate cut", "recession", "crash", "circuit breaker",
    "black swan", "default", "bailout", "contagion", "tariff", "cpi",
    # Las dos publicaciones macro que más mueven el mercado cada mes son el IPC
    # y el informe de empleo. Dejar "cpi" aquí y el empleo fuera era una
    # incoherencia del propio diseño: "...takeaways from the July jobs report"
    # se quedaba en MED por un solo punto.
    "payrolls", "jobs report", "jobless claims",
    # Mismo hueco de vocabulario: estaba "rate hike"/"rate cut", pero los
    # titulares dicen "raises rates" o "by 50 basis points". "Fed raises rates
    # by 50 basis points" se quedaba en MED por no nombrar la subida como la
    # nombra el manual.
    "raises rates", "cuts rates", "raise rates", "cut rates",
    "rate decision", "basis points",
]


def _puntos(titulo_l: str, desc_l: str, keywords, valor: int) -> int:
    """Suma el peso de cada keyword que aparezca, contándola UNA vez y en el
    sitio donde más vale. Una misma noticia puede acumular varias señales, que
    es justo lo que distingue un titular de mercado de una mención suelta."""
    total = 0
    for kw in keywords:
        if _contiene(titulo_l, kw) and not _is_negated(titulo_l, kw):
            total += valor * PESO_TITULO
        elif _contiene(desc_l, kw) and not _is_negated(desc_l, kw):
            total += valor * PESO_DESC
    return total


def _classify_impact(text: str, finnhub_related: list = None, titulo: str = None) -> str:
    """Impacto por ACUMULACIÓN de señales, no por la primera que aparezca.

    `titulo` separa el titular del resto para poder pesarlos distinto. Si no se
    pasa, todo el texto cuenta como titular -- así los llamadores antiguos no
    cambian de comportamiento de golpe, solo dejan de tener la ventaja del
    peso.

    Ver auditoría de Newsfeed, #2 (el clasificador) y la revisión del 13/08.
    """
    t = text.lower()
    titulo_l = (titulo or text).lower()
    desc_l = t if titulo is None else t.replace(titulo_l, " ", 1)

    puntos = 0

    # "surge"/"plunge" solo cuentan con contexto de activo: "surge in
    # unemployment" no es lo mismo que "shares surge". Se mantienen aparte
    # porque su ambigüedad no la resuelve el peso, la resuelve el contexto.
    for palabra, contextos in (("surge", CONTEXT_HIGH_SURGE), ("plunge", CONTEXT_HIGH_PLUNGE)):
        if _contiene(t, palabra) and not _is_negated(t, palabra) and any(c in t for c in contextos):
            puntos += PESO_TITULO if _contiene(titulo_l, palabra) else PESO_DESC

    # Las críticas primero y se descuentan de HIGH_KW, para no cobrarlas dos
    # veces: "tariff" está en las dos listas por diseño.
    puntos += _puntos(titulo_l, desc_l, CRITICO_KW, 1.5)
    puntos += _puntos(titulo_l, desc_l, [k for k in HIGH_KW if k not in CRITICO_KW], 1)
    # Las MED valen la mitad: acumular tres de ellas no debería igualar a un
    # titular con dos señales de crisis.
    puntos += _puntos(titulo_l, desc_l, MED_KW, 1) / 2

    # Finnhub dice que la noticia toca índices o macro: suelo de MED, igual
    # que antes. No sube a HIGH por sí solo -- es una pista de tema, no de
    # magnitud.
    if finnhub_related:
        macro_symbols = {"SPY", "QQQ", "TLT", "GLD", "DXY", "VIX", "ES", "NQ"}
        if any(r.get('symbol', '') in macro_symbols for r in finnhub_related):
            puntos = max(puntos, UMBRAL_MED)

    if puntos >= UMBRAL_HIGH:
        return "HIGH"
    if puntos >= UMBRAL_MED:
        return "MED"
    return "LOW"

def _sentiment(text: str) -> str:
    """
    Nivel 1: sentimiento con desambiguación de palabras en contexto negativo.
    Palabras como 'high' y 'low' son ambiguas — 'high unemployment' es bearish,
    'stock hits high' es bullish. Las excluimos del conteo simple y las evaluamos
    solo si hay contexto de activos/mercados junto a ellas.
    """
    t = text.lower()

    # Palabras positivas netas (sin 'high' que es ambigua; 'surge' se evalúa con contexto abajo)
    pos_words = ["rally","gain","rise","soar","beat","record","growth","strong","bull",
                 "recover","rebound","outperform","upgrade","beat expectations"]
    # Palabras negativas netas (sin 'low' que es ambigua)
    neg_words = ["plunge","crash","fall","drop","sink","miss","weak","bear","collapse","selloff",
                 "tumble","underperform","downgrade","miss expectations","layoffs","bankrupt"]

    pos = sum(1 for w in pos_words if _contiene(t, w) and not _is_negated(t, w))
    neg = sum(1 for w in neg_words if _contiene(t, w) and not _is_negated(t, w))

    # "surge" es positivo SOLO si va con activos de mercado, no con datos macro negativos
    if _contiene(t, "surge") and not _is_negated(t, "surge"):
        if any(ctx in t for ctx in ["stock","share","price","market","equity","s&p","nasdaq"]):
            pos += 1
        elif any(ctx in t for ctx in ["unemployment","jobless","layoff","inflation","deficit","debt"]):
            neg += 1  # surge en datos negativos = señal bearish

    # 'high' en contexto de precio/mercado es positivo; en contexto macro (unemployment, inflation) es negativo
    if _contiene(t, "high"):
        if any(ctx in t for ctx in ["stock","share","price","market","record","52-week"]):
            pos += 1
        elif any(ctx in t for ctx in ["unemployment","inflation","rate","deficit","debt","risk"]):
            neg += 1

    # 'low' es el inverso
    if _contiene(t, "low"):
        if any(ctx in t for ctx in ["unemployment","inflation","rate","volatility"]):
            pos += 1
        elif any(ctx in t for ctx in ["stock","share","price","market","52-week"]):
            neg += 1

    if pos > neg: return "bullish"
    if neg > pos: return "bearish"
    return "neutral"

def _sector(text: str, finnhub_category: str = None) -> str:
    """
    Nivel 2: si viene una categoría de Finnhub, la usamos como señal primaria.
    Si no, fallback a keyword matching.
    """
    # Nivel 2: categoría de Finnhub como señal de mayor precisión
    if finnhub_category:
        mapped = FINNHUB_CATEGORY_TO_SECTOR.get(finnhub_category.lower())
        if mapped and mapped != "GENERAL":
            return mapped

    # Nivel 1: keyword matching como fallback
    t = text.lower()
    # Mismo problema que el impacto y por la misma via: con substring, la
    # keyword "ai" de TECH casaba con said, again, raised, chain, remain...
    # Cualquier titular con una de esas palabras se etiquetaba TECH.
    for sec, kws in SECTORS_MAP.items():
        if any(_contiene(t, k) for k in kws):
            return sec
    return "GENERAL"

def _mins_ago(pub_str: str) -> int:
    try:
        from email.utils import parsedate_to_datetime
        dt = parsedate_to_datetime(pub_str)
        diff = datetime.now(timezone.utc) - dt.astimezone(timezone.utc)
        return max(0, int(diff.total_seconds() / 60))
    except Exception:
        pass
    try:
        # Formato ISO 8601 (usado por Atom y algunos RSS modernos)
        dt = datetime.fromisoformat(pub_str.replace('Z', '+00:00'))
        diff = datetime.now(timezone.utc) - dt.astimezone(timezone.utc)
        return max(0, int(diff.total_seconds() / 60))
    except Exception:
        return 999

def _parse_rss(content, src: dict) -> list:
    """content: preferiblemente BYTES (r.content), no str. Ver _fetch_source --
    un feed con BOM UTF-8 al principio (el de la Fed lo tiene) revienta el
    parseo si se le pasa ya decodificado, y el except de abajo se lo tragaba
    en silencio."""
    items = []
    try:
        root = ET.fromstring(content)
        ns   = {'atom': 'http://www.w3.org/2005/Atom'}

        # El formato se DETECTA, no se declara a mano. Con `fmt` manual había
        # feeds mal etiquetados que devolvían 0 items sin avisar: el de la Fed
        # figuraba como "atom" siendo RSS, y el de Reddit es Atom sin
        # declararlo (así que se le aplicaba el parser RSS). Mirar la raíz del
        # documento no se equivoca ni hay que mantenerlo cuando una fuente
        # cambia de formato.
        fmt = 'atom' if root.tag.endswith('}feed') or root.tag == 'feed' else 'rss'

        if fmt == 'atom':
            entries = root.findall('.//atom:entry', ns) or root.findall('.//{http://www.w3.org/2005/Atom}entry')
            for e in entries[:10]:
                def _t(tag): return (e.findtext(f'{{http://www.w3.org/2005/Atom}}{tag}') or '').strip()
                title = _t('title')
                link  = e.find('{http://www.w3.org/2005/Atom}link')
                link  = link.get('href','') if link is not None else ''
                pub   = _t('updated') or _t('published')
                desc  = _strip_html(_t('summary') or _t('content'))
                if title:
                    items.append(_build(title, desc, link, src, pub))
        else:
            for item in root.findall('.//item')[:10]:
                def _t(tag): return (item.findtext(tag) or '').strip()
                title = _t('title')
                link  = _t('link')
                pub   = _t('pubDate')
                desc  = _strip_html(_t('description') or _t('summary'))
                if title:
                    items.append(_build(title, desc, link, src, pub))
    except Exception:
        pass
    return items

_RASTREO = ("utm_", "fbclid", "gclid", "mc_cid", "mc_eid", "ref", "src")

# Tickers reconocibles en un titular. Se exige que el símbolo EXISTA en el
# S&P 500 en vez de aceptar cualquier palabra en mayúsculas -- si no, "CEO",
# "GDP", "FOMC" o "EE UU" pasarían por tickers y el enlace llevaría a una
# página de Research vacía.
_TICKERS_CONOCIDOS = set(SP500_SECTOR_MAP.keys())

# Miembros reales del índice cuyo símbolo es además una palabra inglesa
# corriente en titulares financieros. Sin esta lista, "shares hit a new LOW"
# enlazaría a Lowe's y "the FED said" a FedEx. Se pierden menciones legítimas
# de estas 20 empresas a cambio de no fabricar enlaces falsos -- el mismo
# criterio de "mejor sin dato que con uno inventado" del resto del proyecto.
# Un cashtag ($LOW) sí las recupera: ahí la intención es inequívoca.
_PALABRAS_NO_TICKER = {
    "A", "ALL", "ARE", "BEN", "CAT", "CEO", "DAY", "EA", "ED", "FAST", "GO",
    "HAS", "HD", "IT", "KEY", "LOW", "MA", "MET", "MO", "NEE", "NOW", "ON",
    "OPEN", "PM", "SO", "TAP", "WELL", "WM", "US", "USA", "EU", "UK", "AI",
    "CPI", "GDP", "FED", "IPO", "ETF", "SEC", "NYSE", "TV", "AM", "PM",
}

_RX_CASHTAG = re.compile(r"\$([A-Z]{1,5})\b")
_RX_MAYUSCULAS = re.compile(r"\b([A-Z]{2,5})\b")


def _extraer_tickers(texto: str, related: list = None) -> list:
    """Símbolos mencionados en un titular, para poder enlazarlos a Research.

    Tres orígenes, de más a menos fiable:
      1. `related` de Finnhub -- viene etiquetado en origen, no se adivina.
      2. Cashtags ($AAPL) -- la intención es explícita, se aceptan aunque el
         símbolo no esté en el S&P 500 (puede ser una small cap).
      3. Mayúsculas sueltas -- solo si el símbolo existe en el S&P 500 y no
         es una palabra corriente (ver _PALABRAS_NO_TICKER).

    Devuelve como mucho 3: un titular con seis enlaces deja de ser un titular.
    """
    encontrados = []

    def _add(sym):
        sym = (sym or "").strip().upper()
        if sym and sym not in encontrados:
            encontrados.append(sym)

    for r in (related or []):
        _add(r.get("symbol") if isinstance(r, dict) else r)

    for sym in _RX_CASHTAG.findall(texto or ""):
        _add(sym)

    for sym in _RX_MAYUSCULAS.findall(texto or ""):
        if sym in _TICKERS_CONOCIDOS and sym not in _PALABRAS_NO_TICKER:
            _add(sym)

    return encontrados[:3]


def _url_canonica(url: str) -> str:
    """URL reducida a lo que identifica el artículo, para deduplicar.

    Se quitan esquema, "www.", la barra final y los parámetros de rastreo --
    el MISMO artículo llega con `?utm_source=rss` desde un feed y limpio desde
    otro, y comparándolos en crudo salen como dos noticias distintas. Los
    parámetros que no son de rastreo se conservan: hay sitios donde el
    identificador del artículo viaja en la query (`?id=1234`), y limpiarla
    entera fusionaría artículos que no tienen nada que ver.
    """
    if not url:
        return ""
    try:
        from urllib.parse import urlsplit, parse_qsl, urlencode
        p = urlsplit(url.strip())
        host = (p.netloc or "").lower().removeprefix("www.")
        query = urlencode([(k, v) for k, v in parse_qsl(p.query)
                           if not k.lower().startswith(_RASTREO)])
        camino = (p.path or "").rstrip("/")
        return f"{host}{camino}" + (f"?{query}" if query else "")
    except Exception:
        return url.strip().lower()


def _build(title: str, desc: str, link: str, src: dict, pub: str) -> dict:
    text   = title + ' ' + desc
    mins   = _mins_ago(pub) if pub else 999
    return {
        "title":      _strip_html(title)[:200],
        "desc":       desc[:300],
        "url":        link,
        "source":     src['label'],
        "source_id":  src['id'],
        "source_url": SOURCE_URLS.get(src['id'], ''),
        "impact":     _classify_impact(text, titulo=title),
        "sentiment":  _sentiment(text),
        "sector":     _sector(text),
        "mins_ago":   mins,
        "pub":        pub,
        # Solo del TITULAR, no de la descripción: el resumen de un feed suele
        # arrastrar la lista de "empresas relacionadas" del pie del artículo, y
        # entonces cada noticia salía con tres enlaces que no tenían nada que
        # ver con lo que contaba. Ver auditoría de Newsfeed, #17.
        "tickers":    _extraer_tickers(title),
    }

def _fetch_source(src: dict) -> tuple:
    """Devuelve (items, source_id, ok) para poder rastrear qué fuentes funcionan.

    TIMEOUT DE 2,5s, no de 8. Medido el 11/08/2026 con las 14 fuentes reales:
    13 responden en menos de 0,7s (la más lenta que aporta algo, 0,61s) y la
    catorceava —benzinga— agotaba los 8s enteros para devolver CERO items. Con
    un tope de 2,5s se le da cuatro veces el margen de la fuente útil más
    lenta, y el endpoint deja de esperar ocho segundos por nada.

    UN REINTENTO, y solo para fallos de CONEXIÓN. Un timeout no se reintenta:
    significa que el servidor va lento, y volver a preguntarle solo suma otro
    timeout al reloj del usuario. Un ConnectionError/DNS, en cambio, suele ser
    un tropiezo instantáneo del que se sale a la primera. Esa distinción es lo
    que hace que el reintento no coma latencia en el caso malo. Ver auditoría
    de Newsfeed, hallazgos #14 y #16.
    """
    if not src.get('url'):
        return [], src['id'], False
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; RSUTerminal/2.0)",
        "Accept": "application/rss+xml, application/xml, text/xml, */*",
    }
    r = None
    for intento in range(2):
        try:
            r = requests.get(src['url'], headers=headers, timeout=FUENTE_TIMEOUT)
            break
        except requests.exceptions.Timeout:
            return [], src['id'], False
        except Exception:
            if intento == 0:
                time.sleep(FUENTE_BACKOFF)
                continue
            return [], src['id'], False
    try:
        if r.status_code == 200:
            # r.content (bytes), NO r.text: un feed que empieza con BOM UTF-8
            # -- el de la Fed lo hace -- rompe ElementTree si se le pasa ya
            # decodificado a str ("not well-formed, line 1, column 1"), y el
            # except de _parse_rss lo convertía en 0 items silenciosos. Con
            # bytes, ElementTree gestiona BOM y encoding declarado él solo.
            items = _parse_rss(r.content, src)
            # Descartar artículos rancios (ver MAX_ANTIGUEDAD_MINS): un feed
            # congelado responde 200 y sirve sus últimos artículos para
            # siempre. mins_ago == 999 es el valor que pone _build cuando la
            # fecha no se pudo parsear -- ahí no se puede juzgar, se conserva
            # (mejor un item sin fecha fiable que perder una fuente entera por
            # un formato de fecha raro).
            frescos = [i for i in items if i['mins_ago'] == 999 or i['mins_ago'] <= MAX_ANTIGUEDAD_MINS]
            if items and not frescos:
                dias = min(i['mins_ago'] for i in items) / 1440
                print(f"[Newsfeed] '{src['id']}' responde 200 pero su artículo más reciente "
                      f"tiene {dias:.0f} días -- feed probablemente congelado, descartado")
            return frescos, src['id'], len(frescos) > 0
        return [], src['id'], False
    except Exception:
        return [], src['id'], False

# ── FINNHUB NEWS ──────────────────────────────────────────────────────────────

def _fetch_finnhub_news() -> tuple:
    """
    Noticias de mercado de Finnhub — mayor calidad y sentimiento real que RSS.
    Usa la key de Finnhub ya configurada en el proyecto (misma que Research).
    """
    key = settings.finnhub_api_key
    if not key:
        return [], False
    try:
        r = requests.get(
            "https://finnhub.io/api/v1/news",
            params={"category": "general", "token": key},
            timeout=8
        )
        if r.status_code != 200:
            return [], False
        items = []
        src = {"id": "finnhub", "label": "FINNHUB"}
        for art in r.json()[:15]:
            headline = art.get('headline', '')
            summary  = art.get('summary', '')
            url      = art.get('url', '')
            ts       = art.get('datetime', 0)
            category = art.get('category', '')   # Nivel 2: categoría nativa de Finnhub
            related  = art.get('related', [])    # Nivel 2: símbolos relacionados (lista o string)
            if not headline:
                continue
            # Calcular mins_ago desde Unix timestamp
            try:
                dt   = datetime.fromtimestamp(ts, tz=timezone.utc)
                mins = max(0, int((datetime.now(timezone.utc) - dt).total_seconds() / 60))
            except Exception:
                mins = 999

            # Normalizar 'related' — puede ser string "AAPL,MSFT" o lista
            if isinstance(related, str):
                related = [{"symbol": s.strip()} for s in related.split(',') if s.strip()]
            elif not isinstance(related, list):
                related = []

            text   = headline + ' ' + summary
            item   = {
                "title":      headline[:200],
                "desc":       summary[:300],
                "url":        url,
                "source":     "FINNHUB",
                "source_id":  "finnhub",
                "source_url": SOURCE_URLS.get("finnhub", ""),
                "impact":     _classify_impact(text, finnhub_related=related, titulo=headline),
                "sentiment":  _sentiment(text),
                "sector":     _sector(text, finnhub_category=category),
                "mins_ago":   mins,
                "pub":        str(ts),
                # Aquí `related` viene etiquetado por Finnhub, así que no hay
                # que adivinar nada -- es el origen más fiable de los tres.
                "tickers":    _extraer_tickers(headline, related=related),
            }
            items.append(item)
        return items, len(items) > 0
    except Exception:
        return [], False

# ── TRUMP / TRUTH SOCIAL ──────────────────────────────────────────────────────

def get_trump_feed(limit: int = 15) -> dict:
    """
    Posts de Trump vía trumpstruth.org — archivo público de Truth Social.
    Usa el RSS oficial del archivo (https://www.trumpstruth.org/feed).
    Etiquetado explícitamente como archivo, no como fuente oficial de Truth Social.
    """
    from services.cache import cache
    cached = cache.get("newsfeed:trump")
    if cached: return cached

    url = "https://www.trumpstruth.org/feed"
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; RSUTerminal/2.0)",
        "Accept": "application/rss+xml, application/xml, text/xml, */*",
    }
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code != 200:
            return {"ok": False, "error": f"trumpstruth.org status {r.status_code}", "posts": []}

        root  = ET.fromstring(r.text)
        posts = []
        for item in root.findall('.//item')[:limit]:
            def _t(tag): return (item.findtext(tag) or '').strip()
            title   = _strip_html(_t('title'))
            content = _strip_html(_t('description') or _t('content:encoded') or _t('summary'))
            link    = _t('link')
            pub     = _t('pubDate')
            mins    = _mins_ago(pub)

            # Clasificar impacto del post por keywords financieras/política
            text = (title + ' ' + content).lower()
            # Un post de Truth Social no tiene titular aparte: el texto ES
            # el mensaje, así que todo cuenta como titular.
            impact = _classify_impact(text)

            posts.append({
                "title":    title[:300] if title else content[:300],
                "content":  content[:500],
                "url":      link,
                "mins_ago": mins,
                "pub":      pub,
                "impact":   impact,
                "sector":   _sector(text),
            })

        posts.sort(key=lambda x: x['mins_ago'])
        result = {
            "ok":        True,
            "posts":     posts,
            "total":     len(posts),
            "source":    "trumpstruth.org (archivo público de Truth Social)",
            "timestamp": get_timestamp(),
        }
        cache.set("newsfeed:trump", result, 300)  # cache 5 min
        return result

    except Exception as e:
        return {"ok": False, "error": str(e), "posts": []}

# ── PRICES ────────────────────────────────────────────────────────────────────

def _get_prices() -> list:
    result = []
    def _fetch(name, ticker):
        try:
            t = yf.Ticker(ticker)
            # period="5d" (antes "2d") + descartar las filas sin Close real:
            # con el mercado ABIERTO, Yahoo devuelve la fila del día en curso
            # con Close=NaN, así que iloc[-1] daba NaN y el widget mostraba
            # "NaN" como precio y como % durante toda la sesión. Con solo 2
            # días descargados, quitar esa fila dejaba 1 sola y el `len < 2`
            # descartaba el ticker entero -- de ahí los 5 días, para que
            # siempre queden al menos 2 cierres REALES. Mismo patrón de fondo
            # ya corregido en cartera_service._get_daily_bars() (25/07/2026).
            hist = t.history(period="5d", interval="1d")
            hist = hist[hist['Close'].notna()]
            if len(hist) < 2:
                return None
            prev = float(hist['Close'].iloc[-2])
            last = float(hist['Close'].iloc[-1])
            if not prev:
                return None
            # Con el mercado abierto, `last` es el cierre de AYER (la sesión
            # de hoy aún no ha cerrado). fast_info sí trae el precio en vivo,
            # que es lo que este widget quiere mostrar -- se usa si está
            # disponible, cayendo al cierre real si no. Mismo criterio que
            # Cartera: un snapshot aproximado de ahora vale más que un cierre
            # exacto de ayer para un ticker de precios en vivo.
            try:
                vivo = float(getattr(t.fast_info, 'last_price', 0) or 0)
                if vivo and math.isfinite(vivo):
                    last = vivo
            except Exception:
                pass
            chg = (last - prev) / prev * 100
            return {"name": name, "price": round(last, 4), "chg": round(chg, 2)}
        except Exception:
            return None
    from services.yf_pool import yf_executor
    futures = {yf_executor.submit(_fetch, name, ticker): name for name, ticker in PRICE_TICKERS.items()}
    for f in as_completed(futures):
        r = f.result()
        if r: result.append(r)
    result.sort(key=lambda x: list(PRICE_TICKERS.keys()).index(x['name']))
    return result

# ── MAIN ──────────────────────────────────────────────────────────────────────

def _fetch_all_items() -> tuple:
    """
    Parte costosa de get_newsfeed — los 15 fetches HTTP en paralelo.
    Separada para poder cachearla independientemente de los filtros,
    de modo que todos los usuarios comparten el mismo ciclo de fetch.
    """
    from services.cache import cache
    cached = cache.get("newsfeed:raw")
    if cached:
        return cached['items'], cached['source_status'], cached['all_source_defs']

    # Compas de espera tras una caida general (ver el final de esta funcion).
    # Se devuelve vacio sin tocar la red: el frontend ya sabe pintar "sin
    # noticias", y es mejor eso que quince peticiones mas a servidores que
    # acaban de fallar.
    if cache.get("newsfeed:caida"):
        return [], {}, SOURCES + [{"id": "finnhub", "label": "FINNHUB"}]

    active_sources = SOURCES
    source_status  = {}
    all_items      = []

    # Sin `with`: al salir de un bloque `with` el executor hace shutdown(wait=True)
    # y vuelve a esperar a los rezagados, deshaciendo el deadline que acabamos de
    # aplicar. Se cierra a mano con wait=False.
    # Tiene que ser >= nº de fuentes + 1 (Finnhub), o las que no caben esperan
    # turno y su tiempo SE SUMA al total en vez de solaparse -- ver el print de
    # más abajo. Estaba en 16 para 15 tareas; con las altas del 13/08/2026 son
    # 18, así que sube con margen para las próximas.
    ex = ThreadPoolExecutor(max_workers=24)
    try:
        rss_futures    = {ex.submit(_fetch_source, src): src for src in active_sources}
        finnhub_future = ex.submit(_fetch_finnhub_news)
        source_status  = {src['id']: False for src in active_sources}
        source_status['finnhub'] = False

        inicio = time.monotonic()
        try:
            for f in as_completed(list(rss_futures) + [finnhub_future], timeout=TANDA_DEADLINE):
                if f is finnhub_future:
                    fh_items, fh_ok = f.result()
                    all_items.extend(fh_items)
                    source_status['finnhub'] = fh_ok
                else:
                    items, src_id, ok = f.result()
                    all_items.extend(items)
                    source_status[src_id] = ok
        except FuturoExpirado:
            # Se sirve lo que haya llegado. Las que no contestaron se quedan en
            # False (arrancan así), que es exactamente lo que ya significa esa
            # bandera: la fuente no aportó nada en este ciclo. El semáforo de
            # fuentes del frontend las pinta en rojo sin cambios.
            pendientes = [rss_futures[f]['id'] for f in rss_futures if not f.done()]
            print(f"[Newsfeed] Tope de {TANDA_DEADLINE:.0f}s alcanzado, se sirve lo recibido. "
                  f"Sin contestar: {pendientes or ['finnhub']}")
        else:
            # max_workers >= nº de tareas, así que todas arrancan a la vez y el
            # reloj es el de la más lenta. Con 8 fuentes por 12 workers no era
            # así: las que no cabían esperaban turno y sumaban al total.
            print(f"[Newsfeed] {len(active_sources) + 1} fuentes en {time.monotonic() - inicio:.2f}s")
    finally:
        ex.shutdown(wait=False, cancel_futures=True)

    # Deduplicar por TÍTULO y por URL. Con solo el título se colaba el mismo
    # artículo dos veces cuando dos fuentes lo sindican con titulares
    # ligeramente distintos ("Fed holds rates" vs "Fed holds rates steady") pero
    # apuntando al mismo enlace. Ver auditoría de Newsfeed, hallazgo #15.
    seen_titulo = set()
    seen_url    = set()
    unique = []
    for item in all_items:
        k_titulo = item['title'][:60].lower()
        k_url    = _url_canonica(item.get('url'))
        if k_titulo in seen_titulo or (k_url and k_url in seen_url):
            continue
        seen_titulo.add(k_titulo)
        if k_url:
            seen_url.add(k_url)
        unique.append(item)

    unique.sort(key=lambda x: x['mins_ago'])

    all_source_defs = SOURCES + [{"id": "finnhub", "label": "FINNHUB"}]

    # Caché de 5 minutos — coincide con el auto-refresh del frontend.
    # Solo cacheamos si hay al menos algunas noticias (no guardamos un estado vacío
    # por fallo de red que quedaría pegado 5 minutos).
    if len(unique) > 5:
        cache.set("newsfeed:raw", {
            "items":           unique,
            "source_status":   source_status,
            "all_source_defs": all_source_defs,
        }, 300)
    else:
        # Caída general de las fuentes. Sin nada que guardar, la siguiente
        # visita repetiría los 15 fetches en paralelo, y la siguiente, y la
        # siguiente: con ~100 usuarios eso es martillear a quince servidores
        # que ya están fallando, justo cuando peor les viene.
        #
        # Se guarda una marca corta (no el resultado vacío, que se serviría
        # como si fuera bueno) para saltarse el ciclo mientras dure. 60s en
        # vez de los 300 del camino normal: es un compás de espera, no una
        # caché de contenido, y el feed tiene que recuperarse en cuanto las
        # fuentes vuelvan. Mismo criterio que el negative cache de Reddit
        # Pulse (services/cache.py, TTL "reddit_fail"). Ver auditoría de
        # Newsfeed, hallazgo #11.
        cache.set("newsfeed:caida", True, 60)

    return unique, source_status, all_source_defs

def get_newsfeed(impact: str = None, sector: str = None, source: str = None,
                  q: str = None, limit: int = 50) -> dict:
    """Antes había aquí un parámetro `sources: list` que la función aceptaba y
    no miraba en ninguna línea, así que `get_newsfeed(sources=['ft'])` devolvía
    TODAS las fuentes como si el filtro se hubiera aplicado (auditoría #13). Se
    eliminó, y `source` es su sustituto de verdad: un único id de fuente, con
    el filtro implementado y con tests. `q` busca en titular, descripción y
    tickers. Ver auditoría de Newsfeed, #18 y #19.
    """
    unique, source_status, all_source_defs = _fetch_all_items()

    # Filtros aplicados en memoria sobre los datos ya cacheados — sin coste de red.
    #
    # TODOS van aquí, en el backend, y NO en el navegador: el recorte a `limit`
    # ocurre al final, así que filtrar en el cliente sobre lo ya recortado deja
    # fuera noticias que sí existen. Medido el 08/08 con el filtro de impacto:
    # pedir HIGH enseñaba 9 de las 22 que había. Ver auditoría, #7 -- `source` y
    # `q` se añaden por el mismo camino para no repetir ese error.
    filtered = unique
    if impact:
        filtered = [i for i in filtered if i['impact'] == impact.upper()]
    if sector:
        filtered = [i for i in filtered if i['sector'] == sector.upper()]
    if source:
        filtered = [i for i in filtered if i['source_id'] == source.lower()]
    if q:
        aguja = q.strip().lower()
        if aguja:
            filtered = [i for i in filtered
                        if aguja in i['title'].lower()
                        or aguja in (i.get('desc') or '').lower()
                        or any(aguja == t.lower() for t in i.get('tickers', []))]

    # Stats sobre el conjunto completo (no solo la página filtrada)
    high = sum(1 for i in unique if i['impact'] == 'HIGH')
    med  = sum(1 for i in unique if i['impact'] == 'MED')
    low  = sum(1 for i in unique if i['impact'] == 'LOW')
    bull = sum(1 for i in unique if i['sentiment'] == 'bullish')
    bear = sum(1 for i in unique if i['sentiment'] == 'bearish')

    return {
        "ok":      True,
        "items":   filtered[:limit],
        "total":   len(unique),
        # Coincidencias ANTES de recortar a `limit`. Sin este número, la UI
        # solo puede decir "80 de 120", que mezcla dos cosas: cuántas encajan
        # con el filtro y cuántas caben en la página.
        "filtrados": len(filtered),
        "stats":   {"high": high, "med": med, "low": low, "bullish": bull, "bearish": bear},
        "sources": [{"id": s['id'], "label": s['label'],
                     "ok": source_status.get(s['id'], False),
                     "url": SOURCE_URLS.get(s['id'], '')} for s in all_source_defs],
        "timestamp": get_timestamp(),
    }

@cache.single_flight("newsfeed:prices")
def get_newsfeed_prices() -> list:
    # Sin caché, cada visita a Newsfeed disparaba los 10 tickers del widget
    # contra yfinance. Medido el 08/08 interceptando las llamadas: **30
    # peticiones a Yahoo por carga**, no 10 -- cada ticker hace history()
    # y ademas fast_info, que a su vez pide lo suyo.
    #
    # Igual que en SPXL, lo que importa no es el segundo y medio que tarda,
    # sino que la cuota de Yahoo la comparte toda la terminal. 5 min es el
    # mismo TTL que usa Market para sus indices, y por el mismo motivo que
    # se documento alli: con 60s caducaba tan rapido que volvia a disparar
    # llamadas en vivo constantemente. Ver auditoria de Newsfeed, #4.
    from services.cache import cache, TTL
    cacheado = cache.get("newsfeed:prices")
    if cacheado is not None:
        return cacheado
    precios = _get_prices()
    if precios:   # una lista vacia es un fallo de red, no un resultado
        cache.set("newsfeed:prices", precios, TTL["market"])
    return precios