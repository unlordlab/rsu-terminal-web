"""
La bolsa de verificación de Watchlist: de 19 hallazgos sin comprobar, tres bugs vivos.

EL CASO, 10/09/2026. Se contrastó cada hallazgo de la auditoría del 21/07 con
el código actual. Nueve ya estaban bien; tres «ya hechos» tenían un fallo real:

  #3  RVOL. La normalización por hora era una RECTA, y la apertura concentra
      mucho más volumen del que una recta supone. Medido con datos de 1 minuto
      de Yahoo en 33 días NORMALES (RVOL final 0,7-1,3): la alerta de «RVOL ≥
      2» saltaba el 61% de las mañanas a las 9:35 y el 30% a las 10:00. Con la
      curva real, medida en OTROS 36 valores, el 0%. Y en festivo entre semana
      calculaba la fracción de una sesión que no existía.

  #2  TOQUE DE EMA. El arreglo del 25/07 SUSTITUYÓ la proximidad por el cruce,
      cuando la auditoría proponía las dos: un rebote que roza la EMA sin
      cruzarla —el toque de soporte clásico— dejó de avisar en una alerta que
      se sigue llamando «Toque de EMA».

  #4  XSS. El ticker del usuario ya se valida, pero `esc()` no escapaba
      comillas, y Congreso e Insider meten datos de TERCEROS en atributos y en
      `onclick`: un repositorio público de GitHub y el texto libre de los Form 4
      de la SEC (en la base real: «GEF, GEF-B», «MOGA/MOGB»).

Uso:
    cd backend
    python -m pytest tests/test_watchlist_bolsa_1009.py -v
"""
import io
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
import pytest

RAIZ = os.path.join(os.path.dirname(__file__), "..", "..")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(RAIZ, "shared"))
sys.path.insert(0, os.path.join(RAIZ, "scripts"))

import time_utils as TU  # noqa: E402
from tickers import normalizar_ticker, url_segura  # noqa: E402

ET = ZoneInfo("America/New_York")


def _et(y, m, d, hh, mm):
    return datetime(y, m, d, hh, mm, tzinfo=ET)


# ── #3: la curva real del volumen ────────────────────────────────────────────

def test_a_las_935_la_curva_espera_el_volumen_REAL_no_el_de_la_recta():
    """EL test. La recta suponía 1,3% a las 9:35; medido, es ~7%. Con la recta
    un día normal leía RVOL 2,3 y la alerta saltaba en falso."""
    f = TU.fraccion_de_volumen_esperada(_et(2026, 9, 9, 9, 35))
    assert 0.05 < f < 0.09, f
    recta = 5 / 390
    assert f > 4 * recta, "la curva ha vuelto a parecerse a la recta"


def test_la_subasta_de_apertura_ya_cuenta_desde_el_primer_segundo():
    """A las 9:30:00 se imprime la subasta: ese ~4% está desde el principio.
    Con un suelo de 0,02 se dividía por la mitad de lo real."""
    assert TU.fraccion_de_volumen_esperada(_et(2026, 9, 9, 9, 30)) == pytest.approx(0.0408)


def test_la_curva_crece_siempre_y_termina_en_el_dia_entero():
    anterior = 0
    for minuto in range(0, 390, 7):
        f = TU.fraccion_de_volumen_esperada(_et(2026, 9, 9, 9, 30) + timedelta(minutes=minuto))
        assert f >= anterior, f"baja en el minuto {minuto}"
        anterior = f
    assert TU.fraccion_de_volumen_esperada(_et(2026, 9, 9, 15, 59)) > 0.9


def test_a_las_10_espera_el_16_por_ciento_no_el_7_7_de_la_recta():
    """La clave 31 de la tabla es el FINAL del minuto 31 (10:01): a las 10:00
    en punto se interpola entre 9:56 y 10:01. Mi primera versión de este test
    esperaba el valor de las 10:01."""
    assert TU.fraccion_de_volumen_esperada(_et(2026, 9, 9, 10, 0)) == pytest.approx(0.1632, abs=0.001)


@pytest.mark.parametrize("cuando", [
    _et(2026, 9, 9, 9, 29),    # antes de abrir
    _et(2026, 9, 9, 16, 0),    # cerrado
    _et(2026, 9, 12, 12, 0),   # sábado
    _et(2026, 9, 7, 12, 0),    # Labor Day, lunes festivo
])
def test_sin_sesion_no_hay_fraccion(cuando):
    """Sin sesión «hoy» ya es un día entero. El festivo es el que faltaba: en
    Labor Day a mediodía la alerta dividía el volumen entero del viernes por
    0,38 y leía 2,6 veces lo normal."""
    assert TU.fraccion_de_volumen_esperada(cuando) is None


