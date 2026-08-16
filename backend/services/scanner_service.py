"""
Scanner Universo S&P 500 — filtros configurables (RVOL, RS Percentile, Fase
Weinstein, Score Técnico), combinables por el usuario.

IMPORTANTE: este módulo NO calcula nada on-demand sobre el universo completo.
El scan pesado (descarga de ~500 tickers vía yfinance) corre 1x/día por
GitHub Actions (scripts/scanner_universe.py +
.github/workflows/scanner_scan.yml) y sube el resultado a un Gist. Aquí solo
se LEE ese Gist y se aplican los filtros que el usuario active — así ninguna
petición real dispara llamadas a Yahoo Finance. Mismo patrón que
thematic_service.py y rsrw_service.py (modo "gist").

Lógica de combinación de criterios (decidida junto con Marc):
  - Cada criterio activado actúa como GATEKEEPER (AND): un ticker solo pasa
    si cumple TODOS los criterios activados. Si no se activa ningún
    criterio, pasan todos los tickers del universo.
  - De los que pasan, se ordena por `score_tecnico` descendente — así el
    filtro decide el "pasa/no pasa" estructural (coherente con el principio
    de gatekeeper + score ya usado en rsu_algoritmo_service.py) y el score
    decide el orden dentro de los que sí cumplen.

Nota sobre RSU Score (fundamental): el score_tecnico de este módulo NO es el
RSU Score v2 completo de research_service.py (ese requiere datos
fundamentales por ticker, demasiado caro para correr sobre 500 tickers cada
noche). Si se quiere el RSU Score v2 real, se debe enriquecer bajo demanda
solo sobre los tickers que ya pasaron el filtro (pocos), llamando a
/api/v1/research/{ticker} desde el frontend — nunca sobre el universo
completo.
"""
from services.gist_client import cabeceras_gist
import json
import requests
import sys, os
from datetime import datetime, timezone
from services.cache import cache
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "shared"))
from time_utils import get_timestamp  # noqa: E402

GIST_ID   = "cb9d69cbf6ca741b4fd86765a41813a7"  # ← rellenar con el ID del Gist nuevo (ver instrucciones de configuración)
GIST_FILE = "scanner_scan.json"
CACHE_KEY = "scanner:universe"
CACHE_TTL = 1800  # 30 min — el dato en sí solo cambia 1x/día, esto es caché local extra

PHASE_LABELS = {1: "Fase 1", 2: "Fase 2", 3: "Fase 3", 4: "Fase 4"}


def _load_gist() -> dict | None:
    if not GIST_ID:
        return None
    try:
        r = requests.get(
            f"https://api.github.com/gists/{GIST_ID}",
            timeout=10,
            headers=cabeceras_gist(),
        )
        r.raise_for_status()
        content = r.json()["files"][GIST_FILE]["content"]
        data = json.loads(content)
        return data if data.get("ok") and data.get("stocks") else None
    except Exception as e:
        print(f"[Scanner] Error leyendo Gist: {e}")
        return None


def _freshness(generated_at: str) -> str:
    try:
        dt   = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
        ago  = datetime.now(timezone.utc) - dt
        mins = int(ago.total_seconds() / 60)
        if mins < 60:   return f"Hace {mins} min"
        if mins < 1440: return f"Hace {mins // 60}h"
        return f"Hace {mins // 1440}d"
    except Exception:
        return "Desconocido"


# La franja que el oscilador L3 dibuja como zona de sobreventa. No es el
# umbral de la senal (la formula exige linea < 25 para dar entrada): es la
# banda que el indicador PINTA, y es la que se pidio poder rastrear.
L3_ZONA_BAJA = (10.0, 20.0)


