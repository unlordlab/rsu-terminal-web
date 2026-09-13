"""
Infraestructura #31: un aviso por Telegram cuando la terminal deja de responder.

EL CASO. El 12/09/2026 un despliegue se interrumpió y la terminal estuvo 12 horas
caída sin que nadie se enterara. `cron_alert.sh` avisa si falla un cron, pero
nada vigilaba que la web respondiera.

Estos tests EJECUTAN el script de verdad (bash + curl), contra un servidor local
que hace de /health y de la API de Telegram: nada de leer el fuente y suponer.

Uso:
    cd backend
    python -m pytest tests/test_vigilar_salud.py -v
"""
import json
import os
import shutil
import subprocess
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
SCRIPT = os.path.join(RAIZ, "scripts", "vigilar_salud.sh")

# Partido en dos a propósito: entero tendría forma de token de bot y el detector
# de secretos del repositorio lo marcaría, con razón.
TOKEN = "1234567890:" + "AAFakeTokenSoloParaTests_abcdefghijk"


def _bash():
    """Un bash que ejecute el script con curl. En Windows, el de Git; el de
    System32 es WSL y no ve el localhost del test."""
    for candidato in (shutil.which("bash"), r"C:\Program Files\Git\bin\bash.exe"):
        if candidato and "System32" not in candidato and os.path.exists(candidato):
            return candidato
    return None


pytestmark = pytest.mark.skipif(_bash() is None or shutil.which("curl") is None,
                                reason="hace falta bash y curl para ejecutar el script")


class _Estado:
    web = 200
    app = 200
    telegram = 200
    mensajes = []


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        codigo = _Estado.web if self.path.startswith("/web/") else _Estado.app
        self.send_response(codigo)
        self.end_headers()
        self.wfile.write(b'{"status":"ok"}' if codigo == 200 else b"caida")

    def do_POST(self):
        largo = int(self.headers.get("Content-Length", 0))
        cuerpo = urllib.parse.parse_qs(self.rfile.read(largo).decode())
        _Estado.mensajes.append({"path": self.path,
                                 "chat_id": cuerpo.get("chat_id", [""])[0],
                                 "text": cuerpo.get("text", [""])[0]})
        self.send_response(_Estado.telegram)
        self.end_headers()
        self.wfile.write(json.dumps({"ok": _Estado.telegram == 200}).encode())


@pytest.fixture
def entorno(tmp_path):
    _Estado.web, _Estado.app, _Estado.telegram = 200, 200, 200
    _Estado.mensajes = []
    servidor = HTTPServer(("127.0.0.1", 0), _Handler)
    hilo = threading.Thread(target=servidor.serve_forever, daemon=True)
    hilo.start()
    puerto = servidor.server_address[1]
    env_file = tmp_path / ".env"
    env_file.write_text(f"TELEGRAM_BOT_TOKEN={TOKEN}\nTELEGRAM_ADMIN_CHAT_ID=999\n", encoding="utf-8")
    variables = dict(os.environ,
                     RSU_HEALTH_URL=f"http://127.0.0.1:{puerto}/web/health",
                     RSU_HEALTH_URL_APP=f"http://127.0.0.1:{puerto}/app/health",
                     TELEGRAM_API_BASE=f"http://127.0.0.1:{puerto}",
                     RSU_VIGILANCIA_DIR=str(tmp_path / "estado"),
                     RSU_ENV_FILE=str(env_file))

    def lanzar():
        r = subprocess.run([_bash(), SCRIPT], env=variables, capture_output=True,
                           text=True, encoding="utf-8", errors="replace", timeout=60)
        return r

    yield lanzar, tmp_path, env_file
    servidor.shutdown()


# ── El comportamiento ───────────────────────────────────────────────────────

def test_si_responde_no_hace_nada(entorno):
    lanzar, _, _ = entorno
    r = lanzar()
    assert r.returncode == 0
    assert _Estado.mensajes == []


def test_una_sola_caida_no_avisa(entorno):
    """Un despliegue deja la web sin responder unos 15 s: un aviso por cada
    despliegue enseña a ignorar los avisos."""
    lanzar, _, _ = entorno
    _Estado.web = _Estado.app = 502
    lanzar()
    assert _Estado.mensajes == []