def test_la_recta_de_Reddit_tambien_respeta_los_festivos(monkeypatch):
    """`session_fraction_elapsed()` la sigue usando Reddit Pulse, que no tiene
    por qué seguir la curva de la bolsa. Pero su propio contrato dice None con
    el mercado cerrado, y un festivo lo es."""
    class _Reloj(datetime):
        @classmethod
        def now(cls, tz=None):
            return _et(2026, 9, 7, 12, 0)
    monkeypatch.setattr(TU, "datetime", _Reloj)
    assert TU.session_fraction_elapsed() is None


# ── #3: la alerta de RVOL ────────────────────────────────────────────────────

def _hist(ultimo_dia, vol_hoy, vol_normal=1_000_000):
    # La ULTIMA barra es la del día que pide la llamada, sea o no laborable.
    # `bdate_range` sola la dejaba en el viernes cuando el test se ejecutaba un
    # sábado, y entonces `_fetch_rvol_single` veía que la última barra no era la
    # de hoy y devolvía None: el test fallaba por el día en que se corriera, no
    # por el código (visto el 12/09/2026 auditando el briefing, con la suite
    # entera verde salvo este).
    dias = pd.bdate_range(end=ultimo_dia, periods=25, tz=ET)
    dias = dias[:-1].append(pd.DatetimeIndex([pd.Timestamp(ultimo_dia, tz=ET)]))
    vols = [vol_normal] * 24 + [vol_hoy]
    return pd.DataFrame({"Close": [1.0] * 25, "Volume": vols}, index=dias)


@pytest.fixture
def W(monkeypatch):
    import services.watchlist_service as W
    W._rvol_cache.clear()
    return W


def _yahoo(monkeypatch, W, hist):
    import yfinance as yf

    class T:
        def __init__(self, s):
            pass

        def history(self, **k):
            return hist
    monkeypatch.setattr(yf, "Ticker", T)


def test_la_alerta_usa_LA_CURVA_y_no_la_recta(monkeypatch, W):
    """Los tests de abajo sustituyen `_fraccion_volumen` por un número fijo, así
    que ninguno notaba si la alerta volvía a importar la recta: el sabotaje se
    escapó. Aquí se para el reloj a las 9:35 de un día de sesión y se llama a
    la función QUE USA LA ALERTA."""
    class _Reloj(datetime):
        @classmethod
        def now(cls, tz=None):
            return _et(2026, 9, 9, 9, 35)
    monkeypatch.setattr(TU, "datetime", _Reloj)
    f = W._fraccion_volumen()
    assert f == pytest.approx(TU.fraccion_de_volumen_esperada(_et(2026, 9, 9, 9, 35)))
    assert f > 4 * (5 / 390), f"la alerta usa la recta ({f:.4f}), no la curva"


def test_un_dia_NORMAL_a_las_935_ya_no_lee_RVOL_2(monkeypatch, W):
    """El caso medido: a las 9:35 un día normal lleva ~7% del volumen. Con la
    recta eso eran RVOL 5,4; con la curva, ~1."""
    hoy = datetime.now(ET).date()
    _yahoo(monkeypatch, W, _hist(hoy, 70_000))
    monkeypatch.setattr(W, "_fraccion_volumen", lambda: 0.07)
    rv = W._fetch_rvol_single("AAPL")
    assert rv == pytest.approx(1.0, abs=0.05)


def test_en_sesion_SIN_la_barra_de_hoy_no_hay_lectura(monkeypatch, W):
    """Si Yahoo aún no trae la barra de hoy, la última es la de ayer COMPLETA.
    Dividirla por el 4% de las 9:31 daría un RVOL de 25 y una alerta falsa."""
    ayer = datetime.now(ET).date() - timedelta(days=1)
    _yahoo(monkeypatch, W, _hist(ayer, 1_000_000))
    monkeypatch.setattr(W, "_fraccion_volumen", lambda: 0.04)
    assert W._fetch_rvol_single("AAPL") is None


def test_con_el_mercado_cerrado_se_lee_el_dia_entero(monkeypatch, W):
    ayer = datetime.now(ET).date() - timedelta(days=1)
    _yahoo(monkeypatch, W, _hist(ayer, 2_000_000))
    monkeypatch.setattr(W, "_fraccion_volumen", lambda: None)
    assert W._fetch_rvol_single("AAPL") == pytest.approx(2.0)


# ── #2: el toque de EMA ──────────────────────────────────────────────────────

