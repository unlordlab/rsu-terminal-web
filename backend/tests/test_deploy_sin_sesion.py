"""
Infraestructura #33: `deploy.sh` no depende de la sesión SSH.

EL CASO, 12/09/2026. Se cortó la conexión durante `docker compose up -d
--force-recreate`: el contenedor viejo quedó parado y con el nombre cambiado
(`a14bc3e16fc1_rsu-terminal-web-app-1`), el nuevo creado sin arrancar, y la
terminal estuvo 12 horas caída. Al volver, el propio deploy.sh no servía para
arreglarlo: su backup busca el contenedor por nombre y abortaba.

Estos tests EJECUTAN deploy.sh de verdad, en una copia aislada, con `git`,
`docker` y `curl` sustituidos por guiones que apuntan cada llamada y simulan el
estado de los contenedores. Nada de leer el fuente y suponer.

Uso:
    cd backend
    python -m pytest tests/test_deploy_sin_sesion.py -v
"""
import os
import shutil
import signal
import subprocess
import time

import pytest

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
CONTENEDOR = "rsu-terminal-web-app-1"


def _bash():
    for candidato in (shutil.which("bash"), r"C:\Program Files\Git\bin\bash.exe"):
        if candidato and "System32" not in candidato and os.path.exists(candidato):
            return candidato
    return None


pytestmark = pytest.mark.skipif(_bash() is None, reason="hace falta bash para ejecutar deploy.sh")

GIT = r'''#!/usr/bin/env bash
E="$STUB_ESTADO"
echo "git $*" >> "$E/llamadas"
case "$1" in
  status) exit 0 ;;
  pull) echo "commit-nuevo" > "$E/head"; echo "Updating" ;;
  rev-parse) cat "$E/head" ;;
  diff) exit 0 ;;
esac
'''

DOCKER = r'''#!/usr/bin/env bash
E="$STUB_ESTADO"
echo "docker $*" >> "$E/llamadas"
case "$1" in
  ps)
    if [[ " $* " == *" -a "* ]]; then cat "$E/todos"; else cat "$E/corriendo"; fi ;;
  rename)
    sed -i "s/^$2\$/$3/" "$E/todos" "$E/corriendo" ;;
  logs) echo "(logs)" ;;
  compose)
    shift
    case "$1" in
      run)
        touch "$E/tests_empezados"
        sleep "${STUB_DURACION_TESTS:-0}"
        exit "${STUB_TESTS_RC:-0}" ;;
      up)
        if [[ " $* " == *"--force-recreate"* ]]; then
          echo "rsu-terminal-web-app-1" > "$E/corriendo"; echo "rsu-terminal-web-app-1" > "$E/todos"
        elif [ -z "${STUB_UP_NO_ARRANCA:-}" ]; then
          cp "$E/todos" "$E/corriendo"
        fi ;;
    esac ;;
esac
exit 0
'''

CURL = '#!/usr/bin/env bash\necho \'{"status":"ok"}\'\n'
BACKUP = '#!/usr/bin/env bash\necho "backup" >> "$STUB_ESTADO/llamadas"\n'


