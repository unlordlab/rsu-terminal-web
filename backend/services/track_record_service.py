"""
Track record público: qué ha pasado DE VERDAD con las señales de la terminal.

Fase 4.1 del roadmap ("la apuesta central"). La idea de fondo es una sola:
un backtest se puede reajustar hasta que dé bien; un registro de señales
reales con su desenlace, no. Por eso esto muestra TODAS las señales, las que
salieron bien y las que salieron mal, sin filtrar ninguna.

Tres fuentes, con naturalezas distintas y por eso separadas en la respuesta:

1. RSU Algoritmo — señales VERDE/VERDE-VOL registradas en vivo desde que se
   activó el tracking (algoritmo_tracking_service.py), con su retorno real a
   5/10/20/60 días ya rellenado por el job diario. Es lo único genuinamente
   FUERA DE MUESTRA que tiene el proyecto: ninguna de estas señales existía
   cuando se calibraron los umbrales.

2. Tesis publicadas — a diferencia de las señales del Algoritmo, aquí el
   resultado se puede reconstruir hacia atrás con precios históricos reales
   (la tesis guarda ticker, fecha y precio objetivo), así que el track record
   arranca con todo el histórico, no desde cero.

3. Candidatos de CANSLIM — el universo COMPLETO de cada scan nocturno
   (canslim_tracking_service.py), no solo los que pasaban el filtro. Es la
   única de las tres que tiene grupo de control: permite comparar los de
   score alto contra los de score bajo, y no solo preguntarse si subieron.
   Como el Algoritmo, empieza a contar desde que se activó -- el Gist del
   scan se sobrescribe cada noche y el pasado no se puede reconstruir.

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


# Tramos de score con los que se agrupa el track record de CANSLIM. Los
# cortes son los MISMOS que ofrece el selector del scanner (60/80/85), más
# el tramo de los que no llegan a ninguno: si se agrupara por rangos
# inventados, el usuario no podría relacionar la tabla con lo que ve en el
# módulo. El tramo "<60" es el grupo de control -- sin él solo se podría
# medir si los candidatos suben, no si suben MÁS que el resto.
TRAMOS_CANSLIM = [
    (85, 101, "85+  Estricto"),
    (80,  85, "80-84  Estándar"),
    (60,  80, "60-79  Amplio"),
    (0,   60, "<60  no candidatos"),
]


def _track_record_canslim() -> dict:
    """Qué hicieron los candidatos que propuso el scan nocturno, por tramo de
    score y contra el SPY del mismo periodo.

    Es la única fuente de las tres que puede responder «¿el score sirve para
    algo?», porque guarda el UNIVERSO entero y no solo los que pasaban el
    filtro: comparar los de 85+ contra los de <60 es la pregunta, y sin
    grupo de control no hay comparación posible.

    Baseline: el SPY del MISMO periodo, calculado por fecha de scan. Un +6%
    a 20 días no dice nada si el mercado hizo +9% -- ahí el módulo habría
    restado valor, no aportado.
    """
    from services.canslim_tracking_service import obtener_filas, fechas_registradas

    filas = obtener_filas()
    fechas = fechas_registradas()
    if not filas:
        # Misma FORMA que la respuesta con datos, para que el frontend no
        # tenga que distinguir "vacío" de "roto".
        return {"n_filas": 0, "n_scans": 0, "primera_fecha": None,
                "por_tramo": [], "spy": {}, "n_pendientes": 0}

    # SPY por fecha de scan y horizonte. Se descarga UNA vez y se reutiliza
    # para todos los tramos -- todas las filas de un mismo scan comparten
    # exactamente el mismo baseline.
    spy_por_fecha = {}
    spy_descargado = False
    try:
        close_d, _ = download_batch(["SPY"], period="2y", min_history=1,
                                    log_prefix="[TrackRecord CANSLIM] ")
        serie = close_d.get("SPY")
        if serie is not None and not serie.empty:
            spy_descargado = True
            idx = [d.date() for d in serie.index]
            for f in fechas:
                try:
                    objetivo = datetime.strptime(f, "%Y-%m-%d").date()
                except (ValueError, TypeError):
                    continue
                pos = next((i for i, d in enumerate(idx) if d >= objetivo), None)
                if pos is None:
                    continue
                base = float(serie.iloc[pos])
                if base <= 0:
                    continue
                retornos = {}
                for dias, campo in [(5, "5d"), (10, "10d"), (20, "20d"), (60, "60d")]:
                    if pos + dias < len(serie):
                        retornos[campo] = round(
                            (float(serie.iloc[pos + dias]) - base) / base * 100, 2)
                spy_por_fecha[f] = retornos
    except Exception as e:
        # Sin baseline la tabla sigue siendo legible, pero hay que DECIRLO --
        # no dejar que se lea como si el +6% ya estuviera comparado.
        print(f"[TrackRecord] Sin baseline SPY para CANSLIM: {type(e).__name__}: {e}")

    def _exceso(fila, etiqueta, campo):
        """Retorno de la fila MENOS el del SPY en el mismo periodo."""
        propio = fila.get(campo)
        base   = spy_por_fecha.get(fila.get("fecha"), {}).get(etiqueta)
        if propio is None or base is None:
            return None
        return round(propio - base, 2)

    por_tramo = []
    for lo, hi, etiqueta in TRAMOS_CANSLIM:
        grupo = [f for f in filas if lo <= (f.get("score") or 0) < hi]
        horizontes, vs_spy = {}, {}
        for et, campo in HORIZONTES:
            horizontes[et] = _stats([f.get(campo) for f in grupo])
            vs_spy[et]     = _stats([_exceso(f, et, campo) for f in grupo])
        por_tramo.append({
            "tramo": etiqueta, "rango": f"{lo}-{hi - 1}",
            "n_filas": len(grupo),
            "por_horizonte": horizontes,
            "por_horizonte_vs_spy": vs_spy,
        })

    return {
        "n_filas": len(filas),
        "n_scans": len(fechas),
        "primera_fecha": fechas[0] if fechas else None,
        "ultima_fecha": fechas[-1] if fechas else None,
        "n_pendientes": sum(1 for f in filas if f.get("resultado_60d") is None),
        "baseline_disponible": bool(spy_por_fecha),
        # No es lo mismo «falló la descarga del SPY» que «el scan es tan
        # reciente que todavía no hay sesión a la que anclarlo» -- el segundo
        # caso es lo normal el primer día, y decir lo primero sería anunciar
        # una avería que no existe.
        "baseline_motivo": (None if spy_por_fecha
                            else ("sin_sesion_todavia" if spy_descargado else "sin_spy")),
        "por_tramo": por_tramo,
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

    try:
        canslim = _track_record_canslim()
    except Exception as e:
        print(f"[TrackRecord] Error con el tracking de CANSLIM: {type(e).__name__}: {e}")
        canslim = None

    if algoritmo is None and tesis is None:
        # Sin ninguna de las dos fuentes no hay track record que enseñar --
        # y no se cachea el fallo, para que el siguiente intento lo reintente.
        return {"ok": False, "error": "No se pudo construir el track record"}

    result = {
        "ok": True,
        "algoritmo": algoritmo,
        "tesis": tesis,
        "canslim": canslim,
        "generado_en": datetime.now(timezone.utc).isoformat(),
        "timestamp": get_timestamp(),
    }
    cache.set("track_record:all", result, 21600)   # 6h
    return result
