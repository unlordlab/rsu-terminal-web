import json
import time
import os
import sys
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor
import yfinance as yf

# Universo compartido -- ver shared/sp500_universe.py (Fase 2.1 del Plan
# Maestro, 20/07/2026). Antes había un diccionario embebido aquí mismo,
# idéntico al de scripts/scanner_universe.py y scripts/rsrw_scan.py -- ahora
# una sola fuente de verdad para los tres. shared/ es sibling de backend/,
# así que se llega con "..".
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "shared"))
from sp500_universe import SP500_SECTOR_MAP  # noqa: E402
from time_utils import get_timestamp  # noqa: E402
from rsrw_engine import (  # noqa: E402
    rs_smooth as _rs_smooth, rs_trend_slope as _rs_trend_slope,
    rs_percentile, rs_momentum, percentil_contra, PERIODS, WEIGHTS, EMA_SMOOTH, TREND_WIN,
    SECTOR_ETFS, GICS_MAP,
)
from yf_batch import download_batch  # noqa: E402

GIST_ID     = "36afc4bd0f8e376b0f6354889bda4d52"
GIST_FILE   = "rsrw_scan.json"
BENCHMARK   = "SPY"
BATCH_SIZE  = 40
BATCH_SLEEP = 1.8

# ── GIST ──────────────────────────────────────────────────────────────────────

def _load_gist() -> dict | None:
    """El Gist del scan nocturno, cacheado 10 min.

    Sin caché, CADA carga de la página RS/RW era una petición a la API de
    GitHub, que limita a 60 por hora y por IP a los clientes sin autenticar.
    Con ~100 usuarios eso se agota en minutos y a partir de ahí el módulo
    entero se queda sin datos -- y no solo este: Market lee otro Gist desde la
    misma IP del VPS y comparte ese presupuesto. Ver auditoría RS/RW, #2.

    10 min es de sobra: el contenido lo reescribe un scan NOCTURNO, así que
    durante la sesión de mercado no cambia nunca.
    """
    from services.cache import cache
    cacheado = cache.get("rsrw:gist")
    if cacheado is not None:
        return cacheado or None      # {} cacheado = fallo reciente, no reintentar

    try:
        r = requests.get(
            f"https://api.github.com/gists/{GIST_ID}",
            timeout=10,
            headers={"Accept": "application/vnd.github.v3+json"}
        )
        r.raise_for_status()
        content = r.json()["files"][GIST_FILE]["content"]
        data    = json.loads(content)
        bueno   = data if data.get("stocks") and len(data["stocks"]) > 10 else None
    except Exception:
        bueno = None

    # También se cachea el fallo, con TTL corto: si GitHub nos está limitando,
    # machacarlo en cada carga de página solo alarga el bloqueo.
    cache.set("rsrw:gist", bueno or {}, 600 if bueno else 60)
    return bueno

def _parse_gist(data: dict) -> tuple:
    meta    = data.get("meta", {})
    stocks  = data.get("stocks", {})
    sectors = data.get("sectors", {})

    if stocks:
        df = pd.DataFrame.from_dict(stocks, orient="index")
        df.index.name = "Ticker"
        rename = {
            "rs_percentile": "RS_Pct",   "rs_score_raw": "RS_Score",
            "rs_21d":        "RS_21d",   "rs_63d":       "RS_63d",
            "rs_126d":       "RS_126d",  "rs_momentum":  "RS_Mom",
            "rs_trend":      "RS_Trend", "rs_vs_sector": "RS_vs_Sector",
            "rvol":          "RVOL",     "sector":       "Sector",
            "price":         "Precio",
        }
        df = df.rename(columns=rename)
        for c in ["RS_Pct","RS_Score","RS_21d","RS_63d","RS_126d","RS_Mom","RS_Trend","RS_vs_Sector","RVOL","Precio"]:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce")
        df = df.dropna(subset=["RS_Pct"])
        # Mapear sectores en inglés a español
        if "Sector" in df.columns:
            df["Sector"] = df["Sector"].map(lambda x: GICS_MAP.get(str(x), x) if pd.notna(x) else "Otros")
            df["Sector"] = df["Sector"].fillna("Otros")
    else:
        df = pd.DataFrame()

    if sectors:
        sdf = pd.DataFrame.from_dict(sectors, orient="index")
        sdf.index.name = "Sector"
        for c in ["RS", "Return_63d", "RS_trend"]:
            if c in sdf.columns:
                sdf[c] = pd.to_numeric(sdf[c], errors="coerce")
    else:
        sdf = pd.DataFrame()

    return df, sdf, meta

