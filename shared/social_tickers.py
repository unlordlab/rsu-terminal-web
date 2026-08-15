"""
social_tickers.py -- lo que Reddit Pulse necesita saber leer, compartido entre
el backend (services/market_service.py) y el escaneo nocturno
(scripts/stocktwits_scan.py).

POR QUÉ EXISTE. StockTwits está tras un challenge de Cloudflare desde la IP del
VPS -- verificado el 28/07/2026 y confirmado de nuevo el 15/08/2026, cuando la
columna SENT salió vacía en las quince filas de producción mientras desde una
IP doméstica respondía 200. La salida es la misma que ya usan Scanner, RS/RW,
CANSLIM, Thematic y Congress: el trabajo lo hace un runner de GitHub Actions,
que no está bloqueado, y publica el resultado a un Gist que el backend lee.

Para que el runner pida sentimiento de LOS MISMOS valores que el backend va a
enseñar, tiene que extraer los tickers igual que él. De ahí este módulo: la
alternativa era una segunda copia de la lista negra y del extractor, que es
exactamente el patrón que este proyecto ya ha desmontado cuatro veces
(rsrw_engine, mcclellan, weinstein_phases, time_utils).

NO depende de nada de backend/ (fastapi, pydantic) -- scripts/ corre en el
runner sin ese entorno instalado.
"""
import re
import time
import xml.etree.ElementTree as ET

import requests

# Subreddits de bolsa. r/buzztickr publica recuentos de menciones con los
# tickers en el propio título ("Market Pulse Aug 06 $SPY $SNDK"), así que
# aporta símbolos limpios y densos -- pero OJO: sus posts son RESÚMENES de
# menciones de Reddit, no conversación original, así que refuerza lo que ya
# destaca en los otros cinco en vez de ser una sexta opinión independiente.
REDDIT_SUBS = ['wallstreetbets', 'stocks', 'investing', 'options', 'StockMarket',
               'buzztickr']

# Palabras en mayúsculas que NO son menciones. La lista solo puede enumerar lo
# que a alguien se le ocurrió; el filtro de verdad es el universo de tickers
# reales que se pasa a extract_tickers().
BLACKLIST = {
    'A','I','IT','IS','AT','BE','BY','DO','FOR','GO','HE','IF','IN','ME',
    'MY','NO','OF','ON','OR','SO','TO','UP','US','WE','AND','ARE','BUT',
    'CAN','DID','GET','GOT','HAS','HAD','HER','HIM','HIS','HOW','ITS',
    'LET','MAY','NEW','NOT','NOW','OFF','OUR','OUT','OWN','PUT','RUN',
    'SAY','SHE','THE','TOO','TWO','USE','WAS','WAY','WHO','WHY','WITH',
    'YOU','YOLO','LMAO','FOMO','EPS','CEO','IPO','ETF','GDP','FED','ALL',
    'GOOD','BEST','NEXT','LAST','HIGH','LOW','MORE','MUCH','JUST','LIKE',
    'MAKE','MANY','MOST','MOVE','NEED','OVER','SOME','SUCH','THAN','THAT',
    'THEM','THEN','THEY','THIS','WHAT','WHEN','WILL','YEAR','HOLD','SELL',
    'BUY','LONG','SHORT','PUMP','DUMP','MOON','BEAR','BULL','CALLS','PUTS',
    'DD','TA','OTM','ITM','ATM','WSB','RH','TD','AI','ML','API','LOL',
    'WTF','OMG','GG','GE','F','T','X','V','D','C','K','M','R','S',
    'PRE','POST','AH','PM','AM','EST','PST','UTC','USD','EUR','CAD',
    'WELL','WORK','TAKE','GIVE','BACK','COME','WANT','SHOW','ONLY','VERY',
    # Palabras corrientísimas en estos foros que ADEMÁS son tickers reales,
    # así que el filtro por universo no las descarta: TECH (Bio-Techne),
    # OPEN (Opendoor), CASH (Pathward), REAL (The RealReal), TRUE (TrueCar).
    # Quien las mencione de verdad normalmente escribe "$TECH", y el "$" salta
    # el filtro igualmente.
    'TECH','OPEN','CASH','REAL','TRUE',
}

_RE_TICKER = re.compile(r'\$([A-Z]{1,6})\b|\b([A-Z]{2,5})\b')


def extract_tickers(text: str, universo=None, limite: int = 30):
    """Menciones de tickers en un texto, con su peso.

    Con "$" delante es inequívocamente un ticker (así se escriben en estos
    foros) y pesa doble; sin "$", solo cuenta si es un ticker real conocido.
    Si no se pasa universo no se filtra nada -- vale más un widget con algo de
    ruido que uno vacío por un fallo de import."""
    found = {}
    for m in _RE_TICKER.finditer(text):
        con_dolar = bool(m.group(1))
        t = (m.group(1) or m.group(2) or '').strip()
        if not t or t in BLACKLIST or not (2 <= len(t) <= 6):
            continue
        if not con_dolar and universo and t not in universo:
            continue
        found[t] = found.get(t, 0) + (2 if con_dolar else 1)
    return sorted(found.items(), key=lambda x: -x[1])[:limite]


