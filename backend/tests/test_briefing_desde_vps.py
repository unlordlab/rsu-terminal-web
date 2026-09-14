"""
Infraestructura #23: el briefing lo lanza el servidor a su hora, y si a las
07:30 UTC no está publicado, avisa.

EL CASO. El planificador de GitHub disparaba el briefing de las 07:00 UTC con
horas de retraso (4 h 50 min de media desde el 27/08; 6 h 26 min el 14/09). Ese
día el usuario pensó que había fallado y echó en falta el aviso de Telegram, que
no llegó porque NO falló: llegaba tarde, y nada avisaba de eso. Un
`workflow_dispatch` arranca en segundos, así que el servidor pide a GitHub que
lo ejecute; el disparo programado se queda de respaldo y no repite un briefing
ya publicado.

Estos tests EJECUTAN el script (bash + curl) contra un servidor local que hace
de API de GitHub y de Telegram.

Uso:
    cd backend
    python -m pytest tests/test_briefing_desde_vps.py -v
"""
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import urllib.parse
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
SCRIPT = os.path.join(RAIZ, "scripts", "briefing_desde_vps.sh")
WORKFLOW = os.path.join(RAIZ, ".github", "workflows", "daily_briefing.yml")
REPO = "unlordlab/rsu-terminal-web"
GIST = "715ee0c4e571517c11fa65c5c2376c34"

# Partidos en dos a propósito: enteros tendrían forma de credencial y el
# detector de secretos del repositorio los marcaría, con razón.
TOKEN_BOT = "1234567890:" + "AAFakeTokenSoloParaTests_abcdefghijk"
TOKEN_GH = "github_pat_" + "FAKE0000SOLOPARATESTS0000"
TOKEN_GIST = "ghp_" + "FAKELECTURA0000000000"


def _bash():
    for candidato in (shutil.which("bash"), r"C:\Program Files\Git\bin\bash.exe"):
        if candidato and "System32" not in candidato and os.path.exists(candidato):
            return candidato
    return None


pytestmark = pytest.mark.skipif(_bash() is None or shutil.which("curl") is None,
                                reason="hace falta bash y curl para ejecutar el script")


def _hoy():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


class _Estado:
    dispatch = 204
    gist = 200
    fecha = None
    run = {"status": "queued", "conclusion": None, "created_at": "2026-09-14T07:00:03Z"}
    peticiones = []
    mensajes = []


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _cuerpo(self):
        largo = int(self.headers.get("Content-Length", 0))
        return self.rfile.read(largo).decode() if largo else ""

    def do_POST(self):
        cuerpo = self._cuerpo()
        if self.path.startswith("/bot"):
            datos = urllib.parse.parse_qs(cuerpo)
            _Estado.mensajes.append({"path": self.path, "chat_id": datos.get("chat_id", [""])[0],
                                     "text": datos.get("text", [""])[0]})
            self._responder(200, {"ok": True})
            return
        _Estado.peticiones.append({"metodo": "POST", "path": self.path, "cuerpo": cuerpo,
                                   "auth": self.headers.get("Authorization")})
        self._responder(_Estado.dispatch, None if _Estado.dispatch == 204 else {"message": "Bad credentials"})

    def do_GET(self):
        _Estado.peticiones.append({"metodo": "GET", "path": self.path, "auth": self.headers.get("Authorization")})
        if self.path.startswith("/gists/"):
            contenido = json.dumps({"date": _Estado.fecha or _hoy(), "text": "briefing"})
            self._responder(_Estado.gist, {"files": {"briefing.json": {"content": contenido}}})
        elif "/runs" in self.path:
            self._responder(200, {"workflow_runs": [_Estado.run]})
        else:
            self._responder(404, {})

    def _responder(self, codigo, datos):
        self.send_response(codigo)
        self.end_headers()
        if datos is not None and codigo != 204:
            self.wfile.write(json.dumps(datos).encode())