def _freshness(meta: dict) -> str:
    try:
        ts  = meta.get("generated_at", "")
        dt  = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        ago = datetime.now(timezone.utc) - dt
        mins = int(ago.total_seconds() / 60)
        if mins < 60:   return f"Hace {mins} min"
        if mins < 1440: return f"Hace {mins//60}h"
        return f"Hace {mins//1440}d"
    except Exception:
        return "Desconocido"

# ── SCAN ON-DEMAND ────────────────────────────────────────────────────────────



def _get_sp500_tickers() -> tuple:
    """
    Universo S&P 500 embebido estáticamente en el código (sin llamada de red ni
    dependencia de lxml/Wikipedia). Se actualiza manualmente cuando cambien las
    constituyentes del índice — suficientemente estable para uso entre revisiones.
    """
    tickers = list(SP500_SECTOR_MAP.keys())
    print(f"[RS/RW scan] Universo S&P 500 (lista estática embebida): {len(tickers)} tickers")
    return tickers, SP500_SECTOR_MAP

# _run_scan_engine() eliminado el 30/07/2026 junto con get_rsrw_scan() y el
# endpoint GET /rsrw/scan. Motivos, todos de la auditoría del módulo:
#
#   #3 -- El scan on-demand descargaba ~500 tickers de Yahoo DENTRO de una
#         petición HTTP, bloqueando el event loop de FastAPI durante minutos.
#         La propia UI ya decía "Scan nocturno automático, sin scan on-demand"
#         y el frontend no lo llamaba desde hacía tiempo (verificado: cero
#         referencias a /rsrw/scan en todo frontend/).
#   #5 -- Aquí vivía `tickers[:max_tickers]` con max_tickers=500 sobre un
#         universo de 503: recortaba ALFABÉTICAMENTE, así que los percentiles
#         se calculaban sobre un universo incompleto al que siempre le
#         faltaban los mismos tres valores del final del abecedario.
#   #14 -- Y aquí se repetían los umbrales 80/20 y los límites 50/30 de
#         leaders/laggards, ya escritos en get_rsrw_from_gist().
#
# El cálculo de verdad vive en scripts/rsrw_scan.py (GitHub Actions, nocturno,
# universo completo) sobre shared/rsrw_engine.py. Si algún día hace falta un
# scan bajo demanda, el sitio correcto es disparar el workflow, no recalcular
# dentro de una petición.

# ── MAIN ENDPOINTS ────────────────────────────────────────────────────────────

def _df_to_records(df: pd.DataFrame, limit: int = 500) -> list:
    if df.empty: return []
    # El nombre del índice decide cómo se llama la clave: "Ticker" para las
    # acciones, "Sector" para la tabla sectorial. Antes se escribía "ticker"
    # SIEMPRE, así que "Tecnología" o "Energía" viajaban en un campo llamado
    # ticker -- el frontend lo tapaba con un `s.ticker || s.sector`, pero
    # cualquier consumidor que se fíe del nombre del campo (el tagging de
    # cartera/watchlist, un deep-link ?ticker=) intentaría buscar un sector
    # como si fuera un símbolo. Ver auditoría RS/RW, #12.
    clave = (df.index.name or "ticker").strip().lower()
    records = []
    for ticker, row in df.iterrows():
        r = {clave: str(ticker)}
        for col in df.columns:
            val = row[col]
            try:
                if pd.isna(val): val = None
                elif isinstance(val, (np.integer,)): val = int(val)
                elif isinstance(val, (np.floating,)): val = round(float(val), 4)
                elif isinstance(val, str): val = val.strip()
            except Exception: pass
            r[col.lower()] = val
        # Asegurar que sector nunca sea vacío
        if not r.get('sector') or str(r.get('sector', '')).strip() in ('', 'nan', 'None'):
            r['sector'] = 'Otros'
        records.append(r)
    return records[:limit]

def _tag_cartera(records: list) -> list:
    """Añade en_cartera a una lista de records de ticker (leaders/laggards,
    nunca a sectors, que no son tickers) -- badge 💼, Fase 3 del roadmap."""
    from services.cartera_service import get_cartera_tickers
    cartera_tickers = get_cartera_tickers()
    for r in records:
        r["en_cartera"] = r.get("ticker") in cartera_tickers
    return records

