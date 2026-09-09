"""
El repositorio es PUBLICO y no había nada que impidiera commitear una credencial.

EL CASO, 09/09/2026, al explicar el formato de los tokens de GitHub para poder
leer los logs de Actions. Buscando si el repo ya se protegía de esto, resultó
que **sí y no**: `test_env_example.py` busca claves de OpenAI, Groq, Google y
Telegram... pero **solo dentro de `.env.example`**. Una credencial en cualquier
otro fichero pasaba sin más. Y no había **ningún** patrón de GitHub, justo
cuando se acababa de crear un token para la CLI.

POR QUÉ IMPORTA MÁS DE LO QUE PARECE. El escaneo de secretos de GitHub detecta
y revoca estos formatos automáticamente — llevan una suma de comprobación al
final, por eso no da falsos positivos. Pero eso llega **después del push**: el
token ya ha estado expuesto en un repositorio público, y en git no se borra
nada — sobrevive en el historial, en los clones y en los forks. Un test que
falle ANTES del commit es la diferencia entre un susto y un incidente.

ES EL MISMO CRITERIO que `test_el_dni_no_esta_escrito_en_el_repositorio`, que
ya recorre el árbol entero por lo mismo: hay cosas que, una vez publicadas, no
se pueden retirar.

LO QUE ESTE TEST NO ES. No es un escáner de secretos completo: busca FORMATOS
CONOCIDOS, no entropía. Una contraseña suelta o una clave de un proveedor que
no esté en la lista se le escapan. Cubre lo que este proyecto usa de verdad, y
la lista crece cuando se añade un proveedor.

Uso:
    cd backend
    python -m pytest tests/test_no_hay_secretos_commiteados.py -v
"""
import io
import os
import re
import subprocess

import pytest

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# Los formatos que este proyecto puede llegar a tener delante. Cada uno lleva
# su longitud mínima para no cazar la palabra suelta: `gsk_` a secas aparece en
# documentación y en este mismo fichero.
CREDENCIALES = [
    ("GitHub PAT clásico",      r"ghp_[A-Za-z0-9]{36}"),
    ("GitHub fine-grained",     r"github_pat_[A-Za-z0-9_]{50,}"),
    ("GitHub OAuth (gh CLI)",   r"gho_[A-Za-z0-9]{36}"),
    ("GitHub App usuario",      r"ghu_[A-Za-z0-9]{36}"),
    ("GitHub App servidor",     r"ghs_[A-Za-z0-9]{36}"),
    ("GitHub refresh",          r"ghr_[A-Za-z0-9]{36}"),
    ("OpenAI / Anthropic",      r"sk-[A-Za-z0-9_-]{32,}"),
    ("Groq",                    r"gsk_[A-Za-z0-9]{40,}"),
    ("Google",                  r"AIza[A-Za-z0-9_-]{33,}"),
    ("Telegram bot",            r"\d{8,10}:[A-Za-z0-9_-]{34,}"),
    ("AWS access key",          r"AKIA[A-Z0-9]{16}"),
]

# Este fichero contiene los patrones, así que se detectaría a sí mismo. Es la
# única exclusión, y es por construcción — no un parche para callar un aviso.
EXCLUIDOS = {os.path.basename(__file__)}

BINARIOS = (".png", ".jpg", ".jpeg", ".gif", ".ico", ".webp", ".woff", ".woff2",
            ".ttf", ".pdf", ".zip", ".db", ".sqlite", ".xlsx")


def _ficheros():
    """Lo que git SIGUE, no lo que hay en el disco.

    La primera version recorria el arbol con `os.walk` y marco cuatro
    credenciales de `backend/.env` -- que es LOCAL y esta en `.gitignore`, o
    sea que nunca ha salido de esta maquina. El riesgo no es tener secretos en
    el disco (ahi tienen que estar, es donde se configuran): es que acaben
    COMMITEADOS, que es lo irreversible en un repositorio publico.

    `git ls-files` responde exactamente a esa pregunta, y de paso respeta el
    `.gitignore` sin tener que mantener una lista de exclusiones en paralelo
    que se quedaria vieja.
    """
    salida = subprocess.run(["git", "ls-files", "-z"], cwd=RAIZ,
                            capture_output=True, text=True, timeout=60)
    assert salida.returncode == 0, (
        "no se ha podido preguntar a git que ficheros sigue; sin eso este test "
        "no comprueba nada y no puede pasar en silencio")
    for rel in salida.stdout.split(chr(0)):
        if not rel or os.path.basename(rel) in EXCLUIDOS:
            continue
        if rel.lower().endswith(BINARIOS):
            continue
        yield os.path.join(RAIZ, rel.replace("/", os.sep))


def _buscar(texto):
    return [(nombre, m) for nombre, patron in CREDENCIALES
            for m in re.findall(patron, texto)]


# ── El barrido ───────────────────────────────────────────────────────────────