@pytest.fixture
def entorno(tmp_path):
    _Estado.dispatch, _Estado.gist, _Estado.fecha = 204, 200, None
    _Estado.peticiones, _Estado.mensajes = [], []
    servidor = HTTPServer(("127.0.0.1", 0), _Handler)
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{servidor.server_address[1]}"
    env_file = tmp_path / ".env"

    def escribir_env(con_dispatch=True):
        lineas = [f"TELEGRAM_BOT_TOKEN={TOKEN_BOT}", "TELEGRAM_ADMIN_CHAT_ID=999", f"GITHUB_TOKEN={TOKEN_GIST}"]
        if con_dispatch:
            lineas.append(f"GITHUB_DISPATCH_TOKEN={TOKEN_GH}")
        env_file.write_text("\n".join(lineas) + "\n", encoding="utf-8")

    escribir_env()
    variables = dict(os.environ, GITHUB_API_BASE=base, TELEGRAM_API_BASE=base,
                     RSU_ENV_FILE=str(env_file), RSU_PYTHON=sys.executable)

    def lanzar(orden, **extra):
        return subprocess.run([_bash(), SCRIPT, orden], env=dict(variables, **extra), capture_output=True,
                              text=True, encoding="utf-8", errors="replace", timeout=60)

    yield lanzar, escribir_env
    servidor.shutdown()


# ── lanzar ──────────────────────────────────────────────────────────────────

def test_lanza_el_workflow_con_workflow_dispatch(entorno):
    lanzar, _ = entorno
    r = lanzar("lanzar")
    assert r.returncode == 0, r.stdout + r.stderr
    [p] = _Estado.peticiones
    assert p["metodo"] == "POST"
    assert p["path"] == f"/repos/{REPO}/actions/workflows/daily_briefing.yml/dispatches"
    assert json.loads(p["cuerpo"]) == {"ref": "main"}
    assert p["auth"] == f"Bearer {TOKEN_GH}", "el de lanzar, no el de leer Gists"
    assert _Estado.mensajes == []
    assert TOKEN_GH not in r.stdout + r.stderr


@pytest.mark.parametrize("codigo,pista", [
    (401, "caducado"),
    (403, "Actions: Read and write"),
    (404, "incluya"),
])
def test_si_github_lo_rechaza_avisa_y_dice_como_arreglarlo(entorno, codigo, pista):
    lanzar, _ = entorno
    _Estado.dispatch = codigo
    r = lanzar("lanzar")
    assert r.returncode == 1
    [m] = _Estado.mensajes
    assert m["chat_id"] == "999"
    assert f"HTTP {codigo}" in m["text"] and pista in m["text"]
    assert "con retraso" in m["text"], "hay que decir que saldrá igual, tarde"
    assert TOKEN_GH not in m["text"] + r.stdout + r.stderr


def test_sin_token_avisa_y_no_llama_a_github(entorno):
    lanzar, escribir_env = entorno
    escribir_env(con_dispatch=False)
    r = lanzar("lanzar")
    assert r.returncode == 1
    assert _Estado.peticiones == []
    assert "GITHUB_DISPATCH_TOKEN" in _Estado.mensajes[0]["text"]


def test_si_github_no_responde_lo_dice(entorno):
    lanzar, _ = entorno
    r = lanzar("lanzar", GITHUB_API_BASE="http://127.0.0.1:9")
    assert r.returncode == 1
    assert "HTTP 000" in _Estado.mensajes[0]["text"] and "no hubo respuesta" in _Estado.mensajes[0]["text"]


# ── comprobar ───────────────────────────────────────────────────────────────

def test_si_el_briefing_de_hoy_esta_no_avisa(entorno):
    lanzar, _ = entorno
    r = lanzar("comprobar")
    assert r.returncode == 0, r.stdout + r.stderr
    assert _Estado.mensajes == []
    gist = [p for p in _Estado.peticiones if p["path"].startswith("/gists/")][0]
    assert gist["path"] == f"/gists/{GIST}"
    assert gist["auth"] == f"Bearer {TOKEN_GIST}", "leer el Gist es cosa del token de lectura"


def test_si_no_esta_avisa_con_la_fecha_y_el_estado_de_la_ejecucion(entorno):
    """EL test del 14/09: tarde no es fallo, y aun así hay que enterarse."""
    lanzar, _ = entorno
    _Estado.fecha = (datetime.now(timezone.utc) - timedelta(days=3)).strftime("%Y-%m-%d")
    r = lanzar("comprobar")
    assert r.returncode == 1
    [m] = _Estado.mensajes
    assert "todavía no está publicado" in m["text"]
    assert _Estado.fecha in m["text"]
    assert "Última ejecución: en cola" in m["text"] and "2026-09-14 07:00" in m["text"]


