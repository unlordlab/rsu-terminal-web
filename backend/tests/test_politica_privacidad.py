"""
Que la política de privacidad no se convierta en mentira con el tiempo.

UNA POLÍTICA NO SE ROMPE EL DÍA QUE SE ESCRIBE: se rompe seis meses después,
cuando alguien añade una tabla con datos personales, o una llamada nueva a un
tercero, o cambia un plazo de conservación, y nadie se acuerda de que hay un
texto que afirma lo contrario. A partir de ese momento el documento no es un
descuido: es una afirmación falsa publicada.

Estos tests son la correa. No comprueban la redacción -- comprueban que las
cosas concretas que el texto AFIRMA sigan siendo ciertas en el código.

Uso:
    cd backend
    python -m pytest tests/test_politica_privacidad.py -v
"""
import io
import os
import re
import sys

from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from main import app  # noqa: E402

POLITICA = os.path.join(os.path.dirname(__file__), '..', '..',
                        'frontend', 'pages', 'privacidad.js')


def _texto() -> str:
    return io.open(POLITICA, encoding='utf-8').read()


# ── Que se pueda leer sin cuenta ─────────────────────────────────────────────

def test_los_datos_del_titular_se_leen_sin_estar_registrado():
    """Quien se está planteando registrarse tiene que poder leer la política
    ANTES de tener cuenta. Si esto exigiera sesión, la política solo la verían
    los que ya han aceptado."""
    with TestClient(app) as c:
        r = c.get("/api/v1/legal/titular")
    assert r.status_code == 200, f"la politica exige sesion: {r.status_code}"
    assert set(r.json()) >= {"nombre", "nif", "email", "completo"}


def test_sin_titular_configurado_se_dice_que_esta_incompleta():
    """Una política sin responsable identificado no sirve. Se dice en vez de
    enseñar un hueco, para que se note."""
    from config import settings
    with TestClient(app) as c:
        d = c.get("/api/v1/legal/titular").json()
    esperado = bool(settings.titular_nombre.strip() and settings.titular_nif.strip()
                    and settings.titular_email.strip())
    assert d["completo"] is esperado


def test_el_dni_no_esta_escrito_en_el_repositorio():
    """EL test que protege lo irreversible. El repositorio es PÚBLICO: un DNI
    escrito en un fichero queda publicado para siempre en el historial de git,
    y de ahí no se quita porque sobrevive en clones y forks. Los datos del
    titular se leen del .env del servidor, nunca del código."""
    raiz = os.path.join(os.path.dirname(__file__), '..', '..')
    patron = re.compile(r"\b\d{8}[A-Za-z]\b")   # forma de un DNI español
    sospechosos = []
    for base, dirs, ficheros in os.walk(raiz):
        dirs[:] = [d for d in dirs if d not in
                   {'.git', 'venv', 'node_modules', '__pycache__', 'assets'}]
        for f in ficheros:
            if not f.endswith(('.js', '.py', '.md', '.yml', '.yaml', '.html', '.json')):
                continue
            ruta = os.path.join(base, f)
            try:
                contenido = io.open(ruta, encoding='utf-8', errors='ignore').read()
            except Exception:
                continue
            for m in patron.findall(contenido):
                sospechosos.append((os.path.relpath(ruta, raiz), m))
    assert not sospechosos, (
        f"posible DNI escrito en el repositorio (que es publico): {sospechosos[:5]}. "
        f"Los datos del titular van en el .env, ver config.py")


# ── Que lo que afirma siga siendo cierto ─────────────────────────────────────

def test_los_plazos_del_texto_son_los_del_codigo():
    """Si alguien cambia un plazo en el código y no aquí, el texto pasa a
    afirmar algo falso."""
    import services.analytics_service as A
    import services.chat_service as C
    t = _texto()
    assert f"{A.RETENCION_DIAS} días" in t, \
        f"la politica no dice los {A.RETENCION_DIAS} dias de analitica que aplica el codigo"
    assert f"{C.RETENCION_DIAS} días" in t, \
        f"la politica no dice los {C.RETENCION_DIAS} dias de chat que aplica el codigo"


