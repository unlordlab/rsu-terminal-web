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
    """Antigüedad de los DATOS, no de la ejecución del scan.

    Antes esto medía el tiempo desde `generated_at`, que es cuándo corrió el
    proceso. El cron va de lunes a viernes, así que en un festivo de mercado
    el scan se ejecuta igual, vuelve a descargar la sesión anterior y
    reescribe el Gist — y la etiqueta decía "Hace 20 min" sobre datos del día
    anterior. El usuario leía como fresco algo que no lo era, que es la
    versión más silenciosa de mentir. Ver auditoría RS/RW, hallazgo #6.

    Ahora se usa `ultima_sesion`, la fecha del último cierre REAL contenido
    en los datos. No hace falta calendario de festivos: esa fecha sale del
    propio índice del benchmark y por definición es una sesión de mercado.

    Los Gists escritos antes de este cambio no traen el campo, así que se
    mantiene el cálculo anterior como respaldo — pero diciendo que es la hora
    del scan, no la de los datos, en vez de dejar la ambigüedad de antes.
    """
    sesion = meta.get("ultima_sesion")
    if sesion:
        try:
            d    = datetime.strptime(sesion, "%Y-%m-%d").date()
            hoy  = datetime.now(timezone.utc).date()
            dias = (hoy - d).days
            if dias <= 0:  return "Cierre de hoy"
            if dias == 1:  return "Cierre de ayer"
            return f"Cierre del {sesion} ({dias} días)"
        except Exception:
            pass
    try:
        ts  = meta.get("generated_at", "")
        dt  = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        ago = datetime.now(timezone.utc) - dt
        mins = int(ago.total_seconds() / 60)
        if mins < 60:   return f"Scan hace {mins} min"
        if mins < 1440: return f"Scan hace {mins//60}h"
        return f"Scan hace {mins//1440}d"
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


# Top decil del universo. Es el corte que usa la amplitud del liderazgo, no
# el UMBRAL_LIDER de 80 de la tabla: con 80 entra el 20% del universo (unos
# 100 valores) y la composición por sectores se aplana tanto que deja de
# distinguir un mercado estrecho de uno ancho.
UMBRAL_TOP_DECIL = 90


def _media(valores: list):
    """Media, no mediana, y la diferencia importa: la media ponderada de los
    sectores es EXACTAMENTE constante (verificado el 02/08/2026 sobre las
    sesiones reales: 25100,0 en las dos fechas comparadas, diferencia 0,0),
    porque el percentil medio de un universo es su propio rango medio. Con
    medianas la suma se movió 771 puntos entre las mismas dos fechas, así
    que un sector podía "subir" sin que ningún otro bajase -- y entonces la
    palabra rotación dejaría de describir lo que la pantalla enseña."""
    if not valores:
        return None
    return round(sum(valores) / len(valores), 1)


