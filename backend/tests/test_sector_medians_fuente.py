"""
Research tiene que DECIR contra qué está comparando cada métrica.

Contexto (29/07/2026): las medianas sectoriales reales de
scripts/sector_medians.py llevaban desde el 20/07/2026 sin llegar nunca a
Research. El job semanal terminaba en ÉXITO en GitHub Actions, pero escribía
en el Gist del secret SECTOR_MEDIANS_GIST_ID mientras research_service.py
leía otro ID hardcodeado. Como _get_sector_comparison() caía en silencio a
SECTOR_BENCHMARKS (valores escritos a mano, sin fecha ni fuente) y el propio
docstring decía "el usuario no necesita saber cuál de las dos fuentes se
usó", nadie podía notarlo: la UI enseñaba exactamente lo mismo en los dos
casos.

Estos tests fijan las tres cosas que impiden que vuelva a pasar:
  1. El ID sale de shared/gist_ids.py, la misma constante para quien escribe
     y quien lee -- no pueden apuntar a Gists distintos.
  2. Unas medianas viejas dejan de considerarse "reales" pasados
     SECTOR_MEDIANS_MAX_EDAD_DIAS (job semanal: 2 ejecuciones perdidas).
  3. La respuesta lleva SIEMPRE el campo `fuente`.

Uso:
    cd backend
    python -m pytest tests/test_sector_medians_fuente.py -v
"""
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.research_service import (  # noqa: E402
    _get_sector_comparison,
    _get_sector_medians_data,
    SECTOR_MEDIANS_GIST_FILE,
    SECTOR_MEDIANS_GIST_ID,
    SECTOR_MEDIANS_MAX_EDAD_DIAS,
)

METRICS       = {"trailing_pe": 30.0}
PROFITABILITY = {"roe": 0.25}


def _gist_response(payload: dict, nombre_fichero: str = SECTOR_MEDIANS_GIST_FILE):
    """Respuesta de la API de Gists tal cual la consume el backend."""
    r = MagicMock(status_code=200)
    r.raise_for_status.return_value = None
    r.json.return_value = {
        "files": {nombre_fichero: {"content": json.dumps(payload)}}
    }
    return r


def _payload(edad_dias: int, mediana_pe: float = 99.0) -> dict:
    generado = datetime.now(timezone.utc) - timedelta(days=edad_dias)
    return {
        "ok": True,
        "generated_at": generado.isoformat(),
        "sectores": {
            "Technology": {
                "medianas": {"trailing_pe": mediana_pe, "roe": 0.20},
                "n_tickers": 68,
            }
        },
    }


def _con_gist(respuesta):
    """Fuerza el camino de descarga (caché vacía) y evita escribir en el
    cache.db real compartido con la app."""
    return (
        patch("services.cache.cache.get", return_value=None),
        patch("services.cache.cache.set"),
        patch("services.research_service.requests.get", return_value=respuesta),
    )


def _ejecutar(respuesta, funcion):
    c1, c2, c3 = _con_gist(respuesta)
    with c1, c2, c3:
        return funcion()


# ── 1. El ID es el mismo para quien escribe y quien lee ──────────────────────

def test_el_backend_y_el_script_usan_la_misma_constante_de_gist():
    """La raíz del incidente: dos fuentes distintas para el mismo ID."""
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'shared'))
    import gist_ids

    assert SECTOR_MEDIANS_GIST_ID == gist_ids.SECTOR_MEDIANS_GIST_ID
    assert SECTOR_MEDIANS_GIST_FILE == gist_ids.SECTOR_MEDIANS_GIST_FILE

    ruta_script = os.path.join(os.path.dirname(__file__), '..', '..', 'scripts', 'sector_medians.py')
    with open(ruta_script, encoding='utf-8') as f:
        codigo = f.read()
    assert "from gist_ids import" in codigo, (
        "scripts/sector_medians.py debe tomar el Gist de shared/gist_ids.py, "
        "no de una variable de entorno propia -- es justo lo que hizo que "
        "escribiera en un Gist distinto del que lee el backend."
    )
    assert "SECTOR_MEDIANS_GIST_ID\"" not in codigo, (
        "El script no debe volver a leer el ID del secret de GitHub: ese "
        "secret puede apuntar a otro Gist y el fallo sale en verde."
    )


