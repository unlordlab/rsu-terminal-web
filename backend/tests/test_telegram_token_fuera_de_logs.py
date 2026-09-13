"""
El token del bot de Telegram no puede salir nunca en un log.

EL CASO, 13/09/2026. La API de bots lleva el token DENTRO de la URL
(https://api.telegram.org/bot<TOKEN>/getUpdates), y cuando `requests` falla, el
texto de la excepción incluye la URL entera. Los `print` de error volcaban esa
excepción tal cual. Ese día, `deploy.sh` corrió la suite dentro del contenedor
de producción —con el `.env` real—, un test arrancó la app entera, el bucle de
vinculación de Telegram intentó `getUpdates` con el token real, el cierre de red
de la suite lo bloqueó, y el error salió impreso con el token en claro en la
salida del despliegue.

DOS ARREGLOS, y los dos se prueban aquí:

  - La causa: la suite no ve credenciales de Telegram de verdad
    (tests/conftest.py las vacía para toda la sesión).
  - El síntoma, por si otra vía lo vuelve a provocar: `sin_token()` tapa
    cualquier token de bot en los mensajes de error.

El token de estos tests es INVENTADO. Nunca uno real en un fichero del repo,
que además es público.

Uso:
    cd backend
    python -m pytest tests/test_telegram_token_fuera_de_logs.py -v
"""
import os
import re
import sys

import pytest
import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import services.telegram_service as T  # noqa: E402

FALSO = "1234567890:AAFakeTokenSoloParaTests_abcdefghijk"


def _error_como_el_real(token):
    """Lo que devuelve `requests` cuando no puede conectar: la URL, con el
    token dentro."""
    return requests.exceptions.ConnectionError(
        f"HTTPSConnectionPool(host='api.telegram.org', port=443): Max retries exceeded "
        f"with url: /bot{token}/getUpdates?offset=1&timeout=25")


# ── sin_token ───────────────────────────────────────────────────────────────

def test_tapa_el_token_dentro_de_un_error_real():
    texto = T.sin_token(_error_como_el_real(FALSO))
    assert FALSO not in texto
    assert "/bot***/getUpdates" in texto, "ya no se ve qué llamada falló: el log pierde su utilidad"


def test_tapa_tambien_un_token_distinto_del_configurado():
    """Por patrón, no solo el token de la configuración: un token de otro
    entorno o uno viejo que se cuele en un mensaje también se tapa."""
    otro = "9876543210:BBOtroTokenDeOtroEntorno_zyxwvutsrq"
    assert otro not in T.sin_token(f"fallo en /bot{otro}/sendMessage")


def test_no_estropea_un_mensaje_sin_token():
    assert T.sin_token("HTTP 429: Too Many Requests") == "HTTP 429: Too Many Requests"


# ── Los prints de error del servicio ────────────────────────────────────────

@pytest.fixture
def con_token(monkeypatch):
    from config import settings
    monkeypatch.setattr(settings, "telegram_bot_token", FALSO)
    monkeypatch.setattr(settings, "telegram_chat_id", "123")
    return settings


def test_getupdates_que_falla_no_imprime_el_token(con_token, monkeypatch, capsys):
    """EL test del caso: exactamente el camino que lo filtró."""
    def falla(*a, **k):
        raise _error_como_el_real(FALSO)
    monkeypatch.setattr(T.requests, "get", falla)
    T.poll_and_process_updates()
    salida = capsys.readouterr().out
    assert "getUpdates" in salida, "el error ya no se registra"
    assert FALSO not in salida, f"el token sale en el log: {salida}"


def test_sendmessage_que_falla_no_imprime_el_token(con_token, monkeypatch, capsys):
    def falla(*a, **k):
        raise _error_como_el_real(FALSO)
    monkeypatch.setattr(T.requests, "post", falla)
    assert T.enviar_telegram("hola") is False
    assert FALSO not in capsys.readouterr().out


def test_ningun_print_de_error_vuelca_la_excepcion_cruda():
    """Candado sobre el fichero: cualquier print de error del servicio que
    vuelque `{e}` o `r.text` tiene que pasarlo por sin_token."""
    ruta = os.path.join(os.path.dirname(__file__), '..', 'services', 'telegram_service.py')
    fuente = open(ruta, encoding="utf-8").read()
    # Solo los prints que están en una función que construye la URL con token.
    bloques = re.split(r"\ndef ", fuente)
    for bloque in bloques:
        if "api.telegram.org/bot{token}" not in bloque:
            continue
        for linea in bloque.splitlines():
            crudo = "{e}" in linea or ("r.text" in linea and "sin_token(r.text" not in linea)
            if "print(" in linea and crudo:
                pytest.fail(f"print que puede volcar el token sin taparlo: {linea.strip()}")


# ── La causa: la suite no ve credenciales reales ────────────────────────────

def test_la_suite_corre_sin_token_de_telegram():
    """En el VPS, `deploy.sh` corre la suite con el `.env` real cargado. Aquí
    dentro el token tiene que estar vacío siempre."""
    from config import settings
    assert settings.telegram_bot_token == "", (
        "la suite ve un token de Telegram: un test que arranque la app intentará usarlo")
    assert settings.telegram_admin_chat_id == ""


# ── Relacionado, del mismo día: la terminal se queda caída si se para ───────

def test_el_contenedor_se_levanta_solo_si_se_para():
    """El 12/09/2026 un despliegue a medias dejó la terminal 12 horas caída:
    sin política de reinicio, cualquier parada la deja apagada hasta que
    alguien la levanta a mano."""
    ruta = os.path.join(os.path.dirname(__file__), '..', '..', 'docker-compose.yml')
    compose = open(ruta, encoding="utf-8").read()
    assert re.search(r"^\s+restart:\s*unless-stopped\s*$", compose, re.M), (
        "docker-compose.yml ya no tiene `restart: unless-stopped`")
