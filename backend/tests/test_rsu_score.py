"""
Test de regresión para _compute_rsu_score() -- ver conversación
19/07/2026, continuación del trabajo de robustez empezado con Piotroski
el 18/07/2026.

3 casos, verificados contra la función real (no calculados a mano y
asumidos): empresa excelente con las 5 categorías presentes, empresa
débil con insiders vendiendo, y datos parciales para comprobar que el
reescalado cuando faltan categorías funciona bien.

Uso:
    cd backend
    python -m pytest tests/test_rsu_score.py -v
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.research_service import _compute_rsu_score  # noqa: E402


def test_rsu_score_empresa_excelente():
    """Las 5 categorías presentes, todas altas -> score alto, COMPRA FUERTE."""
    yf_data = {
        "profitability": {"revenue_growth": 0.30, "roe": 0.30, "net_margin": 0.25},
        "recommendations": {"strong_buy": 8, "buy": 1, "hold": 1, "sell": 0, "total": 10},
        "target_data": {"upside": 30, "mean": 200},
        "metrics": {"peg_ratio": 1.2},
    }
    piotroski = {"score": 8, "max": 9}
    sector_comparison = {"ok": True, "items": {
        "trailing_pe":   {"favorable": True},
        "forward_pe":    {"favorable": True},
        "ev_ebitda":     {"favorable": True},
        "peg_ratio":     {"favorable": True},
        "price_to_book": {"favorable": False},
    }}
    technical = {"market_phase": 2, "phase_label": "Fase 2 - Avance"}

    r = _compute_rsu_score(yf_data, piotroski, sector_comparison, None, technical)

    assert r["score"] == 94, f"Se esperaba score=94, salió {r['score']}. Breakdown: {r['breakdown']}"
    assert r["label"] == "COMPRA FUERTE"
    assert r["color"] == "#00ffad"
    assert len(r["breakdown"]) == 5, "Deberían aparecer las 5 categorías cuando todos los datos están presentes"


def test_rsu_score_empresa_debil_con_insiders_vendiendo():
    """Crecimiento negativo, Piotroski bajo, PEG alto (sin comparativa
    sectorial), consenso bajista, insiders vendiendo (penaliza -3 al
    sentimiento) y fase de declive -> score muy bajo, EVITAR."""
    yf_data = {
        "profitability": {"revenue_growth": -0.05, "roe": 0.03, "net_margin": -0.05},
        "recommendations": {"strong_buy": 1, "buy": 1, "hold": 3, "sell": 5, "total": 10},
        "target_data": {"upside": -10, "mean": 50},
        "metrics": {"peg_ratio": 3.5},
    }
    piotroski = {"score": 1, "max": 9}
    technical = {"market_phase": 4, "phase_label": "Fase 4 - Declive"}
    insider_summary = {"sentiment": "VENDEDOR"}

    r = _compute_rsu_score(yf_data, piotroski, None, insider_summary, technical)

    assert r["score"] == 2, f"Se esperaba score=2, salió {r['score']}. Breakdown: {r['breakdown']}"
    assert r["label"] == "EVITAR"
    assert r["color"] == "#f23645"

    # Sin comparativa sectorial, debe caer al fallback de valoración por PEG absoluto
    labels = [b["label"] for b in r["breakdown"]]
    assert "Valoración (PEG)" in labels, "Sin sector_comparison, debería usar el fallback de PEG, no 'Valoración vs Sector'"

    # El ajuste de insiders vendiendo debe reflejarse en el texto del desglose
    sentimiento = next(b for b in r["breakdown"] if b["label"] == "Sentimiento de Mercado")
    assert "Insiders vendiendo" in sentimiento["val"]


def test_rsu_score_datos_parciales_se_reescala():
    """Si faltan categorías enteras (sin Piotroski, sin comparativa
    sectorial ni PEG, sin analistas ni precio objetivo), el score se
    calcula solo sobre las categorías disponibles -- no debe penalizar
    por ausencia de datos, ni reventar."""
    yf_data = {
        "profitability": {"revenue_growth": 0.10, "roe": 0.10, "net_margin": 0.05},
        "recommendations": None,
        "target_data": {},
        "metrics": {},
    }
    technical = {"market_phase": 1, "phase_label": "Fase 1 - Base"}

    r = _compute_rsu_score(yf_data, None, None, None, technical)

    assert r["score"] == 57, f"Se esperaba score=57, salió {r['score']}. Breakdown: {r['breakdown']}"
    assert r["label"] == "NEUTRAL"
    assert len(r["breakdown"]) == 2, "Solo deberían aparecer las 2 categorías con datos reales (Fundamental y Técnica)"


def test_rsu_score_sentimiento_no_duplica_el_consenso_de_analistas():
    """buy_pct (recomendaciones) y upside (precio objetivo) salen del mismo
    pool de analistas -- antes del fix (roadmap 4.5, 26/07/2026) contaban
    como 2 votos separados en el promedio de "Sentimiento de Mercado",
    pesando el consenso de analistas el doble frente a eps_revisions (señal
    genuinamente distinta). Caso con fuerte discrepancia: analistas muy
    optimistas (100% buy) pero precio objetivo ya por debajo del actual
    (upside negativo) y estimaciones de EPS revisándose a la baja con
    fuerza. Antes del fix: (20+0+0)/3 = 6.67 -> round 7. Con el fix
    (consenso fusionado en 1 voto = 10, promediado con eps_revisions = 0):
    (10+0)/2 = 5 -> round 5."""
    yf_data = {
        "profitability": {},
        "recommendations": {"strong_buy": 8, "buy": 2, "hold": 0, "sell": 0, "total": 10},
        "target_data": {"upside": -20, "mean": 80},
        "metrics": {},
        "eps_revisions": {"net_pct": -60, "up_30d": 1, "down_30d": 9},
    }
    r = _compute_rsu_score(yf_data, None, None, None, None)
    sentimiento = next(b for b in r["breakdown"] if b["label"] == "Sentimiento de Mercado")
    assert sentimiento["pts"] == 5, f"Se esperaba pts=5 (consenso fusionado), salió {sentimiento['pts']}"


def test_rsu_score_sin_ningun_dato_no_revienta():
    """Caso extremo: absolutamente ningún dato disponible -> no debe
    lanzar una excepción, debe devolver score=0 de forma controlada."""
    r = _compute_rsu_score({}, None, None, None, None)

    assert r["score"] == 0
    assert r["breakdown"] == []