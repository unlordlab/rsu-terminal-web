"""
Panel de beneficios empresariales de EE.UU. (Market): ritmo interanual de la
serie `CP` de FRED (cuentas nacionales del BEA).

Lo que fija este fichero son las tres cosas que, si se rompen, el panel sigue
pintando números plausibles sin avisar de nada:

1. INTERANUAL DE VERDAD. Se compara cada trimestre con el MISMO del año
   anterior (4 atrás), no con el anterior. Los beneficios tienen estacionalidad:
   comparar trimestres consecutivos mezcla ciclo con calendario y da un número
   que parece un dato de crecimiento sin serlo.

2. EL RETRASO SE DICE. El BEA publica con meses de demora, así que el dato más
   reciente puede tener dos trimestres. Si `retraso_trimestres` deja de
   calcularse bien, un +18% de hace medio año se lee como si describiera el
   trimestre en curso -- el mismo tipo de engaño que la columna «HOY %» de
   Cartera cuando enseñaba el movimiento de otra sesión.

3. LA SEÑAL NO SE FABRICA. El track record contra las recesiones del NBER se
   recalcula con los datos reales; si esa serie no está disponible se devuelve
   None y la pantalla no dice nada, en vez de citar una cifra sin comprobar.

Uso:
    cd backend
    python -m pytest tests/test_market_beneficios_empresariales.py -v
"""
import sys, os
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import services.market_service as M  # noqa: E402
from services.cache import cache  # noqa: E402


@pytest.fixture(autouse=True)
def sin_cache():
    cache.delete("market:corporate_profits")
    yield
    cache.delete("market:corporate_profits")


def _serie(valores, anio_inicio=2020):
    """Trimestres consecutivos (ene/abr/jul/oct) con los valores dados."""
    meses = ["01", "04", "07", "10"]
    out = []
    for i, v in enumerate(valores):
        out.append((f"{anio_inicio + i // 4}-{meses[i % 4]}-01", float(v)))
    return out


# ── 1. El interanual compara con el mismo trimestre del año anterior ────────

def test_el_interanual_compara_con_cuatro_trimestres_atras():
    """100 -> 110 en cuatro trimestres es +10%. Si se comparara con el
    trimestre anterior (105 -> 110) saldría +4,8%: un número plausible que no
    es un crecimiento interanual."""
    serie = _serie([100, 102, 104, 105, 110])
    with patch.object(M, "fred_csv", side_effect=lambda sid, **kw: serie if sid == "CP" else []):
        d = M.get_corporate_profits()
    assert d["ok"] is True
    assert d["yoy"] == pytest.approx(10.0, abs=0.05)


def test_una_caida_interanual_se_marca_como_contraccion():
    serie = _serie([100, 100, 100, 100, 90])
    with patch.object(M, "fred_csv", side_effect=lambda sid, **kw: serie if sid == "CP" else []):
        d = M.get_corporate_profits()
    assert d["yoy"] < 0
    assert d["estado"] == "CONTRACCIÓN"


def test_no_se_calcula_nada_sin_un_año_completo_de_historia():
    """Con menos de 5 trimestres no hay ningún interanual posible. Se dice que
    no hay dato en vez de inventar una comparación más corta.

    Se comprueba QUÉ guarda salta, no solo que `ok` sea False: hay dos, y la
    segunda («no se pudo calcular ningún interanual») atrapa este caso de
    rebote aunque se quite la primera. Sin distinguirlas, quitar la que
    diagnostica la serie corta no rompía ningún test -- lo destapó el sabotaje.
    """
    with patch.object(M, "fred_csv", side_effect=lambda sid, **kw: _serie([100, 101, 102])):
        d = M.get_corporate_profits()
    assert d["ok"] is False
    assert "trimestres" in d["error"], (
        f"debería decir que faltan trimestres, no un error genérico: {d['error']!r}")


# ── 2. El retraso de publicación se calcula y se expone ─────────────────────

def test_el_retraso_de_publicacion_se_cuenta_en_trimestres():
    """Con el dato más reciente en el primer trimestre y el reloj en el tercero
    del mismo año, son dos trimestres de retraso."""
    from datetime import datetime, timezone

    class RelojFijo(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 8, 13, tzinfo=timezone.utc)

    serie = _serie([100, 102, 104, 106, 118], anio_inicio=2025)   # último: 2026-01
    with patch.object(M, "fred_csv", side_effect=lambda sid, **kw: serie if sid == "CP" else []), \
         patch.object(M, "datetime", RelojFijo):
        d = M.get_corporate_profits()
    assert d["date"] == "2026-01-01"
    assert d["retraso_trimestres"] == 2


# ── 3. La señal contra recesiones se mide, no se escribe a mano ─────────────

def test_sin_la_serie_de_recesiones_no_se_inventa_el_track_record():
    """USREC no disponible -> `senal` a None, y la pantalla no dice nada sobre
    poder de aviso. Nunca una cifra de memoria."""
    serie = _serie([100, 102, 104, 106, 118])
    with patch.object(M, "fred_csv", side_effect=lambda sid, **kw: serie if sid == "CP" else []):
        d = M.get_corporate_profits()
    assert d["senal"] is None


def test_la_senal_trae_siempre_su_base_de_comparacion():
    """Un «el 54% acabó en recesión» sin saber cuánto pasa de normal no informa
    de nada. Las dos cifras viajan juntas o no viaja ninguna."""
    # 8 trimestres cayendo seguidos de 8 creciendo, con recesión marcada solo
    # en el tramo que sigue a las caídas.
    serie = _serie([100] * 4 + [90, 90, 90, 90] + [120, 130, 140, 150], anio_inicio=2015)
    recesiones = [(f"2016-{m:02d}-01", 1) for m in range(1, 13)]
    recesiones += [(f"2017-{m:02d}-01", 0) for m in range(1, 13)]

    def fake(sid, **kw):
        return serie if sid == "CP" else recesiones

    with patch.object(M, "fred_csv", side_effect=fake):
        d = M.get_corporate_profits()
    s = d["senal"]
    assert s is not None
    for campo in ("n_cayendo", "pct_cayendo", "n_creciendo", "pct_creciendo", "meses_vista"):
        assert campo in s, f"falta {campo}: sin base de comparación la cifra engaña"
    assert s["n_cayendo"] > 0 and s["n_creciendo"] > 0


def test_un_fallo_de_fred_no_rompe_el_panel():
    with patch.object(M, "fred_csv", side_effect=Exception("FRED caído")):
        d = M.get_corporate_profits()
    assert d["ok"] is False
    assert "error" in d


# ── Contexto histórico ──────────────────────────────────────────────────────

def test_el_percentil_situa_la_lectura_en_su_propia_historia():
    """El último valor es el más alto de la serie -> percentil alto."""
    serie = _serie([100, 100, 100, 100, 101, 102, 103, 104, 130])
    with patch.object(M, "fred_csv", side_effect=lambda sid, **kw: serie if sid == "CP" else []):
        d = M.get_corporate_profits()
    assert d["percentil"] >= 75
    assert d["n_trimestres"] == len(serie) - 4