def _embudo(stocks: dict, active_criteria: dict) -> list:
    """Cuántos valores del universo cumple CADA criterio por separado.

    Una lista vacía no distingue hoy dos situaciones muy distintas: «no hay
    ningún valor así ahora mismo» y «tus filtros se contradicen». En vez de
    inventar reglas de incompatibilidad --que envejecen mal y acaban molestando
    cuando el mercado hace algo que la regla no preveía-- se cuenta y ya: si un
    criterio solo deja pasar 3 de 501, se ve dónde se estrecha el embudo.

    Reutiliza `_passes_filters` con UN criterio cada vez. Contar aparte, con su
    propia comparación, sería una segunda implementación de las mismas reglas
    -- y acabaría dando números que no cuadran con la tabla.
    """
    total = len(stocks)
    filas = []
    for clave, valor in active_criteria.items():
        pasan = sum(1 for row in stocks.values() if _passes_filters(row, {clave: valor}))
        filas.append({
            "criterio": clave,
            "valor":    valor,
            "pasan":    pasan,
            "de":       total,
            "pct":      round(pasan / total * 100, 1) if total else 0.0,
        })
    # El más restrictivo primero: es el que explica el resultado.
    filas.sort(key=lambda f: f["pasan"])
    return filas


def _diagnostico(embudo: list, encontrados: int) -> str | None:
    """Por qué la lista está vacía, dicho sin adivinar.

    Con resultados no se dice nada: el embudo ya está ahí para quien quiera
    mirarlo, y un mensaje permanente se convierte en ruido."""
    if encontrados > 0 or not embudo:
        return None
    # Con UN solo criterio activo, «los que pasan» y «los encontrados» son el
    # mismo número, así que si no hay resultados este primer caso siempre se
    # cumple. Aquí había una tercera rama para «un solo criterio» que era
    # inalcanzable por eso mismo -- la destapó el sabotaje al no poder tumbarla.
    if any(f["pasan"] == 0 for f in embudo):
        return ("Ningún valor del universo cumple este criterio hoy, ni siquiera por "
                "separado. Prueba a relajarlo.")
    return ("Cada criterio por separado sí tiene resultados, pero ninguno los cumple "
            "todos a la vez. La combinación es la que se queda sin nada.")


def _passes_filters(row: dict, criteria: dict) -> bool:
    """AND estricto: si un criterio está activo (no None), el ticker debe
    cumplirlo para pasar."""
    if criteria.get("rvol_min") is not None:
        if (row.get("rvol") or 0) < criteria["rvol_min"]:
            return False
    if criteria.get("rs_min") is not None:
        if (row.get("rs_pct") or 0) < criteria["rs_min"]:
            return False
    if criteria.get("score_min") is not None:
        if (row.get("score_tecnico") or 0) < criteria["score_min"]:
            return False
    if criteria.get("phase") is not None:
        if row.get("phase") != criteria["phase"]:
            return False
    if criteria.get("sector"):
        if (row.get("sector") or "").lower() != criteria["sector"].lower():
            return False
    if criteria.get("new_high_only"):
        if not row.get("new_high"):
            return False
    # Zona baja del oscilador L3 (el "indicador RSU"): la franja amarilla que
    # el indicador dibuja entre 10 y 20. `or 0` NO vale aquí: un ticker sin
    # lectura tiene l3_fundtrend=None, y convertirlo en 0 lo metería dentro de
    # la zona -- justo el ticker del que no sabemos nada aparecería como
    # sobreventa extrema. Sin dato, fuera del filtro.
    if criteria.get("l3_zona_baja"):
        f = row.get("l3_fundtrend")
        if f is None or not (L3_ZONA_BAJA[0] <= f <= L3_ZONA_BAJA[1]):
            return False
    if criteria.get("absorcion_min") is not None:
        if (row.get("dias_absorcion") or 0) < criteria["absorcion_min"]:
            return False
    return True


def get_breadth_history() -> list:
    """Devuelve el array 'breadth_history' del último scan nocturno (avance/
    declive, % sobre SMA50 y NH-NL por sesión, derivados del propio universo
    de 500 tickers — ver scripts/scanner_universe.py:_compute_breadth_history).
    Consumido por Market Breadth para el Oscilador McClellan real y las
    variaciones semanales, en vez de depender de fuentes externas de amplitud
    poco fiables (^ADV/^DEC de Yahoo)."""
    cached = cache.get(CACHE_KEY)
    if cached:
        data = cached
    else:
        data = _load_gist()
        if not data:
            return []
        cache.set(CACHE_KEY, data, CACHE_TTL)
    return data.get("breadth_history", [])


# Cuánto tiene que abrirse la brecha para llamarla divergencia. Es un
# porcentaje contra otro porcentaje (qué parte de cada universo está sobre su
# SMA50), así que 10 puntos ya es una diferencia clara de salud entre grandes y
# pequeñas, y por debajo de eso los dos índices se mueven prácticamente juntos.
DIVERGENCIA_UMBRAL = 10.0


