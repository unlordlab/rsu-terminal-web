"""
yf_batch.py -- descarga por lotes de yfinance con reintentos opcionales,
compartido entre backend/services/rsrw_service.py, scripts/rsrw_scan.py,
scripts/scanner_universe.py y scripts/thematic_scan.py. Los 4 repetían el
mismo bucle de batching (BATCH_SIZE=40 idéntico en los 4) con 2 niveles de
robustez distintos -- no 3, como decía el roadmap. Parametrizado para que
cada sitio conserve EXACTAMENTE su comportamiento actual (mismo criterio
que shared/rsrw_engine.py, sesión 14: deduplicar sin cambiar
comportamiento salvo decisión explícita).

NO depende de nada de backend/ (fastapi, pydantic) -- scripts/ corre en el
runner de GitHub Actions sin ese entorno instalado.
"""
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import yfinance as yf

import price_cache
from festivos_mercado import ultima_sesion_cerrada

# ── LA BARRA DE LA ÚLTIMA SESIÓN, QUE LLEGA VACÍA CASI TODAS LAS NOCHES ──────
#
# EL CASO, Scanner #25. Del 05 al 12/09/2026, en 5 de 7 noches, el escaneo se
# publicó con los precios de ANTEAYER: Yahoo servía la barra del día a ~1% de
# los tickers. La noche del 11 al 12 quedó instrumentada: de 2.426 valores, 27
# traían la sesión del 11 y 2.397 se quedaban en la del 10 — y en el MISMO
# minuto, `Ticker("A").history(period="5d")` sí la traía. O sea que el dato
# existía y la descarga en lote no lo veía. De ahí sale Market con la amplitud
# de anteayer, el briefing contando la sesión equivocada, y RS/RW, CANSLIM y
# Temáticos con un día de retraso.
#
# NO SE ARREGLA MOVIENDO EL CRON: a esa hora el dato ya está publicado (se
# comprobó al día siguiente: las dos vías lo traen). Lo que falla es la
# descarga, y por eso la reparación es una SEGUNDA PASADA, solo de la barra
# que falta y solo para los tickers que no la traen:
#
#   - rango corto (`period="5d"`) en vez de los 2 años del lote grande: si el
#     problema es que la petición larga no la sirve, la corta sí.
#   - `auto_adjust=False`: si el problema es que Yahoo manda el `adjclose` de
#     la última barra a null, `auto_adjust=True` convierte ese cierre en NaN y
#     el `dropna()` borra la fila. Pidiendo el cierre SIN ajustar no hay nada
#     que anular — y para la última barra el cierre ajustado ES el cierre a
#     secas, porque solo se ajusta hacia atrás: ningún dividendo posterior
#     puede haberla tocado todavía.
#
# La pasada cubre las dos explicaciones a la vez, y el registro dice cuál era:
# para los que sigan sin barra tras el reintento se anota si la fila NO VIENE o
# si viene con el cierre ajustado vacío.
UMBRAL_ULTIMA_SESION = 0.9   # por debajo de esto, se repara
MUESTRA_DIAGNOSTICO  = 3     # cuántos se examinan uno a uno si siguen fallando


def _fecha_ultima(serie):
    """La fecha (de Nueva York) de la última barra de una serie."""
    if serie is None or len(serie) == 0:
        return None
    return serie.index[-1].date()


def _pegar(serie, ts, valor):
    """Añade una barra al final respetando el huso del índice que ya había."""
    if serie is None:
        return None
    tz = getattr(serie.index, "tz", None)
    if tz is not None and getattr(ts, "tzinfo", None) is not None:
        ts = ts.tz_convert(tz)
    elif tz is None and getattr(ts, "tzinfo", None) is not None:
        ts = ts.tz_localize(None)
    return pd.concat([serie, pd.Series([valor], index=[ts])])


