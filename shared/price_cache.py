"""
price_cache.py -- caché en disco de precios, compartida entre los scans
nocturnos de una misma noche.

EL PROBLEMA QUE RESUELVE (pendiente 2.10 de TODO_RSU_TERMINAL.md):
los scans nocturnos se fueron apilando sesión a sesión en el mismo bloque
horario, y tres de ellos descargan EXACTAMENTE los mismos ~503 tickers del
S&P 500 con 15 minutos de diferencia, cada uno por su cuenta:

    22:15  Scanner Universo   503 + 1.961 Russell   2y
    22:30  RS/RW              503 + ETFs            260d
    22:45  CANSLIM            503                   2y

Es tres veces el mismo trabajo contra Yahoo desde el mismo runner, cada
noche — y ya no hay proxy residencial de red de seguridad (se dio de baja).

CÓMO FUNCIONA:
cada ticker se guarda en disco la primera vez que alguien lo descarga, con
el número de filas que trajo. Una petición posterior del MISMO ticker con
un periodo más corto se sirve recortando (`.tail(n)`) en vez de volver a
bajarlo.

POR QUÉ RECORTAR POR FILAS Y NO POR FECHA (verificado con datos reales
antes de construir esto, 28/07/2026): `period="260d"` de yfinance devuelve
260 SESIONES DE COTIZACIÓN, no 260 días naturales — recortar por calendario
daba 178 filas en vez de 260. Con `.tail(260)` sobre una descarga de 2y el
índice sale idéntico día por día, y los valores coinciden con diferencias
máximas de 6e-5 sobre precios de $70-340 (ruido de precisión float32 de
yfinance, error relativo ~1e-7). La única diferencia real es la vela del
día en curso si el mercado está abierto, que se mueve entre dos descargas
cualesquiera — con o sin caché.

ACTIVACIÓN: solo si la variable de entorno RSU_PRICE_CACHE apunta a un
directorio. Sin ella, `download_batch()` se comporta exactamente igual que
siempre — en local y en los workflows individuales no cambia nada.
"""
import os
import pickle
import re
from datetime import datetime, timezone

# Sesiones de cotización que devuelve yfinance para cada `period`. Solo hace
# falta para decidir si lo cacheado da para servir una petición más corta.
_FACTORES = {"d": 1, "wk": 5, "mo": 21, "y": 252}
_RE_PERIODO = re.compile(r"^(\d+)(d|wk|mo|y)$")


def filas_de_periodo(period: str):
    """Nº aproximado de sesiones que trae un `period` de yfinance. None si
    no se reconoce (p.ej. "max") -- en ese caso nunca se sirve de caché."""
    if not period:
        return None
    m = _RE_PERIODO.match(period.strip().lower())
    if not m:
        return None
    return int(m.group(1)) * _FACTORES[m.group(2)]


def directorio() -> str | None:
    """Directorio de caché activo, o None si no está activada."""
    d = os.environ.get("RSU_PRICE_CACHE", "").strip()
    if not d:
        return None
    try:
        os.makedirs(d, exist_ok=True)
    except OSError:
        return None
    return d


def _fecha_hoy() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _ruta(cache_dir: str, ticker: str) -> str:
    # Los tickers pueden traer '.', '^', '=' (BRK-B, ^GSPC, EURUSD=X): se
    # sanean para que sean nombres de fichero válidos en cualquier sistema.
    seguro = re.sub(r"[^A-Za-z0-9_-]", "_", ticker)
    return os.path.join(cache_dir, f"{seguro}.pkl")


# Lo que un `hl` cacheado tiene que traer para servir. Es el contrato que
# escribe shared/yf_batch.py; si allí se añade otra columna, aquí también.
_COLUMNAS_HL = {"Open", "High", "Low"}


def leer(cache_dir: str, ticker: str, filas_necesarias, necesita_volumen: bool, necesita_hl: bool):
    """Devuelve (close, vol, hl) recortados a `filas_necesarias`, o None si
    no sirve: no está cacheado, es de otro día, tiene menos filas de las
    pedidas, o le falta el volumen/HL que se pide ahora."""
    if filas_necesarias is None:
        return None
    try:
        with open(_ruta(cache_dir, ticker), "rb") as f:
            e = pickle.load(f)
    except (OSError, pickle.UnpicklingError, EOFError):
        return None

    if e.get("fecha") != _fecha_hoy():
        return None            # de otra noche: los precios ya no son los de hoy
    close = e.get("close")
    if close is None or len(close) < filas_necesarias:
        return None            # se cacheó un periodo más corto del que hace falta
    if necesita_volumen and e.get("vol") is None:
        return None
    if necesita_hl and e.get("hl") is None:
        return None
    # Una entrada escrita ANTES de que el lote empezara a traer `Open`
    # (14/08/2026) tiene el HL completo y pasaría todos los filtros de arriba,
    # pero le falta la columna que necesita el oscilador L3 -- se serviría un
    # DataFrame incompleto y el cálculo reventaría o, peor, se saltaría ese
    # ticker en silencio. Se trata como fallo de caché: se vuelve a descargar.
    if necesita_hl and not _COLUMNAS_HL.issubset(set(e["hl"].columns)):
        return None

    n = filas_necesarias
    vol = e.get("vol")
    hl  = e.get("hl")
    return (
        close.tail(n),
        vol.tail(n) if vol is not None else None,
        hl.tail(n) if hl is not None else None,
    )


def escribir(cache_dir: str, ticker: str, close, vol=None, hl=None) -> None:
    """Guarda lo descargado. Nunca revienta el scan si el disco falla: el
    caché es una optimización, no una fuente de verdad."""
    try:
        with open(_ruta(cache_dir, ticker), "wb") as f:
            pickle.dump({"fecha": _fecha_hoy(), "close": close, "vol": vol, "hl": hl}, f)
    except (OSError, pickle.PicklingError) as e:
        print(f"[PriceCache] No se pudo cachear {ticker}: {type(e).__name__}: {e}")