@pytest.fixture
def alertas(monkeypatch, W):
    """Una base de alertas temporal, con una alerta de EMA50 ya ARMADA."""
    tmp = os.path.join(tempfile.mkdtemp(), "users.db")
    monkeypatch.setattr(W, "DB_PATH", tmp)
    W.init_db()

    def crear(last_side):
        c = sqlite3.connect(tmp)
        c.execute("INSERT INTO alerts (user_id, ticker, condition, target_price, status, created_at, "
                  "seen, metric, ema_period, recurring, last_side) VALUES "
                  "(1, 'AAPL', 'touch', 50, 'active', ?, 1, 'ema_touch', 50, 1, ?)",
                  (datetime.now().isoformat(), last_side))
        c.commit()
        c.close()

    def pasada(precio, ema=100.0):
        monkeypatch.setattr("services.cartera_service.fetch_live_prices",
                            lambda ts: {t: {"price": precio} for t in ts})
        monkeypatch.setattr(W, "_get_live_ema", lambda t, p, lp: ema)
        return W.check_all_active_alerts()
    return crear, pasada


def test_un_REBOTE_que_roza_la_EMA_sin_cruzarla_AVISA(alertas):
    """EL test del #2. Viene de arriba, baja al 0,2% de la EMA y no la cruza.
    Desde el 25/07 esto no avisaba en una alerta llamada «Toque de EMA»."""
    crear, pasada = alertas
    crear("above")
    assert len(pasada(100.2)) == 1


def test_el_CRUCE_rapido_sigue_avisando(alertas):
    """Lo que arregló el 25/07 no se puede perder: de un lado al otro entre dos
    pasadas, aunque ninguna caiga dentro de la banda."""
    crear, pasada = alertas
    crear("above")
    assert len(pasada(98.0)) == 1


def test_lejos_y_del_mismo_lado_NO_avisa(alertas):
    crear, pasada = alertas
    crear("above")
    assert pasada(103.0) == []


def test_la_primera_pasada_solo_ARMA_aunque_este_en_la_banda(alertas):
    """Recién creada (o rearmada tras el enfriamiento de 24 h) solo se apunta
    el lado. Si ya estaba pegada a la EMA, avisa en la pasada siguiente."""
    crear, pasada = alertas
    crear(None)
    assert pasada(100.1) == []
    assert len(pasada(100.1)) == 1


def test_la_banda_es_la_de_antes_del_25_07():
    import services.watchlist_service as W
    assert W.EMA_TOUCH_TOLERANCE_PCT == 0.5


# ── #4: datos de terceros ────────────────────────────────────────────────────

@pytest.mark.parametrize("crudo,esperado", [
    ("AAPL", "AAPL"), ("brk.b", "BRK.B"), ("^GSPC", "^GSPC"),
    ("GEF, GEF-B", "GEF"),              # en la base real de Insider
    ("MOGA/MOGB", "MOGA"),              # en la base real de Insider
    ("X');alert(1)//", None),           # lo que rompería el onclick
    ('A" onmouseover="x', None),
    ("", None), (None, None),
    ("N/A", None), ("n/a", None), ("NONE", None), ("N.A.", None),   # «N/A» daba «N»: OTRA empresa
    ("F", "F"), ("T", "T"),             # los de una letra reales siguen valiendo
])
def test_normalizar_ticker(crudo, esperado):
    assert normalizar_ticker(crudo) == esperado


@pytest.mark.parametrize("url,ok", [
    ("https://efdsearch.senate.gov/x.pdf", True), ("http://clerk.house.gov/a", True),
    ("javascript:alert(1)", False), ("JaVaScRiPt:alert(1)", False),
    ("data:text/html,<script>", False), ("", False), (None, False),
])
def test_url_segura(url, ok):
    assert (url_segura(url) is not None) == ok


def test_congreso_no_publica_un_ticker_ni_una_url_envenenados(monkeypatch):
    """El dataset es un repositorio público de terceros. Se ejecuta el escaneo
    entero contra un dataset falso con los dos venenos."""
    import congress_scan as C
    hoy = datetime.now().strftime("%Y-%m-%d")
    base = {"transaction_type": "Purchase", "transaction_date": hoy, "filer_name": "X",
            "chamber": "senate", "amount_range_low": 1000}
    dataset = [dict(base, ticker="AAPL", doc_url="https://efdsearch.senate.gov/a.pdf"),
               dict(base, ticker="X');alert(1)//", doc_url="https://ok.gov/b"),
               dict(base, ticker="MSFT", doc_url="javascript:alert(document.domain)")]

    class R:
        def raise_for_status(self):
            pass

        def json(self):
            return dataset
    monkeypatch.setattr(C.requests, "get", lambda *a, **k: R())
    trades = C.run_scan()["trades"]
    assert sorted(t["ticker"] for t in trades) == ["AAPL", "MSFT"], "entró el ticker envenenado"
    urls = {t["ticker"]: t["doc_url"] for t in trades}
    assert urls["AAPL"].startswith("https://")
    assert urls["MSFT"] is None, "la URL javascript: ha llegado al Gist"


