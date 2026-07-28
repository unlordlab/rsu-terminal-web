"""
Track record público: qué ha pasado DE VERDAD con las señales de la terminal.

Fase 4.1 del roadmap ("la apuesta central"). La idea de fondo es una sola:
un backtest se puede reajustar hasta que dé bien; un registro de señales
reales con su desenlace, no. Por eso esto muestra TODAS las señales, las que
salieron bien y las que salieron mal, sin filtrar ninguna.

Dos fuentes, con naturalezas distintas y por eso separadas en la respuesta:

1. RSU Algoritmo — señales VERDE/VERDE-VOL registradas en vivo desde que se
   activó el tracking (algoritmo_tracking_service.py), con su retorno real a
   5/10/20/60 días ya rellenado por el job diario. Es lo único genuinamente
   FUERA DE MUESTRA que tiene el proyecto: ninguna de estas señales existía
   cuando se calibraron los umbrales.

2. Tesis publicadas — a diferencia de las señales del Algoritmo, aquí el
   resultado se puede reconstruir hacia atrás con precios históricos reales
   (la tesis guarda ticker, fecha y precio objetivo), así que el track record
   arranca con todo el histórico, no desde cero.

Baseline obligatorio: cada retorno se acompaña del retorno del SPY en EL
MISMO periodo. "+8%" no significa nada si el mercado hizo +12%; sin esa
comparación, un track record en un mercado alcista se vende solo y no dice
nada. Es la misma corrección que la auditoría del Algoritmo pide para el
backtest (baseline condicional).
"""
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "shared"))
from yf_batch import download_batch  # noqa: E402
from time_utils import get_timestamp  # noqa: E402

HORIZONTES = [("5d", "resultado_5d"), ("10d", "resultado_10d"),
              ("20d", "resultado_20d"), ("60d", "resultado_60d")]

# Por debajo de esto, cualquier media es anecdótica. No se oculta el dato —
# se marca, que es distinto. Mismo criterio que el flag `fiable` que ya usa
# el backtest del Algoritmo cuando un grupo tiene pocas muestras.
MIN_MUESTRA_FIABLE = 5


def _stats(valores: list) -> dict:
    """Agregado honesto de una lista de retornos (%). Devuelve n siempre —
    una media sin su n no es interpretable."""
    limpios = [v for v in valores if v is not None]
    n = len(limpios)
    if n == 0:
        return {"n": 0, "media": None, "mediana": None, "pct_positivas": None,
                "mejor": None, "peor": None, "fiable": False}
    ordenados = sorted(limpios)
    medio = n // 2
    mediana = ordenados[medio] if n % 2 else (ordenados[medio - 1] + ordenados[medio]) / 2
    return {
        "n": n,
        "media": round(sum(limpios) / n, 2),
        "mediana": round(mediana, 2),
        "pct_positivas": round(sum(1 for v in limpios if v > 0) / n * 100, 1),
        "mejor": round(max(limpios), 2),
        "peor": round(min(limpios), 2),
        "fiable": n >= MIN_MUESTRA_FIABLE,
    }


def _track_record_algoritmo() -> dict:
    from services.algoritmo_tracking_service import obtener_senales_tracked

    senales = obtener_senales_tracked(limit=500)
    por_horizonte = {}
    for etiqueta, campo in HORIZONTES:
        por_horizonte[etiqueta] = _stats([s.get(campo) for s in senales])

    # El retorno "con stop -7%" se registra en paralelo desde el principio —
    # es lo que de verdad habría vivido alguien siguiendo la señal con una
    # salida definida, no el que aguanta pase lo que pase.
    con_stop = {}
    for etiqueta, campo in HORIZONTES:
        con_stop[etiqueta] = _stats([s.get(campo + "_stop") for s in senales])

    pendientes = sum(1 for s in senales if s.get("resultado_60d") is None)
    return {
        "n_senales": len(senales),
        "n_pendientes": pendientes,   # aún sin cumplir los 60 días
        "por_horizonte": por_horizonte,
        "por_horizonte_con_stop": con_stop,
        "senales": [
            {
                "fecha": s.get("fecha", "")[:10],
                "estado": s.get("estado"),
                "senal": s.get("senal"),
                "score": s.get("score"),
                "umbral_verde": s.get("umbral_verde"),
                "precio_entrada": s.get("precio_entrada"),
                "resultado_5d": s.get("resultado_5d"),
                "resultado_10d": s.get("resultado_10d"),
                "resultado_20d": s.get("resultado_20d"),
                "resultado_60d": s.get("resultado_60d"),
                "stopeada_dia": s.get("stopeada_dia"),
            }
            for s in senales
        ],
    }