def _credenciales_en(rutas):
    """El barrido, en una funcion aparte para poder EJECUTARLO con un fichero
    de prueba. Metido dentro del test, el sabotaje de «deja de mirar el
    contenido» se escapaba: sin credenciales que encontrar, un barrido que no
    abre nada y uno que funciona dan el mismo resultado."""
    encontrados = []
    for ruta in rutas:
        try:
            texto = io.open(ruta, encoding="utf-8", errors="ignore").read()
        except Exception:
            continue
        for nombre, valor in _buscar(texto):
            # Se dice el TIPO y donde, nunca el valor: un test que imprime la
            # credencial la copia a los registros del CI, que son publicos.
            encontrados.append(f"{os.path.relpath(ruta, RAIZ)} - {nombre} "
                               f"(empieza por {valor[:8]}...)")
    return encontrados


def test_el_barrido_SI_mira_el_contenido_de_los_ficheros():
    """Se le pone delante un fichero con un token de mentira y se exige que lo
    encuentre. Sin esto, un barrido que no abre ningun fichero pasaria igual,
    porque hoy no hay credenciales que encontrar."""
    import tempfile
    falso = "ghp_" + "a1B2" * 9
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False,
                                     encoding="utf-8") as f:
        f.write("TOKEN = " + repr(falso) + chr(10))
        ruta = f.name
    try:
        hallado = _credenciales_en([ruta])
        assert hallado, "el barrido no abre los ficheros: no comprueba nada"
        assert "GitHub PAT" in hallado[0], hallado
        assert falso not in hallado[0], "el aviso publica la credencial entera"
    finally:
        os.unlink(ruta)


def test_no_hay_ninguna_credencial_en_TODO_el_repositorio():
    """EL test. Antes esto solo se comprobaba en `.env.example`, asi que una
    clave en cualquier otro fichero se subia sin que nada chistara."""
    encontrados = _credenciales_en(_ficheros())
    assert not encontrados, (
        "credenciales en un repositorio PÚBLICO:\n  " + "\n  ".join(encontrados[:10])
        + "\n\nRevócala YA en el proveedor: en git no se borra nada, sobrevive "
          "en el historial, en los clones y en los forks.")


def test_se_barre_el_repositorio_ENTERO_no_un_fichero():
    """Si el recorrido dejara de encontrar ficheros, el test de arriba pasaría
    sin mirar nada — que es exactamente lo que hacía la versión anterior, con
    su único `.env.example`."""
    rutas = list(_ficheros())
    assert len(rutas) > 200, f"solo se están revisando {len(rutas)} ficheros"
    nombres = {os.path.basename(r) for r in rutas}
    for imprescindible in (".env.example", "daily_briefing.py", "market.js"):
        assert imprescindible in nombres, f"el barrido no llega a {imprescindible}"


# ── Que el detector detecte de verdad ────────────────────────────────────────

@pytest.mark.parametrize("nombre,ejemplo", [
    ("GitHub PAT clásico",    "ghp_" + "a1B2" * 9),
    ("GitHub OAuth (gh CLI)", "gho_" + "a1B2" * 9),
    ("GitHub App servidor",   "ghs_" + "a1B2" * 9),
    ("GitHub fine-grained",   "github_pat_" + "a1B2c3D4" * 8),
    ("Groq",                  "gsk_" + "a1B2" * 12),
    ("OpenAI / Anthropic",    "sk-" + "a1B2" * 10),
    ("AWS access key",        "AKIA" + "ABCD1234EFGH5678"),
])
def test_reconoce_cada_formato(nombre, ejemplo):
    """Que el test pase no significa que sepa detectar nada. Aquí se le pone
    delante un ejemplo con la forma exacta de cada uno."""
    hallado = _buscar(f"TOKEN = '{ejemplo}'")
    assert hallado, f"no reconoce el formato de {nombre}"
    assert hallado[0][0] == nombre, f"lo reconoce como {hallado[0][0]}, no como {nombre}"


@pytest.mark.parametrize("texto", [
    "el prefijo ghp_ identifica un PAT clásico",       # documentación
    "gsk_ es el prefijo de Groq",
    "GROQ_API_KEY=tu_clave_aqui",                      # plantilla
    "GITHUB_TOKEN=changeme",
    "sk-lo-que-sea",                                   # demasiado corto
    "AIza",
    "1234567890:corto",
])
def test_no_marca_lo_que_NO_es_una_credencial(texto):
    """La mitad del trabajo. Un detector que marca documentación y plantillas
    se acaba desactivando, y entonces no protege de nada — es lo que ya pasó
    con el guardián de f-strings marcando siete ficheros correctos."""
    assert not _buscar(texto), f"falso positivo con: {texto}"


def test_el_aviso_NO_imprime_la_credencial():
    """Los registros del CI de un repo público son públicos: un test que
    imprime lo que ha encontrado publica el secreto una segunda vez."""
    import inspect
    fuente = inspect.getsource(_credenciales_en)
    assert "valor[:8]" in fuente, "el aviso imprime la credencial entera"
    assert "{valor}" not in fuente


def test_solo_se_excluye_este_fichero():
    """Cada exclusión es un agujero. Esta existe porque el fichero contiene los
    propios patrones; cualquier otra habría que justificarla."""
    assert EXCLUIDOS == {os.path.basename(__file__)}