def _diagnosticar_uno(ticker, esperada):
    """Por qué ESE ticker sigue sin la barra: ¿no viene la fila, o viene con el
    cierre ajustado vacío? Es lo que separa las dos explicaciones posibles, y
    solo se puede ver ticker a ticker: en una descarga de varios, el índice es
    la UNIÓN de todos, así que una fila de NaN puede ser «llegó vacía» o
    «no llegó y la puso otro ticker». Nunca levanta: es un diagnóstico."""
    try:
        h = yf.Ticker(ticker).history(period="5d", auto_adjust=False)
        filas = [i for i in h.index if i.date() == esperada]
        if not filas:
            return f"{ticker}: la fila del {esperada} NO VIENE (últimas {[str(i.date()) for i in h.index[-2:]]})"
        fila = h.loc[filas[0]]
        cierre = fila.get("Close")
        ajustado = fila.get("Adj Close")
        return (f"{ticker}: fila presente · Close={cierre} · Adj Close={ajustado}"
                + ("  ← el ajustado viene vacío: eso es lo que borraba la barra"
                   if pd.isna(ajustado) and not pd.isna(cierre) else ""))
    except Exception as e:
        return f"{ticker}: el diagnóstico falló ({type(e).__name__}: {e})"


def reparar_ultima_sesion(close_d, vol_d, hl_d, esperada, batch_size=40, batch_sleep=1.8,
                          cache_dir=None, log_prefix=""):
    """Rellena la barra de `esperada` a los tickers que llegaron sin ella.

    Devuelve (cuántos faltaban, cuántos se recuperaron). No toca a los que ya
    la traen, no inventa barras si el reintento tampoco las trae, y no puede
    tumbar el scan: lo peor que hace es no recuperar nada.
    """
    if not close_d or esperada is None:
        return 0, 0
    faltan = [t for t, s in close_d.items()
              if _fecha_ultima(s) is not None and _fecha_ultima(s) < esperada]
    if not faltan:
        return 0, 0
    cobertura = 1 - len(faltan) / len(close_d)
    print(f"{log_prefix}Barra del {esperada}: la traen {cobertura:.0%} de los tickers. "
          f"Segunda pasada para los {len(faltan)} que no la traen (rango corto, sin ajustar)")

    recuperados = 0
    lotes = [faltan[i:i + batch_size] for i in range(0, len(faltan), batch_size)]
    for i, lote in enumerate(lotes):
        try:
            raw = yf.download(lote, period="5d", auto_adjust=False,
                              progress=False, threads=True)
        except Exception as e:
            print(f"{log_prefix}Reparación: el lote {i+1}/{len(lotes)} falló ({type(e).__name__}: {e})")
            continue
        if raw is None or raw.empty:
            continue
        multi = isinstance(raw.columns, pd.MultiIndex)

        def _col(campo, sym):
            if multi:
                if campo not in raw.columns.get_level_values(0):
                    return None
                tabla = raw[campo]
                return tabla[sym] if sym in tabla.columns else None
            return raw[campo] if campo in raw.columns else None

        for sym in lote:
            cierres = _col("Close", sym)
            if cierres is None:
                continue
            marcas = [ts for ts in cierres.index if ts.date() == esperada]
            if not marcas:
                continue
            ts = marcas[0]
            valor = cierres.loc[ts]
            if pd.isna(valor):
                continue
            close_d[sym] = _pegar(close_d[sym], ts, float(valor))
            if sym in vol_d:
                vols = _col("Volume", sym)
                if vols is not None and ts in vols.index and not pd.isna(vols.loc[ts]):
                    vol_d[sym] = _pegar(vol_d[sym], ts, float(vols.loc[ts]))
            if hl_d is not None and sym in hl_d:
                fila = {}
                for campo in ("Open", "High", "Low"):
                    col = _col(campo, sym)
                    if col is not None and ts in col.index and not pd.isna(col.loc[ts]):
                        fila[campo] = float(col.loc[ts])
                if len(fila) == 3:
                    nueva = pd.DataFrame([fila], index=[ts])
                    hl_d[sym] = pd.concat([hl_d[sym], nueva])
            if cache_dir:
                # El caché lo leen los otros tres scans de la misma noche: si no
                # se reescribe, el arreglo dura solo para este.
                price_cache.escribir(cache_dir, sym, close_d[sym],
                                     vol_d.get(sym), (hl_d or {}).get(sym))
            recuperados += 1
        if i < len(lotes) - 1:
            time.sleep(batch_sleep)

    siguen = [t for t in faltan if _fecha_ultima(close_d[t]) < esperada]
    print(f"{log_prefix}Reparación: {recuperados} de {len(faltan)} recuperados, "
          f"{len(siguen)} siguen sin la barra del {esperada}")
    if siguen:
        desde_velas = reparar_con_velas(close_d, hl_d, siguen, esperada, batch_size,
                                        batch_sleep, cache_dir, vol_d, log_prefix)
        recuperados += desde_velas
        siguen = [t for t in faltan if _fecha_ultima(close_d[t]) < esperada]
    for t in siguen[:MUESTRA_DIAGNOSTICO]:
        print(f"{log_prefix}🔬 {_diagnosticar_uno(t, esperada)}")
    return len(faltan), recuperados


