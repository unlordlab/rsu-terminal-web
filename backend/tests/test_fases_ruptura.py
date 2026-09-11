"""
Fases Weinstein: la ruptura cuenta, y un valor que cae no «acumula».

EL CASO, 11/09/2026, auditando OSS en Research. Un 57% por debajo de su
máximo, un 27% por debajo de su media de 30 semanas y con todas las medias
bajando, salía «Tendencia RANGO · Fase 1 · Acumulación», en diario y en
semanal. Dos fallos que se sumaban (ver la cabecera de
shared/weinstein_phases.py):

  1. Solo había Fase 4 con la media de 30 semanas ya bajando, y tras una
     subida fuerte esa media sigue plana semanas después del desplome.
  2. Fase 1 o 3 se decidía por el precio de hace 6 meses: OSS era Fase 3
     hasta el 03/09 y pasó a Fase 1 al caer por debajo del precio de marzo.
     Cuanto más caía, más «acumulación».

Medido en el S&P 500 ese día: de 87 valores en Fase 1, 36 caían como OSS. La
implementación se comprobó contra la medición (200 de 200 fechas iguales), y
OSS sale ahora Fase 4 en diario y semanal desde el 20/08.

Uso:
    cd backend
    python -m pytest tests/test_fases_ruptura.py -v
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "shared"))

from weinstein_phases import (  # noqa: E402
    BANDA_RUPTURA, classify_phase, classify_phase_debounced, classify_phase_weekly,
)


def _serie(*tramos):
    """Tramos (desde, hasta, sesiones) encadenados en una serie diaria."""
    valores = np.concatenate([np.linspace(a, b, n) for a, b, n in tramos])
    return pd.Series(valores, index=pd.bdate_range("2022-01-03", periods=len(valores)))


# La forma de OSS: sube, se estanca y cae un 25% por debajo de una media de
# 30 semanas que, por venir de subir, todavía está plana.
IDA_Y_VUELTA = _serie((100, 100, 100), (100, 200, 150), (200, 190, 60), (190, 140, 30))


def test_la_serie_tiene_la_forma_de_OSS():
    """Si la media ya estuviera bajando, el test de abajo pasaría por la
    regla de siempre y no probaría nada."""
    sma = IDA_Y_VUELTA.rolling(150).mean()
    assert abs(sma.iloc[-1] / sma.iloc[-16] - 1) < 0.004, "la media de 30 semanas tiene que estar plana"
    assert IDA_Y_VUELTA.iloc[-1] < sma.iloc[-1] * (1 - BANDA_RUPTURA)


def test_un_desplome_bajo_la_media_de_30_semanas_es_fase_4():
    """EL test. La media aún no ha girado (viene de subir), pero el precio ha
    roto muy por debajo con la de medio plazo bajando."""
    r = classify_phase(IDA_Y_VUELTA)
    assert r["phase"] == 4 and r["trend"] == "BAJISTA", r
    assert "ruptura reciente" in r["phase_label"]


def test_y_lo_mismo_en_semanal():
    r = classify_phase_weekly(IDA_Y_VUELTA)
    assert r["phase"] == 4 and r["trend"] == "BAJISTA", r


def test_cuanto_mas_cae_NO_se_vuelve_acumulacion():
    """El salto de OSS: con la regla vieja, la fase pasaba a 1 en cuanto el
    precio perdía el de hace 6 meses. Durante toda la caída, ni un día en
    Fase 1."""
    fases = {classify_phase(IDA_Y_VUELTA.iloc[:k])["phase"] for k in range(270, len(IDA_Y_VUELTA) + 1)}
    assert 1 not in fases, fases


def test_una_caida_confirmada_no_aparece_sin_confirmar():
    r = classify_phase_debounced(IDA_Y_VUELTA)
    assert r["phase"] == 4 and r["phase_confirmed"] is True, r


def test_una_base_larga_despues_de_caer_es_fase_1():
    """El caso de verdad de acumulación: cae y luego se queda lateral el
    tiempo suficiente para que la media de 30 semanas se aplane."""
    r = classify_phase(_serie((200, 100, 150), (100, 100, 220)))
    assert r["phase"] == 1 and r["trend"] == "RANGO", r


def test_un_techo_largo_despues_de_subir_es_fase_3():
    """Lateral en lo alto durante meses, con la media ya plana. Salía
    «Acumulación» con la regla vieja (precio igual que hace 6 meses) y con la
    primera versión de esta (la media no se había movido en 3 meses)."""
    # 260: la media lleva más de 3 meses sin moverse, que es donde fallaba
    # medir «cuánto se movió la media»: decía 0% y salía Fase 1.
    for plano in (170, 200, 260):
        r = classify_phase(_serie((100, 200, 200), (200, 200, plano)))
        assert r["phase"] == 3 and r["trend"] == "RANGO", (plano, r)


def test_salir_de_una_base_por_arriba_es_fase_2():
    """Con la media de 30 semanas todavía plana, o incluso bajando: solo la
    ruptura puede decir Fase 2 (la regla de siempre no llega)."""
    for serie in (_serie((150, 100, 150), (100, 100, 100), (100, 115, 20)),
                  _serie((200, 100, 150), (100, 100, 80), (100, 118, 20))):
        r = classify_phase(serie)
        assert r["phase"] == 2 and r["trend"] == "ALCISTA", r
        assert "ruptura reciente" in r["phase_label"], r


def test_oscilar_pegado_a_la_media_no_es_ruptura():
    """Dentro de la banda no hay ruptura: una base que respira no salta a
    Fase 4 por bajar un 3%, aunque la media de 50 sesiones ya baje."""
    serie = _serie((200, 100, 150), (100, 100, 200), (100, 96.5, 30))
    e50 = serie.ewm(span=50, adjust=False).mean()
    assert e50.iloc[-1] < e50.iloc[-11] * 0.994, "la de medio plazo tiene que estar bajando"
    assert classify_phase(serie)["phase"] == 1


def test_un_solo_dia_de_caida_no_es_una_ruptura():
    """Un 8% por debajo de la media en un día, pero la de medio plazo aún no
    se ha movido: no hay ruptura confirmada."""
    serie = _serie((200, 100, 150), (100, 100, 220))
    serie.iloc[-1] = 92
    assert serie.iloc[-1] < serie.rolling(150).mean().iloc[-1] * (1 - BANDA_RUPTURA)
    assert classify_phase(serie)["phase"] == 1


def test_una_correccion_sobre_la_media_sigue_siendo_fase_2_pero_lo_dice():
    """Weinstein: por encima de una media de 30 semanas que sube, la fase no
    cambia aunque corrija. OSS el 16/07, un 40% por debajo del máximo, salía
    «Avance» a secas; ahora la etiqueta avisa. El número no cambia."""
    serie = _serie((50, 200, 260), (200, 175, 15))
    assert serie.iloc[-1] > serie.rolling(150).mean().iloc[-1], "tiene que seguir por encima de la media"
    r = classify_phase(serie)
    assert r["phase"] == 2, r
    assert "en corrección" in r["phase_label"], r


def test_la_tendencia_sigue_a_la_fase():
    """Scanner guarda `trend` con este mismo significado."""
    for serie, esperada in ((IDA_Y_VUELTA, "BAJISTA"), (_serie((200, 100, 150), (100, 100, 220)), "RANGO")):
        assert classify_phase(serie)["trend"] == esperada


# ── El cambio de regla no se anuncia como movimiento del mercado ─────────────
#
# El Scanner compara la fase de hoy con la de hace unas sesiones para decir
# quién ha ENTRADO en Fase 2. La primera noche con la regla nueva, unos 14
# valores del S&P 500 habrían «entrado» sin moverse: solo cambió la fórmula.
# Cada fila guarda ahora qué regla la calculó, y solo se comparan iguales.

import io  # noqa: E402
from datetime import date, timedelta  # noqa: E402

import pytest  # noqa: E402

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import services.snapshots_service as S  # noqa: E402
from weinstein_phases import REGLA_FASES  # noqa: E402


@pytest.fixture
def db(tmp_path, monkeypatch):
    monkeypatch.setattr(S, "DB_PATH", str(tmp_path / "snapshots.db"))
    S.init_db()


def _sembrar(filas):
    """filas: [(dias_atras, ticker, fase, regla)]"""
    conn = S._conn()
    for atras, ticker, fase, regla in filas:
        conn.execute(
            "INSERT INTO snapshot_ticker (fecha, ticker, sector, precio, rvol, rs_pct, "
            "phase, phase_confirmed, regla_fase) VALUES (?,?,?,?,?,?,?,?,?)",
            ((date(2026, 9, 15) - timedelta(days=atras)).isoformat(), ticker,
             "Technology", 100.0, 1.0, 75.0, fase, 1, regla))
    conn.commit(); conn.close()


def test_el_dia_del_cambio_no_se_inventan_entradas(db):
    """Ayer Fase 3 con la regla vieja, hoy Fase 2 con la nueva: no ha entrado
    nadie, y la sección lo dice en vez de enseñar una lista vacía."""
    _sembrar([(3, "AAA", 3, None), (1, "AAA", 3, None), (0, "AAA", 2, REGLA_FASES)])
    r = S.transiciones_de_fase(sesiones=5)
    assert r["ok"] is False and "cambió" in r["error"], r


def test_despues_solo_se_compara_con_la_regla_nueva(db):
    """Con dos sesiones de la regla nueva ya se compara, pero solo entre ellas:
    AAA cambió de fase por la fórmula (no sale); BBB entró de verdad (sale)."""
    _sembrar([(3, "AAA", 3, None), (1, "AAA", 2, REGLA_FASES), (0, "AAA", 2, REGLA_FASES),
              (3, "BBB", 1, None), (1, "BBB", 1, REGLA_FASES), (0, "BBB", 2, REGLA_FASES)])
    r = S.transiciones_de_fase(sesiones=5)
    assert r["ok"] is True and r["sesiones"] == 1, r
    assert [x["ticker"] for x in r["entradas"]] == ["BBB"]


def test_la_regla_viaja_del_escaneo_al_snapshot():
    raiz = os.path.join(os.path.dirname(__file__), "..", "..")
    escaneo = io.open(os.path.join(raiz, "scripts", "scanner_universe.py"), encoding="utf-8").read()
    assert '"phase_regla":       REGLA_FASES,' in escaneo
    assert '"phase_regla":     r.get("phase_regla"),' in escaneo
    snap = io.open(os.path.join(raiz, "backend", "services", "snapshots_service.py"), encoding="utf-8").read()
    assert 's.get("phase_regla"))' in snap and "dias_absorcion, regla_fase)" in snap
