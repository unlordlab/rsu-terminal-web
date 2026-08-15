"""
Sentimiento social de StockTwits -> Gist.

POR QUÉ ESTE SCRIPT EXISTE. StockTwits está tras un challenge de Cloudflare
desde la IP del VPS. Estaba documentado desde el 28/07/2026 y se confirmó de
nuevo el 15/08/2026 mirando producción: la columna SENT salía vacía en las
quince filas, mientras desde una IP doméstica la misma llamada devolvía 200 con
30 mensajes. No es un fallo del código, es dónde corre.

Un runner de GitHub Actions no está bloqueado. Mismo patrón que ya usan Scanner,
RS/RW, CANSLIM, Thematic y Congress: el runner hace el trabajo y publica a un
Gist; el backend lo lee.

QUÉ SE PIDE, Y POR QUÉ NO TODO EL UNIVERSO. Se podrían escanear los ~570
tickers del universo (medido: 30 peticiones en 1,3s, así que cabría), pero el
widget enseña quince. Se piden solo los que el backend va a acabar mostrando:
los mismos titulares de Reddit que él lee, extraídos con el MISMO código
(shared/social_tickers.py), más los que estén en tendencia en StockTwits. Unas
50 peticiones por vuelta en vez de 570 -- proporcionado a lo que se usa.

Un ticker que el backend enseñe y no esté aquí se queda sin sentimiento y la
pantalla pone un guion, que es la verdad.

Uso:
    GIST_TOKEN=... STOCKTWITS_GIST_ID=... python scripts/stocktwits_scan.py
"""
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "shared"))
from social_tickers import (  # noqa: E402
    extract_tickers, fetch_reddit_titles_via_rss, fetch_sentimiento, fetch_trending,
)
from sp500_universe import SP500_SECTOR_MAP  # noqa: E402

GIST_TOKEN = os.environ.get("GIST_TOKEN", "")
GIST_ID    = os.environ.get("STOCKTWITS_GIST_ID", "")
GIST_FILE  = "stocktwits_sentimiento.json"

# Cuántos tickers de Reddit se piden. El backend enseña 15 y ordena por
# menciones, así que con 30 hay margen de sobra para cubrir los que salgan.
TOP_REDDIT = 30
MAX_WORKERS = 6


def run_scan() -> dict:
    trending = fetch_trending()
    print(f"📈 StockTwits trending: {len(trending)} símbolos")

    titulos = fetch_reddit_titles_via_rss()
    menciones = {}
    universo = set(SP500_SECTOR_MAP.keys())
    for titulo in titulos:
        for ticker, peso in extract_tickers(titulo.upper(), universo):
            menciones[ticker] = menciones.get(ticker, 0) + peso
    desde_reddit = [t for t, _ in sorted(menciones.items(), key=lambda x: -x[1])[:TOP_REDDIT]]
    print(f"📊 Reddit: {len(titulos)} títulos -> {len(desde_reddit)} tickers")

    # Orden estable y sin repetidos: trending primero (son los que más se
    # mueven), luego los de Reddit que no estuvieran ya.
    objetivo = list(dict.fromkeys(trending + desde_reddit))
    print(f"🔎 Pidiendo sentimiento de {len(objetivo)} valores...")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        resultados = list(ex.map(fetch_sentimiento, objetivo))

    sentimiento = {t: s for t, s in zip(objetivo, resultados) if s}
    print(f"✅ Con mensajes etiquetados: {len(sentimiento)} de {len(objetivo)}")

    if not trending and not sentimiento:
        # Si el runner tampoco puede con StockTwits, NO se publica un fichero
        # vacío encima del anterior: el backend seguiría leyendo el último
        # bueno, que envejece pero no miente sobre lo que hay.
        raise ValueError("StockTwits no respondió ni al trending ni a ningún stream")

    return {
        "ok":           True,
        "trending":     trending,
        "sentimiento":  sentimiento,
        "n_pedidos":    len(objetivo),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def save_to_gist(result: dict):
    if not GIST_TOKEN or not GIST_ID:
        raise ValueError("GIST_TOKEN o STOCKTWITS_GIST_ID no configurados")
    r = requests.patch(
        f"https://api.github.com/gists/{GIST_ID}",
        headers={"Authorization": f"token {GIST_TOKEN}", "Accept": "application/vnd.github+json"},
        json={"files": {GIST_FILE: {"content": json.dumps(result, ensure_ascii=False, indent=2)}}},
        timeout=30,
    )
    if r.status_code not in (200, 201):
        raise ValueError(f"Gist error {r.status_code}: {r.text[:300]}")
    print(f"✅ Publicado en {r.json()['html_url']}")


def main():
    print(f"💬 StockTwits scan — {datetime.now(timezone.utc):%Y-%m-%d %H:%M UTC}")
    save_to_gist(run_scan())


if __name__ == "__main__":
    main()