def get_universe_dataframe():
    """
    Devuelve (df, meta) con el DataFrame COMPLETO del universo (todas las
    acciones, no solo líderes/laggards) tal como lo deja el último scan
    guardado en el Gist. Pensado para que otros módulos (ej. Composición
    Sectorial en Market) puedan agregar métricas por sector reutilizando este
    mismo dato, sin repetir la carga del Gist ni hacer llamadas nuevas a APIs.
    Devuelve None si el Gist no está disponible o no tiene datos válidos.
    """
    data = _load_gist()
    if not data:
        return None
    df, sdf, meta = _parse_gist(data)
    if df.empty:
        return None
    return df, meta

def get_rsrw_from_gist() -> dict:
    try:
        data = _load_gist()
        if not data:
            return {"ok": False, "error": "Gist vacío o no disponible", "mode": "gist"}

        df, sdf, meta = _parse_gist(data)
        if df.empty:
            return {"ok": False, "error": "Sin datos en el Gist", "mode": "gist"}

        leaders = df[df["RS_Pct"] >= 80].sort_values("RS_Pct", ascending=False)
        laggards = df[df["RS_Pct"] <= 20].sort_values("RS_Pct", ascending=True)

        return {
            "ok":        True,
            "mode":      "gist",
            "freshness": _freshness(meta),
            "meta":      meta,
            "total":     len(df),
            "leaders":   _tag_cartera(_df_to_records(leaders, 50)),
            "laggards":  _tag_cartera(_df_to_records(laggards, 30)),
            "sectors":   _df_to_records(sdf) if not sdf.empty else [],
            "timestamp": get_timestamp(),
        }
    except Exception as e:
        return {"ok": False, "error": str(e), "mode": "gist"}

# Mismos cortes que ya usa get_rsrw_from_gist() para separar líderes de
# rezagados. No se inventan bandas nuevas: si la pantalla llama "líder" a un
# RS de 80, el histórico tiene que usar ese mismo número o estaría contando
# cruces de una frontera que el usuario no ve en ninguna parte.
UMBRAL_LIDER   = 80
UMBRAL_REZAGO  = 20

# Por debajo de esto, comparar dos fotos es medir ruido: el percentil se
# mueve solo con que otro ticker suba. No se oculta el dato, se marca.
MIN_SESIONES_FIABLE = 5


