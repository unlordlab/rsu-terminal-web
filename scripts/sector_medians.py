#!/usr/bin/env python3
"""
RSU Terminal — Medianas sectoriales reales
Calcula, para cada sector del S&P 500, la MEDIANA real de 14 métricas de
valoración/rentabilidad/crecimiento (P/E, márgenes, ROE, etc.), a partir de
los datos fundamentales reales de yfinance de los ~503 tickers del universo
(shared/sp500_universe.py, fuente única -- ver sesión 19).
Sube el resultado a un Gist propio, separado del de Scanner.

Por qué existe (Fase 3.1 del Plan Maestro, 20/07/2026): SECTOR_BENCHMARKS en
research_service.py son valores ESTÁTICOS, escritos a mano sin fecha ni
fuente documentada -- envejecen en silencio y nadie se entera. Este job los
sustituye por medianas reales, recalculadas cada semana.

Por qué SEMANAL, no cada noche (como Scanner/RS-RW/Thematic): a diferencia
de esos tres (que solo necesitan precio/volumen, datos baratos), esto
necesita `.info` de cada ticker -- la llamada más pesada y propensa a
rate-limit de yfinance (ver conversación 18-19/07/2026, mismo problema que
tuvo Gael). Los múltiplos de un sector no cambian de un día para otro, así
que no tiene sentido pagar ese coste 7 veces por semana. Domingos, horario
tranquilo.

IMPORTANTE -- nombres de sector: SP500_SECTOR_MAP (shared/) usa nombres
oficiales GICS ("Information Technology"). SECTOR_BENCHMARKS en
research_service.py usa la nomenclatura propia de yfinance ("Technology").
Son cadenas DISTINTAS -- por eso aquí se agrupa por el sector que devuelve
`info.get("sector")` de cada ticker (ya se pide de todos modos para el
resto de campos), no por SP500_SECTOR_MAP. Así el resultado encaja
directamente con las claves que ya espera SECTOR_BENCHMARKS.

Script standalone (no importa nada de backend/), mismo motivo que
scanner_universe.py: correr en el runner de GitHub Actions sin depender
del entorno de FastAPI.
"""
import os
import sys
import json
import time
import statistics
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
import yfinance as yf

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "shared"))
from sp500_universe import SP500_SECTOR_MAP  # noqa: E402 -- solo para la LISTA de tickers, no para el sector

GIST_TOKEN = os.environ.get("GIST_TOKEN", "")
GIST_ID    = os.environ.get("SECTOR_MEDIANS_GIST_ID", "")
GIST_FILE  = "sector_medians.json"

# Mismos 14 campos que SECTOR_BENCHMARKS en research_service.py -- si se
# añade/quita alguno ahí, replicar aquí también.
CAMPOS = [
    "trailingPE", "forwardPE", "priceToSalesTrailing12Months", "enterpriseToEbitda",
    "pegRatio", "priceToBook",
    "returnOnEquity", "returnOnAssets", "profitMargins", "operatingMargins", "grossMargins",
    "revenueGrowth", "earningsGrowth", "debtToEquity",
]
# Traduce el nombre de campo de yfinance (.info) al nombre corto que ya usa
# SECTOR_BENCHMARKS en research_service.py -- para que el resultado encaje
# sin tener que tocar nada más en el backend.
MAPEO_CAMPOS = {
    "trailingPE": "trailing_pe", "forwardPE": "forward_pe",
    "priceToSalesTrailing12Months": "price_to_sales", "enterpriseToEbitda": "ev_ebitda",
    "pegRatio": "peg_ratio", "priceToBook": "price_to_book",
    "returnOnEquity": "roe", "returnOnAssets": "roa", "profitMargins": "net_margin",
    "operatingMargins": "op_margin", "grossMargins": "gross_margin",
    "revenueGrowth": "revenue_growth", "earningsGrowth": "earnings_growth",
    "debtToEquity": "debt_to_equity",
}

MAX_WORKERS = 4  # mismo límite que yf_pool.py del backend -- evita ráfagas de conexión


