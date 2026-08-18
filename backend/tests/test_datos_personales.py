"""
Llevarse los datos y borrar la cuenta: los dos derechos que no tenían código.

POR QUÉ EXISTE ESTO. Hasta el 18/08/2026 no había forma de que nadie se
llevara sus datos ni de que borrara su cuenta. Con el RGPD el derecho de
acceso (art. 15), el de portabilidad (art. 20) y el de supresión (art. 17) son
exigibles, y una política de privacidad que los prometa sin código detrás es
papel mojado. Se construyó ANTES de redactar la política, a propósito: para
que el texto describa un sistema que ya cumple en vez de uno que promete.

LO QUE DE VERDAD SE PROTEGE AQUÍ es el borrado a medias. Los datos de una
persona viven en CUATRO bases distintas:

    users.db          -> cuenta, watchlist, alertas, progreso de la academia
    community.db      -> el feedback que haya enviado
    chat_historial.db -> sus preguntas al chat
    analytics.db      -> qué secciones y qué tickers ha mirado

Borrar "la cuenta" tocando solo `users.db` deja vivas las otras tres. Y eso no
es un fallo hipotético: en esa misma sesión ya había pasado dos veces arreglar
una rama y dejar viva la de al lado (los NaN de CANSLIM, los del WebSocket).
Por eso hay un test que recorre el inventario entero y otro que comprueba que
el inventario no se haya quedado corto respecto a las tablas que existen.

Uso:
    cd backend
    python -m pytest tests/test_datos_personales.py -v
"""
import os
import sqlite3
import sys
import tempfile
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import services.datos_personales_service as D  # noqa: E402

EMAIL = "borrame@local.test"
USER_ID = 4242