@pytest.fixture
def repo(tmp_path):
    base = tmp_path / "repo"
    (base / "scripts").mkdir(parents=True)
    (base / "backend").mkdir()
    (base / "agents").mkdir()
    shutil.copy(os.path.join(RAIZ, "deploy.sh"), base / "deploy.sh")
    (base / "scripts" / "backup_dbs.sh").write_text(BACKUP, newline="\n")
    stubs = tmp_path / "stubs"
    stubs.mkdir()
    for nombre, cuerpo in (("git", GIT), ("docker", DOCKER), ("curl", CURL)):
        (stubs / nombre).write_text(cuerpo, newline="\n")
    estado = tmp_path / "estado"
    estado.mkdir()
    (estado / "head").write_text("commit-viejo\n")
    (estado / "corriendo").write_text(CONTENEDOR + "\n")
    (estado / "todos").write_text(CONTENEDOR + "\n")
    (estado / "llamadas").write_text("")
    for f in (base / "deploy.sh", base / "scripts" / "backup_dbs.sh", *stubs.iterdir()):
        os.chmod(f, 0o755)
    entorno = dict(os.environ)
    entorno.update({
        "PATH": _ruta_bash(stubs) + os.pathsep + entorno.get("PATH", ""),
        "STUB_ESTADO": _ruta_bash(estado),
        "DEPLOY_ESPERA_ARRANQUE": "0",
        "DEPLOY_DIR_LOGS": _ruta_bash(tmp_path / "logs"),
        "DEPLOY_CERROJO": _ruta_bash(tmp_path / "cerrojo"),
    })
    return {"base": base, "estado": estado, "logs": tmp_path / "logs",
            "cerrojo": tmp_path / "cerrojo", "env": entorno}


def _ruta_bash(p):
    """En Windows, bash de Git necesita /c/... en el PATH."""
    p = str(p)
    if os.name == "nt" and len(p) > 1 and p[1] == ":":
        return "/" + p[0].lower() + p[2:].replace("\\", "/")
    return p


def _desplegar(repo, extra=None, timeout=60, **kw):
    env = dict(repo["env"], **(extra or {}))
    return subprocess.run([_bash(), "./deploy.sh"], cwd=repo["base"], env=env,
                          capture_output=True, text=True, encoding="utf-8", errors="replace",
                          timeout=timeout, **kw)


def _llamadas(repo):
    return (repo["estado"] / "llamadas").read_text()


def _estado_final(repo):
    ficheros = list(repo["logs"].glob("deploy-*.log.estado"))
    assert len(ficheros) == 1, ficheros
    return ficheros[0].read_text().strip()


def test_despliegue_normal_termina_y_se_ve_en_la_sesion(repo):
    r = _desplegar(repo)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "NO se para si se corta la conexión" in r.stdout
    assert "=== Despliegue completado" in r.stdout, "la sesión debe ver el log en directo"
    assert _estado_final(repo) == "0"
    logs = list(repo["logs"].glob("deploy-*.log"))
    assert len(logs) == 1
    assert "=== Despliegue completado" in logs[0].read_text(encoding="utf-8")
    # En Linux `ultimo.log` es un enlace al de este despliegue. (El bash de Git
    # para Windows copia en vez de enlazar, así que ahí no se comprueba.)
    if os.name != "nt":
        assert os.path.realpath(repo["logs"] / "ultimo.log") == os.path.realpath(logs[0])
    llamadas = _llamadas(repo)
    assert "backup" in llamadas and "docker compose up -d --force-recreate" in llamadas
    assert not repo["cerrojo"].exists(), "el cerrojo se suelta al terminar"


def test_si_fallan_los_tests_la_sesion_lo_dice_y_no_se_recrea(repo):
    r = _desplegar(repo, {"STUB_TESTS_RC": "1"})
    assert r.returncode == 1
    assert "terminó con error" in r.stdout
    assert _estado_final(repo) != "0"
    assert "--force-recreate" not in _llamadas(repo)
    assert not repo["cerrojo"].exists()