def test_insider_normaliza_lo_YA_guardado(monkeypatch):
    """La validación en la ingesta no limpia la base: «GEF, GEF-B» ya está en
    la real. Se normaliza también al leer."""
    import services.insider_service as I
    tmp = os.path.join(tempfile.mkdtemp(), "insider.db")
    monkeypatch.setattr(I, "DB_PATH", tmp)
    I.init_db()
    c = sqlite3.connect(tmp)
    hoy = datetime.now().strftime("%Y-%m-%d")
    for i, t in enumerate(["GEF, GEF-B", "X');alert(1)//", "NVDA"]):
        c.execute("INSERT INTO insider_tx (dedup_key, ticker, company, insider_name, title, is_director, "
                  "is_officer, type, type_code, shares, price, value, tx_date, filing_url, ingested_at) "
                  "VALUES (?,?,?,?,?,0,1,'COMPRA','P',1,1,60000,?,'u',?)",
                  (f"k{i}", t, "C", "N", "CEO", hoy, datetime.now().isoformat()))
    c.commit()
    c.close()
    tickers = sorted(f["ticker"] for f in I._read_transactions())
    assert tickers == ["", "GEF", "NVDA"], tickers


def test_insider_normaliza_al_INGERIR(monkeypatch):
    """Se ejecuta el parser de verdad con un Form 4 cuyo símbolo trae dos
    clases escritas a mano, como en la base real."""
    import services.insider_service as I
    xml = ("<ownershipDocument><issuer><issuerTradingSymbol>GEF, GEF-B</issuerTradingSymbol>"
           "<issuerName>Greif</issuerName></issuer><reportingOwner><reportingOwnerId>"
           "<rptOwnerName>A B</rptOwnerName></reportingOwnerId><reportingOwnerRelationship>"
           "<isOfficer>1</isOfficer></reportingOwnerRelationship></reportingOwner>"
           "</ownershipDocument>")

    class R:
        status_code = 200
        text = xml
        content = xml.encode()
    monkeypatch.setattr(I, "_sec_get", lambda *a, **k: R())
    assert I._parse_form4("https://www.sec.gov/x.xml")["ticker"] == "GEF"


def test_congreso_ya_no_mete_la_URL_cruda_en_el_href():
    """Defensa en la pantalla además del origen: `safeUrl()` en el enlace."""
    js = io.open(os.path.join(RAIZ, "frontend", "pages", "congress.js"), encoding="utf-8").read()
    linea = next(l for l in js.splitlines() if "doc_url" in l and "href" in l)
    assert "esc(safeUrl(t.doc_url))" in linea
    assert "esc(t.doc_url)" not in linea


# ── esc(): se EJECUTA la función real ────────────────────────────────────────

def _esc_de_ui_js():
    """El cuerpo REAL de `esc` en ui.js, no una copia: si alguien lo cambia,
    esto ejecuta lo cambiado."""
    js = io.open(os.path.join(RAIZ, "frontend", "core", "ui.js"), encoding="utf-8").read()
    m = re.search(r"export function esc\(str\) \{\n(.*?)\n\}\n", js, re.S)
    assert m, "no se encuentra `export function esc(str)` en ui.js"
    return "function esc(str) {\n" + m.group(1) + "\n}"


@pytest.mark.skipif(shutil.which("node") is None, reason="sin Node (en CI sí lo hay)")
def test_esc_escapa_las_COMILLAS_ejecutandolo():
    """EL test de seguridad. Una comilla doble sin escapar dentro de
    `title="…"` o `href="…"` cierra el atributo y deja escribir otro."""
    casos = ['A" onmouseover="alert(1)', "B'x", "<i>&</i>", "normal"]
    prog = _esc_de_ui_js() + "\nconsole.log(JSON.stringify(" + json.dumps(casos) + ".map(esc)));"
    out = subprocess.run(["node", "-e", prog], capture_output=True, text=True, timeout=30)
    assert out.returncode == 0, out.stderr
    r = json.loads(out.stdout)
    assert r[0] == "A&quot; onmouseover=&quot;alert(1)"
    assert r[1] == "B&#39;x"
    assert r[2] == "&lt;i&gt;&amp;&lt;/i&gt;"
    assert r[3] == "normal"
    assert all('"' not in x and "'" not in x for x in r)