def get_rs_sectores(ventana: int = 10) -> dict:
    """Rotación sectorial: qué sectores ganan y pierden fuerza relativa.

    POR QUÉ ESTO SÍ SE PUEDE MEDIR Y LA AMPLITUD CLÁSICA NO
    `rs_pct` es un rango dentro del universo, así que el RS medio de TODO el
    universo está clavado en 50 por construcción, todos los días. Lo que no
    está fijado es cómo se reparte esa fuerza entre sectores: si el RS medio
    de Tecnología sube de 45 a 70, el de algún otro sector ha bajado, y la
    suma ponderada sigue valiendo exactamente lo mismo. Eso es justamente lo
    que significa rotación -- el dinero no aparece, cambia de sitio. Ver
    _media() para por qué el estadístico es la media y no la mediana.

    Se compara la sesión más reciente contra la más antigua de la ventana,
    igual que get_rs_movimientos(), para que las dos pantallas hablen del
    mismo periodo.
    """
    from services.snapshots_service import fechas_snapshot_ticker, filas_rs_sector

    fechas = fechas_snapshot_ticker(limite=max(ventana, 2))
    if len(fechas) < 2:
        return {
            "ok": False,
            "error": "Hacen falta al menos dos sesiones guardadas para medir rotación.",
            "sesiones_disponibles": len(fechas),
        }

    fecha_hoy, fecha_antes = fechas[0], fechas[-1]
    datos = filas_rs_sector([fecha_hoy, fecha_antes])

    def _por_sector(filas):
        agrupado = {}
        for f in filas:
            agrupado.setdefault(f["sector"], []).append(f["rs_pct"])
        return agrupado

    hoy   = _por_sector(datos.get(fecha_hoy, []))
    antes = _por_sector(datos.get(fecha_antes, []))
    if not hoy:
        return {"ok": False, "error": f"Sin datos sectoriales para {fecha_hoy}."}

    sectores = []
    for sector, valores in hoy.items():
        med_hoy   = _media(valores)
        med_antes = _media(antes.get(sector, []))
        sectores.append({
            "sector":     GICS_MAP.get(sector, sector),
            "sector_en":  sector,
            "etf":        SECTOR_ETFS.get(GICS_MAP.get(sector, sector)),
            "n":          len(valores),
            "rs_medio":   med_hoy,
            "rs_previa":  med_antes,
            # Sin lectura previa no hay variación que calcular. Un sector que
            # aparece por primera vez en el universo no ha "subido desde 0".
            "variacion":  None if med_antes is None else round(med_hoy - med_antes, 1),
            "n_lideres":  sum(1 for v in valores if v >= UMBRAL_LIDER),
        })

    con_variacion = [s for s in sectores if s["variacion"] is not None]
    con_variacion.sort(key=lambda s: -s["variacion"])
    sectores.sort(key=lambda s: -s["rs_medio"])

    return {
        "ok":               True,
        "sesiones":         len(fechas),
        "sesiones_pedidas": ventana,
        "desde":            fecha_antes,
        "hasta":            fecha_hoy,
        "fiable":           len(fechas) >= MIN_SESIONES_FIABLE,
        "sectores":         sectores,
        "entrando":         con_variacion[:3],
        "saliendo":         list(reversed(con_variacion[-3:])) if len(con_variacion) >= 3 else [],
        "timestamp":        get_timestamp(),
    }


