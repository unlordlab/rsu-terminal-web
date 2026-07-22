import requests
import xml.etree.ElementTree as ET
import sqlite3
import os
import sys
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "shared"))
from time_utils import get_timestamp  # noqa: E402

EDGAR_BASE  = "https://efts.sec.gov/LATEST/search-index"
EDGAR_FULL  = "https://www.sec.gov"
HEADERS     = {
    "User-Agent":      "RSU Terminal contact@rsu-terminal.com",
    "Accept-Encoding": "gzip, deflate",
    "Host":            "efts.sec.gov",
}

# ── PERSISTENCIA ──────────────────────────────────────────────────────────────
#
# El feed de EDGAR ("getcurrent") es una foto de "lo que se está presentando
# ahora mismo" en TODO el mercado, no un histórico consultable. Y de esa foto,
# la mayoría de Form 4 son ejercicios de opciones / RSUs liberadas / retención
# fiscal (códigos M, A, F...), no compras o ventas reales — así que de cada
# pasada solo unas pocas líneas superan el filtro de compra/venta ≥ $50k.
#
# En vez de tirar esa foto cada 30 min y depender de que justo en ese instante
# haya suficiente señal, cada pasada se acumula en SQLite (dedupe por filing +
# transacción) y el feed que ve el usuario lee de ese histórico acumulado de
# los últimos días — así la sección se va llenando sola con el tiempo en vez
# de partir de cero en cada refresco.
DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'insider_history.db')
FEED_WINDOW_DAYS = 10   # cuántos días se muestran en el feed por defecto
RETENTION_DAYS   = 3650  # ~10 años -- el feed getcurrent de EDGAR es efímero e
                        # irreproducible, y el volumen es minúsculo (unas decenas
                        # de filas/día), así que no hay motivo para purgarlo pronto


