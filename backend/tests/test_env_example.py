"""
`.env.example` tiene que seguir siendo copiable sin romper el arranque.

Contexto: la plantilla llevaba meses conteniendo `COMMUNITY_PASSWORD`, un
campo eliminado de `Settings` hacía tiempo. Como pydantic-settings valida el
fichero .env de forma estricta, copiarla a `backend/.env` **tumbaba el
arranque** con ValidationError — es decir, la plantilla oficial del proyecto
dejaba la app sin arrancar. Y no es un riesgo teórico: exactamente ese
mecanismo causó un 502 en producción el 20/07/2026 al quitar
`openrouter_api_key` de Settings sin quitarla del .env real.

Este test lo detecta en CI en vez de en el próximo despliegue.

Matiz verificado el 28/07/2026 (por eso el test lee el fichero y no monta
variables de entorno): la validación estricta aplica al FICHERO .env. Una
variable de entorno suelta con un nombre desconocido simplemente se ignora.

Uso:
    cd backend
    python -m pytest tests/test_env_example.py -v
"""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import Settings  # noqa: E402

RUTA = os.path.join(os.path.dirname(__file__), '..', '..', '.env.example')
RE_VARIABLE = re.compile(r"^\s*([A-Z][A-Z0-9_]*)\s*=", re.MULTILINE)


def _variables_activas() -> list:
    """Las variables que se aplicarían de verdad al copiar el fichero — las
    comentadas con # son ejemplos apagados y no llegan a Settings."""
    with open(RUTA, encoding="utf-8") as f:
        lineas = [l for l in f if not l.lstrip().startswith("#")]
    return RE_VARIABLE.findall("".join(lineas))


def test_el_fichero_existe():
    assert os.path.isfile(RUTA), "No hay .env.example en la raíz del proyecto"


def test_toda_variable_activa_existe_como_campo_en_settings():
    campos = set(Settings.model_fields)
    desconocidas = [v for v in _variables_activas() if v.lower() not in campos]
    assert not desconocidas, (
        "Estas variables de .env.example NO existen en Settings y harían fallar "
        f"el arranque al copiar el fichero: {desconocidas}. "
        "Quítalas de la plantilla o añade su campo en backend/config.py."
    )


def test_no_hay_variables_duplicadas():
    activas = _variables_activas()
    repetidas = {v for v in activas if activas.count(v) > 1}
    assert not repetidas, f"Variables repetidas en .env.example: {repetidas}"


def test_estan_las_dos_claves_obligatorias_en_produccion():
    # Son las que el validador de config.py exige cambiar con
    # ENVIRONMENT=production: si faltan de la plantilla, alguien desplegará
    # sin saber que existen y el arranque le fallará en el peor momento.
    activas = _variables_activas()
    for obligatoria in ("SECRET_KEY", "ADMIN_KEY"):
        assert obligatoria in activas, f"Falta {obligatoria} en .env.example"


def test_la_plantilla_no_trae_secretos_de_verdad():
    """Un despiste al actualizarla podría dejar una clave real commiteada."""
    with open(RUTA, encoding="utf-8") as f:
        contenido = f.read()
    sospechosos = [
        r"sk-[A-Za-z0-9_-]{20,}",        # OpenAI/Anthropic
        r"gsk_[A-Za-z0-9]{20,}",         # Groq
        r"AIza[A-Za-z0-9_-]{30,}",       # Google
        r"\d{8,10}:[A-Za-z0-9_-]{30,}",  # Telegram bot token
    ]
    for patron in sospechosos:
        assert not re.search(patron, contenido), (
            f"Parece haber una clave real en .env.example (patrón {patron}). "
            "La plantilla va a git: no puede contener secretos."
        )


# ── Protección de arranque en producción ─────────────────────────────────────
# Descubierto el 28/07/2026 al probar la plantilla nueva: el validador solo
# comparaba contra los defaults LITERALES de config.py, así que copiar
# .env.example, poner ENVIRONMENT=production y olvidarse de cambiar las claves
# dejaba la app arrancando con credenciales escritas en un fichero público del
# repositorio -- exactamente lo que ese validador existe para impedir.

from config import _es_valor_de_relleno  # noqa: E402


def test_detecta_los_valores_de_relleno():
    for valor in ("dev_secret", "changeme_admin_key", "changeme",
                  "cambia_esto_por_una_clave_larga_y_aleatoria",
                  "CAMBIA_ESTO_YA", "tu_password", "your_secret", ""):
        assert _es_valor_de_relleno(valor), f"Debería detectarse como relleno: {valor!r}"


def test_no_marca_claves_reales_como_relleno():
    # Si esto fallara, la app dejaría de arrancar en producción con una clave
    # legítima: romper producción para prevenir algo hipotético sería peor que
    # el problema. Por eso NO se comprueba longitud mínima, solo patrones.
    for valor in ("a7f3c9d2e5b8", "kY8#mP2!vQ7@nR4",
                  "j5K9mN2pQ7rS4tV8wX1yZ3aB6cD0eF", "supercalifragilistico42"):
        assert not _es_valor_de_relleno(valor), f"No debería marcarse: {valor!r}"


def test_los_placeholders_de_la_plantilla_se_detectan_todos():
    """Cierra el círculo: cualquier relleno que se escriba en .env.example
    tiene que ser reconocido por el validador, o la protección se queda
    coja en cuanto alguien edite la plantilla."""
    activas = {}
    with open(RUTA, encoding="utf-8") as f:
        for linea in f:
            if linea.lstrip().startswith("#") or "=" not in linea:
                continue
            k, _, v = linea.partition("=")
            activas[k.strip()] = v.strip()
    for clave in ("SECRET_KEY", "ADMIN_KEY"):
        assert _es_valor_de_relleno(activas[clave]), (
            f"El relleno de {clave} en .env.example ({activas[clave]!r}) NO lo "
            "detecta config.py: alguien podría desplegarlo tal cual en producción."
        )
