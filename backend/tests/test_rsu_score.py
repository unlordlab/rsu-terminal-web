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
    """Si faltan categorías enteras, el score se calcula solo sobre las
    disponibles -- no debe penalizar por ausencia de datos, ni reventar.

    ACTUALIZADO el 29/07/2026: este test usaba 2 categorías y esperaba 57.
    Sigue comprobando lo mismo (que el reescalado funciona), pero con 3, que
    es el mínimo a partir del cual se publica un score. Con menos ya no se
    publica -- no porque el reescalado falle, sino porque con una o dos
    lecturas deja de ser un score compuesto. Ver
    test_un_etf_con_solo_fase_tecnica_no_publica_score."""
    yf_data = {
        "profitability": {"revenue_growth": 0.10, "roe": 0.10, "net_margin": 0.05},
        "recommendations": None,
        "target_data": {},
        "metrics": {},
    }
    technical = {"market_phase": 1, "phase_label": "Fase 1 - Base"}
    piotroski = {"score": 6, "max": 9, "evaluables": 9}

    r = _compute_rsu_score(yf_data, piotroski, None, None, technical)

    assert len(r["breakdown"]) == 3, "Fundamental, Piotroski y Técnica"
    assert r["n_categorias"] == 3
    # 10 (fundamental) + 13 (piotroski, 6/9*20) + 13 (fase 1) = 36 / 3 / 20 * 100
    assert r["score"] == 60, f"Se esperaba score=60, salió {r['score']}. Breakdown: {r['breakdown']}"
    assert r["label"] == "NEUTRAL"


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
    """Caso extremo: absolutamente ningún dato disponible -> no debe lanzar
    una excepción.

    ACTUALIZADO el 29/07/2026: antes devolvía score=0, y eso era en sí una
    cifra fabricada -- un 0/100 se pinta en rojo como "EVITAR", que es un
    veredicto, cuando lo único cierto es que no hay datos. Ahora devuelve
    None, igual que cualquier otro caso por debajo del mínimo de categorías."""
    r = _compute_rsu_score({}, None, None, None, None)

    assert r["score"] is None
    assert r["label"] is None
    assert r["n_categorias"] == 0
    assert r["breakdown"] == []

# ── Mínimo de categorías para publicar un score (29/07/2026) ─────────────────
# El reescalado sobre las categorías disponibles es correcto, pero no se decía
# sobre CUÁNTAS se había medido: un 82 salido de una categoría se pintaba igual
# que uno salido de cinco. Y no era teórico -- los ETF no publican cuentas, así
# que no tienen fundamentales, ni Piotroski, ni consenso de analistas, y solo
# sobrevive la Fase Técnica:
#
#     SPY  100/100 COMPRA FUERTE   (1 de 5 categorías)
#     QQQ  100/100 COMPRA FUERTE   (1 de 5)
#     GLD    0/100 EVITAR          (1 de 5)
#
# SPY y QQQ están entre lo más tecleado de la terminal y el score es lo primero
# que se mira. Con una sola lectura no hay score compuesto: hay un indicador
# técnico disfrazado de veredicto.

from services.research_service import MIN_CATEGORIAS_RSU_SCORE  # noqa: E402

_TECNICO_SOLO = {"market_phase": 2, "phase_label": "Fase 2 - Avance"}


def test_un_etf_con_solo_fase_tecnica_no_publica_score():
    """Reproduce SPY/QQQ: sin fundamentales de ningún tipo."""
    r = _compute_rsu_score({"profitability": {}, "metrics": {}}, None, None, None, _TECNICO_SOLO)

    assert r["n_categorias"] == 1
    assert r["score"] is None, (
        f"Con 1 sola categoría no puede publicarse un score: salió {r['score']}."
    )
    assert r["label"] is None, "Tampoco un veredicto tipo COMPRA FUERTE."
    assert r["motivo"], "Hay que explicar por qué no se puede calcular."


def test_un_etf_en_fase_4_tampoco_publica_un_evitar():
    """El caso GLD: el sesgo va en los dos sentidos, no solo al alza."""
    r = _compute_rsu_score({"profitability": {}, "metrics": {}}, None, None, None,
                            {"market_phase": 4, "phase_label": "Fase 4 - Declive"})
    assert r["score"] is None and r["label"] is None


def test_el_breakdown_se_sigue_mostrando_aunque_no_haya_score():
    """Lo que sí se ha podido medir se enseña igual: no publicar un total no
    es lo mismo que ocultar el dato."""
    r = _compute_rsu_score({"profitability": {}, "metrics": {}}, None, None, None, _TECNICO_SOLO)
    assert len(r["breakdown"]) == 1
    assert r["breakdown"][0]["label"] == "Fase Técnica"


def test_con_el_minimo_de_categorias_si_se_publica():
    """Justo en el umbral: 3 de 5."""
    yf_data = {
        # Sin peg_ratio a propósito: con él aparecería también la categoría de
        # Valoración y serían 4, no las 3 justas que este test quiere probar.
        "profitability": {"revenue_growth": 0.30, "roe": 0.30, "net_margin": 0.25},
        "metrics": {},
    }
    r = _compute_rsu_score(yf_data, {"score": 8, "max": 9, "evaluables": 9}, None, None, _TECNICO_SOLO)
    assert r["n_categorias"] == MIN_CATEGORIAS_RSU_SCORE
    assert r["score"] is not None and r["label"] is not None


def test_el_score_declara_siempre_sobre_cuantas_categorias_se_midio():
    """Un score de 3 categorías y uno de 5 no son comparables, y hasta ahora
    se veían idénticos."""
    yf_data = {
        "profitability": {"revenue_growth": 0.30, "roe": 0.30, "net_margin": 0.25},
        "recommendations": {"strong_buy": 8, "buy": 1, "hold": 1, "sell": 0, "total": 10},
        "target_data": {"upside": 30, "mean": 200},
        "metrics": {"peg_ratio": 1.2},
    }
    sector = {"ok": True, "items": {"trailing_pe": {"favorable": True}}}
    r = _compute_rsu_score(yf_data, {"score": 8, "max": 9, "evaluables": 9}, sector, None, _TECNICO_SOLO)
    assert r["n_categorias"] == 5
    assert r["min_categorias"] == MIN_CATEGORIAS_RSU_SCORE


def test_lo_que_no_se_publica_tampoco_contamina_el_track_record():
    """La pregunta que el historial existe para responder -- '¿un 90 le gana a
    un 40?' -- no tiene sentido si en la muestra hay SPY con un 100 salido de
    un único indicador técnico."""
    from unittest.mock import patch
    import services.rsu_score_tracking_service as tracking

    sin_score = _compute_rsu_score({"profitability": {}, "metrics": {}}, None, None, None, _TECNICO_SOLO)
    escrituras = {"n": 0}

    class _ConnFalsa:
        def execute(self, *a, **k): escrituras["n"] += 1
        def commit(self): pass
        def close(self): pass

    with patch.object(tracking, "_conn", lambda: _ConnFalsa()):
        tracking.registrar_score("SPY", sin_score, 640.0)

    assert escrituras["n"] == 0, (
        "Un score que la ficha no publica no puede acabar en el historial."
    )
