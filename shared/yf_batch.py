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


def download_batch(tickers, period, batch_size=40, batch_sleep=1.8,
                    max_retries=1, retry_sleep=2.5, coverage_threshold=1.0,
                    min_history=130, include_volume=True, log_prefix=""):
    """Devuelve (close_d, vol_d): dict[ticker] -> pd.Series. Con
    max_retries=1 (por defecto) es un único intento por lote, sin
    reintento -- el patrón que ya tenían scanner_universe.py/
    thematic_scan.py. Con max_retries=3 y coverage_threshold=0.85
    reproduce el patrón de rsrw_service.py/rsrw_scan.py: hasta 3
    reintentos por lote, re-solicitando solo los símbolos que faltaron."""
    close_d, vol_d = {}, {}
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
                if isinstance(raw.columns, pd.MultiIndex):
                    closes = raw["Close"] if "Close" in raw.columns.get_level_values(0) else pd.DataFrame()
                    vols   = raw["Volume"] if include_volume and "Volume" in raw.columns.get_level_values(0) else pd.DataFrame()
                else:
                    closes = raw[["Close"]] if "Close" in raw.columns else pd.DataFrame()
                    vols   = raw[["Volume"]] if include_volume and "Volume" in raw.columns else pd.DataFrame()

                for sym in batch:
                    if sym in closes.columns:
                        series = closes[sym].dropna()
                        if len(series) >= min_history:
                            close_d[sym] = series
                            if include_volume:
                                vol_d[sym] = vols[sym].dropna() if sym in vols.columns else pd.Series(dtype=float)
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

    return close_d, vol_d
