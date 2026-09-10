"""
tickers.py -- qué puede ser un ticker, para los datos que vienen de TERCEROS.

EL CASO, 10/09/2026, vaciando la bolsa de verificación de Watchlist. Dos
fuentes meten tickers y URLs de fuera directamente en la pantalla de todos:

  - Congreso: `scripts/congress_scan.py` copia `ticker` y `doc_url` tal cual
    de un repositorio público de GitHub (kadoa-org/congress-trading-monitor),
    y `congress.js` los pinta dentro de un `onclick="goToResearch('…')"` y de
    un `href`.
  - Insider Flow: `issuerTradingSymbol` de los Form 4 de la SEC es texto libre
    que escribe cada empresa. En la base real ya hay «GEF, GEF-B» y
    «MOGA/MOGB» — inofensivos, pero prueban que puede entrar cualquier cosa.

Dentro de un `onclick`, escapar HTML no sirve: el navegador descodifica la
entidad antes de ejecutar el JavaScript, y la comilla vuelve. La única
defensa real es que el dato llegue ya siendo lo que dice ser.

Es el MISMO patrón que ya validaba la entrada de usuarios en Watchlist y
Research (`^[A-Z0-9.\\-^=]{1,12}$`). Aquí va compartido para los escaneos, que
corren fuera del backend.
"""
import re

TICKER_RE = re.compile(r"^[A-Z0-9.\-^=]{1,12}$")

# Cómo escribe la gente «sin símbolo», ya sin espacios, puntos, barras ni guiones.
SIN_SIMBOLO = {"NA", "NONE", "NULL", "NIL", "", "0"}


def ticker_valido(valor) -> bool:
    return bool(valor) and bool(TICKER_RE.match(str(valor)))


def normalizar_ticker(valor):
    """El ticker, o None si no hay ninguno reconocible.

    Si viene una lista escrita a mano —«GEF, GEF-B», «MOGA/MOGB»— se queda con
    el PRIMERO que sea un ticker válido: es la clase principal, y así el
    enlace a Research funciona en vez de romperse. Si no hay ninguno, None:
    mejor sin ticker que con uno que no es.
    """
    t = str(valor or "").strip().upper()
    # Los «no tiene símbolo» se escriben de muchas formas, y partir «N/A» por
    # la barra daba «N» — un ticker válido de OTRA empresa. Un Form 4 de una
    # compañía sin cotización acababa atribuido a quien no es.
    if re.sub(r"[\s./\-]", "", t) in SIN_SIMBOLO:
        return None
    if TICKER_RE.match(t):
        return t
    for trozo in re.split(r"[,/;\s]+", t):
        if TICKER_RE.match(trozo):
            return trozo
    return None


def url_segura(valor):
    """La URL si es http(s); None si no. Un `javascript:` en un enlace se
    ejecuta al pulsarlo, con la sesión del usuario abierta."""
    u = str(valor or "").strip()
    return u if re.match(r"^https?://", u, re.IGNORECASE) else None