def test_dos_caidas_seguidas_avisan_y_dicen_donde_esta_el_fallo(entorno):
    """EL test del caso: el contenedor caído, dos pasadas, un aviso."""
    lanzar, _, _ = entorno
    _Estado.web = _Estado.app = 502
    lanzar()
    lanzar()
    assert len(_Estado.mensajes) == 1
    m = _Estado.mensajes[0]
    assert m["chat_id"] == "999", "el aviso tiene que ir al chat del admin"
    assert "NO responde" in m["text"] and "contenedor" in m["text"]


def test_si_la_app_responde_el_aviso_apunta_a_nginx(entorno):
    lanzar, _, _ = entorno
    _Estado.web, _Estado.app = 502, 200
    lanzar()
    lanzar()
    assert "Nginx" in _Estado.mensajes[0]["text"]


def test_una_caida_larga_avisa_una_sola_vez(entorno):
    """Cada 5 minutos durante 12 horas serían 144 mensajes iguales."""
    lanzar, _, _ = entorno
    _Estado.web = _Estado.app = 502
    for _ in range(5):
        lanzar()
    assert len(_Estado.mensajes) == 1


def test_al_volver_avisa_de_que_se_ha_recuperado(entorno):
    lanzar, _, _ = entorno
    _Estado.web = _Estado.app = 502
    lanzar()
    lanzar()
    _Estado.web = _Estado.app = 200
    lanzar()
    assert len(_Estado.mensajes) == 2
    assert "vuelve a responder" in _Estado.mensajes[1]["text"]
    lanzar()
    assert len(_Estado.mensajes) == 2, "repite el aviso de recuperación"


def test_una_recuperacion_sin_caida_avisada_no_manda_nada(entorno):
    """Un fallo suelto (por debajo del umbral) no merece un «ya ha vuelto»."""
    lanzar, _, _ = entorno
    _Estado.web = _Estado.app = 502
    lanzar()
    _Estado.web = _Estado.app = 200
    lanzar()
    assert _Estado.mensajes == []


def test_si_telegram_falla_se_reintenta_en_la_siguiente_pasada(entorno):
    """Si el aviso no sale, no puede darse por avisado: se perdería la caída."""
    lanzar, _, _ = entorno
    _Estado.web = _Estado.app = 502
    _Estado.telegram = 500
    lanzar()
    lanzar()
    _Estado.telegram = 200
    lanzar()
    exitosos = [m for m in _Estado.mensajes if "NO responde" in m["text"]]
    assert len(exitosos) == 2, "no ha reintentado el aviso que falló"


def test_sin_credenciales_no_revienta(entorno):
    lanzar, _, env_file = entorno
    env_file.write_text("OTRA_COSA=1\n", encoding="utf-8")
    _Estado.web = _Estado.app = 502
    lanzar()
    r = lanzar()
    assert r.returncode == 0 and "Sin credenciales" in r.stdout


# ── El token ────────────────────────────────────────────────────────────────

def test_el_token_no_sale_en_la_salida_del_script(entorno):
    """El log del cron es un fichero en disco: no puede llevar el token."""
    lanzar, _, _ = entorno
    _Estado.web = _Estado.app = 502
    salidas = lanzar().stdout + lanzar().stdout
    _Estado.telegram = 500
    salidas += lanzar().stdout
    assert TOKEN not in salidas


def test_el_token_no_va_en_los_argumentos_de_curl():
    """En los argumentos se ve con `ps` desde cualquier sesión del servidor.
    Se le pasa a curl por la entrada estándar (`-K -`)."""
    fuente = open(SCRIPT, encoding="utf-8").read()
    for linea in fuente.splitlines():
        if "curl" in linea and "token" in linea.lower() and not linea.strip().startswith("#"):
            pytest.fail(f"el token va en la línea de curl: {linea.strip()}")
    assert "-K -" in fuente


def test_el_script_tiene_saltos_de_linea_de_linux():
    """Editado desde Windows, un fin de línea CRLF hace que bash en el VPS
    falle con «$'\r': command not found» — y un vigilante que no arranca
    es peor que no tenerlo, porque da la tranquilidad sin dar el aviso."""
    assert b"\r" not in open(SCRIPT, "rb").read()