def get_rs_cartera() -> dict:
    """Fuerza relativa de las posiciones abiertas en Cartera.

    POR QUÉ HACE FALTA
    El scan nocturno recorre el S&P 500, y dos tercios de la cartera no están
    en el índice (medido el 01/08: 33 de 50 posiciones). Es decir, la
    herramienta que mide fuerza relativa no podía decir nada de la mayoría de
    lo que hay realmente comprado. Ver auditoría RS/RW, hallazgo #7.

    POR QUÉ NO SE AMPLÍA EL UNIVERSO DEL SCAN
    Sería lo fácil y cambiaría el significado del número para todos. El RS es
    un percentil, o sea una posición RELATIVA: si se meten las posiciones de
    la cartera en el conjunto contra el que se comparan, el RS de AAPL pasa a
    depender de qué haya en cartera. Aquí el S&P 500 sigue siendo la vara y
    estos valores se miden CONTRA ella, con `percentil_contra()`, que
    reproduce exactamente el convenio de `rs_percentile()` (verificado: 0,00
    de diferencia en los 501 tickers del índice).

    POR QUÉ EN EL BACKEND Y NO EN EL SCAN NOCTURNO
    Porque una posición que se abra hoy tiene que aparecer hoy, no mañana por
    la noche. El coste es una descarga en lote de unas decenas de tickers,
    cacheada, frente a las 503 del scan.
    """
    from services.cache import cache
    from services.cartera_service import get_cartera_tickers

    cached = cache.get("rsrw:cartera")
    if cached:
        return cached

    tickers = sorted(get_cartera_tickers())
    if not tickers:
        return {"ok": False, "error": "No hay posiciones abiertas en Cartera."}

    data = _load_gist()
    if not data:
        return {"ok": False, "error": "Sin scan nocturno disponible: no hay universo contra el que comparar."}
    df_ref, _, meta = _parse_gist(data)
    if df_ref.empty:
        return {"ok": False, "error": "El scan nocturno no trae universo."}
    referencia = df_ref["RS_Score"]
    en_indice  = set(df_ref.index)

    close_d, _ = download_batch(
        tickers + [BENCHMARK], period="260d", batch_size=40,
        min_history=63, log_prefix="[RS Cartera] ",
    )
    spy = close_d.get(BENCHMARK)
    if spy is None or spy.empty:
        return {"ok": False, "error": "Sin datos del índice de referencia (SPY)."}

    filas, sin_datos = [], []
    for t in tickers:
        prices = close_d.get(t)
        # Menos de 63 sesiones no da ni para el tramo intermedio del RS: se
        # dice cuáles quedan fuera en vez de omitirlas sin más, que dejaría
        # al usuario pensando que ese ticker no tiene fuerza relativa.
        if prices is None or len(prices) < 63:
            sin_datos.append(t)
            continue
        spy_r = spy.reindex(prices.index).ffill()
        raw = {p: (float(_rs_smooth(prices, spy_r, p).iloc[-1]) if not _rs_smooth(prices, spy_r, p).empty else 0.0)
               for p in PERIODS}
        rs_score = sum(raw[p] * WEIGHTS[p] for p in PERIODS) * 100
        filas.append({
            "ticker":     t,
            "rs_score":   round(rs_score, 2),
            "rs_pct":     percentil_contra(rs_score, referencia),
            "rs_21d":     round(raw[21] * 100, 2),
            "rs_63d":     round(raw[63] * 100, 2),
            "rs_126d":    round(raw[126] * 100, 2),
            "rs_mom":     rs_momentum(raw[21] * 100, raw[63] * 100),
            "en_indice":  t in en_indice,
            "en_cartera": True,
        })

    filas.sort(key=lambda r: -(r["rs_pct"] or 0))
    result = {
        "ok":          True,
        "posiciones":  len(tickers),
        "calculadas":  len(filas),
        "sin_datos":   sin_datos,
        "fuera_indice": sum(1 for f in filas if not f["en_indice"]),
        "referencia":  f"S&P 500 ({len(referencia)} valores)",
        "freshness":   _freshness(meta),
        "filas":       filas,
        "timestamp":   get_timestamp(),
    }
    cache.set("rsrw:cartera", result, 900)   # 15 min
    return result


def get_rs_movimientos(ventana: int = 10) -> dict:
    """Cómo ha cambiado el percentil RS de cada valor en las últimas sesiones.

    Responde a lo que una foto no puede: un valor que ha pasado de RS 65 a RS
    88 en dos semanas es liderazgo EMERGENTE; otro lleva seis meses clavado
    en 88 y es liderazgo consolidado. En la tabla de líderes los dos aparecen
    igual.

    Los datos salen de `snapshot_ticker` (snapshots.db), que guarda el
    percentil de ~500 tickers cada sesión desde el 25/07/2026. **Verificado
    el 01/08 que ese `rs_pct` es EXACTAMENTE el mismo número que el `RS_Pct`
    del Gist de RS/RW**: diferencia 0,00 en los 501 tickers comparados. Los
    calculan dos scans distintos con ventanas de descarga distintas, pero el
    percentil es un rango y los rangos no se mueven por diferencias pequeñas
    en el valor subyacente. Sin esa comprobación esto estaría mezclando dos
    varas de medir, que es el error que costó caro en CANSLIM #6.
    """
    from services.snapshots_service import fechas_snapshot_ticker, rs_pct_en_fecha

    fechas = fechas_snapshot_ticker(limite=max(ventana, 2))
    if len(fechas) < 2:
        return {
            "ok": False,
            "error": "Hacen falta al menos dos sesiones guardadas para comparar.",
            "sesiones_disponibles": len(fechas),
        }

    fecha_hoy   = fechas[0]
    fecha_antes = fechas[-1]          # la más antigua DENTRO de la ventana
    hoy   = rs_pct_en_fecha(fecha_hoy)
    antes = rs_pct_en_fecha(fecha_antes)

    movimientos = []
    for ticker, rs_hoy in hoy.items():
        rs_antes = antes.get(ticker)
        if rs_antes is None:
            continue          # no estaba en el universo entonces: no hay variación
        movimientos.append({
            "ticker":     ticker,
            "rs_actual":  round(rs_hoy, 1),
            "rs_previo":  round(rs_antes, 1),
            "variacion":  round(rs_hoy - rs_antes, 1),
            "cruce_alza": rs_antes <  UMBRAL_LIDER  and rs_hoy >= UMBRAL_LIDER,
            "cruce_baja": rs_antes >= UMBRAL_LIDER  and rs_hoy <  UMBRAL_LIDER,
        })

    por_variacion = sorted(movimientos, key=lambda m: -m["variacion"])
    nuevos  = sorted([m for m in movimientos if m["cruce_alza"]], key=lambda m: -m["rs_actual"])
    perdidos = sorted([m for m in movimientos if m["cruce_baja"]], key=lambda m: m["rs_actual"])

    return {
        "ok": True,
        # Se reporta la ventana REAL, no la pedida: si se piden 10 sesiones y
        # solo hay 4 guardadas, se compara con lo que hay y se dice cuánto es.
        "sesiones":        len(fechas),
        "sesiones_pedidas": ventana,
        "desde":           fecha_antes,
        "hasta":           fecha_hoy,
        "fiable":          len(fechas) >= MIN_SESIONES_FIABLE,
        "umbral_lider":    UMBRAL_LIDER,
        "comparados":      len(movimientos),
        "nuevos_lideres":  _tag_cartera(nuevos[:20]),
        "lideres_perdidos": _tag_cartera(perdidos[:20]),
        "mas_suben":       _tag_cartera(por_variacion[:15]),
        "mas_bajan":       _tag_cartera(list(reversed(por_variacion[-15:]))),
        "timestamp":       get_timestamp(),
    }