def test_no_se_lanzan_dos_despliegues_a_la_vez(repo):
    # Un proceso vivo con el cerrojo: lo lanza el MISMO bash para que `kill -0`
    # lo vea también en Windows.
    guion = ('sleep 20 & P=$!; mkdir -p "$DEPLOY_CERROJO"; echo $P > "$DEPLOY_CERROJO/pid"; '
             './deploy.sh; R=$?; kill $P; exit $R')
    r = subprocess.run([_bash(), "-c", guion], cwd=repo["base"], env=repo["env"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
    assert r.returncode == 1
    assert "Ya hay un despliegue en marcha" in r.stdout
    assert "ultimo.log" in r.stdout
    assert _llamadas(repo) == "", "el segundo no debe tocar ni git ni docker"


def test_un_cerrojo_abandonado_no_bloquea(repo):
    repo["cerrojo"].mkdir()
    (repo["cerrojo"] / "pid").write_text("999999\n")
    r = _desplegar(repo)
    assert r.returncode == 0, r.stdout + r.stderr
    assert not repo["cerrojo"].exists()


def test_recupera_el_estado_que_dejo_el_corte_del_12_09(repo):
    renombrado = "a14bc3e16fc1_" + CONTENEDOR
    (repo["estado"] / "corriendo").write_text("")
    (repo["estado"] / "todos").write_text(renombrado + "\n")
    r = _desplegar(repo)
    assert r.returncode == 0, r.stdout + r.stderr
    llamadas = _llamadas(repo).splitlines()
    i_rename = llamadas.index(f"docker rename {renombrado} {CONTENEDOR}")
    i_backup = llamadas.index("backup")
    assert i_rename < i_backup, "hay que devolverle el nombre ANTES del backup, que lo busca por nombre"
    assert "Terminal recuperada" in r.stdout


def test_si_no_se_puede_recuperar_se_para_antes_del_backup(repo):
    (repo["estado"] / "corriendo").write_text("")
    (repo["estado"] / "todos").write_text("")
    r = _desplegar(repo, {"STUB_UP_NO_ARRANCA": "1"})
    assert r.returncode == 1
    assert "No se ha podido recuperar" in r.stdout
    assert "backup" not in _llamadas(repo)


def test_si_el_despliegue_muere_por_una_senal_no_consta_como_bueno(repo):
    """Encontrado al probar el corte: muerto por una señal, el EXIT veía el
    código de la última orden (0) y el despliegue muerto constaba como bueno."""
    env = dict(repo["env"], STUB_DURACION_TESTS="4")
    sesion = subprocess.Popen([_bash(), "./deploy.sh"], cwd=repo["base"], env=env,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    marca = repo["estado"] / "tests_empezados"
    limite = time.time() + 30
    while not marca.exists() and time.time() < limite:
        time.sleep(0.05)
    pid = (repo["cerrojo"] / "pid").read_text().strip()
    subprocess.run([_bash(), "-c", f"kill -TERM {pid}"], env=repo["env"], check=True)
    salida, _ = sesion.communicate(timeout=30)
    assert sesion.returncode == 1, salida
    assert _estado_final(repo) == "143"
    assert "--force-recreate" not in _llamadas(repo)
    assert not repo["cerrojo"].exists()


@pytest.mark.skipif(not hasattr(os, "killpg"), reason="simular el corte de SSH necesita grupos de procesos (Linux)")
def test_el_despliegue_sigue_aunque_se_corte_la_sesion(repo):
    """Lo que hace un corte de SSH: SIGHUP a todo el grupo de procesos de la
    sesión. Antes eso mataba a docker compose a mitad de recrear."""
    env = dict(repo["env"], STUB_DURACION_TESTS="3")
    sesion = subprocess.Popen([_bash(), "./deploy.sh"], cwd=repo["base"], env=env,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, start_new_session=True)
    marca = repo["estado"] / "tests_empezados"
    limite = time.time() + 30
    while not marca.exists() and time.time() < limite:
        time.sleep(0.05)
    assert marca.exists(), "el despliegue no llegó a los tests"
    os.killpg(sesion.pid, signal.SIGHUP)          # se corta la conexión
    sesion.wait(timeout=10)
    limite = time.time() + 30
    while not list(repo["logs"].glob("deploy-*.log.estado")) and time.time() < limite:
        time.sleep(0.1)
    assert _estado_final(repo) == "0", next(repo["logs"].glob("deploy-*.log")).read_text()
    assert "docker compose up -d --force-recreate" in _llamadas(repo)
    assert not repo["cerrojo"].exists()
