"""
Test del diagnóstico de presupuesto del briefing diario (hallazgos #28 y #29
de la auditoría de Newsfeed, 11/08/2026).

El hallazgo #28 decía que las instrucciones fijas son el 53% del prompt y que
había bloques duplicados. Al medirlo con el prompt REAL resultó que:
  - No hay duplicación: los "bloques repetidos" eran _ESTILO_V1 vs _ESTILO_V2,
    y solo se envía uno de los dos (PROMPT_VERSION decide cuál).
  - Las instrucciones fijas son el 44%, no el 53%.
  - Lo que sí es cierto, y nadie sabía: el prompt NO cabe en el nivel de
    recorte normal (6.914 tok estimados contra un techo de 6.450), así que el
    briefing se genera a diario con datos recortados.

El hallazgo #29 pedía comprobar el margen real de TPM antes de comprimir nada.
La respuesta de Groq ya trae ese dato gratis en cada llamada (cabeceras
x-ratelimit-* y usage.prompt_tokens); antes se descartaba. Estos tests cubren
que ahora se lee, que el desvío de la estimación se calcula, y que el camino
del 413 (que main() necesita para bajar de nivel de recorte) sigue intacto.

Uso:
    cd backend
    python -m pytest tests/test_briefing_diagnostico.py -v
"""
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'scripts'))

import daily_briefing as db  # noqa: E402


def _respuesta(status=200, headers=None, usage=None, texto="briefing"):
    r = MagicMock()
    r.status_code = status
    r.headers = headers or {}
    r.text = "cuerpo"
    r.json.return_value = {
        "choices": [{"message": {"content": texto}}],
        **({"usage": usage} if usage else {}),
    }
    return r


CABECERAS = {
    "x-ratelimit-limit-tokens":     "8000",
    "x-ratelimit-remaining-tokens": "5120",
    "x-ratelimit-limit-requests":   "30",
}


def test_lee_el_limite_real_de_tpm_de_las_cabeceras():
    """#29: el límite de TPM deja de ser un 8000 copiado de la documentación
    y pasa a leerse de lo que responde la cuenta real."""
    diag = db._diagnostico_ratelimit(_respuesta(headers=CABECERAS))
    assert diag["tpm_limite_real"] == "8000"
    assert diag["tpm_restante"] == "5120"
    assert diag["rpm_limite_real"] == "30"


def test_sin_cabeceras_no_inventa_un_limite():
    """Sin el dato, None -- no se rellena con GROQ_TPM_LIMIT, que es
    justo la suposición que este diagnóstico existe para comprobar."""
    diag = db._diagnostico_ratelimit(_respuesta(headers={}))
    assert diag["tpm_limite_real"] is None
    assert diag["tokens_reales"] is None


def test_calcula_el_desvio_entre_mi_estimacion_y_el_recuento_de_groq():
    """El 31/07/2026 la estimación se desvió un 13% y provocó un 413. Ahora
    ese desvío queda registrado en cada ejecución, no solo cuando falla."""
    prompt = "x" * 2900  # estimar_tokens -> 1000 con CHARS_POR_TOKEN=2.9
    assert db.estimar_tokens(prompt) == 1000

    with patch.object(db, "GROQ_KEY", "clave-de-prueba"), \
         patch("requests.post", return_value=_respuesta(
             headers=CABECERAS, usage={"prompt_tokens": 1130})):
        texto, diag = db.generate_briefing(prompt)

    assert texto == "briefing"
    assert diag["tokens_estimados"] == 1000
    assert diag["tokens_reales"] == 1130
    assert diag["desvio_estimacion"] == 13.0


def test_el_413_sigue_siendo_recuperable_y_deja_ver_las_cabeceras():
    """main() distingue el 413 para bajar de nivel de recorte en vez de
    morirse -- leer el diagnóstico antes no debe tragarse esa excepción."""
    with patch.object(db, "GROQ_KEY", "clave-de-prueba"), \
         patch("requests.post", return_value=_respuesta(status=413, headers=CABECERAS)):
        with pytest.raises(db.PromptDemasiadoGrande):
            db.generate_briefing("x" * 2900)


def test_solo_se_envia_una_version_del_prompt():
    """El #28 daba por duplicados unos bloques que en realidad son las dos
    versiones del prompt. Solo una llega a Groq; la otra es la vía de vuelta
    atrás vía BRIEFING_PROMPT_VERSION y no cuesta ni un token."""
    with patch.object(db, "PROMPT_VERSION", "v2"):
        assert db._reglas_de_estilo() is db._ESTILO_V2
        assert db._cierre_y_estructura() is db._CIERRE_V2
    with patch.object(db, "PROMPT_VERSION", "v1"):
        assert db._reglas_de_estilo() is db._ESTILO_V1
        assert db._cierre_y_estructura() is db._CIERRE_V1
