#!/usr/bin/env python3
"""
Congress Trading Scanner -- descarga el dataset público de
kadoa-org/congress-trading-monitor (MIT, actualizado a diario), agregado
desde las 3 fuentes oficiales del STOCK Act (Senado eFD, Cámara Clerk,
rama ejecutiva OGE), filtra a los últimos CONGRESS_WINDOW_DAYS y publica
un resumen compacto a un Gist propio -- mismo patrón que
scripts/canslim_scan.py / rsrw_scan.py.

Atribución: dataset original de https://github.com/kadoa-org/congress-trading-monitor
(licencia MIT), que a su vez agrega divulgaciones públicas obligatorias
bajo el STOCK Act. No se genera ni infiere ningún dato -- solo se filtra
y renombra lo que el dataset de origen ya publica.
"""
import json
import os
from collections import defaultdict
from datetime import datetime, timedelta, timezone

import requests

KADOA_TRADES_URL = "https://raw.githubusercontent.com/kadoa-org/congress-trading-monitor/main/public/data/trades.json"
GIST_TOKEN  = os.environ.get("GIST_TOKEN", "")
GIST_ID     = os.environ.get("CONGRESS_GIST_ID", "")
GIST_FILE   = "congress_scan.json"
WINDOW_DAYS = 90  # ventana que se conserva en NUESTRO Gist (el de kadoa tiene el histórico completo desde 2012)

BUY_TYPES  = {"purchase"}
SELL_TYPES = {"sale (full)", "sale (partial)", "sale"}
# "exchange" y otros tipos ambiguos se excluyen de buy/sell -- no se fuerza
# una dirección que el propio dato no deja clara.


def _direction(transaction_type: str) -> str | None:
    t = (transaction_type or "").strip().lower()
    if t in BUY_TYPES:
        return "buy"
    if t in SELL_TYPES:
        return "sell"
    return None


def run_scan() -> dict:
    r = requests.get(KADOA_TRADES_URL, timeout=60)
    r.raise_for_status()
    all_trades = r.json()
    if not isinstance(all_trades, list) or not all_trades:
        raise ValueError("Dataset de kadoa vacío o con formato inesperado")

    cutoff = (datetime.now(timezone.utc) - timedelta(days=WINDOW_DAYS)).strftime("%Y-%m-%d")
    recent = [t for t in all_trades if (t.get("transaction_date") or "") >= cutoff]

    trades = []
    for t in recent:
        direction = _direction(t.get("transaction_type"))
        if not t.get("ticker") or not direction:
            continue
        trades.append({
            "ticker":             t["ticker"],
            "asset_name":         t.get("asset_name"),
            "filer_name":         t.get("filer_name"),
            "chamber":            t.get("chamber"),      # "senate" | "house"
            "party":              t.get("party"),
            "state":              t.get("state"),
            "direction":          direction,
            "transaction_type":   t.get("transaction_type"),
            "transaction_date":   t.get("transaction_date"),
            "filing_date":        t.get("filing_date"),
            "amount_range_low":   t.get("amount_range_low"),
            "amount_range_high":  t.get("amount_range_high"),
            "amount_range_label": t.get("amount_range_label"),
            "days_to_file":       t.get("days_to_file"),
            "is_late":            bool(t.get("is_late")),
            "doc_url":            t.get("doc_url"),
            "ret_since":          t.get("ret_since"),
        })

    # Clusters: 2+ filers DISTINTOS comprando el mismo ticker dentro de la ventana
    buys_by_ticker = defaultdict(list)
    for t in trades:
        if t["direction"] == "buy":
            buys_by_ticker[t["ticker"]].append(t)

    clusters = []
    for ticker, buys in buys_by_ticker.items():
        filers = {b["filer_name"] for b in buys if b["filer_name"]}
        if len(filers) >= 2:
            clusters.append({
                "ticker":        ticker,
                "asset_name":    buys[0].get("asset_name"),
                "n_filers":      len(filers),
                "filers":        sorted(filers),
                "min_total_usd": sum(b.get("amount_range_low") or 0 for b in buys),  # suma del extremo BAJO del rango -- nunca una cifra exacta
                "signal":        "FUERTE" if len(filers) >= 3 else "MODERADA",
            })
    clusters.sort(key=lambda c: -c["min_total_usd"])

    trades.sort(key=lambda t: (t["transaction_date"], t["filing_date"]), reverse=True)

    return {
        "ok": True,
        "trades": trades,
        "clusters": clusters,
        "window_days": WINDOW_DAYS,
        "total": len(trades),
        "source": "kadoa-org/congress-trading-monitor (MIT) -- agrega Senado eFD, Cámara Clerk y OGE bajo el STOCK Act",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def save_to_gist(result: dict):
    if not GIST_TOKEN or not GIST_ID:
        raise ValueError("GIST_TOKEN o CONGRESS_GIST_ID no configurados")
    r = requests.patch(
        f"https://api.github.com/gists/{GIST_ID}",
        headers={"Authorization": f"token {GIST_TOKEN}", "Accept": "application/vnd.github+json"},
        json={"files": {GIST_FILE: {"content": json.dumps(result, ensure_ascii=False, indent=2)}}},
        timeout=30,
    )
    if r.status_code not in (200, 201):
        raise ValueError(f"Gist error {r.status_code}: {r.text[:300]}")
    print(f"✅ Congress Trading guardado en Gist: {r.json()['html_url']}")


def main():
    print(f"🏛️  Congress Trading Scanner — {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}")
    result = run_scan()
    print(f"📊 {result['total']} operaciones en los últimos {WINDOW_DAYS} días, {len(result['clusters'])} clusters")
    save_to_gist(result)
    print("✅ Scan completado")


if __name__ == "__main__":
    main()
