"""
Plazos de conservación y analítica sin nombres.

DOS COSAS QUE UNA POLÍTICA DE PRIVACIDAD NO PUEDE PROMETER SIN CÓDIGO.

1. LOS PLAZOS. Hasta el 18/08/2026 no se purgaba NADA: la analítica y el
   historial del chat crecían desde el primer día y para siempre. Prometer «se
   conserva 90 días» sin nada que lo borre es una promesa vacía -- justo lo que
   este proyecto lleva meses quitando de otros sitios.

2. LOS NOMBRES. `analytics.events` guardaba el email en cada evento: 1.379
   eventos, 478 identificables, 125 personas distintas. Eso no es medir el uso,
   es perfilar personas. Ahora se guarda una huella irreversible, y las
   preguntas que la tabla respondía -- qué secciones se usan, qué tickers se
   miran, cuántas personas distintas vuelven -- se contestan exactamente igual.

POR QUÉ EL HASH LLEVA LA CLAVE DEL SERVIDOR. Un SHA-256 del email a secas NO
sería irreversible en la práctica: el espacio de emails de los usuarios es
pequeño y conocido, así que cualquiera con la base delante podría probarlos uno
a uno hasta que cuadre. Con la clave secreta mezclada (HMAC) eso deja de poder
hacerse sin robar además esa clave. Hay un test que lo comprueba, porque es el
detalle que convierte esto en seudonimización de verdad y no en teatro.

Y EL QUE MÁS IMPORTA DE TODOS: al cambiar el email por el seudónimo, el borrado
de cuenta -- construido unas horas antes -- habría dejado de limpiar la
analítica EN SILENCIO. El DELETE no falla: simplemente no encuentra filas. Ese
es el test que cierra el círculo.

Uso:
    cd backend
    python -m pytest tests/test_retencion_y_seudonimo.py -v
"""
import os
import sqlite3
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import services.analytics_service as A  # noqa: E402

EMAIL = "alguien@local.test"


def _bd_analytics(dias_atras=(0, 10, 200), email=EMAIL, con_columna_email=False):
    """Base temporal con eventos de varias antigüedades."""
    tmp = os.path.join(tempfile.mkdtemp(), "analytics.db")
    with patch.object(A, "DB_PATH", tmp):
        A.init_db()
        conn = sqlite3.connect(tmp)
        for i, d in enumerate(dias_atras):
            ts = (datetime.now(timezone.utc) - timedelta(days=d)).isoformat()
            if con_columna_email:
                conn.execute("INSERT INTO events (ts, event_type, section, ticker, email) "
                             "VALUES (?,?,?,?,?)", (ts, 'page_view', '/market', None, email))
            else:
                conn.execute("INSERT INTO events (ts, event_type, section, ticker, usuario_hash) "
                             "VALUES (?,?,?,?,?)", (ts, 'page_view', '/market', None, A.seudonimo(email)))
        conn.commit(); conn.close()
    return tmp


# ── Seudonimizar de verdad ───────────────────────────────────────────────────

def test_el_seudonimo_es_estable():
    """Si cambiara en cada llamada, `COUNT(DISTINCT ...)` contaría un usuario
    nuevo por evento y la analítica dejaría de servir para nada."""
    assert A.seudonimo(EMAIL) == A.seudonimo(EMAIL)
    assert A.seudonimo("  ALGUIEN@LOCAL.TEST  ") == A.seudonimo(EMAIL), \
        "el mismo email escrito distinto tiene que dar el mismo seudonimo"


def test_personas_distintas_dan_seudonimos_distintos():
    assert A.seudonimo("a@local.test") != A.seudonimo("b@local.test")


def test_el_seudonimo_no_contiene_el_email():
    h = A.seudonimo(EMAIL)
    assert EMAIL not in h and "alguien" not in h and "@" not in h


def test_sin_email_no_hay_seudonimo():
    """Quien no está identificado sigue sin estarlo: no se inventa una huella
    para las visitas anónimas."""
    assert A.seudonimo(None) is None
    assert A.seudonimo("") is None


def test_el_hash_lleva_la_clave_del_servidor_y_no_es_un_sha256_pelado():
    """EL detalle que lo hace seudonimización y no teatro. Con un SHA-256 del
    email a secas, cualquiera con la base delante prueba los emails uno a uno
    hasta que cuadre -- el espacio es pequeño y conocido."""
    import hashlib
    pelado = hashlib.sha256(EMAIL.encode()).hexdigest()[:32]
    assert A.seudonimo(EMAIL) != pelado, \
        "el seudonimo se puede revertir probando emails: falta la clave del servidor"