def _track_record_tesis() -> dict:
    """Retorno real de cada tesis publicada desde su fecha de publicación.

    Reconstruido con precios históricos: la tesis guarda ticker y fecha, así
    que no hace falta haber registrado nada en su momento. Se calcula además
    si el precio objetivo llegó a alcanzarse EN ALGÚN MOMENTO (máximo desde
    la publicación), que es la pregunta real — no solo dónde cotiza hoy."""
    from services.tesis_service import _conn as _tesis_conn

    conn = _tesis_conn()
    try:
        filas = conn.execute(
            "SELECT ticker, nombre, fecha, rating, precio_objetivo, autor, titulo "
            "FROM tesis WHERE status = 'approved' AND ticker IS NOT NULL AND ticker != '' "
            "ORDER BY fecha DESC"
        ).fetchall()
    finally:
        conn.close()

    tesis = [dict(f) for f in filas]
    if not tesis:
        # Misma FORMA que la respuesta con datos: un consumidor que lea
        # `resumen_vs_spy` no debe encontrarse la clave ausente solo porque
        # todavía no haya tesis.
        return {"n_tesis": 0, "tesis": [], "resumen": _stats([]),
                "resumen_vs_spy": _stats([]), "objetivo_alcanzado": {"n": 0, "alcanzados": 0}}

    tickers = sorted({t["ticker"].upper() for t in tesis})
    # SPY en el mismo lote: el baseline no es opcional (ver docstring).
    close_d, _, hl_d = download_batch(
        tickers + ["SPY"], period="5y", min_history=1, include_hl=True,
        log_prefix="[TrackRecord] ",
    )

    def _precio_en_o_despues(serie, fecha_iso):
        """Primer cierre en o después de la fecha — una tesis publicada en
        fin de semana o festivo se ancla a la siguiente sesión real."""
        try:
            objetivo = datetime.strptime(fecha_iso[:10], "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return None, None
        for i, idx in enumerate(serie.index):
            if idx.date() >= objetivo:
                return float(serie.iloc[i]), i
        return None, None

    spy = close_d.get("SPY")
    salida, retornos = [], []
    for t in tesis:
        tk    = t["ticker"].upper()
        serie = close_d.get(tk)
        if serie is None or serie.empty:
            salida.append({**t, "estado_dato": "sin_precios"})
            continue

        precio_pub, pos = _precio_en_o_despues(serie, t.get("fecha") or "")
        if precio_pub is None or not precio_pub:
            salida.append({**t, "estado_dato": "fecha_fuera_de_rango"})
            continue

        precio_hoy = float(serie.iloc[-1])
        retorno    = round((precio_hoy - precio_pub) / precio_pub * 100, 2)

        # ¿Llegó a tocarse el precio objetivo en algún momento? Con el máximo
        # intradía (High), no con cierres: un objetivo alcanzado a media
        # sesión se alcanzó, aunque cerrara por debajo.
        objetivo_alcanzado = None
        po = t.get("precio_objetivo")
        hl = hl_d.get(tk)
        if po and hl is not None and not hl.empty:
            highs = hl["High"].iloc[pos:]
            if len(highs):
                objetivo_alcanzado = bool(float(highs.max()) >= float(po))

        spy_retorno = None
        if spy is not None and not spy.empty:
            spy_pub, _ = _precio_en_o_despues(spy, t.get("fecha") or "")
            if spy_pub:
                spy_retorno = round((float(spy.iloc[-1]) - spy_pub) / spy_pub * 100, 2)

        retornos.append(retorno)
        salida.append({
            **t,
            "estado_dato": "ok",
            "precio_publicacion": round(precio_pub, 2),
            "precio_actual": round(precio_hoy, 2),
            "retorno_pct": retorno,
            "spy_mismo_periodo_pct": spy_retorno,
            # Lo único que de verdad importa: ¿aportó algo frente a no hacer nada?
            "vs_spy_pp": round(retorno - spy_retorno, 2) if spy_retorno is not None else None,
            "objetivo_alcanzado": objetivo_alcanzado,
        })

    vs_spy = [t["vs_spy_pp"] for t in salida if t.get("vs_spy_pp") is not None]
    con_objetivo = [t for t in salida if t.get("objetivo_alcanzado") is not None]
    return {
        "n_tesis": len(salida),
        "tesis": salida,
        "resumen": _stats(retornos),
        "resumen_vs_spy": _stats(vs_spy),
        "objetivo_alcanzado": {
            "n": len(con_objetivo),
            "alcanzados": sum(1 for t in con_objetivo if t["objetivo_alcanzado"]),
        },
    }


def get_track_record() -> dict:
    """Punto de entrada único. Cacheado 6h: son datos que cambian una vez al
    día como mucho (el job de resultados corre a diario) y la parte de tesis
    descarga histórico de yfinance."""
    from services.cache import cache

    cached = cache.get("track_record:all")
    if cached:
        return cached

    try:
        algoritmo = _track_record_algoritmo()
    except Exception as e:
        print(f"[TrackRecord] Error con el tracking del Algoritmo: {type(e).__name__}: {e}")
        algoritmo = None

    try:
        tesis = _track_record_tesis()
    except Exception as e:
        print(f"[TrackRecord] Error con las tesis: {type(e).__name__}: {e}")
        tesis = None

    if algoritmo is None and tesis is None:
        # Sin ninguna de las dos fuentes no hay track record que enseñar --
        # y no se cachea el fallo, para que el siguiente intento lo reintente.
        return {"ok": False, "error": "No se pudo construir el track record"}

    result = {
        "ok": True,
        "algoritmo": algoritmo,
        "tesis": tesis,
        "generado_en": datetime.now(timezone.utc).isoformat(),
        "timestamp": get_timestamp(),
    }
    cache.set("track_record:all", result, 21600)   # 6h
    return result
