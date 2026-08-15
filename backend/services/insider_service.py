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

# ── Ritmo de peticiones a SEC EDGAR ──────────────────────────────────────────
#
# SEC EDGAR bloquea (429) por encima de ~10 peticiones/segundo por IP (fair
# access policy publicada). _ingest_cycle() dispara hasta 100 filings x 2
# peticiones cada uno vía ThreadPoolExecutor(10) -- sin ningún control de
# ritmo, los workers concurrentes superan de largo ese límite en ráfaga, y el
# bloqueo de SEC persiste más allá de la propia ráfaga (el siguiente ciclo,
# 20 min después, ya empieza fallando en la primera petición). Ver incidente
# 26/07/2026. _sec_get() es el único punto por el que pasan todas las
# peticiones de este módulo a sec.gov/efts.sec.gov, con un lock global que
# las espacia -- así el límite se respeta de verdad sin importar cuántos
# workers concurrentes (o llamadas de usuarios distintos) lo usen a la vez.
import threading
_sec_rate_lock = threading.Lock()
_sec_last_call = [0.0]
_SEC_MIN_INTERVAL = 0.15  # ~6-7 req/s, con margen bajo el límite oficial


def _sec_get(url, **kwargs):
    with _sec_rate_lock:
        elapsed = time.monotonic() - _sec_last_call[0]
        if elapsed < _SEC_MIN_INTERVAL:
            time.sleep(_SEC_MIN_INTERVAL - elapsed)
        _sec_last_call[0] = time.monotonic()
    return requests.get(url, **kwargs)

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


# ── IDENTIDAD DE UN FILING ───────────────────────────────────────────────────
#
# EDGAR publica el MISMO Form 4 dos veces en el feed "getcurrent": una bajo el
# CIK del emisor y otra bajo el del directivo que lo presenta. Las dos URLs
# apuntan al mismo documento y traen exactamente las mismas transacciones:
#
#   /Archives/edgar/data/2058103/000176962826000336/0001769628-26-000336-index.htm
#   /Archives/edgar/data/1769628/000176962826000336/0001769628-26-000336-index.htm
#                        ^^^^^^^ solo cambia el CIK
#
# Hasta el 04/08/2026 la clave de deduplicación era la URL COMPLETA, así que
# las dos entraban como transacciones distintas. Medido sobre la base real:
# 50 de 98 filas eran duplicados (el 51%) y los importes salían inflados
# exactamente el 101% -- $180M donde en realidad había $89M. Ese doble conteo
# también fabricaba clusters: la misma persona contada dos veces parecía dos
# directivos comprando a la vez.
#
# El número de accession identifica el documento con independencia de bajo qué
# CIK se liste, así que es la identidad correcta.
import re as _re

_ACCESSION_GUION = _re.compile(r'(\d{10}-\d{2}-\d{6})')
_ACCESSION_PLANO = _re.compile(r'/(\d{18})/')


def _accession(filing_url: str) -> str:
    """Número de accession normalizado (con guiones) de una URL de EDGAR.

    Si la URL no tiene una forma reconocible se devuelve tal cual: es
    preferible dejar pasar un duplicado a colapsar dos filings distintos en
    uno, que borraría una transacción real."""
    if not filing_url:
        return ""
    m = _ACCESSION_GUION.search(filing_url)
    if m:
        return m.group(1)
    m = _ACCESSION_PLANO.search(filing_url)
    if m:
        d = m.group(1)
        return f"{d[:10]}-{d[10:12]}-{d[12:]}"
    return filing_url