def test_al_registrar_un_evento_no_se_guarda_el_email():
    tmp = os.path.join(tempfile.mkdtemp(), "analytics.db")
    with patch.object(A, "DB_PATH", tmp):
        A.init_db()
        A.log_page_view("/market", EMAIL)
        A.log_ticker_view("/research", "AAPL", EMAIL)
        conn = sqlite3.connect(tmp)
        filas = conn.execute("SELECT email, usuario_hash FROM events").fetchall()
        conn.close()
    assert len(filas) == 2
    for email, h in filas:
        assert not email, f"se ha guardado el email: {email}"
        assert h == A.seudonimo(EMAIL)


def test_los_eventos_viejos_con_email_se_migran_y_el_email_desaparece():
    """Dejar los antiguos como estaban haría inútil el cambio: la tabla
    seguiría siendo identificable. Se conserva el seudónimo, así que la
    analítica histórica no se pierde."""
    tmp = _bd_analytics(dias_atras=(0, 1), con_columna_email=True)
    with patch.object(A, "DB_PATH", tmp):
        A.init_db()   # la migración corre aquí
        conn = sqlite3.connect(tmp)
        filas = conn.execute("SELECT email, usuario_hash FROM events").fetchall()
        conn.close()
    assert filas, "no deberia haberse borrado nada, solo transformado"
    for email, h in filas:
        assert not email, "el email viejo sigue ahi"
        assert h == A.seudonimo(EMAIL), "se ha perdido a quien pertenecia el evento"


# ── Los plazos ───────────────────────────────────────────────────────────────

def test_la_analitica_purga_lo_que_pasa_de_los_90_dias():
    tmp = _bd_analytics(dias_atras=(0, 10, 89, 91, 200))
    with patch.object(A, "DB_PATH", tmp):
        n = A.purgar_antiguos()
        conn = sqlite3.connect(tmp)
        quedan = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        conn.close()
    assert n == 2, f"purgados {n}: deberian ser los de 91 y 200 dias"
    assert quedan == 3


def test_la_analitica_no_purga_lo_reciente():
    tmp = _bd_analytics(dias_atras=(0, 1, 30))
    with patch.object(A, "DB_PATH", tmp):
        assert A.purgar_antiguos() == 0


def test_el_chat_purga_lo_que_pasa_de_los_30_dias():
    import services.chat_service as C
    tmp = os.path.join(tempfile.mkdtemp(), "chat.db")
    conn = sqlite3.connect(tmp)
    conn.execute("CREATE TABLE mensajes (id INTEGER PRIMARY KEY, usuario TEXT, rol TEXT, mensaje TEXT, creado_en TEXT)")
    for d in (0, 5, 29, 31, 90):
        ts = (datetime.now(timezone.utc) - timedelta(days=d)).isoformat()
        conn.execute("INSERT INTO mensajes (usuario, rol, mensaje, creado_en) VALUES (?,?,?,?)",
                     (EMAIL, 'user', 'hola', ts))
    conn.commit(); conn.close()

    with patch.object(C, "DB_PATH", tmp):
        n = C.purgar_antiguos()
    conn = sqlite3.connect(tmp)
    quedan = conn.execute("SELECT COUNT(*) FROM mensajes").fetchone()[0]
    conn.close()
    assert n == 2, f"purgados {n}: deberian ser los de 31 y 90 dias"
    assert quedan == 3


def test_los_plazos_son_los_que_promete_la_politica():
    """Estos dos numeros aparecen en la politica de privacidad. Cambiarlos aqui
    sin cambiarlos alli convierte el texto en una promesa falsa."""
    import services.chat_service as C
    assert A.RETENCION_DIAS == 90
    assert C.RETENCION_DIAS == 30


# ── Y que el borrado de cuenta siga funcionando ──────────────────────────────

def test_borrar_la_cuenta_sigue_limpiando_la_analitica_tras_el_seudonimo():
    """EL test que cierra el círculo. El borrado de cuenta buscaba por `email`;
    al cambiar la columna, habria dejado de encontrar nada EN SILENCIO -- el
    DELETE no falla, simplemente no toca ninguna fila."""
    import services.datos_personales_service as D
    tmp = _bd_analytics(dias_atras=(0, 1, 2))
    with patch.object(A, "DB_PATH", tmp), \
         patch.object(D, "INVENTARIO", [(tmp, 'events', 'usuario_hash', 'seudonimo')]):
        antes = D.quedan_datos(1, EMAIL)
        r = D.borrar(1, EMAIL)
        despues = D.quedan_datos(1, EMAIL)
    assert antes == {"events": 3}, antes
    assert r["borradas"]["events"] == 3, r
    assert despues == {}, despues


def test_el_inventario_apunta_a_la_columna_nueva_no_a_la_vieja():
    """Sin esto, el fallo de arriba volveria a colarse en cuanto alguien
    reordenara el inventario."""
    import services.datos_personales_service as D
    entrada = [e for e in D.INVENTARIO if e[1] == 'events']
    assert entrada, "la analitica ha desaparecido del inventario de borrado"
    _, _, columna, tipo = entrada[0]
    assert columna == 'usuario_hash', f"el borrado busca por '{columna}', que ya no existe"
    assert tipo == 'seudonimo'