def get_rsrw_ticker(ticker: str) -> dict:
    try:
        ticker_up = ticker.upper()
        spy    = yf.Ticker(BENCHMARK).history(period="260d")["Close"]
        prices = yf.Ticker(ticker_up).history(period="260d")["Close"]
        if len(prices) < 63:
            return {"ok": False, "error": "Histórico insuficiente"}

        spy_r = spy.reindex(prices.index).ffill()
        # rs_vals guarda el diferencial RAW (sin escalar) de cada periodo —
        # igual que _run_scan_engine(), para que el RS Score de esta función
        # sea comparable con el del scan nocturno, no una escala distinta.
        rs_vals_raw = {}
        for p in PERIODS:
            sm = _rs_smooth(prices, spy_r, p)
            rs_vals_raw[p] = float(sm.iloc[-1]) if not sm.empty else 0.0

        # Antes: cada rs_vals ya se multiplicaba por 100 aquí Y el rs_score
        # se volvía a multiplicar por 100 sobre esos valores ya escalados —
        # doble escalado que inflaba el RS Score ~100x (13125.8 en vez de
        # ~131.3 para INTC). Ahora: los componentes RAW se pesan y se
        # escalan una única vez, igual que en _run_scan_engine().
        rs_score = sum(rs_vals_raw[p] * WEIGHTS[p] for p in PERIODS) * 100
        rs_trend = _rs_trend_slope(_rs_smooth(prices, spy_r, 63))

        hist_rs = _rs_smooth(prices, spy_r, 63).tail(60)
        chart   = {
            "dates":  [d.strftime('%Y-%m-%d') for d in hist_rs.index],
            "values": [round(float(v) * 100, 2) for v in hist_rs.values],
        }

        # Percentil real: se busca en el scan nocturno (Gist) más reciente. Sin
        # scan disponible o ticker ausente de él, se deja sin percentil (None),
        # no se fabrica -- mismo criterio que la caché de universo de CANSLIM
        # (sesión 23).
        rs_pct = None
        try:
            gist_data = _load_gist()
            if gist_data:
                df, _, _ = _parse_gist(gist_data)
                if ticker_up in df.index:
                    val = df.loc[ticker_up, "RS_Pct"]
                    rs_pct = round(float(val), 1) if pd.notna(val) else None
        except Exception:
            pass

        return {
            "ok":       True,
            "ticker":   ticker_up,
            "rs_score": round(rs_score, 2),
            "rs_pct":   rs_pct,
            "rs_21d":   round(rs_vals_raw[21] * 100, 2),
            "rs_63d":   round(rs_vals_raw[63] * 100, 2),
            "rs_126d":  round(rs_vals_raw[126] * 100, 2),
            "rs_trend": rs_trend,
            "chart":    chart,
            "timestamp": get_timestamp(),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}