def get_divergencia_universos() -> dict:
    """Grandes contra pequeñas: la amplitud del S&P 500 frente a la del Russell
    2000, por separado.

    El scan ya calculaba amplitud, pero sobre el universo COMBINADO -- y ahí una
    mitad tapa a la otra por construcción. Separadas, aparece la lectura
    clásica: cuando las grandes siguen fuertes y las pequeñas se deterioran, el
    liderazgo se está estrechando.

    Devuelve `ok: False` si el scan todavía no publica las dos series (un Gist
    anterior a este cambio) -- así la pantalla lo dice en vez de enseñar una
    brecha calculada contra la nada.
    """
    cached = cache.get(CACHE_KEY)
    data = cached or _load_gist()
    if not data:
        return {"ok": False, "error": "Sin datos del scan nocturno todavía."}
    if not cached:
        cache.set(CACHE_KEY, data, CACHE_TTL)

    grandes  = data.get("breadth_sp500") or []
    pequenas = data.get("breadth_russell") or []
    if not grandes or not pequenas:
        return {"ok": False, "error": "El scan todavía no publica las dos amplitudes por separado — "
                                      "aparecerá tras el próximo escaneo nocturno."}

    # Solo fechas presentes en LAS DOS series: comparar el último dato de una
    # contra el de la otra sin cuadrar fechas restaría días distintos si un
    # universo se quedó sin datos una sesión.
    por_fecha_g = {d["date"]: d for d in grandes}
    por_fecha_p = {d["date"]: d for d in pequenas}
    fechas = sorted(set(por_fecha_g) & set(por_fecha_p))
    if not fechas:
        return {"ok": False, "error": "Las dos amplitudes no comparten ninguna sesión."}

    serie = []
    for f in fechas:
        g, p = por_fecha_g[f], por_fecha_p[f]
        if g.get("pct_above_sma50") is None or p.get("pct_above_sma50") is None:
            continue
        serie.append({
            "date":     f,
            "sp500":    g["pct_above_sma50"],
            "russell":  p["pct_above_sma50"],
            "brecha":   round(g["pct_above_sma50"] - p["pct_above_sma50"], 1),
            "nh_nl_sp500":   g.get("new_highs", 0) - g.get("new_lows", 0),
            "nh_nl_russell": p.get("new_highs", 0) - p.get("new_lows", 0),
        })
    if not serie:
        return {"ok": False, "error": "Ninguna sesión tiene el % sobre SMA50 en los dos universos."}

    hoy = serie[-1]
    brecha = hoy["brecha"]
    if brecha >= DIVERGENCIA_UMBRAL:
        estado, lectura = "GRANDES", ("Las grandes aguantan mejor que las pequeñas. Liderazgo "
                                      "estrecho: el índice puede subir sostenido por pocos nombres.")
    elif brecha <= -DIVERGENCIA_UMBRAL:
        estado, lectura = "PEQUEÑAS", ("Las pequeñas aguantan mejor que las grandes. Suele ser "
                                       "señal de apetito por riesgo y de subida más repartida.")
    else:
        estado, lectura = "JUNTAS", ("Los dos universos se mueven a la par: no hay divergencia "
                                     "que leer ahora mismo.")
    return {
        "ok": True, "serie": serie[-60:], "hoy": hoy,
        "estado": estado, "lectura": lectura,
        "umbral": DIVERGENCIA_UMBRAL,
        "sesiones": len(serie),
        "timestamp": get_timestamp(),
        "freshness": _freshness(data.get("generated_at", "")),
    }


def get_universe_stocks() -> dict:
    """Devuelve el dict completo {ticker: {...}} del último scan nocturno,
    reutilizando el mismo caché que get_scanner_data(). Pensado para consumo
    interno de otros servicios (p.ej. Market Breadth necesita el flag
    above_sma50 de las ~500 acciones para calcular el % real sobre SMA50)."""
    cached = cache.get(CACHE_KEY)
    if cached:
        data = cached
    else:
        data = _load_gist()
        if not data:
            return {}
        cache.set(CACHE_KEY, data, CACHE_TTL)
    return data.get("stocks", {})


