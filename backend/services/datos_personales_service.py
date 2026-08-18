"""
Los datos de una persona, reunidos y borrables desde un solo sitio.

POR QUÉ HACE FALTA ESTO. Hasta el 18/08/2026 no existía ninguna forma de que
alguien se llevara sus datos ni de que borrara su cuenta. Con el RGPD eso no
son funcionalidades opcionales: el derecho de acceso (art. 15) y el de
supresión (art. 17) son exigibles, y una política de privacidad que los
prometa sin código detrás está mintiendo.

Y hace falta un módulo aparte porque **los datos de una persona están
repartidos en cuatro bases distintas**, cada una creada para lo suyo:

    users.db          -> cuenta, watchlist, alertas, progreso de la academia
    community.db      -> el feedback que haya enviado
    chat_historial.db -> sus preguntas al chat
    analytics.db      -> qué secciones y qué tickers ha mirado

Borrar "la cuenta" tocando solo `users.db` dejaría vivas las otras tres, y esa
es exactamente la clase de borrado a medias que convierte una promesa en un
incumplimiento. El inventario de este fichero es la lista completa, y si algún
día se añade una tabla con datos personales hay que añadirla AQUÍ también --
el test `test_datos_personales.py` comprueba que no se quede ninguna fuera.

UNA COSA QUE NO SE BORRA, Y ESTÁ DECIDIDO ASÍ: los datos de mercado (escaneos,
snapshots, cadenas de opciones) no tienen nada de personal -- son precios
públicos. No se tocan al borrar una cuenta.
"""
import json
import os
import sqlite3

_AQUI = os.path.dirname(__file__)

# Las cuatro bases y cómo se identifica a la persona en cada una. La clave es
# distinta según la tabla: unas guardan el id numérico y otras el email, y eso
# no se puede unificar sin migrar datos existentes.
DB_USERS     = os.path.join(_AQUI, '..', 'users.db')
DB_COMMUNITY = os.path.join(_AQUI, '..', 'community.db')
DB_CHAT      = os.path.join(_AQUI, '..', 'chat_historial.db')
DB_ANALYTICS = os.path.join(_AQUI, '..', 'analytics.db')

# (base, tabla, columna que identifica, tipo de clave)
INVENTARIO = [
    (DB_USERS,     'users',            'id',         'user_id'),
    (DB_USERS,     'watchlist',        'user_id',    'user_id'),
    (DB_USERS,     'alerts',           'user_id',    'user_id'),
    (DB_USERS,     'academy_progress', 'user_id',    'user_id'),
    (DB_USERS,     'academy_quiz',     'user_id',    'user_id'),
    (DB_COMMUNITY, 'feedback',         'user_id',    'user_id'),
    (DB_CHAT,      'mensajes',         'usuario',    'email'),
    (DB_ANALYTICS, 'events',           'email',      'email'),
]


def _filas(db, tabla, columna, valor) -> list:
    """Lee las filas de una persona. Tolerante a que la tabla no exista: las
    bases se crean al usarse por primera vez, así que en una instalación nueva
    puede faltar alguna y eso no es un error."""
    if not os.path.exists(db):
        return []
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in conn.execute(
            f'SELECT * FROM {tabla} WHERE {columna} = ?', (valor,))]
    except sqlite3.OperationalError:
        return []
    finally:
        conn.close()


def exportar(user_id: int, email: str) -> dict:
    """Todo lo que la terminal guarda de una persona, en un JSON que se pueda
    leer sin ser informático (art. 20 RGPD, portabilidad).

    NO se incluye `password_hash`: no es un dato que le sirva de nada a quien
    lo pide y publicarlo solo añade riesgo si el fichero acaba en el sitio
    equivocado. Se dice que existe, que es lo que importa saber."""
    export = {}
    for db, tabla, columna, tipo in INVENTARIO:
        valor = user_id if tipo == 'user_id' else email
        filas = _filas(db, tabla, columna, valor)
        if tabla == 'users':
            for f in filas:
                if 'password_hash' in f:
                    f['password_hash'] = '[no se exporta: es el hash de tu contraseña]'
                # El código de vinculación de Telegram es de un solo uso y de
                # 15 minutos; exportarlo no aporta y es una credencial viva.
                f.pop('telegram_link_code', None)
        export[tabla] = filas

    return {
        "ok": True,
        "email": email,
        "datos": export,
        "nota": ("Esto es todo lo que RSU Terminal guarda asociado a tu cuenta. "
                 "Los datos de mercado (precios, escaneos, cadenas de opciones) no "
                 "van aquí porque no son tuyos ni te identifican: son públicos."),
    }


def borrar(user_id: int, email: str) -> dict:
    """Borra a la persona de las cuatro bases. Devuelve cuántas filas se han
    quitado de cada tabla, porque un borrado que no dice qué borró no se puede
    comprobar -- y este es justo el tipo de operación en la que hay que poder
    demostrar que se hizo.

    Es IRREVERSIBLE: no hay papelera. Quien llama debe haber confirmado la
    identidad antes (ver el endpoint, que exige la contraseña)."""
    borradas = {}
    for db, tabla, columna, tipo in INVENTARIO:
        if not os.path.exists(db):
            continue
        valor = user_id if tipo == 'user_id' else email
        conn = sqlite3.connect(db)
        try:
            cur = conn.execute(f'DELETE FROM {tabla} WHERE {columna} = ?', (valor,))
            borradas[tabla] = cur.rowcount or 0
            conn.commit()
        except sqlite3.OperationalError:
            borradas[tabla] = 0
        finally:
            conn.close()
    return {"ok": True, "borradas": borradas, "total": sum(borradas.values())}


def quedan_datos(user_id: int, email: str) -> dict:
    """Qué queda de una persona después de borrar. Existe para poder
    COMPROBAR el borrado en vez de confiar en que fue bien -- lo usa el test, y
    sirve igual para responder a alguien que pregunte si se le borró de
    verdad."""
    resto = {}
    for db, tabla, columna, tipo in INVENTARIO:
        valor = user_id if tipo == 'user_id' else email
        n = len(_filas(db, tabla, columna, valor))
        if n:
            resto[tabla] = n
    return resto