def _dedup_key(t: dict) -> str:
    """Identidad de una transacción: el documento que la reporta más sus
    datos. Nota conocida: si un mismo Form 4 declarase dos líneas idénticas
    (misma fecha, acciones, precio y tipo) se contarían como una. Es el mismo
    comportamiento que ya tenía la clave anterior y no se ha observado en los
    datos reales -- los filers agregan esos lotes."""
    return "|".join([
        _accession(t.get("filing_url", "")),
        str(t.get("tx_date", t.get("date", ""))),
        str(t.get("shares", "")),
        str(t.get("price", "")),
        t.get("type_code", ""),
    ])


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
    # Filings ya procesados, den o no transacciones. Sin esto, cada ciclo
    # volvía a descargar los ~100 filings del feed getcurrent aunque ya se
    # hubieran mirado: medido en el log real, seis ciclos seguidos con
    # scanned=100 y new_rows=0, es decir ~1.200 peticiones a la SEC para nada.
    # No basta con mirar insider_tx: la mayoría de Form 4 no producen ninguna
    # fila (son ejercicios de opciones, o quedan por debajo del mínimo), y esos
    # son justamente los que se re-descargaban eternamente.
    conn.execute('''
        CREATE TABLE IF NOT EXISTS insider_seen_filing (
            accession TEXT PRIMARY KEY,
            seen_at   TEXT NOT NULL
        )
    ''')
    conn.commit()
    _migrar_dedupe_por_accession(conn)
    _migrar_cargos_vacios(conn)
    conn.close()


def _migrar_cargos_vacios(conn) -> int:
    """Rellena el cargo de las filas ya guardadas que se quedaron sin él.

    El arreglo de `_cargo()` solo actúa al ingerir, así que sin esto las filas
    que ya estaban en la base seguirían enseñando un guion durante días. Las
    banderas is_director/is_officer SÍ están guardadas, que es justo lo que
    hace falta. `is_ten_pct` no se guarda como columna, así que esas filas —si
    las hubiera— se quedan como están en vez de adivinar.

    Idempotente: solo toca filas con el cargo vacío, y tras pasar ya no
    quedan."""
    try:
        pares = [
            ("Directivo · Consejero", "is_officer = 1 AND is_director = 1"),
            ("Directivo",             "is_officer = 1 AND is_director = 0"),
            ("Consejero",             "is_officer = 0 AND is_director = 1"),
        ]
        total = 0
        for cargo, cond in pares:
            cur = conn.execute(
                f"UPDATE insider_tx SET title = ? WHERE (title = '' OR title IS NULL) AND {cond}",
                (cargo,)
            )
            total += cur.rowcount
        conn.commit()
        if total:
            print(f"[Insider] Migración de cargos: {total} filas sin cargo rellenadas desde las banderas del Form 4")
        return total
    except Exception as e:
        print(f"[Insider] La migración de cargos falló, se reintenta al arrancar: {type(e).__name__}: {e}")
        return 0


def _migrar_dedupe_por_accession(conn) -> int:
    """Recalcula las claves de deduplicación al formato por accession y
    colapsa los duplicados que dejó pasar la clave anterior (ver el bloque
    de _accession). Idempotente: las claves viejas empiezan por la URL
    completa, así que basta con mirar si queda alguna con ese formato.

    Se conserva la fila de id más bajo de cada grupo -- la primera que se
    ingirió. Da igual cuál se quede: los duplicados son el mismo documento
    con los mismos datos, solo cambia el CIK del enlace."""
    try:
        pendiente = conn.execute(
            "SELECT 1 FROM insider_tx WHERE dedup_key LIKE 'http%' LIMIT 1"
        ).fetchone()
        if not pendiente:
            return 0

        filas = conn.execute(
            "SELECT id, filing_url, tx_date, shares, price, type_code FROM insider_tx ORDER BY id"
        ).fetchall()

        grupos, sobrantes = {}, []
        for f in filas:
            clave = _dedup_key({
                "filing_url": f["filing_url"], "tx_date": f["tx_date"],
                "shares": f["shares"], "price": f["price"], "type_code": f["type_code"],
            })
            if clave in grupos:
                sobrantes.append(f["id"])
            else:
                grupos[clave] = f["id"]

        # Primero se borran los duplicados y después se reescriben las claves:
        # al revés, el UPDATE chocaría contra el UNIQUE de dedup_key.
        if sobrantes:
            conn.executemany("DELETE FROM insider_tx WHERE id = ?", [(i,) for i in sobrantes])
        conn.executemany(
            "UPDATE insider_tx SET dedup_key = ? WHERE id = ?",
            [(clave, rid) for clave, rid in grupos.items()]
        )
        conn.commit()
        print(f"[Insider] Migración de deduplicación: {len(sobrantes)} filas duplicadas eliminadas, "
              f"{len(grupos)} claves reescritas por accession")
        return len(sobrantes)
    except Exception as e:
        print(f"[Insider] La migración de deduplicación falló, se reintenta al arrancar: {type(e).__name__}: {e}")
        return 0