def test_el_texto_nombra_a_los_terceros_que_reciben_algo_personal():
    """Groq recibe el texto de las preguntas y Telegram el identificador del
    chat. Son los dos únicos, y los dos tienen que estar dichos."""
    t = _texto()
    for tercero in ("Groq", "Telegram"):
        assert tercero in t, f"la politica no menciona a {tercero}"


def test_el_texto_cubre_las_cuatro_bases_con_datos_personales():
    """El inventario de borrado y el texto tienen que hablar de lo mismo. Si
    aparece una base nueva con datos de persona, esto avisa."""
    import services.datos_personales_service as D
    t = _texto().lower()
    # Cada base tiene su palabra en el texto; no se comprueba el nombre del
    # fichero sino que el concepto esté explicado.
    conceptos = {
        'users.db':          'cuenta',
        'community.db':      'feedback',
        'chat_historial.db': 'chat',
        'analytics.db':      'secciones',
    }
    bases = {os.path.basename(db) for db, _, _, _ in D.INVENTARIO}
    for base in bases:
        assert base in conceptos, (
            f"hay una base con datos personales ({base}) que la politica no contempla: "
            f"añadela al texto y a este test")
        assert conceptos[base] in t, f"la politica no explica los datos de {base}"


def test_se_dice_que_todavia_no_hay_https():
    """Servirse por HTTP es una limitación real de seguridad. Callarla en una
    política de privacidad sería justo el tipo de omisión cómoda que este
    proyecto no se permite."""
    t = _texto()
    assert "HTTPS" in t and "HTTP" in t, "la politica no dice que todavia no hay HTTPS"


def test_se_dice_que_no_hay_analitica_de_terceros_y_es_verdad():
    """El texto afirma que no hay Google Analytics ni píxeles. Si algún día se
    añade uno, esto lo caza."""
    t = _texto()
    assert "Google Analytics" in t, "el texto ya no afirma que no hay analitica de terceros"
    raiz_front = os.path.join(os.path.dirname(__file__), '..', '..', 'frontend')
    rastreadores = ('googletagmanager', 'google-analytics', 'connect.facebook',
                    'hotjar', 'mixpanel', 'segment.com')
    encontrados = []
    for base, dirs, ficheros in os.walk(raiz_front):
        dirs[:] = [d for d in dirs if d not in {'assets', 'vendor', 'node_modules'}]
        for f in ficheros:
            if not f.endswith(('.js', '.html')):
                continue
            c = io.open(os.path.join(base, f), encoding='utf-8', errors='ignore').read().lower()
            encontrados += [r for r in rastreadores if r in c]
    assert not encontrados, (
        f"la politica dice que no hay analitica de terceros, pero se ha encontrado: "
        f"{set(encontrados)}")


def test_las_paginas_publicas_no_piden_datos_que_exigen_sesion():
    """LA REGRESIÓN QUE YA PASÓ, el mismo día. El respaldo por HTTP del ticker
    del topbar pedía /market/indices también en /privacidad; ahí devuelve 401 y
    el interceptor de sesión caducada rebotaba a login -- dejando la política
    inalcanzable para quien no tiene cuenta, que es justo para quien está
    escrita.

    Se protege comprobando que las dos piezas que hacen peticiones al arrancar
    -- el WebSocket y el respaldo del ticker -- consulten la MISMA lista de
    rutas públicas, y que la política esté en ella."""
    front = os.path.join(os.path.dirname(__file__), '..', '..', 'frontend')
    ws = io.open(os.path.join(front, 'core', 'websocket.js'), encoding='utf-8').read()
    tb = io.open(os.path.join(front, 'components', 'topbar.js'), encoding='utf-8').read()

    m = re.search(r"RUTAS_SIN_SESION\s*=\s*\[([^\]]*)\]", ws)
    assert m, "no se encuentra la lista de rutas publicas en websocket.js"
    rutas = m.group(1)
    assert "/privacidad" in rutas, (
        "la politica no esta en RUTAS_SIN_SESION: al abrirla sin cuenta, la "
        "peticion de datos protegidos devuelve 401 y rebota a login")

    assert "export const RUTAS_SIN_SESION" in ws,         "la lista tiene que estar exportada para que no haya dos copias"
    assert "RUTAS_SIN_SESION" in tb, (
        "el respaldo del ticker no consulta la lista: volvera a pedir datos "
        "protegidos en las paginas publicas")
