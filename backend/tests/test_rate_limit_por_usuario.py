"""
El límite por usuario volvió a ser por IP el día que la sesión pasó a cookie.

EL CASO, 09/09/2026, verificando la bolsa de hallazgos «sin comprobar» de
Infraestructura. El #5 decía «el rate limiting por usuario en realidad es por
IP», y el código traía un comentario largo explicando cómo se había arreglado:
la clave dejó de ser los primeros 20 caracteres de la cabecera —idénticos para
cualquier JWT— y pasó a ser el hash del token entero.

El arreglo era correcto. Pero el **08/08** la sesión pasó a **cookie httpOnly**
(Páginas Contenido #2), y desde entonces el navegador **ya no manda
`Authorization`**. `_get_key` solo miraba esa cabecera, así que para todo
usuario de navegador `auth` venía vacío, la clave quedaba en `"ip:"` y el
límite volvió a ser **por IP** — que es literalmente el hallazgo que esa
función existe para cerrar.

UN MES ENTERO ASÍ, y sin ninguna señal: no hay error, no hay excepción, no hay
log. Solo dos personas en la misma oficina compartiendo cuota otra vez, y un
comentario en el código afirmando que eso ya no pasaba.

ES EL PATRÓN DE «AUDITAR TODAS LAS RAMAS» visto desde el otro lado: no es que
se arreglara una rama y no su hermana, es que se arregló una capa y otra capa
la deshizo un mes después. `verify_token` empezó a preferir la cookie y nadie
miró quién más leía la cabecera.

Uso:
    cd backend
    python -m pytest tests/test_rate_limit_por_usuario.py -v
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from auth import COOKIE_NAME  # noqa: E402
from middleware import rate_limit as RL  # noqa: E402


class _Peticion:
    """Lo mínimo que mira `_get_key`: cookies, cabeceras e IP."""

    def __init__(self, cookies=None, headers=None, ip="1.2.3.4"):
        self.cookies = cookies or {}
        self.headers = headers or {}
        self.client = type("C", (), {"host": ip})() if ip else None


def _clave(**kw):
    return RL._get_key(_Peticion(**kw))


# ── El caso que se deshizo ───────────────────────────────────────────────────

def test_dos_usuarias_en_la_MISMA_IP_no_comparten_cuota():
    """EL test. Con la sesión en cookie, `_get_key` veía la cabecera vacía y
    las dos caían en la misma clave `"1.2.3.4:"`."""
    ana = _clave(cookies={COOKIE_NAME: "sesion-de-ana"})
    bea = _clave(cookies={COOKIE_NAME: "sesion-de-bea"})
    assert ana != bea, (
        "dos sesiones distintas en la misma IP comparten cuota: el límite es "
        "por IP otra vez, que es justo el hallazgo #5")


def test_la_misma_sesion_SI_comparte_cuota_consigo_misma():
    """La otra mitad: si cada petición diera una clave distinta, no habría
    límite ninguno."""
    a = _clave(cookies={COOKIE_NAME: "sesion-de-ana"})
    b = _clave(cookies={COOKIE_NAME: "sesion-de-ana"})
    assert a == b


def test_la_cookie_MANDA_sobre_la_cabecera():
    """Mismo orden que `verify_token`. Si aquí ganara la cabecera, un token
    viejo en el navegador de alguien que ya usaba la terminal seguiría
    decidiendo su cuota después de un login nuevo."""
    con_las_dos = _clave(cookies={COOKIE_NAME: "sesion-nueva"},
                         headers={"Authorization": "Bearer token-viejo"})
    solo_cookie = _clave(cookies={COOKIE_NAME: "sesion-nueva"})
    assert con_las_dos == solo_cookie


def test_la_cabecera_sigue_valiendo_para_los_tokens_de_SERVICIO():
    """`daily_briefing.py` y el disparador de Options Flow no tienen navegador
    ni cookies. Si la cabecera dejara de contar, todos los servicios caerían en
    la misma clave por IP."""
    uno = _clave(headers={"Authorization": "Bearer token-del-briefing"})
    otro = _clave(headers={"Authorization": "Bearer token-de-options"})
    assert uno != otro
    assert not uno.endswith(":"), "el token de servicio no está entrando en la clave"


def test_sin_credencial_ninguna_se_agrupa_por_IP():
    """Es lo correcto para el tráfico anónimo: no hay usuario al que atribuir
    la cuota, así que responde la IP."""
    assert _clave() == "1.2.3.4:"


def test_IPs_distintas_no_comparten_cuota():
    a = _clave(cookies={COOKIE_NAME: "s"}, ip="1.2.3.4")
    b = _clave(cookies={COOKIE_NAME: "s"}, ip="5.6.7.8")
    assert a != b


def test_sin_cliente_no_revienta():
    """Detrás de algunos proxys `request.client` viene a None. Una excepción
    aquí tumbaría CUALQUIER petición, no solo la limitada."""
    assert _clave(ip=None).startswith("unknown:")


# ── Que no se vuelva a desincronizar ─────────────────────────────────────────

def test_el_nombre_de_la_cookie_se_IMPORTA_no_se_copia():
    """Una constante duplicada es exactamente como esto se desincronizó la
    primera vez. Si alguien renombra la cookie en `auth.py`, este módulo tiene
    que romperse en el import, no seguir mirando un nombre que ya no existe.

    SE COMPRUEBA EL IMPORT, NO EL VALOR. Mi primera versión hacía
    `RL.COOKIE_SESION is COOKIE_NAME` — y **pasaba con una copia literal**,
    porque Python internaliza las cadenas cortas con forma de identificador y
    `is` devuelve True para dos «rsu_session» distintos. El sabotaje de copiar
    la constante se escapaba."""
    import ast
    import inspect
    arbol = ast.parse(inspect.getsource(RL))
    importa = [n for n in ast.walk(arbol)
               if isinstance(n, ast.ImportFrom) and n.module == "auth"
               and any(a.name == "COOKIE_NAME" for a in n.names)]
    assert importa, (
        "el nombre de la cookie no se importa de auth.py: si lo renombran allí, "
        "este módulo seguirá mirando un nombre que ya no existe y el límite "
        "volverá a ser por IP sin que nada falle")
    assert RL.COOKIE_SESION == COOKIE_NAME


def test_la_clave_no_lleva_la_credencial_en_claro():
    """La clave acaba en un diccionario en memoria y en `/rate-limit-stats`,
    que es de admin pero se lee. Un token de sesión en claro ahí es un token
    de sesión más en un sitio más."""
    clave = _clave(cookies={COOKIE_NAME: "sesion-secreta-de-ana"})
    assert "sesion-secreta-de-ana" not in clave
    assert len(clave.split(":")[1]) == 16, "el hash debería ir truncado a 16"