def _filings_ya_vistos(accessions: list) -> set:
    if not accessions:
        return set()
    conn = _conn()
    try:
        marcas = ",".join("?" * len(accessions))
        return {r["accession"] for r in conn.execute(
            f"SELECT accession FROM insider_seen_filing WHERE accession IN ({marcas})", accessions
        ).fetchall()}
    finally:
        conn.close()


def _marcar_filings_vistos(accessions: list) -> None:
    """Se marcan DESPUÉS de procesarlos, no antes: si el ciclo se cae a mitad,
    los que no llegaron a mirarse se reintentan en la pasada siguiente."""
    if not accessions:
        return
    ahora = datetime.now().isoformat()
    conn = _conn()
    try:
        conn.executemany(
            "INSERT OR IGNORE INTO insider_seen_filing (accession, seen_at) VALUES (?, ?)",
            [(a, ahora) for a in accessions]
        )
        # El feed getcurrent solo lista lo que se está presentando ahora, así
        # que un filing de hace un mes no puede reaparecer. Se poda para que la
        # tabla no crezca sin fin.
        corte = (datetime.now() - timedelta(days=30)).isoformat()
        conn.execute("DELETE FROM insider_seen_filing WHERE seen_at < ?", (corte,))
        conn.commit()
    finally:
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
            dedup_key = _dedup_key(t)
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
        # Las filas sin fecha de transacción envejecen por su fecha de
        # ingesta. Antes quedaban EXENTAS de la purga y del filtro de ventana
        # (`tx_date != ''`), así que eran inmortales: se quedaban en el feed
        # para siempre. Hoy no hay ninguna en la base, pero el camino existía.
        cur = conn.execute(
            "DELETE FROM insider_tx WHERE (tx_date != '' AND tx_date < ?) "
            "OR (tx_date = '' AND ingested_at < ?)",
            (cutoff, cutoff)
        )
        conn.commit()
        return cur.rowcount
    finally:
        conn.close()


