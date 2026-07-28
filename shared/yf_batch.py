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
import pandas as pd
import yfinance as yf

import price_cache


def download_batch(tickers, period, batch_size=40, batch_sleep=1.8,
                    max_retries=1, retry_sleep=2.5, coverage_threshold=1.0,
                    min_history=130, include_volume=True, include_hl=False, log_prefix=""):
    """Devuelve (close_d, vol_d): dict[ticker] -> pd.Series. Con
    max_retries=1 (por defecto) es un único intento por lote, sin
    reintento -- el patrón que ya tenían scanner_universe.py/
    thematic_scan.py. Con max_retries=3 y coverage_threshold=0.85
    reproduce el patrón de rsrw_service.py/rsrw_scan.py: hasta 3
    reintentos por lote, re-solicitando solo los símbolos que faltaron.

    include_hl=True (usado por scripts/canslim_scan.py, sesión 32) añade
    un tercer valor de retorno hl_d: dict[ticker] -> pd.DataFrame con
    columnas High/Low, extraídas del mismo yf.download() ya en curso --
    con include_hl=False (default) el retorno sigue siendo el 2-tuple de
    siempre, sin tocar el contrato de los 4 consumidores existentes.

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
                else:
                    closes = raw[["Close"]] if "Close" in raw.columns else pd.DataFrame()
                    vols   = raw[["Volume"]] if quiere_vol and "Volume" in raw.columns else pd.DataFrame()
                    highs  = raw[["High"]] if quiere_hl and "High" in raw.columns else pd.DataFrame()
                    lows   = raw[["Low"]] if quiere_hl and "Low" in raw.columns else pd.DataFrame()

                for sym in batch:
                    if sym in closes.columns:
                        series = closes[sym].dropna()
                        vol_sym = (vols[sym].dropna() if sym in vols.columns else pd.Series(dtype=float)) if quiere_vol else None
                        hl_sym  = pd.DataFrame({
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

    if include_hl:
        return close_d, vol_d, hl_d
    return close_d, vol_d