# ── SI LA BARRA DIARIA LLEGA VACÍA, EL CIERRE SALE DE LAS VELAS DE 30 MINUTOS ─
#
# Scanner #26, 15/09/2026. La segunda pasada de arriba recuperó 0 de 2.402 la
# primera noche que corrió, y su propio diagnóstico dijo por qué: «SPY: fila
# presente · Close=nan · Adj Close=nan», pedido con `Ticker.history` y sin
# ajustar. O sea que a esa hora Yahoo tiene la fila de la sesión pero sin el
# cierre, por cualquier camino de barras DIARIAS. Ninguna de las dos
# explicaciones de #25 (rango largo, ajuste) era la buena.
#
# Las velas intradía de la misma sesión sí se sirven en directo. Medido el
# 15/09 sobre 39 valores contra el cierre oficial del 14/09: el cierre de la
# última vela de 30 min se separa un 0,03% de mediana (0,4% como mucho) y solo
# 1 de 39 cambia de sube a baja, por un movimiento mínimo. El VOLUMEN no sirve:
# sale un 17% corto de mediana porque la subasta de cierre no está en las velas.
# Por eso se pega el cierre y el OHLC, pero NO el volumen: un RVOL con el
# volumen de la víspera es un dato viejo, y uno con el 83% del volumen es un
# dato falso.
#
# Solo cuenta una sesión COMPLETA: si la última vela no es la de las 15:30 ET,
# no se pega nada.
VELA_INTRADIA = "30m"
ULTIMA_VELA_ET = (15, 30)


def _barra_desde_velas(velas, esperada):
    """{Open, High, Low, Close} de la sesión `esperada` a partir de sus velas,
    o None si no está completa. `velas` es un DataFrame de UN ticker."""
    if velas is None or len(velas) == 0 or "Close" not in velas:
        return None
    idx = velas.index
    if getattr(idx, "tz", None) is not None:
        idx = idx.tz_convert("America/New_York")
    del_dia = velas[[ts.date() == esperada for ts in idx]].dropna(subset=["Close"])
    if del_dia.empty:
        return None
    ultima = del_dia.index[-1]
    ultima = ultima.tz_convert("America/New_York") if getattr(ultima, "tzinfo", None) else ultima
    if (ultima.hour, ultima.minute) < ULTIMA_VELA_ET:
        return None
    return {"Open": float(del_dia["Open"].iloc[0]), "High": float(del_dia["High"].max()),
            "Low": float(del_dia["Low"].min()), "Close": float(del_dia["Close"].iloc[-1])}


def reparar_con_velas(close_d, hl_d, tickers, esperada, batch_size=40, batch_sleep=1.8,
                      cache_dir=None, vol_d=None, log_prefix="", descargar=None):
    """Tercera pasada: la barra de `esperada` desde las velas de 30 min.
    Devuelve cuántos se recuperaron. Nunca levanta."""
    descargar = descargar or (lambda lote: yf.download(
        lote, period="5d", interval=VELA_INTRADIA, auto_adjust=False,
        prepost=False, progress=False, threads=True))
    recuperados = 0
    lotes = [tickers[i:i + batch_size] for i in range(0, len(tickers), batch_size)]
    for i, lote in enumerate(lotes):
        try:
            raw = descargar(lote)
        except Exception as e:
            print(f"{log_prefix}Velas de {VELA_INTRADIA}: el lote {i+1}/{len(lotes)} falló "
                  f"({type(e).__name__}: {e})")
            continue
        if raw is None or raw.empty:
            continue
        multi = isinstance(raw.columns, pd.MultiIndex)
        for sym in lote:
            try:
                velas = raw.xs(sym, axis=1, level=1) if multi else raw
            except KeyError:
                continue
            barra = _barra_desde_velas(velas, esperada)
            if barra is None:
                continue
            # La barra se fecha como las diarias de esa serie: medianoche de NY.
            ts = pd.Timestamp(esperada).tz_localize("America/New_York")
            close_d[sym] = _pegar(close_d[sym], ts, barra["Close"])
            if hl_d is not None and sym in hl_d:
                nueva = pd.DataFrame([{k: barra[k] for k in ("Open", "High", "Low")}], index=[ts])
                viejo = hl_d[sym]
                if getattr(viejo.index, "tz", None) is None:
                    nueva.index = nueva.index.tz_localize(None)
                hl_d[sym] = pd.concat([viejo, nueva])
            if cache_dir:
                price_cache.escribir(cache_dir, sym, close_d[sym],
                                     (vol_d or {}).get(sym), (hl_d or {}).get(sym))
            recuperados += 1
        if i < len(lotes) - 1:
            time.sleep(batch_sleep)
    print(f"{log_prefix}Velas de {VELA_INTRADIA}: {recuperados} de {len(tickers)} recuperados "
          f"(cierre y OHLC; el volumen de ese día se deja sin poner)")
    return recuperados