def fetch_reddit_titles_via_rss(log=print):
    """Títulos "hot" de los subreddits de bolsa, vía el RSS público.

    Sustituye al scraping con navegador headless (Playwright) que se montó el
    23/07/2026. Aquel enfoque funcionó mientras el bloqueo de Reddit era un
    challenge JavaScript, que un Chromium real resolvía. Verificado en
    producción el 28/07/2026 que ya NO es así: old.reddit.com devuelve 403 con
    el texto "Your request has been blocked due to a network policy" ANTES de
    servir página alguna. Es un bloqueo de RED por IP de datacenter, previo a
    cualquier JS, así que el navegador no aportaba nada -- solo ~180MB de
    imagen y varios segundos por petición.

    El RSS sí responde 200 desde esa misma IP, y los seis subreddits caben en
    UNA petición con la sintaxis multi-subreddit (`r/a+b+c`), lo que además
    esquiva el 429 que aparecía al pedirlos uno a uno.

    Devuelve [] si falla -- quien llama ya trata la ausencia sin fabricar nada.
    """
    url = f"https://www.reddit.com/r/{'+'.join(REDDIT_SUBS)}/hot/.rss?limit=100"
    cabeceras = {"User-Agent": "Mozilla/5.0 (compatible; RSUTerminal/1.0)"}
    try:
        # Reddit limita el ritmo también en el RSS: dos peticiones seguidas dan
        # 429 (verificado). Un reintento cubre la colisión puntual sin
        # insistir hasta hacerse pesado.
        r = None
        for intento, espera in enumerate((4, 10)):
            r = requests.get(url, headers=cabeceras, timeout=15)
            if r.status_code != 429:
                break
            if intento == 0:
                log(f"[RedditRSS] 429 (límite de ritmo) — reintento en {espera}s")
                time.sleep(espera)
        if r.status_code != 200:
            log(f"[RedditRSS] HTTP {r.status_code} al pedir {len(REDDIT_SUBS)} subreddits")
            return []
        root = ET.fromstring(r.content)
        ns = {"a": "http://www.w3.org/2005/Atom"}
        titulos = [(e.findtext("a:title", "", ns) or "").strip() for e in root.findall("a:entry", ns)]
        titulos = [t for t in titulos if t]
        log(f"[RedditRSS] {len(titulos)} títulos de r/{'+'.join(REDDIT_SUBS)}")
        return titulos
    except Exception as e:
        log(f"[RedditRSS] Falló: {type(e).__name__}: {e}")
        return []


UA_STOCKTWITS = "Mozilla/5.0 (compatible; MarketDashboard/2.0)"


def parse_sentimiento(mensajes) -> dict | None:
    """Reparto alcista/bajista a partir de los mensajes de StockTwits.

    NO es sentimiento inferido con un modelo -- que sobre jerga de foro acierta
    poco -- sino la etiqueta que el PROPIO AUTOR pone a su mensaje al
    publicarlo. Sin mensajes etiquetados devuelve None, no un 50/50 de relleno
    que sería indistinguible de un valor realmente dividido.

    Vive aquí para que el runner y el backend produzcan exactamente la misma
    forma: el runner la calcula y la publica, el backend la lee del Gist."""
    etiquetas = [((m.get("entities") or {}).get("sentiment") or {}).get("basic")
                 for m in (mensajes or [])]
    alcistas = sum(1 for e in etiquetas if e == "Bullish")
    bajistas = sum(1 for e in etiquetas if e == "Bearish")
    total = alcistas + bajistas
    if not total:
        return None
    return {
        "alcistas":    alcistas,
        "bajistas":    bajistas,
        "mensajes":    total,
        "pct_alcista": round(alcistas / total * 100),
        # De cuántos mensajes sale: un 100% de 3 y uno de 25 no dicen lo mismo,
        # y sin este número el primero se lee como unanimidad.
        "muestra":     len(etiquetas),
    }


def fetch_sentimiento(ticker: str) -> dict | None:
    """Una llamada a StockTwits. Devuelve None ante cualquier problema --
    incluido el challenge de Cloudflare que se come esto desde el VPS."""
    try:
        r = requests.get(
            f"https://api.stocktwits.com/api/2/streams/symbol/{ticker}.json",
            headers={"User-Agent": UA_STOCKTWITS}, timeout=8,
        )
        if r.status_code != 200:
            return None
        return parse_sentimiento(r.json().get("messages", []))
    except Exception:
        return None


def fetch_trending(limite: int = 20) -> list:
    """Símbolos en tendencia en StockTwits, en orden. [] si no se puede."""
    try:
        r = requests.get("https://api.stocktwits.com/api/2/trending/symbols.json",
                         headers={"User-Agent": UA_STOCKTWITS}, timeout=8)
        if r.status_code != 200:
            return []
        salida = []
        for item in r.json().get("symbols", []):
            t = (item.get("symbol") or "").upper()
            # Solo letras. El trending de StockTwits mezcla cripto (PEPE.X,
            # LINK.X, ICP.X, LUNC.X) y cotizadas de otros mercados (AC.TSX),
            # que yfinance no sabe precisar: entraban en la tabla y ocupaban
            # cinco de las quince filas con guiones en todas las columnas.
            # Medido el 15/08/2026 sobre el trending real. Esto también deja
            # fuera notaciones tipo BRK.B, que en este trending no aparecen.
            if t.isalpha() and 2 <= len(t) <= 6:
                salida.append(t)
            if len(salida) >= limite:
                break
        return salida
    except Exception:
        return []