def get_rs_amplitud(ventana: int = 20) -> dict:
    """¿El liderazgo del mercado es ancho o estrecho?

    LA PREGUNTA DE LA AUDITORÍA ERA BUENA; LA MÉTRICA QUE PROPONÍA, NO
    El hallazgo pedía "cuántos valores del universo tienen RS alto". Ese
    número es constante: `rs_pct` es un percentil DEL PROPIO universo, así
    que el 20% siempre está por encima de 80 -- medido el 02/08/2026 sobre
    las cuatro sesiones guardadas, salía 20,2% en las cuatro, hasta el
    decimal. Un gráfico de eso sería una línea recta.

    Lo que sí distingue un mercado ancho de uno estrecho es CÓMO se reparte
    ese top decil entre sectores. Si los 50 valores más fuertes salen de dos
    sectores, el liderazgo es estrecho aunque el recuento no se mueva.

    La referencia no es "un onceavo por sector": los sectores no tienen el
    mismo tamaño, y a Tecnología le corresponde más liderazgo solo por tener
    más valores. Se compara la cuota de cada sector en el top decil contra
    su cuota en el universo -- 1,0 es exactamente lo que le tocaría por
    tamaño, 3,0 es tres veces más de lo que le tocaría.
    """
    from services.snapshots_service import fechas_snapshot_ticker, filas_rs_sector

    fechas = fechas_snapshot_ticker(limite=max(ventana, 1))
    if not fechas:
        return {"ok": False, "error": "Todavía no hay ninguna sesión guardada."}

    fechas_asc = sorted(fechas)
    datos = filas_rs_sector(fechas_asc)

    serie = []
    for fecha in fechas_asc:
        filas = datos.get(fecha, [])
        if not filas:
            continue
        universo = len(filas)
        top = [f for f in filas if f["rs_pct"] >= UMBRAL_TOP_DECIL]
        if not top:
            continue

        cuenta_top, cuenta_uni = {}, {}
        for f in filas:
            cuenta_uni[f["sector"]] = cuenta_uni.get(f["sector"], 0) + 1
        for f in top:
            cuenta_top[f["sector"]] = cuenta_top.get(f["sector"], 0) + 1

        dominante, n_dom = max(cuenta_top.items(), key=lambda kv: kv[1])
        cuota_dom = n_dom / len(top) * 100
        cuota_uni = cuenta_uni.get(dominante, 0) / universo * 100

        # Solo tiene sentido con rs_score, que es absoluto. Es NULL en todas
        # las sesiones anteriores al 02/08/2026, cuando el scan empezó a
        # publicarlo -- se devuelve None, no un 0 que parecería "nadie bate
        # al índice", que es una afirmación muy distinta de "no lo sé".
        con_score = [f["rs_score"] for f in filas if f["rs_score"] is not None]
        pct_bate  = round(sum(1 for v in con_score if v > 0) / len(con_score) * 100, 1) if con_score else None

        serie.append({
            "fecha":            fecha,
            "universo":         universo,
            "n_top":            len(top),
            "sectores_totales": len(cuenta_uni),
            "sectores_top":     len(cuenta_top),
            "dominante":        GICS_MAP.get(dominante, dominante),
            "cuota_dominante":  round(cuota_dom, 1),
            "cuota_universo":   round(cuota_uni, 1),
            "sobre_representacion": round(cuota_dom / cuota_uni, 2) if cuota_uni > 0 else None,
            "pct_bate_spy":     pct_bate,
        })

    if not serie:
        return {"ok": False, "error": "Ninguna sesión guardada tiene valores en el top decil."}

    actual  = serie[-1]
    previa  = serie[0] if len(serie) > 1 else None
    reparto = []
    filas_hoy = datos.get(actual["fecha"], [])
    top_hoy   = [f for f in filas_hoy if f["rs_pct"] >= UMBRAL_TOP_DECIL]
    cuenta_uni_hoy = {}
    for f in filas_hoy:
        cuenta_uni_hoy[f["sector"]] = cuenta_uni_hoy.get(f["sector"], 0) + 1
    cuenta_top_hoy = {}
    for f in top_hoy:
        cuenta_top_hoy[f["sector"]] = cuenta_top_hoy.get(f["sector"], 0) + 1
    # Se recorre el universo, no el top: un sector con CERO representantes
    # entre los más fuertes es información, y si solo se listara lo que está
    # en el top desaparecería de la pantalla justo cuando más dice.
    for sector, n_uni in cuenta_uni_hoy.items():
        n_top_s   = cuenta_top_hoy.get(sector, 0)
        cuota_top = n_top_s / len(top_hoy) * 100 if top_hoy else 0.0
        cuota_u   = n_uni / len(filas_hoy) * 100 if filas_hoy else 0.0
        reparto.append({
            "sector":         GICS_MAP.get(sector, sector),
            "n_top":          n_top_s,
            "n_universo":     n_uni,
            "cuota_top":      round(cuota_top, 1),
            "cuota_universo": round(cuota_u, 1),
            "sobre_representacion": round(cuota_top / cuota_u, 2) if cuota_u > 0 else None,
        })
    reparto.sort(key=lambda s: -s["n_top"])

    return {
        "ok":               True,
        "sesiones":         len(serie),
        "sesiones_pedidas": ventana,
        "fiable":           len(serie) >= MIN_SESIONES_FIABLE,
        "umbral_top":       UMBRAL_TOP_DECIL,
        "actual":           actual,
        "previa":           previa,
        "serie":            serie,
        "reparto":          reparto,
        "timestamp":        get_timestamp(),
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