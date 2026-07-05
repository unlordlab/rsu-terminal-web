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
import json
import requests
from datetime import datetime, timezone
from services.cache import cache

GIST_ID   = ""  # ← rellenar con el ID del Gist nuevo (ver instrucciones de configuración)
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
            headers={"Accept": "application/vnd.github.v3+json"},
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
    return True


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
        "rvol_min":  rvol_min,
        "rs_min":    rs_min,
        "score_min": score_min,
        "phase":     phase,
        "sector":    sector,
    }
    active_criteria = {k: v for k, v in criteria.items() if v is not None}

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
                "trend":         row.get("trend"),
                "score_tecnico": row.get("score_tecnico"),
            })

    matches.sort(key=lambda r: r.get("score_tecnico") or 0, reverse=True)

    return {
        "ok":               True,
        "freshness":        _freshness(data.get("generated_at", "")),
        "universe_size":    data.get("universe_size", len(stocks)),
        "matched":          len(matches),
        "active_criteria":  active_criteria,
        "results":          matches[:limit],
        "timestamp":        datetime.now().strftime("%H:%M:%S"),
    }