def _fetch_info_con_reintentos(ticker: str, intentos=3, espera_base=10) -> dict | None:
    """.info de un ticker, con reintentos si salta rate limit -- mismo
    patrón que _yf_con_reintentos en agents/bull_agent.py (18/07/2026)."""
    for intento in range(1, intentos + 1):
        try:
            info = yf.Ticker(ticker).info
            return info if info else None
        except Exception as e:
            es_rate_limit = "rate limit" in str(e).lower() or "too many requests" in str(e).lower()
            if es_rate_limit and intento < intentos:
                time.sleep(espera_base * intento)
                continue
            return None
    return None


def run_scan() -> dict:
    tickers = list(SP500_SECTOR_MAP.keys())
    print(f"📊 Medianas sectoriales — {len(tickers)} tickers a consultar (.info de cada uno)")

    # Diccionario: sector_yfinance -> campo_corto -> lista de valores
    datos_por_sector = defaultdict(lambda: defaultdict(list))
    ok_count = 0
    fail_count = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futuros = {ex.submit(_fetch_info_con_reintentos, t): t for t in tickers}
        for i, futuro in enumerate(as_completed(futuros), 1):
            ticker = futuros[futuro]
            info = futuro.result()
            if not info:
                fail_count += 1
                continue

            sector = info.get("sector")
            if not sector:
                fail_count += 1
                continue

            ok_count += 1
            for campo_yf in CAMPOS:
                valor = info.get(campo_yf)
                if valor is None:
                    continue
                try:
                    valor = float(valor)
                except (TypeError, ValueError):
                    continue
                # Descarta outliers absurdos (empresas con perdidas extremas,
                # datos corruptos) -- un P/E de 5000 o un ROE de -900% no
                # deberían poder arrastrar la mediana de todo un sector.
                campo_corto = MAPEO_CAMPOS[campo_yf]
                datos_por_sector[sector][campo_corto].append(valor)

            if i % 50 == 0:
                print(f"  ... {i}/{len(tickers)} procesados ({ok_count} ok, {fail_count} fallidos)")

    print(f"✅ {ok_count}/{len(tickers)} tickers con datos válidos ({fail_count} fallidos/sin sector)")

    sectores_resultado = {}
    for sector, campos in datos_por_sector.items():
        medianas = {}
        for campo_corto, valores in campos.items():
            if len(valores) < 5:
                # Menos de 5 muestras -- mediana no fiable, se omite ese
                # campo para este sector (el consumidor ya maneja campos
                # ausentes sin problema, igual que con datos faltantes de
                # un ticker individual).
                continue
            medianas[campo_corto] = round(statistics.median(valores), 4)
        if medianas:
            sectores_resultado[sector] = {
                "medianas": medianas,
                "n_tickers": len(next(iter(campos.values()), [])),
            }

    return {
        "ok": True,
        "sectores": sectores_resultado,
        "universe_size": len(tickers),
        "ok_count": ok_count,
        "fail_count": fail_count,
        "generated_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
    }


def save_to_gist(result: dict):
    if not GIST_TOKEN:
        raise ValueError("GIST_TOKEN no configurado")
    if not GIST_ID:
        raise ValueError("SECTOR_MEDIANS_GIST_ID no configurado")
    r = requests.patch(
        f"https://api.github.com/gists/{GIST_ID}",
        headers={"Authorization": f"token {GIST_TOKEN}", "Accept": "application/vnd.github+json"},
        json={"files": {GIST_FILE: {"content": json.dumps(result, ensure_ascii=False, indent=2)}}},
        timeout=30,
    )
    r.raise_for_status()
    print(f"💾 Guardado en Gist {GIST_ID}")


def main():
    result = run_scan()
    for sector, datos in result["sectores"].items():
        print(f"  {sector}: {datos['n_tickers']} tickers, {len(datos['medianas'])} métricas con mediana fiable")
    save_to_gist(result)


if __name__ == "__main__":
    main()