# ── 2. Camino real (el que nunca llegó a ejecutarse en producción) ───────────

def test_medianas_frescas_se_usan_y_se_declaran_como_reales():
    data = _ejecutar(_gist_response(_payload(edad_dias=2)), _get_sector_medians_data)
    assert data.get("sectores"), "Unas medianas de hace 2 días deben aceptarse"

    r = _ejecutar(
        _gist_response(_payload(edad_dias=2, mediana_pe=99.0)),
        lambda: _get_sector_comparison("Technology", METRICS, PROFITABILITY),
    )
    assert r["ok"] is True
    assert r["fuente"] == "real"
    assert r["n_tickers"] == 68
    assert r["edad_dias"] == 2
    # Se compara contra la mediana REAL (99.0), no contra el estático de
    # Technology (28.0). En trailing_pe menos es mejor, así que el MISMO P/E
    # de 30 sale "favorable" contra la mediana real y "desfavorable" contra
    # el estático: el veredicto que ve el usuario depende de qué fuente se
    # usó, y por eso la respuesta tiene que declararla.
    assert r["items"]["trailing_pe"]["sector_avg"] == 99.0
    assert r["items"]["trailing_pe"]["favorable"] is True

    estatico = _ejecutar(
        _gist_response({}, nombre_fichero="gistfile1.txt"),
        lambda: _get_sector_comparison("Technology", METRICS, PROFITABILITY),
    )
    assert estatico["items"]["trailing_pe"]["sector_avg"] == 28.0
    assert estatico["items"]["trailing_pe"]["favorable"] is False


# ── 3. Caducidad: un fósil no es un dato real ────────────────────────────────

def test_medianas_caducadas_caen_a_los_estaticos():
    edad = SECTOR_MEDIANS_MAX_EDAD_DIAS + 1
    r = _ejecutar(
        _gist_response(_payload(edad_dias=edad)),
        lambda: _get_sector_comparison("Technology", METRICS, PROFITABILITY),
    )
    assert r["fuente"] == "estatica", (
        f"Con {edad} días (máximo {SECTOR_MEDIANS_MAX_EDAD_DIAS}) el job semanal "
        "lleva 2+ ejecuciones sin regenerar: eso no puede seguir presentándose "
        "como mediana real."
    )
    assert r["items"]["trailing_pe"]["sector_avg"] == 28.0  # SECTOR_BENCHMARKS


def test_sin_generated_at_no_se_asume_que_esta_fresco():
    payload = _payload(edad_dias=1)
    del payload["generated_at"]
    r = _ejecutar(
        _gist_response(payload),
        lambda: _get_sector_comparison("Technology", METRICS, PROFITABILITY),
    )
    assert r["fuente"] == "estatica"


# ── 4. El fallo real de producción, ahora detectable ─────────────────────────

def test_gist_sin_el_fichero_esperado_lo_declara_en_vez_de_disimularlo():
    """El estado exacto en el que llevaba semanas: el Gist existe y responde
    200, pero solo tiene el 'gistfile1.txt' del día que se creó a mano."""
    r = _ejecutar(
        _gist_response({}, nombre_fichero="gistfile1.txt"),
        lambda: _get_sector_comparison("Technology", METRICS, PROFITABILITY),
    )
    assert r["ok"] is True, "Research sigue funcionando con los estáticos, no se cae"
    assert r["fuente"] == "estatica", (
        "Antes de este fix la respuesta era idéntica a la del camino real: "
        "por eso el incidente duró semanas sin que nadie lo viera."
    )


def test_la_fuente_va_siempre_en_la_respuesta():
    for payload, nombre in [
        (_payload(edad_dias=1), SECTOR_MEDIANS_GIST_FILE),
        ({}, "gistfile1.txt"),
    ]:
        r = _ejecutar(
            _gist_response(payload, nombre_fichero=nombre),
            lambda: _get_sector_comparison("Technology", METRICS, PROFITABILITY),
        )
        assert r.get("fuente") in ("real", "estatica")

    # Incluso cuando no hay benchmark de ningún tipo para ese sector.
    r = _ejecutar(
        _gist_response({}, nombre_fichero="gistfile1.txt"),
        lambda: _get_sector_comparison("Sector Inventado", METRICS, PROFITABILITY),
    )
    assert r["ok"] is False
    assert r["fuente"] == "estatica"
