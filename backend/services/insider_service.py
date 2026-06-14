import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import time

EDGAR_BASE  = "https://efts.sec.gov/LATEST/search-index"
EDGAR_FULL  = "https://www.sec.gov"
HEADERS     = {
    "User-Agent":      "RSU Terminal contact@rsu-terminal.com",
    "Accept-Encoding": "gzip, deflate",
    "Host":            "efts.sec.gov",
}

# ── HELPERS ───────────────────────────────────────────────────────────────────

def _get_timestamp():
    from datetime import timezone
    cet = timezone(timedelta(hours=1))
    return datetime.now(cet).strftime('%H:%M:%S')

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
            "ticker":       ticker,
            "company":      company,
            "insider_name": name,
            "title":        title,
            "is_director":  is_dir,
            "is_officer":   is_off,
            "transactions": transactions,
        }
    except Exception:
        return {}

def _search_form4(days_back: int = 3, min_value: int = 50000) -> list:
    """Busca Form 4s recientes en SEC EDGAR"""
    try:
        date_from = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
        url = "https://efts.sec.gov/LATEST/search-index?q=%22form+4%22&dateRange=custom&startdt=" + date_from + "&forms=4"

        r = requests.get(
            "https://efts.sec.gov/LATEST/search-index",
            params={
                "q":         "\"form 4\"",
                "forms":     "4",
                "dateRange": "custom",
                "startdt":   date_from,
                "_source":   "file_date,display_names,period_of_report,file_num",
                "from":      "0",
                "size":      "40",
            },
            headers={"User-Agent": "RSU Terminal contact@rsu-terminal.com"},
            timeout=15,
        )

        if r.status_code != 200:
            return []

        hits = r.json().get("hits", {}).get("hits", [])
        results = []

        for hit in hits[:40]:
            src      = hit.get("_source", {})
            accession = hit.get("_id", "").replace("-", "")
            if not accession: continue

            # URL del filing index
            cik = src.get("file_num", "")
            results.append({
                "accession": hit.get("_id", ""),
                "date":      src.get("file_date", ""),
                "names":     src.get("display_names", []),
            })

        return results
    except Exception:
        return []

# ── FEED PRINCIPAL ────────────────────────────────────────────────────────────

def get_insider_feed() -> dict:
    from services.cache import cache
    cached = cache.get("insider:feed")
    if cached: return cached

    try:
        # RSS feed de SEC EDGAR Form 4 — más fiable
        r = requests.get(
            "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=4&dateb=&owner=include&count=100&search_text=&output=atom",
            headers={"User-Agent": "RSU Terminal contact@rsu-terminal.com"},
            timeout=15,
        )

        if r.status_code != 200:
            raise ValueError(f"SEC EDGAR error {r.status_code}")

        # Parsear Atom feed
        root     = ET.fromstring(r.content)
        ns       = {'atom': 'http://www.w3.org/2005/Atom'}
        entries  = root.findall('atom:entry', ns)

        filings  = []
        for entry in entries[:40]:
            title   = entry.find('atom:title', ns)
            link    = entry.find('atom:link', ns)
            updated = entry.find('atom:updated', ns)
            summary = entry.find('atom:summary', ns)

            title_text   = title.text   if title   is not None else ''
            link_href    = link.get('href', '') if link is not None else ''
            updated_text = updated.text[:10] if updated is not None else ''
            summary_text = summary.text if summary is not None else ''

            filings.append({
                "title":   title_text,
                "url":     link_href,
                "date":    updated_text,
                "summary": summary_text[:200],
            })

        # Parsear los primeros 15 Form 4s para obtener detalles
        transactions = []
        def parse_filing(f):
            # Obtener index page
            try:
                idx_url = f["url"].replace("-index.htm", "")
                r2 = requests.get(
                    f["url"],
                    headers={"User-Agent": "RSU Terminal contact@rsu-terminal.com"},
                    timeout=8,
                )
                if r2.status_code != 200: return None

                # Buscar el XML del Form 4 en el índice
                content = r2.text
                import re
                # Buscar XML del Form 4 — excluir stylesheets (xslF345X06)
                xml_matches = re.findall(r'href="(/Archives/edgar/data/[^"]+\.xml)"', content)
                xml_url = None
                for match in xml_matches:
                    if 'xsl' not in match.lower():
                        xml_url = "https://www.sec.gov" + match
                        break
                if not xml_url and xml_matches:
                    xml_url = "https://www.sec.gov" + xml_matches[-1]
                if not xml_url: return None
                parsed   = _parse_form4(xml_url)
                if not parsed or not parsed.get('transactions'): return None

                # Solo devolver la transacción más grande
                if not parsed['transactions']: return None
                best = max(parsed['transactions'], key=lambda x: x['value'])
                if best['value'] < 50000: return None
                return {
                    "ticker":       parsed.get('ticker', ''),
                    "company":      parsed.get('company', ''),
                    "insider_name": parsed.get('insider_name', ''),
                    "title":        parsed.get('title', ''),
                    "is_director":  parsed.get('is_director', False),
                    "is_officer":   parsed.get('is_officer', False),
                    "type":         best['type'],
                    "type_code":    best['type_code'],
                    "shares":       best['shares'],
                    "price":        best['price'],
                    "value":        best['value'],
                    "date":         best['date'],
                    "filing_url":   f['url'],
                }
            except Exception:
                return None

        with ThreadPoolExecutor(max_workers=8) as ex:
            results = list(ex.map(parse_filing, filings[:40]))

        transactions = [r for r in results if r is not None and r.get('ticker')]

        # Deduplicar por ticker+insider+fecha+valor
        seen = set()
        deduped = []
        for t in transactions:
            key = (t.get('ticker',''), t.get('insider_name',''), t.get('date',''), t.get('value',0))
            if key not in seen:
                seen.add(key)
                deduped.append(t)
        transactions = deduped

        # Ordenar por valor
        transactions.sort(key=lambda x: x.get('value', 0), reverse=True)

        # Separar compras y ventas
        buys  = [t for t in transactions if t['type_code'] == 'P']
        sells = [t for t in transactions if t['type_code'] == 'S']

        result = {
            "ok":          True,
            "buys":        buys[:15],
            "sells":       sells[:10],
            "total":       len(transactions),
            "timestamp":   _get_timestamp(),
            "source":      "SEC EDGAR Form 4",
        }
        cache.set("insider:feed", result, 1800)  # 30 min
        return result

    except Exception as e:
        return {"ok": False, "error": str(e)}

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

        result = {
            "ok":           True,
            "ticker":       ticker,
            "transactions": transactions[:20],
            "buys":         len([t for t in transactions if t['type_code'] == 'P']),
            "sells":        len([t for t in transactions if t['type_code'] == 'S']),
            "timestamp":    _get_timestamp(),
            "source":       "SEC EDGAR Form 4",
        }
        cache.set(f"insider:ticker:{ticker}", result, 3600)
        return result

    except Exception as e:
        return {"ok": False, "error": str(e), "ticker": ticker}

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
                })

        clusters.sort(key=lambda x: x['total_value'], reverse=True)

        result = {
            "ok":        True,
            "clusters":  clusters[:10],
            "timestamp": _get_timestamp(),
        }
        cache.set("insider:clusters", result, 1800)
        return result

    except Exception as e:
        return {"ok": False, "error": str(e)}