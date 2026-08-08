from services.gist_client import cabeceras_gist
import json
import requests

CONGRESS_GIST_ID   = "a45cef2f0472d0a8b4f532073889a03d"
CONGRESS_GIST_FILE = "congress_scan.json"


def _load_congress_gist() -> dict | None:
    if not CONGRESS_GIST_ID:
        return None
    try:
        r = requests.get(
            f"https://api.github.com/gists/{CONGRESS_GIST_ID}",
            headers=cabeceras_gist(), timeout=10,
        )
        if r.status_code != 200:
            return None
        content = r.json()["files"].get(CONGRESS_GIST_FILE, {}).get("content", "")
        return json.loads(content) if content else None
    except Exception:
        return None


def get_congress_feed() -> dict:
    from services.cache import cache
    cached = cache.get("congress:feed")
    if cached:
        return cached
    data = _load_congress_gist()
    if not data or not data.get("ok"):
        return {"ok": False, "error": "Sin datos todavía -- esperando al primer scan nocturno o dispáralo a mano (workflow_dispatch)."}
    buys  = [t for t in data["trades"] if t["direction"] == "buy"][:30]
    sells = [t for t in data["trades"] if t["direction"] == "sell"][:20]
    from services.cartera_service import get_cartera_tickers
    cartera_tickers = get_cartera_tickers()
    for t in buys + sells:
        t["en_cartera"] = t["ticker"] in cartera_tickers
    result = {
        "ok": True, "buys": buys, "sells": sells, "total": data["total"],
        "window_days": data["window_days"], "source": data["source"],
        "generated_at": data["generated_at"],
    }
    cache.set("congress:feed", result, 600)
    return result


def get_congress_clusters() -> dict:
    from services.cache import cache
    cached = cache.get("congress:clusters")
    if cached:
        return cached
    data = _load_congress_gist()
    if not data or not data.get("ok"):
        return {"ok": False, "clusters": [], "error": "Sin datos todavía."}
    from services.cartera_service import get_cartera_tickers
    cartera_tickers = get_cartera_tickers()
    clusters = data["clusters"]
    for c in clusters:
        c["en_cartera"] = c["ticker"] in cartera_tickers
    result = {"ok": True, "clusters": clusters, "generated_at": data["generated_at"]}
    cache.set("congress:clusters", result, 600)
    return result


def get_congress_ticker(ticker: str) -> dict:
    data = _load_congress_gist()
    if not data or not data.get("ok"):
        return {"ok": False, "error": "Sin datos todavía."}
    rows = [t for t in data["trades"] if t["ticker"].upper() == ticker.upper()]
    if not rows:
        return {"ok": False, "error": f"Sin operaciones de congresistas en {ticker.upper()} en los últimos {data['window_days']} días."}
    return {"ok": True, "ticker": ticker.upper(), "trades": rows, "total": len(rows)}