def get_scanner_data() -> dict:
    """Devuelve el universo completo sin filtrar (para poblar selectores de
    sector, mostrar totales, etc.)."""
    cached = cache.get(CACHE_KEY)
    if cached:
        data = cached
    else:
        data = _load_gist()
        if not data:
            return {
                "ok": False,
                "error": "Scanner no disponible todavía — el scan nocturno (GitHub Action) "
                         "aún no ha generado datos, o el Gist no está configurado (ver SCANNER_GIST_ID).",
            }
        cache.set(CACHE_KEY, data, CACHE_TTL)

    stocks = data.get("stocks", {})
    sectors = sorted(set(v.get("sector", "") for v in stocks.values() if v.get("sector")))
    return {
        "ok":            True,
        "freshness":     _freshness(data.get("generated_at", "")),
        "generated_at":  data.get("generated_at", ""),
        "universe_size": data.get("universe_size", len(stocks)),
        "sectors":       sectors,
        "meta":          data.get("meta", {}),
    }


def run_filter(
    rvol_min: float = None,
    rs_min: float = None,
    score_min: float = None,
    phase: int = None,
    sector: str = None,
    new_high_only: bool = None,
    absorcion_min: int = None,
    l3_zona_baja: bool = None,
    limit: int = 100,
) -> dict:
    cached = cache.get(CACHE_KEY)
    data = cached if cached else _load_gist()
    if data and not cached:
        cache.set(CACHE_KEY, data, CACHE_TTL)
    if not data:
        return {
            "ok": False,
            "error": "Scanner no disponible todavía — el scan nocturno (GitHub Action) "
                     "aún no ha generado datos, o el Gist no está configurado (ver SCANNER_GIST_ID).",
        }

    criteria = {
        "rvol_min":      rvol_min,
        "rs_min":        rs_min,
        "score_min":     score_min,
        "phase":         phase,
        "sector":        sector,
        "new_high_only": new_high_only,
        "absorcion_min": absorcion_min,
        "l3_zona_baja":  l3_zona_baja,
    }
    active_criteria = {k: v for k, v in criteria.items() if v is not None}

    from services.cartera_service import get_cartera_tickers
    cartera_tickers = get_cartera_tickers()

    stocks  = data.get("stocks", {})
    matches = []
    for ticker, row in stocks.items():
        if _passes_filters(row, criteria):
            matches.append({
                "ticker":        ticker,
                "sector":        row.get("sector"),
                "precio":        row.get("precio"),
                "rvol":          row.get("rvol"),
                "rs_pct":        row.get("rs_pct"),
                "phase":         row.get("phase"),
                "phase_label":   row.get("phase_label"),
                # La fase SEMANAL ya la calcula el scan nocturno y viaja en el
                # Gist desde siempre -- solo faltaba pasarla. La diaria se
                # voltea con ruido; la semanal es la escala en la que Weinstein
                # trabajaba, así que cuando las dos discrepan es información,
                # no un error: normalmente significa que el giro diario aún no
                # se ha consolidado.
                "phase_weekly":       row.get("phase_weekly"),
                "phase_weekly_label": row.get("phase_weekly_label"),
                "trend":         row.get("trend"),
                "score_tecnico": row.get("score_tecnico"),
                "new_high":      bool(row.get("new_high")),
                "above_sma50":   row.get("above_sma50"),
                "dias_absorcion": row.get("dias_absorcion", 0),
                "l3_fundtrend":  row.get("l3_fundtrend"),
                "l3_linea":      row.get("l3_linea"),
                "l3_estado":     row.get("l3_estado"),
                "en_cartera":    ticker in cartera_tickers,
            })

    matches.sort(key=lambda r: r.get("score_tecnico") or 0, reverse=True)
    embudo = _embudo(stocks, active_criteria)

    return {
        "ok":               True,
        "freshness":        _freshness(data.get("generated_at", "")),
        "universe_size":    data.get("universe_size", len(stocks)),
        "matched":          len(matches),
        "active_criteria":  active_criteria,
        "embudo":           embudo,
        "diagnostico":      _diagnostico(embudo, len(matches)),
        "results":          matches[:limit],
        "timestamp":        get_timestamp(),
    }