def download_batch(tickers, period, batch_size=40, batch_sleep=1.8,
                    max_retries=1, retry_sleep=2.5, coverage_threshold=1.0,
                    min_history=130, include_volume=True, include_hl=False, log_prefix="",
                    reparar_ultima=False, ahora_et=None):
    """Devuelve (close_d, vol_d): dict[ticker] -> pd.Series. Con
    max_retries=1 (por defecto) es un único intento por lote, sin
    reintento -- el patrón que ya tenían scanner_universe.py/
    thematic_scan.py. Con max_retries=3 y coverage_threshold=0.85
    reproduce el patrón de rsrw_service.py/rsrw_scan.py: hasta 3
    reintentos por lote, re-solicitando solo los símbolos que faltaron.

    include_hl=True (usado por scripts/canslim_scan.py, sesión 32) añade
    un tercer valor de retorno hl_d: dict[ticker] -> pd.DataFrame con
    columnas Open/High/Low, extraídas del mismo yf.download() ya en curso --
    con include_hl=False (default) el retorno sigue siendo el 2-tuple de
    siempre, sin tocar el contrato de los 4 consumidores existentes.

    El `Open` se añadió el 14/08/2026 para poder calcular el oscilador L3 en
    el scan nocturno (shared/l3_banker.py necesita OHLC completo para su
    precio típico). Es una columna MÁS en el mismo DataFrame, así que
    canslim_scan.py, que lee hl["High"]/hl["Low"], no se entera. Viene en la
    misma respuesta de yfinance: no cuesta ni una petición extra.

    Si la variable de entorno RSU_PRICE_CACHE apunta a un directorio, los
    tickers ya descargados esa misma noche por OTRO scan se sirven de ahí y
    solo se descarga lo que falte (ver shared/price_cache.py y el pendiente
    2.10). Sin esa variable no cambia absolutamente nada."""
    close_d, vol_d, hl_d = {}, {}, {}

    # ── Lo que ya tenga otro scan de esta misma noche ────────────────────────
    cache_dir = price_cache.directorio()
    if cache_dir:
        filas = price_cache.filas_de_periodo(period)
        pendientes = []
        for sym in tickers:
            hit = price_cache.leer(cache_dir, sym, filas, include_volume, include_hl)
            if hit is None:
                pendientes.append(sym)
                continue
            close, vol, hl = hit
            if len(close) < min_history:
                continue      # cacheado pero insuficiente para ESTE llamador
            close_d[sym] = close
            if include_volume: vol_d[sym] = vol if vol is not None else pd.Series(dtype=float)
            if include_hl:     hl_d[sym]  = hl
        if len(pendientes) < len(tickers):
            print(f"{log_prefix}Caché de precios: {len(tickers) - len(pendientes)} de {len(tickers)} "
                  f"símbolos ya descargados esta noche, quedan {len(pendientes)} por bajar")
        tickers = pendientes
        if not tickers:
            return (close_d, vol_d, hl_d) if include_hl else (close_d, vol_d)

    batches = [tickers[i:i + batch_size] for i in range(0, len(tickers), batch_size)]
    n_batches = len(batches)

    for i, batch in enumerate(batches):
        print(f"{log_prefix}Lote {i+1}/{n_batches} ({len(batch)} símbolos)...")
        original_batch = list(batch)
        original_size  = len(original_batch)
        got_syms = set()

        for attempt in range(max_retries):
            try:
                raw = yf.download(batch, period=period, auto_adjust=True, progress=False, threads=True)
                # Con caché activa se extraen SIEMPRE volumen y High/Low aunque
                # este llamador no los pida: ya vienen en la misma respuesta de
                # yfinance, y si no se cachean, el siguiente scan que sí los
                # necesite tendría que volver a descargar el ticker entero.
                quiere_vol = include_volume or bool(cache_dir)
                quiere_hl  = include_hl or bool(cache_dir)
                if isinstance(raw.columns, pd.MultiIndex):
                    closes = raw["Close"] if "Close" in raw.columns.get_level_values(0) else pd.DataFrame()
                    vols   = raw["Volume"] if quiere_vol and "Volume" in raw.columns.get_level_values(0) else pd.DataFrame()
                    highs  = raw["High"] if quiere_hl and "High" in raw.columns.get_level_values(0) else pd.DataFrame()
                    lows   = raw["Low"] if quiere_hl and "Low" in raw.columns.get_level_values(0) else pd.DataFrame()
                    opens  = raw["Open"] if quiere_hl and "Open" in raw.columns.get_level_values(0) else pd.DataFrame()
                else:
                    closes = raw[["Close"]] if "Close" in raw.columns else pd.DataFrame()
                    vols   = raw[["Volume"]] if quiere_vol and "Volume" in raw.columns else pd.DataFrame()
                    highs  = raw[["High"]] if quiere_hl and "High" in raw.columns else pd.DataFrame()
                    lows   = raw[["Low"]] if quiere_hl and "Low" in raw.columns else pd.DataFrame()
                    opens  = raw[["Open"]] if quiere_hl and "Open" in raw.columns else pd.DataFrame()

                for sym in batch:
                    if sym in closes.columns:
                        series = closes[sym].dropna()
                        vol_sym = (vols[sym].dropna() if sym in vols.columns else pd.Series(dtype=float)) if quiere_vol else None
                        hl_sym  = pd.DataFrame({
                            "Open": opens[sym] if sym in opens.columns else pd.Series(dtype=float),
                            "High": highs[sym] if sym in highs.columns else pd.Series(dtype=float),
                            "Low":  lows[sym]  if sym in lows.columns  else pd.Series(dtype=float),
                        }) if quiere_hl else None

                        # Se cachea lo descargado ANTES del filtro de
                        # min_history: otro scan con un umbral más bajo puede
                        # aprovechar el mismo ticker.
                        if cache_dir:
                            price_cache.escribir(cache_dir, sym, series, vol_sym, hl_sym)

                        if len(series) >= min_history:
                            close_d[sym] = series
                            if include_volume:
                                vol_d[sym] = vol_sym if vol_sym is not None else pd.Series(dtype=float)
                            if include_hl:
                                hl_d[sym] = hl_sym
                            got_syms.add(sym)

                missing  = [s for s in original_batch if s not in got_syms]
                coverage = len(got_syms) / original_size if original_size else 1.0

                if coverage >= coverage_threshold or attempt == max_retries - 1:
                    if missing and max_retries > 1:
                        print(f"{log_prefix}Lote {i+1}/{n_batches}: {len(missing)} símbolos sin datos suficientes tras {attempt+1} intento(s): {missing[:15]}{'...' if len(missing) > 15 else ''}")
                    break

                print(f"{log_prefix}Lote {i+1}/{n_batches}: cobertura {coverage:.0%} tras intento {attempt+1}, reintentando {len(missing)} símbolos...")
                batch = missing
                time.sleep(retry_sleep)
            except Exception as e:
                print(f"{log_prefix}Lote {i+1}/{n_batches} intento {attempt+1} falló: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_sleep)
                continue

        if i < n_batches - 1:
            time.sleep(batch_sleep)

    # La barra de la última sesión, para los que llegaron sin ella. Va aquí y no
    # en cada consumidor porque el hueco lo sufren los cuatro scans nocturnos y
    # los cuatro leen el mismo caché: repararlo una vez lo arregla para todos.
    # `reparar_ultima=False` por defecto — las llamadas del backend corren
    # dentro de una petición web y no pueden permitirse una pasada extra.
    if reparar_ultima and close_d:
        ahora = ahora_et or datetime.now(ZoneInfo("America/New_York"))
        reparar_ultima_sesion(close_d, vol_d, hl_d if include_hl else None,
                              ultima_sesion_cerrada(ahora), batch_size, batch_sleep,
                              cache_dir, log_prefix)

    if include_hl:
        return close_d, vol_d, hl_d
    return close_d, vol_d
