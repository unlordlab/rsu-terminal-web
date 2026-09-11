"""
Research: el panel de niveles técnicos, más sencillo y sin datos a medias.

EL CASO, 11/09/2026, auditando OSS con el usuario. Los números del panel eran
correctos (validados con datos reales), pero:

  · la «Tendencia» repetía la fase con otras palabras; ahora es la de medio
    plazo (la media de 50 sesiones), con su motivo en una frase;
  · la media que decide la fase, la de 30 semanas, no salía en ningún sitio;
  · SMA y EMA daban casi los mismos números en dos columnas, y «✗ Bajo SMA50»
    repetía la tabla: ahora una sola tabla de medias;
  · el short interest no decía de cuándo era (el dato del 31/08 salía sin
    fecha y con un «del float ·» colgando) ni si subía;
  · la fecha de resultados era una estimación (Finnhub 03/11, Yahoo 04/11
    marcada como estimada) y se enseñaba como segura;
  · los dos tooltips describían un método que no se usa desde julio.

Verificado en el navegador con el research.js real y datos reales de OSS,
NVDA y MTD (el caso en que la fase diaria y la semanal no coinciden), también
en ancho de móvil.

Uso:
    cd backend
    python -m pytest tests/test_research_panel_tecnico.py -v
"""
import io
import os
import re

from services import research_service as R

RAIZ = os.path.join(os.path.dirname(__file__), "..", "..")
RESEARCH_JS = io.open(os.path.join(RAIZ, "frontend", "pages", "research.js"), encoding="utf-8").read()
TOOLTIP_JS = io.open(os.path.join(RAIZ, "frontend", "components", "tooltip.js"), encoding="utf-8").read()


def _bloque(js, inicio, fin):
    return js[js.index(inicio):js.index(fin)]


PANEL = _bloque(RESEARCH_JS, "function technicalSection(data)", "function squeezeGauge(s)")


# ── La tendencia de medio plazo ──────────────────────────────────────────────

def test_tendencia_bajista_como_OSS():
    t = R.tendencia_medio_plazo(8.91, 10.75, 12.13, 11.16, "bajista")
    assert t["direccion"] == "BAJISTA"
    assert t["motivo"] == "Por debajo de su media de 50 sesiones, que baja, y también de las de 20 y 200"


def test_tendencia_alcista():
    t = R.tendencia_medio_plazo(218.36, 219.87, 214.56, 198.26, "alcista")
    assert t["direccion"] == "ALCISTA"
    assert t["motivo"] == "Por encima de su media de 50 sesiones, que sube, y también de la de 200"


def test_con_la_media_plana_es_lateral():
    assert R.tendencia_medio_plazo(100, 101, 102, 98, "plana")["direccion"] == "LATERAL"


def test_cruzar_la_media_contra_su_pendiente_es_lateral():
    """Por encima de una media que baja: todavía no hay tendencia alcista."""
    assert R.tendencia_medio_plazo(105, 103, 100, 110, "bajista")["direccion"] == "LATERAL"


def test_sin_media_de_200_no_se_rompe():
    t = R.tendencia_medio_plazo(90, 95, 100, None, "bajista")
    assert t["direccion"] == "BAJISTA" and "200" not in t["motivo"]


# ── Short interest con fecha y evolución, resultados marcados si son estimados ─

def test_el_short_interest_dice_de_cuando_es_y_si_sube(monkeypatch):
    monkeypatch.setattr(R, "_info_de", lambda t: {
        "shortPercentOfFloat": 0.1913, "sharesShort": 4643236, "shortRatio": 5.01,
        "dateShortInterest": 1788134400, "sharesShortPriorMonth": 4146746})
    s = R._get_short_interest("OSS")
    assert s["date"] == "2026-08-31"
    assert s["cambio_previo_pct"] == 12.0


def test_sin_fecha_no_se_inventa(monkeypatch):
    monkeypatch.setattr(R, "_info_de", lambda t: {"shortPercentOfFloat": 0.05, "sharesShort": 1000})
    s = R._get_short_interest("X")
    assert s["date"] is None and s["cambio_previo_pct"] is None


def test_una_fecha_que_yahoo_marca_como_estimada_lo_es(monkeypatch):
    monkeypatch.setattr(R, "_info_de", lambda t: {"isEarningsDateEstimate": True})
    assert R._earnings_estimada("OSS", "2026-11-03") is True


def test_si_las_dos_fuentes_no_coinciden_es_estimada(monkeypatch):
    # 04/11/2026 12:30 UTC en Yahoo, 03/11 en Finnhub
    monkeypatch.setattr(R, "_info_de", lambda t: {"isEarningsDateEstimate": False, "earningsTimestampStart": 1793795400})
    assert R._earnings_estimada("OSS", "2026-11-03") is True
    assert R._earnings_estimada("OSS", "2026-11-04") is False


# ── El panel ─────────────────────────────────────────────────────────────────

def test_el_panel_ensena_la_media_que_decide_la_fase():
    assert "['30 semanas',   t.sma150, 'la que decide la fase']" in PANEL


def test_ya_no_repite_lo_mismo_dos_veces():
    codigo = "\n".join(l for l in RESEARCH_JS.splitlines() if not l.strip().startswith("//"))
    for viejo in ("SMA (CLÁSICAS)", "EMAs · PENDIENTE", "Bajo SMA50", "techRow(", "emaRow(", "FASE SEMANAL (CONFIRMACIÓN)"):
        assert viejo not in codigo, viejo


def test_la_fase_principal_es_la_semanal_y_la_diaria_solo_si_difiere():
    fase = _bloque(RESEARCH_JS, "function tarjetaFase(t)", "function tarjetaFuerza(rs)")
    assert "const fase    = semanal ? t.phase_weekly : t.market_phase;" in fase
    assert "t.market_phase !== t.phase_weekly" in fase and "'En diario: '" in fase


def test_lo_que_viene_de_fuera_se_escapa():
    """El nombre del sector y de la industria vienen de Yahoo; antes se
    pintaban tal cual."""
    assert "esc(rs.benchmark_label" in PANEL and "esc(td.motivo)" in PANEL and "esc(s.date" not in PANEL
    assert "esc(fmtFecha(s.date))" in PANEL


def test_la_fecha_estimada_se_dice():
    assert "ne.estimada" in PANEL and "Fecha estimada" in PANEL


# ── Los tooltips describen el método de verdad ───────────────────────────────

def _tooltip(clave):
    i = TOOLTIP_JS.index(f'    "{clave}": {{')
    return TOOLTIP_JS[i:TOOLTIP_JS.index("\n    },", i)]


def test_el_tooltip_de_tendencia_no_describe_el_metodo_viejo():
    t = _tooltip("asset-trend")
    assert "5 condiciones" not in t and "EMA20 por encima de la EMA50" not in t
    assert "media de las últimas 50 sesiones" in t


def test_el_tooltip_de_fase_explica_la_regla_actual_y_lo_que_no_es():
    t = _tooltip("market-phase")
    assert "posición respecto a la EMA200" not in t and "EMAs ordenadas" not in t
    assert "30 semanas" in t and "ruptura reciente" in t and "recorrido del último año" in t
    assert "no dice lo que va a hacer" in t
    assert not re.search(r"sesi[oó]n \d|hallazgo", t, re.I), "los tooltips son para el usuario final"