def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = _conn()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS insider_tx (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            dedup_key     TEXT UNIQUE NOT NULL,
            ticker        TEXT NOT NULL,
            company       TEXT,
            insider_name  TEXT,
            title         TEXT,
            is_director   INTEGER DEFAULT 0,
            is_officer    INTEGER DEFAULT 0,
            type          TEXT,       -- 'COMPRA' | 'VENTA'
            type_code     TEXT,       -- 'P' | 'S'
            shares        INTEGER,
            price         REAL,
            value         INTEGER,
            tx_date       TEXT,       -- fecha de la transacción (del propio Form 4)
            filing_url    TEXT,
            ingested_at   TEXT NOT NULL
        )
    ''')
    conn.execute("CREATE INDEX IF NOT EXISTS idx_insider_tx_date ON insider_tx(tx_date)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_insider_tx_ticker ON insider_tx(ticker)")
    conn.execute('''
        CREATE TABLE IF NOT EXISTS insider_ingest_log (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            ran_at      TEXT NOT NULL,
            ok          INTEGER NOT NULL,
            scanned     INTEGER DEFAULT 0,
            found       INTEGER DEFAULT 0,
            new_rows    INTEGER DEFAULT 0,
            error       TEXT
        )
    ''')
    conn.commit()
    conn.close()


def _save_transactions(rows: list) -> int:
    """INSERT OR IGNORE de una lista de transacciones ya parseadas. Devuelve
    cuántas eran realmente nuevas (las repetidas se descartan por dedup_key)."""
    if not rows:
        return 0
    conn = _conn()
    new_count = 0
    try:
        now_iso = datetime.now().isoformat()
        for t in rows:
            dedup_key = "|".join([
                t.get("filing_url", ""), str(t.get("tx_date", "")),
                str(t.get("shares", "")), str(t.get("price", "")), t.get("type_code", ""),
            ])
            cur = conn.execute(
                "INSERT OR IGNORE INTO insider_tx "
                "(dedup_key, ticker, company, insider_name, title, is_director, is_officer, "
                " type, type_code, shares, price, value, tx_date, filing_url, ingested_at) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    dedup_key, t.get("ticker", ""), t.get("company", ""), t.get("insider_name", ""),
                    t.get("title", ""), int(bool(t.get("is_director"))), int(bool(t.get("is_officer"))),
                    t.get("type", ""), t.get("type_code", ""), t.get("shares", 0), t.get("price", 0),
                    t.get("value", 0), t.get("tx_date", t.get("date", "")), t.get("filing_url", ""), now_iso,
                )
            )
            if cur.rowcount > 0:
                new_count += 1
        conn.commit()
    finally:
        conn.close()
    return new_count


def _cleanup_old_transactions(days: int = RETENTION_DAYS) -> int:
    """Purga transacciones con fecha de negocio anterior a `days` días. Se
    llama en cada ciclo de ingesta (routers/ws.py, insider_ingest_loop) —
    barato de correr (una sola DELETE indexada) así que no hace falta un
    bucle aparte solo para esto."""
    cutoff = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    conn = _conn()
    try:
        cur = conn.execute("DELETE FROM insider_tx WHERE tx_date != '' AND tx_date < ?", (cutoff,))
        conn.commit()
        return cur.rowcount
    finally:
        conn.close()


def _read_transactions(days: int = FEED_WINDOW_DAYS) -> list:
    cutoff = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    conn = _conn()
    try:
        rows = conn.execute(
            "SELECT * FROM insider_tx WHERE tx_date >= ? OR tx_date = '' ORDER BY value DESC",
            (cutoff,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def _last_ingest_info() -> dict:
    conn = _conn()
    try:
        row = conn.execute("SELECT MAX(ingested_at) AS last, COUNT(*) AS total FROM insider_tx").fetchone()
        return {"last_ingest": row["last"], "total_stored": row["total"]}
    finally:
        conn.close()


def _log_ingest_attempt(ok: bool, scanned: int = 0, found: int = 0, new_rows: int = 0, error: str = None):
    conn = _conn()
    try:
        conn.execute(
            "INSERT INTO insider_ingest_log (ran_at, ok, scanned, found, new_rows, error) VALUES (?,?,?,?,?,?)",
            (datetime.now().isoformat(), int(ok), scanned, found, new_rows, error)
        )
        # Solo conservar las últimas 50 entradas de log — es diagnóstico, no histórico de negocio
        conn.execute("DELETE FROM insider_ingest_log WHERE id NOT IN "
                      "(SELECT id FROM insider_ingest_log ORDER BY id DESC LIMIT 50)")
        conn.commit()
    finally:
        conn.close()


def _last_ingest_log() -> dict:
    conn = _conn()
    try:
        row = conn.execute("SELECT * FROM insider_ingest_log ORDER BY id DESC LIMIT 1").fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

# ── HELPERS ───────────────────────────────────────────────────────────────────

_ENTITY_MARKERS = (
    "LLC", "L.L.C", "L.P.", " LP", "LP)", "CORP", "INC", "INC.", "FUND", "HOLDINGS",
    "HOLDING", "TRUST", "PARTNERS", "PARTNERSHIP", "CAPITAL", "MANAGEMENT",
    "GROUP", "ADVISORS", "ADVISERS", "ASSET", "LTD", "N.A.", "BANK", "PLC",
    "CO.", "COMPANY", "INVESTMENTS", "VENTURES", "SECURITIES", "FINANCIAL",
)

def _looks_like_entity(name: str) -> bool:
    """Red de seguridad por nombre: además del filtro estructural
    (isDirector/isOfficer), rechaza nombres que claramente son de una entidad
    (fondo, gestora, holding...) y no de una persona física."""
    if not name:
        return False
    upper = name.upper()
    return any(marker in upper for marker in _ENTITY_MARKERS)

def _parse_form4(filing_url: str) -> dict:
    """Parsea un Form 4 de SEC EDGAR"""
    try:
        r = requests.get(filing_url, headers={"User-Agent": "RSU Terminal contact@rsu-terminal.com"}, timeout=10)
        if r.status_code != 200: return {}
        root = ET.fromstring(r.content)

        ns = {'': ''}

        def find(tag):
            # Intentar con /value primero
            el = root.find('.//' + tag + '/value')
            if el is not None and el.text:
                return el.text.strip()
            el = root.find('.//' + tag)
            return el.text.strip() if el is not None and el.text else ''

        ticker   = find('issuerTradingSymbol')
        company  = find('issuerName')
        name     = find('rptOwnerName')
        title    = find('officerTitle') or find('reportingOwnerRelationship')
        is_dir   = find('isDirector') == '1'
        is_off   = find('isOfficer') == '1'
        is_10pct = find('isTenPercentOwner') == '1'
        is_other = find('isOther') == '1'

        # Transacciones
        transactions = []
        for tx in root.findall('.//nonDerivativeTransaction'):
            def tx_find(tag):
                # Los valores están dentro de <tag><value>X</value></tag>
                el = tx.find('.//' + tag + '/value')
                if el is not None and el.text:
                    return el.text.strip()
                # Fallback directo
                el = tx.find('.//' + tag)
                return el.text.strip() if el is not None and el.text else ''

            tx_type  = tx_find('transactionCode')
            shares   = tx_find('transactionShares')
            price    = tx_find('transactionPricePerShare')
            date     = tx_find('transactionDate')
            owned    = tx_find('sharesOwnedFollowingTransaction')

            try:
                shares_f = float(shares) if shares else 0
                price_f  = float(price)  if price  else 0
                value    = round(shares_f * price_f)
            except Exception:
                shares_f = 0
                price_f  = 0
                value    = 0

            if tx_type in ('P', 'S') and shares_f > 0 and value >= 50000:
                transactions.append({
                    "type":      'COMPRA' if tx_type == 'P' else 'VENTA',
                    "type_code": tx_type,
                    "shares":    int(shares_f),
                    "price":     round(price_f, 2),
                    "value":     value,
                    "date":      date,
                    "owned_after": owned,
                })

        return {
            "ticker":         ticker,
            "company":        company,
            "insider_name":   name,
            "title":          title,
            "is_director":    is_dir,
            "is_officer":     is_off,
            "is_ten_pct":     is_10pct,
            "is_other":       is_other,
            "transactions":   transactions,
        }
    except Exception:
        return {}

# ── FEED PRINCIPAL ────────────────────────────────────────────────────────────

def _ingest_cycle(max_filings: int = 100) -> dict:
    """Una pasada de scraping sobre el feed 'getcurrent' de EDGAR: descarga
    hasta `max_filings` Form 4 recientes, extrae TODAS las transacciones
    compra/venta ≥ $50k de cada uno (antes solo se quedaba con la más grande
    por filing) y las guarda en SQLite. Pensada para llamarse periódicamente
    desde un bucle en segundo plano (ver routers/ws.py, insider_ingest_loop)
    — mismo patrón que alerts_check_loop().

    Cada paso imprime a stdout (visible en los logs de uvicorn/Docker) y
    además queda registrado en insider_ingest_log, consultable vía
    /api/v1/insider/feed (campo last_ingest_log) sin tener que mirar logs."""
    print("[InsiderIngest] Iniciando ciclo de ingesta...")
    try:
        r = requests.get(
            "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=4&dateb=&owner=include&count=100&search_text=&output=atom",
            headers={"User-Agent": "RSU Terminal contact@rsu-terminal.com"},
            timeout=15,
        )
        print(f"[InsiderIngest] GET getcurrent atom feed -> status {r.status_code}, {len(r.content)} bytes")
        if r.status_code != 200:
            msg = f"SEC EDGAR error {r.status_code}: {r.text[:200]}"
            print(f"[InsiderIngest] FALLO: {msg}")
            _log_ingest_attempt(False, error=msg)
            return {"ok": False, "error": msg, "new": 0}

        root    = ET.fromstring(r.content)
        ns      = {'atom': 'http://www.w3.org/2005/Atom'}
        entries = root.findall('atom:entry', ns)
        print(f"[InsiderIngest] Atom feed parseado -> {len(entries)} entries encontradas")

        filings = []
        for entry in entries[:max_filings]:
            link    = entry.find('atom:link', ns)
            updated = entry.find('atom:updated', ns)
            link_href    = link.get('href', '') if link is not None else ''
            updated_text = updated.text[:10] if updated is not None else ''
            if link_href:
                filings.append({"url": link_href, "date": updated_text})
        print(f"[InsiderIngest] {len(filings)} filings con URL válida a procesar")

        def parse_filing(f):
            try:
                r2 = requests.get(f["url"], headers={"User-Agent": "RSU Terminal contact@rsu-terminal.com"}, timeout=8)
                if r2.status_code != 200: return []

                import re
                xml_matches = re.findall(r'href="(/Archives/edgar/data/[^"]+\.xml)"', r2.text)
                xml_url = None
                for match in xml_matches:
                    if 'xsl' not in match.lower():
                        xml_url = "https://www.sec.gov" + match
                        break
                if not xml_url and xml_matches:
                    xml_url = "https://www.sec.gov" + xml_matches[-1]
                if not xml_url: return []

                parsed = _parse_form4(xml_url)
                if not parsed or not parsed.get('transactions'): return []

                # Filtro de "persona real": nos quedamos solo con directivos y
                # consejeros (isDirector / isOfficer en el propio Form 4) —
                # esto excluye estructuralmente a los "10% owners" que son
                # fondos/holdings institucionales (isTenPercentOwner=1,
                # isDirector=0, isOfficer=0), en vez de adivinar por el nombre.
                if not (parsed.get('is_director') or parsed.get('is_officer')):
                    return []

                # Red de seguridad adicional: si por lo que sea el nombre del
                # reporting owner tiene pinta de entidad (fondo, LLC, holding,
                # trust...) en vez de una persona, se descarta igualmente,
                # aunque estuviera marcado como director/officer.
                if _looks_like_entity(parsed.get('insider_name', '')):
                    return []

                # Todas las transacciones que pasan el filtro de este filing,
                # no solo la más grande — un mismo Form 4 puede traer varias
                # líneas de compra/venta reales (p.ej. distintos lotes/precios).
                out = []
                for tx in parsed['transactions']:
                    if tx['value'] < 50000:
                        continue
                    out.append({
                        "ticker":       parsed.get('ticker', ''),
                        "company":      parsed.get('company', ''),
                        "insider_name": parsed.get('insider_name', ''),
                        "title":        parsed.get('title', ''),
                        "is_director":  parsed.get('is_director', False),
                        "is_officer":   parsed.get('is_officer', False),
                        "type":         tx['type'],
                        "type_code":    tx['type_code'],
                        "shares":       tx['shares'],
                        "price":        tx['price'],
                        "value":        tx['value'],
                        "tx_date":      tx['date'],
                        "filing_url":   f['url'],
                    })
                return out
            except Exception as e_inner:
                print(f"[InsiderIngest] Error parseando filing {f.get('url','?')}: {type(e_inner).__name__}: {e_inner}")
                return []

        with ThreadPoolExecutor(max_workers=10) as ex:
            results = list(ex.map(parse_filing, filings))

        all_tx = [t for sub in results for t in sub if t.get('ticker')]
        print(f"[InsiderIngest] {len(all_tx)} transacciones válidas (P/S ≥ $50k) extraídas de {len(filings)} filings")

        new_count = _save_transactions(all_tx)
        print(f"[InsiderIngest] Ciclo completo -> {new_count} nuevas guardadas (resto ya existían por dedupe)")

        purged = _cleanup_old_transactions()
        if purged:
            print(f"[InsiderIngest] Purgadas {purged} transacciones con más de {RETENTION_DAYS} días")

        _log_ingest_attempt(True, scanned=len(filings), found=len(all_tx), new_rows=new_count)
        return {"ok": True, "scanned": len(filings), "found": len(all_tx), "new": new_count, "purged": purged}

    except Exception as e:
        msg = f"{type(e).__name__}: {e}"
        print(f"[InsiderIngest] EXCEPCIÓN: {msg}")
        _log_ingest_attempt(False, error=msg)
        return {"ok": False, "error": msg, "new": 0}


def get_insider_feed() -> dict:
    """Sirve el feed desde el histórico acumulado en SQLite (ver _ingest_cycle
    e insider_ingest_loop en routers/ws.py). Si la base está vacía — típico
    justo tras el primer arranque, antes de que corra el primer ciclo del
    bucle en segundo plano — hace una pasada de ingesta síncrona para no
    dejar la sección vacía en el primer vistazo."""
    info = _last_ingest_info()
    if not info["total_stored"]:
        _ingest_cycle()

    rows = _read_transactions(FEED_WINDOW_DAYS)

    # Deduplicar por ticker+insider+fecha+valor (por si el mismo movimiento
    # aparece dos veces con dedup_key distinto por redondeos de precio)
    seen = set()
    deduped = []
    for t in rows:
        key = (t.get('ticker', ''), t.get('insider_name', ''), t.get('tx_date', ''), t.get('value', 0))
        if key not in seen:
            seen.add(key)
            deduped.append(t)

    deduped.sort(key=lambda x: x.get('value', 0), reverse=True)
    for t in deduped:
        t['date'] = t.get('tx_date', '')  # alias para compatibilidad con el frontend existente

    buys  = [t for t in deduped if t['type_code'] == 'P']
    sells = [t for t in deduped if t['type_code'] == 'S']

    from services.cartera_service import get_cartera_tickers
    cartera_tickers = get_cartera_tickers()
    for t in buys[:15] + sells[:10]:
        t["en_cartera"] = t.get("ticker") in cartera_tickers

    info = _last_ingest_info()
    return {
        "ok":              True,
        "buys":            buys[:15],
        "sells":           sells[:10],
        "total":           len(deduped),
        "window_days":     FEED_WINDOW_DAYS,
        "last_ingest":     info["last_ingest"],
        "last_ingest_log": _last_ingest_log(),
        "timestamp":       get_timestamp(),
        "source":          "SEC EDGAR Form 4 (histórico acumulado)",
    }

# ── TICKER ESPECÍFICO ─────────────────────────────────────────────────────────

def get_insider_ticker(ticker: str) -> dict:
    from services.cache import cache
    cached = cache.get(f"insider:ticker:{ticker}")
    if cached: return cached

    try:
        # Buscar CIK por ticker
        r = requests.get(
            f"https://efts.sec.gov/LATEST/search-index?q=%22{ticker}%22&forms=4&dateRange=custom&startdt={(datetime.now()-timedelta(days=180)).strftime('%Y-%m-%d')}",
            headers={"User-Agent": "RSU Terminal contact@rsu-terminal.com"},
            timeout=10,
        )

        # Alternativa: usar EDGAR company search
        r2 = requests.get(
            "https://www.sec.gov/cgi-bin/browse-edgar",
            params={
                "company":   "",
                "CIK":       ticker,
                "type":      "4",
                "dateb":     "",
                "owner":     "include",
                "count":     "20",
                "search_text": "",
                "action":    "getcompany",
                "output":    "atom",
            },
            headers={"User-Agent": "RSU Terminal contact@rsu-terminal.com"},
            timeout=10,
        )

        if r2.status_code != 200:
            raise ValueError("Sin datos EDGAR")

        root    = ET.fromstring(r2.content)
        ns      = {'atom': 'http://www.w3.org/2005/Atom'}
        entries = root.findall('atom:entry', ns)

        transactions = []
        import re

        def parse_entry(entry):
            link = entry.find('atom:link', ns)
            if link is None: return None
            url = link.get('href', '')
            if not url: return None

            try:
                r3 = requests.get(url, headers={"User-Agent": "RSU Terminal contact@rsu-terminal.com"}, timeout=8)
                if r3.status_code != 200: return None
                xml_matches = re.findall(r'href="(/Archives/edgar/data/[^"]+\.xml)"', r3.text)
                xml_url = None
                for match in xml_matches:
                    if 'xsl' not in match.lower():
                        xml_url = "https://www.sec.gov" + match
                        break
                if not xml_url and xml_matches:
                    xml_url = "https://www.sec.gov" + xml_matches[-1]
                if not xml_url: return None
                parsed  = _parse_form4(xml_url)
                if not parsed or not parsed.get('transactions'): return None

                # Mismo filtro de persona real que en el feed principal
                if not (parsed.get('is_director') or parsed.get('is_officer')): return None
                if _looks_like_entity(parsed.get('insider_name', '')): return None

                results = []
                for tx in parsed['transactions']:
                    results.append({
                        "ticker":       ticker,
                        "company":      parsed.get('company', ''),
                        "insider_name": parsed.get('insider_name', ''),
                        "title":        parsed.get('title', ''),
                        "type":         tx['type'],
                        "type_code":    tx['type_code'],
                        "shares":       tx['shares'],
                        "price":        tx['price'],
                        "value":        tx['value'],
                        "date":         tx['date'],
                        "owned_after":  tx.get('owned_after', ''),
                    })
                return results
            except Exception:
                return None

        with ThreadPoolExecutor(max_workers=5) as ex:
            results = list(ex.map(parse_entry, entries[:10]))

        for r_list in results:
            if r_list:
                transactions.extend(r_list)

        transactions.sort(key=lambda x: x.get('date', ''), reverse=True)

        from services.cartera_service import get_cartera_tickers
        result = {
            "ok":           True,
            "ticker":       ticker,
            "transactions": transactions[:20],
            "buys":         len([t for t in transactions if t['type_code'] == 'P']),
            "sells":        len([t for t in transactions if t['type_code'] == 'S']),
            "en_cartera":   ticker.upper() in get_cartera_tickers(),
            "timestamp":    get_timestamp(),
            "source":       "SEC EDGAR Form 4",
        }
        cache.set(f"insider:ticker:{ticker}", result, 3600)
        return result

    except Exception as e:
        return {"ok": False, "error": str(e), "ticker": ticker}

# ── CONFLUENCIA CON OPTIONS FLOW ─────────────────────────────────────────────

def get_confluence_tickers() -> set:
    """Tickers con señal de compra en Insider (compras recientes o cluster)
    Y señal alcista en Options Flow (top_bullish del mismo scan reciente) --
    dos módulos midiendo "dinero inteligente" desde ángulos distintos
    coincidiendo en el mismo ticker (badge ⚡, Fase 3 del roadmap). No
    descarga nada nuevo, reutiliza lo que ambos módulos ya calculan. Falla
    en silencio a conjunto vacío si cualquiera de los dos no está
    disponible -- no debe tumbar Insider ni Options Flow por un problema
    puntual del otro módulo."""
    try:
        from services.options_service import get_options_flow_simple
        feed     = get_insider_feed()
        clusters = get_insider_clusters()
        insider_tickers = {t["ticker"] for t in feed.get("buys", []) if t.get("ticker")} \
                        | {c["ticker"] for c in clusters.get("clusters", []) if c.get("ticker")}
        options_tickers = {t["ticker"] for t in get_options_flow_simple().get("top_bullish", []) if t.get("ticker")}
        return insider_tickers & options_tickers
    except Exception as e:
        print(f"[Insider] No se pudo calcular la confluencia con Options Flow: {e}")
        return set()

# ── CLUSTER BUYING ────────────────────────────────────────────────────────────

def get_insider_clusters() -> dict:
    """Detecta cuando múltiples insiders del mismo ticker compran simultáneamente"""
    from services.cache import cache
    cached = cache.get("insider:clusters")
    if cached: return cached

    try:
        feed = get_insider_feed()
        if not feed.get('ok'):
            raise ValueError("Sin datos feed")

        # Agrupar compras por ticker
        from collections import defaultdict
        ticker_buys = defaultdict(list)
        for buy in feed.get('buys', []):
            if buy.get('ticker'):
                ticker_buys[buy['ticker']].append(buy)

        # Clusters = tickers con 2+ insiders comprando
        from services.cartera_service import get_cartera_tickers
        cartera_tickers = get_cartera_tickers()
        clusters = []
        for ticker, buys in ticker_buys.items():
            if len(buys) >= 2:
                total_value   = sum(b.get('value', 0) for b in buys)
                total_shares  = sum(b.get('shares', 0) for b in buys)
                clusters.append({
                    "ticker":       ticker,
                    "company":      buys[0].get('company', ''),
                    "n_insiders":   len(buys),
                    "total_value":  total_value,
                    "total_shares": total_shares,
                    "insiders":     [{"name": b['insider_name'], "title": b['title'], "value": b['value']} for b in buys],
                    "signal":       "FUERTE" if len(buys) >= 3 else "MODERADA",
                    "signal_color": "#00ffad" if len(buys) >= 3 else "#ffb800",
                    "en_cartera":   ticker in cartera_tickers,
                })

        clusters.sort(key=lambda x: x['total_value'], reverse=True)

        result = {
            "ok":        True,
            "clusters":  clusters[:10],
            "timestamp": get_timestamp(),
        }
        cache.set("insider:clusters", result, 1800)
        return result

    except Exception as e:
        return {"ok": False, "error": str(e)}


init_db()