def test_si_el_gist_no_se_lee_avisa_igual(entorno):
    lanzar, _ = entorno
    _Estado.gist = 500
    r = lanzar("comprobar")
    assert r.returncode == 1
    assert "no se pudo leer el Gist" in _Estado.mensajes[0]["text"]


def test_orden_desconocida():
    r = subprocess.run([_bash(), SCRIPT, "otra"], capture_output=True, text=True, timeout=30)
    assert r.returncode == 2


def test_ningun_token_va_en_la_linea_de_comandos_de_curl():
    """Por argumentos se verían en `ps`. Tienen que ir por la entrada estándar."""
    src = open(SCRIPT, encoding="utf-8").read()
    for linea in src.splitlines():
        if re.search(r"\bcurl\b", linea) and not linea.lstrip().startswith("#"):
            assert "token" not in linea.lower(), linea
            assert "-K -" in linea, linea


# ── El workflow no repite un briefing ya publicado ──────────────────────────

def _workflow():
    return open(WORKFLOW, encoding="utf-8").read()


def test_el_disparo_programado_se_queda_de_respaldo():
    wf = _workflow()
    assert "cron: '0 7 * * 1-5'" in wf
    assert "workflow_dispatch" in wf


def test_solo_el_programado_mira_si_ya_esta_publicado():
    wf = _workflow()
    i = wf.index("id: hoy")
    paso = wf[i:wf.index("- name:", i)]
    assert "if: github.event_name == 'schedule'" in paso, (
        "lanzado a mano o por el servidor tiene que generarse siempre")


def test_todos_los_pasos_que_generan_se_saltan_si_ya_esta():
    wf = _workflow()
    for paso in ("Checkout", "Setup Python", "Install dependencies", "Generate Daily Briefing"):
        i = wf.index(f"- name: {paso}")
        assert "if: steps.hoy.outputs.ya != '1'" in wf[i:i + 200], paso
    i = wf.index("- name: Avisar por Telegram si falló")
    assert "if: failure()" in wf[i:i + 120]


def test_la_lectura_de_la_fecha_del_workflow_funciona_de_verdad():
    """Se ejecuta el mismo trozo de Python del workflow sobre la respuesta que
    da la API de Gists: si leyera mal la fecha, el respaldo repetiría el
    briefing o, peor, dejaría de generarlo."""
    wf = _workflow()
    codigo = re.search(r"python3 -c '([^']+)'", wf).group(1)
    respuesta = {"files": {"briefing.json": {"content": json.dumps({"date": "2026-09-14", "text": "x"})}}}
    r = subprocess.run([sys.executable, "-c", codigo], input=json.dumps(respuesta),
                       capture_output=True, text=True, timeout=30)
    assert r.stdout.strip() == "2026-09-14"
    assert 'if [ "$FECHA" = "$HOY" ]' in wf and "date -u +%Y-%m-%d" in wf


def test_un_aviso_con_comillas_y_saltos_de_linea_llega_entero():
    """El texto va dentro de la configuración de curl, entre comillas: una
    comilla o un salto de línea sin escapar cortaría el mensaje o rompería la
    petición. Se manda de verdad y se compara lo que llega."""
    _Estado.mensajes = []
    servidor = HTTPServer(("127.0.0.1", 0), _Handler)
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    try:
        src = open(SCRIPT, encoding="utf-8").read()
        i = src.index("para_config() {")
        funcion = src[i:src.index("\n}\n", i) + 3]
        url = f"http://127.0.0.1:{servidor.server_address[1]}/botX/sendMessage"
        guion = (funcion + "\n{ printf 'url = \"%s\"\n' \"$2\"; "
                 "printf 'data-urlencode = \"text=%s\"\n' \"$(para_config \"$1\")\"; } | curl -s -o /dev/null -K -")
        texto = 'Dice "hola" \ con barra\ny otra línea: «ok»'
        subprocess.run([_bash(), "-c", guion, "x", texto, url], capture_output=True, timeout=30)
    finally:
        servidor.shutdown()
    assert [m["text"] for m in _Estado.mensajes] == [texto]