@pytest.fixture
def bases():
    """Cuatro bases temporales con datos de dos personas: la que se borra y
    otra que NO debe tocarse. Sin la segunda, un `DELETE` sin `WHERE` pasaría
    todos los tests."""
    tmp = tempfile.mkdtemp()
    rutas = {}
    for nombre in ('users', 'community', 'chat', 'analytics'):
        rutas[nombre] = os.path.join(tmp, f"{nombre}.db")

    u = sqlite3.connect(rutas['users'])
    u.executescript("""
        CREATE TABLE users (id INTEGER PRIMARY KEY, email TEXT, password_hash TEXT,
                            tier TEXT, telegram_link_code TEXT);
        CREATE TABLE watchlist (id INTEGER PRIMARY KEY, user_id INTEGER, ticker TEXT);
        CREATE TABLE alerts (id INTEGER PRIMARY KEY, user_id INTEGER, ticker TEXT);
        CREATE TABLE academy_progress (user_id INTEGER, lesson_key TEXT);
        CREATE TABLE academy_quiz (user_id INTEGER, module_id TEXT, score INTEGER);
    """)
    u.execute("INSERT INTO users VALUES (?,?,?,?,?)",
              (USER_ID, EMAIL, "$2b$12$hashfalso", "tier1", "ABC123"))
    u.execute("INSERT INTO users VALUES (?,?,?,?,?)",
              (999, "otro@local.test", "$2b$12$otro", "free", None))
    u.execute("INSERT INTO watchlist VALUES (1,?,'AAPL')", (USER_ID,))
    u.execute("INSERT INTO watchlist VALUES (2,?,'NVDA')", (USER_ID,))
    u.execute("INSERT INTO watchlist VALUES (3,999,'TSLA')")
    u.execute("INSERT INTO alerts VALUES (1,?,'AAPL')", (USER_ID,))
    u.execute("INSERT INTO academy_progress VALUES (?,'leccion-1')", (USER_ID,))
    u.execute("INSERT INTO academy_quiz VALUES (?,'mod-1',8)", (USER_ID,))
    u.commit(); u.close()

    c = sqlite3.connect(rutas['community'])
    c.execute("CREATE TABLE feedback (id INTEGER PRIMARY KEY, user_id INTEGER, mensaje TEXT)")
    c.execute("INSERT INTO feedback VALUES (1,?,'una sugerencia')", (USER_ID,))
    c.execute("INSERT INTO feedback VALUES (2,999,'de otro')")
    c.commit(); c.close()

    ch = sqlite3.connect(rutas['chat'])
    ch.execute("CREATE TABLE mensajes (id INTEGER PRIMARY KEY, usuario TEXT, mensaje TEXT)")
    ch.execute("INSERT INTO mensajes VALUES (1,?,'que es el RSU Score')", (EMAIL,))
    ch.execute("INSERT INTO mensajes VALUES (2,'otro@local.test','otra cosa')")
    ch.commit(); ch.close()

    a = sqlite3.connect(rutas['analytics'])
    a.execute("CREATE TABLE events (id INTEGER PRIMARY KEY, ts TEXT, event_type TEXT, section TEXT, ticker TEXT, email TEXT)")
    for i in range(5):
        a.execute("INSERT INTO events VALUES (?,?,?,?,?,?)",
                  (i, "2026-08-18", "page_view", "/market", None, EMAIL))
    a.execute("INSERT INTO events VALUES (99,'2026-08-18','page_view','/market',NULL,'otro@local.test')")
    a.commit(); a.close()

    with patch.object(D, "DB_USERS", rutas['users']), \
         patch.object(D, "DB_COMMUNITY", rutas['community']), \
         patch.object(D, "DB_CHAT", rutas['chat']), \
         patch.object(D, "DB_ANALYTICS", rutas['analytics']), \
         patch.object(D, "INVENTARIO", [
             (rutas['users'],     'users',            'id',      'user_id'),
             (rutas['users'],     'watchlist',        'user_id', 'user_id'),
             (rutas['users'],     'alerts',           'user_id', 'user_id'),
             (rutas['users'],     'academy_progress', 'user_id', 'user_id'),
             (rutas['users'],     'academy_quiz',     'user_id', 'user_id'),
             (rutas['community'], 'feedback',         'user_id', 'user_id'),
             (rutas['chat'],      'mensajes',         'usuario', 'email'),
             (rutas['analytics'], 'events',           'email',   'email'),
         ]):
        yield rutas


# ── Llevarse los datos ───────────────────────────────────────────────────────

def test_la_exportacion_trae_las_cuatro_bases_no_solo_la_cuenta(bases):
    d = D.exportar(USER_ID, EMAIL)["datos"]
    assert len(d["users"]) == 1
    assert len(d["watchlist"]) == 2
    assert len(d["alerts"]) == 1
    assert len(d["academy_progress"]) == 1
    assert len(d["academy_quiz"]) == 1
    assert len(d["feedback"]) == 1, "el feedback vive en otra base y se olvida fácil"
    assert len(d["mensajes"]) == 1, "el historial del chat vive en otra base"
    assert len(d["events"]) == 5, "la analítica vive en otra base"


def test_la_exportacion_no_saca_el_hash_de_la_contraseña(bases):
    """No le sirve de nada a quien lo pide y añade riesgo si el fichero acaba
    donde no debe. Se dice que existe, que es lo que importa."""
    u = D.exportar(USER_ID, EMAIL)["datos"]["users"][0]
    assert "$2b$" not in str(u.get("password_hash", ""))
    assert "password_hash" in u, "hay que decir que existe, no ocultarlo"


def test_la_exportacion_no_saca_el_codigo_de_vinculacion(bases):
    """Es una credencial viva de un solo uso: exportarla no aporta nada."""
    assert "telegram_link_code" not in D.exportar(USER_ID, EMAIL)["datos"]["users"][0]


def test_no_se_exportan_los_datos_de_otra_persona(bases):
    d = D.exportar(USER_ID, EMAIL)["datos"]
    assert all(f["ticker"] != "TSLA" for f in d["watchlist"])
    assert all("otro@local.test" not in str(f.values()) for f in d["events"])


