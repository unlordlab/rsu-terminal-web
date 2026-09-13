"""
Todo fetch que manda JSON tiene que decir que es JSON.

EL CASO, 13/09/2026. El usuario: «en Watchlist no me deja añadir más tickers».
La causa venía del 08/08 (78e508b, la sesión pasó a una cookie httpOnly): cada
página tenía su propio `authHeader()` y ESE incluía
`'Content-Type': 'application/json'`. La migración los sustituyó por el
compartido de `core/api.js`, que solo devuelve `Authorization`. Sin la cabecera,
`fetch` manda el cuerpo como `text/plain`, y FastAPI 0.115 solo interpreta JSON
cuando la cabecera lo dice: responde **422** sin mirar el contenido.

Desde el 08/08, en silencio, fallaban SEIS envíos:

  - Watchlist: añadir un ticker desde su propia página, y crear una alerta.
  - Academy: marcar una lección como leída, guardar el resultado de un quiz y
    pedir el certificado. La pantalla lo disimulaba — marcaba la lección y la
    desmarcaba al fallar, y los quizzes tragaban el error.
  - Community: enviar feedback.

Lo que SÍ funcionaba (añadir desde Research o el Scanner) va por
`core/ui.js::addToWatchlist`, que pone la cabecera a mano.

Uso:
    cd backend
    python -m pytest tests/test_fetch_json_con_content_type.py -v
"""
import os
import re
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

RAIZ = os.path.join(os.path.dirname(__file__), '..', '..', 'frontend')

_FETCH = re.compile(r"fetch\(\s*([^,()]+?),\s*\{(.*?)\}\s*\)", re.S)


def _sin_cabecera(texto):
    """Las llamadas fetch(url, {…}) que mandan cuerpo y no dicen Content-Type."""
    fuera = []
    for m in _FETCH.finditer(texto):
        opciones = m.group(2)
        if "body" in opciones and "Content-Type" not in opciones and "FormData" not in opciones:
            fuera.append((texto[:m.start()].count("\n") + 1, m.group(1).strip()))
    return fuera


def test_ningun_fetch_manda_json_sin_decir_que_es_json():
    malos = []
    for base, _, nombres in os.walk(RAIZ):
        for n in nombres:
            if not n.endswith(".js"):
                continue
            ruta = os.path.join(base, n)
            for linea, url in _sin_cabecera(open(ruta, encoding="utf-8").read()):
                malos.append(f"{os.path.relpath(ruta, RAIZ)}:{linea} → {url}")
    assert not malos, (
        "fetch con cuerpo y sin 'Content-Type: application/json' (el servidor responde 422):\n  "
        + "\n  ".join(malos))


def test_el_candado_reconoce_la_forma_exacta_que_fallaba():
    """Un candado que no puede fallar no protege nada."""
    viejo = ("const res = await fetch('/api/v1/academy/progress/lesson', {\n"
             "    method: 'POST', headers: authHeader(), body: JSON.stringify({ lesson_key: key })\n"
             "});")
    assert _sin_cabecera(viejo), "no detecta la forma que rompía Academy"
    bueno = viejo.replace("headers: authHeader()",
                          "headers: { ...authHeader(), 'Content-Type': 'application/json' }")
    assert not _sin_cabecera(bueno), "marca como mala la forma arreglada"


def test_el_servidor_de_verdad_rechaza_el_json_sin_cabecera():
    """La prueba de que la cabecera no es un detalle de estilo: el mismo cuerpo,
    con y sin ella, contra el endpoint real de añadir a la watchlist."""
    from fastapi.testclient import TestClient
    import services.users_service as U
    import services.watchlist_service as W

    tmp = tempfile.mkdtemp()
    antes = (U.DB_PATH, W.DB_PATH)
    U.DB_PATH = W.DB_PATH = os.path.join(tmp, "users.db")
    try:
        U.init_db()
        W.init_db()
        conn = U._conn()
        conn.execute("INSERT INTO users (email, password_hash, created_at) "
                     "VALUES ('ana@x.com', 'x', '2026-01-01')")
        conn.commit()
        conn.close()

        from main import app
        from auth import verify_token
        app.dependency_overrides[verify_token] = lambda: {"sub": "ana@x.com", "tv": 0}
        try:
            c = TestClient(app)          # sin `with`: no arranca los bucles de fondo
            sin = c.post("/api/v1/watchlist", content='{"ticker":"NVDA"}',
                         headers={"Content-Type": "text/plain;charset=UTF-8"})
            con = c.post("/api/v1/watchlist", content='{"ticker":"NVDA"}',
                         headers={"Content-Type": "application/json"})
        finally:
            app.dependency_overrides.clear()
        assert sin.status_code == 422, "el servidor ya acepta JSON sin cabecera: este test sobra"
        assert con.status_code == 200 and con.json()["ok"] is True
    finally:
        U.DB_PATH, W.DB_PATH = antes