def _read_transactions(days: int = FEED_WINDOW_DAYS) -> list:
    cutoff = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    conn = _conn()
    try:
        # Mismo criterio que la purga: sin fecha de transacción se usa la de
        # ingesta, en vez de dejar la fila fuera del filtro de ventana.
        rows = conn.execute(
            "SELECT * FROM insider_tx WHERE (tx_date != '' AND tx_date >= ?) "
            "OR (tx_date = '' AND ingested_at >= ?) ORDER BY value DESC",
            (cutoff, cutoff)
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


def _last_ingest_log(incluir_error: bool = False) -> dict:
    """Último intento de ingesta. `incluir_error` trae el texto crudo de la
    excepción, que NO debe salir en la respuesta pública: iba al feed de todos
    los usuarios y podía llevar rutas internas, URLs con parámetros o el
    mensaje de una librería. Para el usuario basta con saber si el último
    ciclo funcionó y cuándo fue; el detalle sigue en los logs del servidor."""
    conn = _conn()
    try:
        row = conn.execute("SELECT * FROM insider_ingest_log ORDER BY id DESC LIMIT 1").fetchone()
        if not row:
            return None
        d = dict(row)
        if not incluir_error:
            d["error"] = "El último intento de actualización falló" if not d.get("ok") else None
        return d
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

# ¿Entran los dueños del 10% que no son consejeros ni directivos?
#
# El filtro existe para dejar fuera a fondos, gestoras y holdings, que
# declaran isTenPercentOwner=1 sin ningún cargo. Pero se llevaba por delante
# también a los fundadores y grandes accionistas individuales, que son
# exactamente el tipo de comprador que este módulo busca — y `is_ten_pct` se
# parseaba del Form 4 sin usarse en ninguna parte.
#
# Con esto activado siguen pasando por el filtro de nombre (_looks_like_entity),
# que es el que descarta LLC, TRUST, PARTNERS, CAPITAL y compañía. Es una
# decisión de producto, no técnica: si en producción se cuelan demasiadas
# entidades con nombre de persona, se pone a False y vuelve al comportamiento
# anterior sin tocar nada más.
INCLUIR_10_PCT = True


def _es_persona_reportante(parsed: dict) -> bool:
    """Filtro de «persona real», en un solo sitio: lo aplicaban por separado
    el feed principal y la búsqueda por ticker, con el riesgo de que uno se
    corrigiera y el otro no."""
    declarado = parsed.get('is_director') or parsed.get('is_officer')
    if INCLUIR_10_PCT:
        declarado = declarado or parsed.get('is_ten_pct')
    if not declarado:
        return False
    # Red de seguridad por nombre: aunque venga marcado como persona, si se
    # llama como un fondo o un holding, fuera.
    return not _looks_like_entity(parsed.get('insider_name', ''))


def _cargo(titulo: str, is_director: bool, is_officer: bool, is_ten_pct: bool) -> str:
    """Cargo legible cuando el Form 4 no trae `officerTitle`.

    Un consejero que no es directivo NO tiene ese campo — es exclusivo de los
    officers — y el otro candidato (`reportingOwnerRelationship`) es un
    contenedor sin texto, así que salía vacío y la pantalla pintaba un guion.
    Medido el 04/08/2026 sobre la base real: 20 de 98 filas sin cargo, y las
    20 eran consejeros. El dato existía en las banderas del propio Form 4, solo
    que no se leía.

    «Consejero» y «Directivo» traducen director y officer en su sentido de la
    SEC: miembro del consejo frente a alto cargo ejecutivo."""
    if titulo:
        return titulo
    partes = []
    if is_officer:  partes.append("Directivo")
    if is_director: partes.append("Consejero")
    if is_ten_pct:  partes.append("10% del capital")
    return " · ".join(partes)


def _parse_form4(filing_url: str) -> dict:
    """Parsea un Form 4 de SEC EDGAR"""
    try:
        r = _sec_get(filing_url, headers={"User-Agent": "RSU Terminal contact@rsu-terminal.com"}, timeout=10)
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
            "title":          _cargo(title, is_dir, is_off, is_10pct),
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
        atom_url = "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=4&dateb=&owner=include&count=100&search_text=&output=atom"
        r = _sec_get(atom_url, headers={"User-Agent": "RSU Terminal contact@rsu-terminal.com"}, timeout=15)
        if r.status_code == 429:
            # Un solo reintento respetando Retry-After (o 60s por defecto) --
            # si SEC sigue bloqueando tras esperar, se registra el fallo y se
            # deja para el próximo ciclo (20 min) en vez de insistir más.
            wait_s = min(int(r.headers.get("Retry-After", 60) or 60), 120)
            print(f"[InsiderIngest] 429 en el feed atom -- reintentando en {wait_s}s")
            time.sleep(wait_s)
            r = _sec_get(atom_url, headers={"User-Agent": "RSU Terminal contact@rsu-terminal.com"}, timeout=15)
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
                filings.append({"url": link_href, "date": updated_text, "acc": _accession(link_href)})

        # Dos filtros antes de descargar nada, y los dos importan:
        #
        #  1. El mismo Form 4 aparece DOS veces en el feed (una por el CIK del
        #     emisor y otra por el del directivo). Sin esto se descargaba dos
        #     veces el mismo documento dentro de la MISMA pasada.
        #  2. Los filings de pasadas anteriores no hace falta volver a mirarlos.
        #
        # Antes se descargaba todo y se deduplicaba al guardar, o sea después
        # de haber gastado las peticiones. Ahora se descarta primero.
        unicos, vistos_en_esta_pasada = [], set()
        for f in filings:
            if f["acc"] in vistos_en_esta_pasada:
                continue
            vistos_en_esta_pasada.add(f["acc"])
            unicos.append(f)

        ya_vistos = _filings_ya_vistos([f["acc"] for f in unicos])
        pendientes = [f for f in unicos if f["acc"] not in ya_vistos]
        print(f"[InsiderIngest] {len(filings)} entries -> {len(unicos)} documentos distintos -> "
              f"{len(pendientes)} sin procesar todavía ({len(ya_vistos)} ya vistos, no se descargan)")
        filings = pendientes

        if not filings:
            print("[InsiderIngest] Nada nuevo en el feed; ciclo terminado sin descargar ningún filing")
            _log_ingest_attempt(True, scanned=0, found=0, new_rows=0)
            return {"ok": True, "scanned": 0, "found": 0, "new": 0, "purged": 0}

        def parse_filing(f):
            try:
                r2 = _sec_get(f["url"], headers={"User-Agent": "RSU Terminal contact@rsu-terminal.com"}, timeout=8)
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

                if not _es_persona_reportante(parsed):
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

        # Se marcan todos los procesados, también los que no dieron ninguna
        # transacción: son la mayoría, y son justamente los que se
        # re-descargaban ciclo tras ciclo por no dejar constancia de haberlos
        # mirado.
        _marcar_filings_vistos([f["acc"] for f in filings])

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


INGEST_RETRY_COOLDOWN_S = 300  # 5 min

# El cooldown evita reintentar en bucle, pero NO es un lock: dos peticiones
# concurrentes con la base vacía y sin intento reciente pasaban las dos y
# lanzaban su propio ciclo completo contra la SEC. Este lock es NO BLOQUEANTE
# a propósito -- si otra petición ya está ingiriendo, esta sigue y sirve lo que
# haya, en vez de quedarse esperando. Encolar peticiones HTTP detrás de una
# descarga de decenas de segundos sería cambiar un problema por otro peor.
_ingest_lock = threading.Lock()

def get_insider_feed() -> dict:
    """Sirve el feed desde el histórico acumulado en SQLite (ver _ingest_cycle
    e insider_ingest_loop en routers/ws.py). Si la base está vacía — típico
    justo tras el primer arranque, antes de que corra el primer ciclo del
    bucle en segundo plano — hace una pasada de ingesta síncrona para no
    dejar la sección vacía en el primer vistazo.

    Cooldown: sin esto, cada petición concurrente mientras la base sigue
    vacía (varios usuarios a la vez, o get_confluence_tickers() desde
    Options Flow) dispararía su propio ciclo completo contra SEC -- si SEC
    ya está devolviendo 429, eso solo empeora el bloqueo. Si el último
    intento (con éxito o no) fue hace menos de INGEST_RETRY_COOLDOWN_S, no
    se reintenta."""
    info = _last_ingest_info()
    if not info["total_stored"]:
        last_log = _last_ingest_log()
        recently_tried = (
            last_log and last_log.get("ran_at") and
            (datetime.now() - datetime.fromisoformat(last_log["ran_at"])).total_seconds() < INGEST_RETRY_COOLDOWN_S
        )
        if not recently_tried and _ingest_lock.acquire(blocking=False):
            try:
                # Se relee dentro del lock: si otra petición acabó de ingerir
                # mientras esta esperaba su turno, ya no hace falta repetirlo.
                if not _last_ingest_info()["total_stored"]:
                    _ingest_cycle()
            finally:
                _ingest_lock.release()

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

    # Por FECHA, no por importe. La cabecera de la pantalla dice «RECIENTES» y
    # el orden era por tamaño, así que una compra grande de hace nueve días
    # salía por encima de una de ayer. El importe queda como desempate dentro
    # del mismo día, que es donde de verdad ayuda a priorizar.
    # Las filas sin fecha caen al final: '' ordena por debajo de cualquier
    # fecha en descendente, y así no encabezan nada.
    deduped.sort(key=lambda x: (x.get('tx_date') or '', x.get('value', 0)), reverse=True)
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

def _transacciones_locales(ticker: str) -> list:
    """Lo que la terminal ya tiene guardado de este valor, con el mismo shape
    que devuelve la consulta a EDGAR. `insider_tx` tiene índice por ticker y
    hasta diez años de retención, y hasta ahora esta vista no lo miraba
    siquiera: iba a EDGAR y se conformaba con los diez últimos filings."""
    conn = _conn()
    try:
        filas = conn.execute(
            "SELECT * FROM insider_tx WHERE ticker = ? ORDER BY tx_date DESC",
            (ticker.upper(),)
        ).fetchall()
    finally:
        conn.close()
    return [{
        "ticker":       r["ticker"],
        "company":      r["company"],
        "insider_name": r["insider_name"],
        "title":        r["title"],
        "type":         r["type"],
        "type_code":    r["type_code"],
        "shares":       r["shares"],
        "price":        r["price"],
        "value":        r["value"],
        "date":         r["tx_date"],
        "owned_after":  "",
        "filing_url":   r["filing_url"],
    } for r in filas]


def _fusionar_transacciones(*fuentes) -> list:
    """Une varias listas quitando lo repetido y ordenando por fecha.

    La clave es la misma que la de la ingesta —documento más datos de la
    operación— para que una transacción presente a la vez en la base local y
    en la respuesta de EDGAR aparezca una sola vez.

    Si alguna fila llegara sin `filing_url` se identifica por sus propios
    datos. Eso NO basta para casar con una fila local (que sí lo tiene), así
    que las dos fuentes deben traerlo — se comprobó midiendo: sin `filing_url`
    en las filas de EDGAR salían las 10 transacciones de SCHW por duplicado."""
    vistas, salida = set(), []
    for fuente in fuentes:
        for t in fuente or []:
            if t.get("filing_url"):
                clave = _dedup_key(t)
            else:
                clave = "|".join(str(t.get(c, "")) for c in
                                 ("insider_name", "date", "shares", "price", "type_code"))
            if clave in vistas:
                continue
            vistas.add(clave)
            salida.append(t)
    salida.sort(key=lambda t: (t.get("date") or "", t.get("value", 0)), reverse=True)
    return salida


def get_insider_ticker(ticker: str) -> dict:
    from services.cache import cache
    cached = cache.get(f"insider:ticker:{ticker}")
    if cached: return cached

    # El histórico local se lee FUERA del try de EDGAR, y eso es lo que hace
    # que este hallazgo valga de algo: si la SEC da timeout —pasó al verificar
    # este mismo cambio— antes se perdía todo y la pantalla decía «sin datos»
    # aunque hubiera diez transacciones guardadas en disco. Ahora lo local se
    # sirve igualmente y solo se pierde lo que EDGAR habría añadido.
    locales = _transacciones_locales(ticker)

    try:
        # Aquí había una petición a efts.sec.gov/LATEST/search-index cuyo
        # resultado no se leía NUNCA: se asignaba a una variable y la línea
        # siguiente la pisaba con la búsqueda de verdad. Una petición a la SEC
        # por cada búsqueda de ticker, tirada. Eliminada el 04/08/2026.
        r2 = _sec_get(
            "https://www.sec.gov/cgi-bin/browse-edgar",
            params={
                "company":   "",
                "CIK":       ticker,
                "type":      "4",
                "dateb":     "",
                "owner":     "include",
                # Se pedían 20 y se procesaban 10 (entries[:10] más abajo):
                # EDGAR devolvía el doble de lo que se iba a mirar.
                "count":     "10",
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
                r3 = _sec_get(url, headers={"User-Agent": "RSU Terminal contact@rsu-terminal.com"}, timeout=8)
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

                if not _es_persona_reportante(parsed): return None

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
                        # Sin esto, la fusión con el histórico local no puede
                        # reconocer que es el MISMO documento: las filas de la
                        # base identifican por accession y estas caerían a una
                        # clave distinta, duplicando cada transacción.
                        "filing_url":   url,
                    })
                return results
            except Exception:
                return None

        with ThreadPoolExecutor(max_workers=5) as ex:
            results = list(ex.map(parse_entry, entries[:10]))

        for r_list in results:
            if r_list:
                transactions.extend(r_list)

        # El histórico local va PRIMERO en la fusión, así que ante una misma
        # transacción presente en los dos sitios gana la fila ya guardada.
        transactions = _fusionar_transacciones(locales, transactions)

        from services.cartera_service import get_cartera_tickers
        result = {
            "ok":           True,
            "ticker":       ticker,
            "transactions": transactions[:20],
            "n_locales":    len(locales),
            "buys":         len([t for t in transactions if t['type_code'] == 'P']),
            "sells":        len([t for t in transactions if t['type_code'] == 'S']),
            "en_cartera":   ticker.upper() in get_cartera_tickers(),
            "timestamp":    get_timestamp(),
            "source":       "SEC EDGAR Form 4",
        }
        cache.set(f"insider:ticker:{ticker}", result, 3600)
        return result

    except Exception as e:
        print(f"[Insider] EDGAR falló para {ticker}: {type(e).__name__}: {e}")
        if not locales:
            return {"ok": False, "error": "No se pudo consultar SEC EDGAR y no hay histórico guardado de este valor.",
                    "ticker": ticker}
        # Con datos en disco no se devuelve un error: se sirve lo que hay y se
        # dice de dónde viene y qué falta. NO se cachea, para que la próxima
        # búsqueda vuelva a intentar EDGAR en vez de quedarse con la versión
        # incompleta durante una hora.
        from services.cartera_service import get_cartera_tickers
        transactions = _fusionar_transacciones(locales)
        return {
            "ok":           True,
            "ticker":       ticker,
            "transactions": transactions[:20],
            "n_locales":    len(locales),
            "buys":         len([t for t in transactions if t['type_code'] == 'P']),
            "sells":        len([t for t in transactions if t['type_code'] == 'S']),
            "en_cartera":   ticker.upper() in get_cartera_tickers(),
            "timestamp":    get_timestamp(),
            "source":       "Histórico guardado en la terminal — SEC EDGAR no respondió, puede faltar lo más reciente",
            "parcial":      True,
            # El aviso, en el formato que pinta el envoltorio compartido
            # (frontend/core/ui.js::panel). Antes esto se quedaba aquí: el
            # backend redactaba la advertencia y la pantalla no la leía nunca,
            # así que durante una caída de la SEC el usuario veía una tabla que
            # parecía completa Y con el subtítulo «SEC EDGAR Form 4» encima,
            # afirmando un origen que no era el suyo.
            "avisos": [{
                "tipo":    "parcial",
                "mensaje": "La SEC no respondió. Esto es el histórico ya guardado "
                           "en la terminal, así que puede faltar lo más reciente.",
            }],
        }

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
    """Varios directivos DISTINTOS del mismo valor comprando en el mismo
    periodo. Es la señal más fuerte del módulo: que uno compre puede ser
    cualquier cosa, que compren tres a la vez es mucho más difícil de
    explicar por casualidad.

    DOS FALLOS CORREGIDOS EL 04/08/2026, los dos convertían la señal en ruido:

    1. Contaba TRANSACCIONES, no personas. Una misma persona con dos líneas
       de compra aparecía como «2 insiders». Caso real que estaba en pantalla:
       XAIR salía como cluster con Goodman Robert Scott contado dos veces —
       el mismo documento listado bajo dos CIK (ver _accession). Ahora se
       cuentan nombres distintos, y las transacciones se reportan aparte.

    2. Leía del feed ya recortado a las 15 compras mayores, así que un
       cluster de tres compras modestas era invisible mientras una sola
       compra grande ocupaba sitio. Ahora lee la ventana completa.
    """
    from services.cache import cache
    cached = cache.get("insider:clusters")
    if cached: return cached

    try:
        # Ventana completa desde la base, no el top 15 del feed.
        rows = _read_transactions(FEED_WINDOW_DAYS)

        from collections import defaultdict
        ticker_buys = defaultdict(list)
        for t in rows:
            if t.get('type_code') == 'P' and t.get('ticker'):
                ticker_buys[t['ticker']].append(t)

        from services.cartera_service import get_cartera_tickers
        cartera_tickers = get_cartera_tickers()
        clusters = []
        for ticker, buys in ticker_buys.items():
            # Un cluster son PERSONAS, no operaciones.
            por_persona = defaultdict(list)
            for b in buys:
                nombre = (b.get('insider_name') or '').strip().upper()
                if nombre:
                    por_persona[nombre].append(b)
            n_personas = len(por_persona)
            if n_personas < 2:
                continue

            total_value  = sum(b.get('value', 0) for b in buys)
            total_shares = sum(b.get('shares', 0) for b in buys)
            insiders = [{
                "name":  ops[0].get('insider_name', ''),
                "title": next((o.get('title') for o in ops if o.get('title')), ''),
                "value": sum(o.get('value', 0) for o in ops),
                "n_ops": len(ops),
            } for ops in por_persona.values()]
            insiders.sort(key=lambda i: -i["value"])

            clusters.append({
                "ticker":       ticker,
                "company":      buys[0].get('company', ''),
                "n_insiders":   n_personas,
                "n_operaciones": len(buys),
                "total_value":  total_value,
                "total_shares": total_shares,
                "insiders":     insiders,
                "signal":       "FUERTE" if n_personas >= 3 else "MODERADA",
                "signal_color": "#00ffad" if n_personas >= 3 else "#ffb800",
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