# ── Borrar ───────────────────────────────────────────────────────────────────

def test_el_borrado_limpia_LAS_CUATRO_bases(bases):
    """EL test. Borrar solo `users.db` dejaría vivos el feedback, el historial
    del chat y toda la analítica -- que es justo el borrado a medias que
    convierte una promesa en un incumplimiento."""
    r = D.borrar(USER_ID, EMAIL)
    assert r["ok"] is True
    assert D.quedan_datos(USER_ID, EMAIL) == {}, D.quedan_datos(USER_ID, EMAIL)
    # 1 users + 2 watchlist + 1 alerta + 1 progreso + 1 quiz + 1 feedback
    # + 1 mensaje de chat + 5 eventos de analitica
    assert r["total"] == 13, r["borradas"]


def test_el_borrado_dice_cuanto_borro_de_cada_tabla(bases):
    """Un borrado que no dice qué borró no se puede comprobar, y este es justo
    el tipo de operación en la que hay que poder demostrar que se hizo."""
    b = D.borrar(USER_ID, EMAIL)["borradas"]
    assert b["users"] == 1 and b["watchlist"] == 2 and b["events"] == 5
    assert b["mensajes"] == 1 and b["feedback"] == 1


def test_el_borrado_no_toca_a_nadie_mas(bases):
    """Sin esta comprobación, un DELETE sin WHERE pasaría todos los demás
    tests de este fichero."""
    D.borrar(USER_ID, EMAIL)
    u = sqlite3.connect(bases['users'])
    assert u.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 1
    assert u.execute("SELECT COUNT(*) FROM watchlist").fetchone()[0] == 1
    u.close()
    a = sqlite3.connect(bases['analytics'])
    assert a.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 1
    a.close()
    c = sqlite3.connect(bases['community'])
    assert c.execute("SELECT COUNT(*) FROM feedback").fetchone()[0] == 1
    c.close()


def test_una_base_que_no_existe_no_rompe_el_borrado(bases):
    """En una instalación nueva puede faltar alguna base: se crean al usarse
    por primera vez. Eso no es un error y no debe abortar el borrado del
    resto."""
    os.remove(bases['chat'])
    r = D.borrar(USER_ID, EMAIL)
    assert r["ok"] is True
    assert r["borradas"]["users"] == 1


# ── Que el inventario no se quede corto ──────────────────────────────────────

def test_el_inventario_cubre_todas_las_tablas_con_datos_de_persona():
    """Lo que de verdad falla en esto no es el borrado: es que alguien añada
    una tabla nueva con `user_id` o `email` y no la apunte aquí. Este test
    mira las bases REALES y compara.

    Si falla, no hay que tocar el test: hay que añadir la tabla nueva al
    INVENTARIO de datos_personales_service.py."""
    import services.datos_personales_service as real
    inventariadas = {(os.path.basename(db), tabla) for db, tabla, _, _ in real.INVENTARIO}

    sospechosas = set()
    for db in (real.DB_USERS, real.DB_COMMUNITY, real.DB_CHAT, real.DB_ANALYTICS):
        if not os.path.exists(db):
            continue
        conn = sqlite3.connect(db)
        for (tabla,) in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"):
            cols = {r[1] for r in conn.execute(f"PRAGMA table_info({tabla})")}
            # `id` a secas no cuenta: lo tienen todas. Se busca la marca de que
            # la fila pertenece a ALGUIEN.
            if cols & {"user_id", "email", "usuario", "user_email"}:
                sospechosas.add((os.path.basename(db), tabla))
        conn.close()

    faltan = sospechosas - inventariadas
    assert not faltan, (
        f"tablas con datos de persona que NO se exportan ni se borran: {sorted(faltan)}. "
        f"Añádelas al INVENTARIO de datos_personales_service.py")
