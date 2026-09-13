"""
Dashboard: «sigue donde lo dejaste» en Academy, y una tarjeta por sección.

EL CASO, Páginas Contenido #20, 11/09/2026. El Dashboard era la misma portada
para todos: nada te devolvía a lo que estabas haciendo. Ahora una tarjeta dice
por dónde seguir en Academy —la siguiente lección del módulo que dejaste a
medias, el quiz que te falta, el primer módulo si no has empezado, el
certificado si ya lo tienes todo, o el módulo nuevo que salió después de tu
certificado— y un clic te lleva ahí.

QUÉ ESTÁ COMPLETO LO DICE EL SERVIDOR, con la misma regla que emite el
certificado (`pendientes` de /api/v1/academy/certificado): la pantalla no
vuelve a calcular el 70% del quiz. La tarjeta solo decide POR DÓNDE seguir, en
el orden en que Academy enseña los módulos (PHASES, que para eso sale ahora a
academy_modulos.js, compartido con Academy).

Y de paso, pedido por el usuario: el Dashboard no enlazaba seis secciones del
menú (Congress Trading, Track Record, Roadmap, Manifiesto, Equipo y
Disclaimer). Ahora un test obliga a que cada sección del menú tenga tarjeta.

Verificado en el navegador con el dashboard.js y el academy.js reales: los
seis casos de la tarjeta, que sin datos o con error del servidor no se pinta,
que el botón lleva a la lección siguiente, y que `/academy?modulo=12` abre el
módulo con sus lecciones leídas marcadas (un valor inventado enseña el índice).

Uso:
    cd backend
    python -m pytest tests/test_academy_continuar.py -v
"""
import io
import json
import os
import re
import shutil
import subprocess
import tempfile

import pytest

from services import academy_certificado as C

RAIZ = os.path.join(os.path.dirname(__file__), "..", "..")


def _js(*partes):
    return io.open(os.path.join(RAIZ, "frontend", *partes), encoding="utf-8").read()


MODULOS_JS = _js("pages", "academy_modulos.js")
CONTINUAR_JS = _js("pages", "academy_continuar.js")
DASHBOARD_JS = _js("pages", "dashboard.js")
ACADEMY_JS = _js("pages", "academy.js")
SIDEBAR_JS = _js("components", "sidebar.js")


def _sin_comentarios(js):
    return "\n".join(l for l in js.splitlines() if not l.strip().startswith("//"))


# ── El servidor: la última lección leída ─────────────────────────────────────

@pytest.fixture
def A(monkeypatch, tmp_path):
    from services import academy_service
    monkeypatch.setattr(academy_service, "DB_PATH", str(tmp_path / "u.db"))
    academy_service.init_db()
    return academy_service


def test_sin_lecciones_no_hay_ultima(A):
    assert A.obtener_progreso(1)["ultima"] is None


def test_la_ultima_es_la_ultima_leida_no_la_mas_alta(A):
    for k in ("12-1", "12-2", "0-1"):
        A.marcar_leccion(1, k)
    assert A.obtener_progreso(1)["ultima"] == "0-1"


def test_releer_una_leccion_no_la_mueve(A):
    """Releer no actualiza la fecha: la última sigue siendo lo último NUEVO."""
    for k in ("3-1", "3-2", "3-1"):
        A.marcar_leccion(1, k)
    assert A.obtener_progreso(1)["ultima"] == "3-2"


def test_la_ultima_es_de_cada_usuario(A):
    A.marcar_leccion(1, "5-1")
    A.marcar_leccion(2, "7-1")
    assert A.obtener_progreso(1)["ultima"] == "5-1"
    assert A.obtener_progreso(2)["ultima"] == "7-1"


# ── El orden de los módulos ──────────────────────────────────────────────────

IDS = [int(x) for x in re.findall(r"^\s+\{ id:(\d+),", MODULOS_JS, re.M)]
EN_FASES = [int(x) for grupo in re.findall(r"modules:\[([\d,\s]+)\]", MODULOS_JS)
            for x in grupo.split(",")]


def test_modulos_y_fases_se_han_leido():
    assert len(IDS) >= 33 and len(EN_FASES) >= 33


def test_cada_modulo_esta_en_UNA_fase():
    """La tarjeta recorre las fases: un módulo fuera de ellas no se
    propondría nunca; uno repetido se propondría dos veces."""
    assert sorted(EN_FASES) == sorted(IDS), (set(IDS) ^ set(EN_FASES))


def test_cada_modulo_que_exige_el_certificado_esta_en_la_lista():
    """Si el certificado exigiera un módulo que la tarjeta no conoce, la
    tarjeta no sabría mandar a nadie ahí."""
    assert set(C.catalogo()) <= set(IDS), set(C.catalogo()) - set(IDS)


def test_academy_y_el_dashboard_usan_la_MISMA_lista():
    assert "export const MODULES" in MODULOS_JS and "export const PHASES" in MODULOS_JS
    assert "const MODULES = [" not in ACADEMY_JS and "const PHASES = [" not in ACADEMY_JS
    for js in (ACADEMY_JS, DASHBOARD_JS):
        assert "from '/pages/academy_modulos.js'" in js


# ── La tarjeta del Dashboard ─────────────────────────────────────────────────

def test_el_dashboard_carga_la_tarjeta():
    render = DASHBOARD_JS[DASHBOARD_JS.index("export async function render"):]
    render = render[:render.index("\n}\n")]
    assert 'id="academy-continuar"' in render
    assert re.search(r"^\s+loadAcademyContinuar\(container\.querySelector\('#academy-continuar'\)\);",
                     render, re.M)


def test_lo_completo_lo_dice_el_servidor():
    """La regla del 70% vive en el servidor. Una segunda regla en la
    pantalla podría decir «completo» donde el certificado dice que no."""
    assert "/api/v1/academy/certificado" in DASHBOARD_JS
    # Solo el bloque de Academy: el resto del Dashboard tiene `opacity:0.75`.
    bloque = DASHBOARD_JS[DASHBOARD_JS.index("// ── ACADEMY: SIGUE DONDE LO DEJASTE"):]
    for js in (bloque, CONTINUAR_JS):
        codigo = _sin_comentarios(js)
        assert "0.7" not in codigo and "70 /" not in codigo and "UMBRAL" not in codigo


def test_el_boton_no_lleva_datos_en_un_onclick():
    tarjeta = DASHBOARD_JS[DASHBOARD_JS.index("function tarjetaAcademy"):]
    tarjeta = tarjeta[:tarjeta.index("\n}\n")]
    assert "onclick" not in tarjeta
    assert "esc(destino)" in tarjeta and "esc(p.modulo.title)" in tarjeta and "esc(p.leccion.title)" in tarjeta


def test_el_modulo_de_continuar_no_tiene_imports():
    assert not re.search(r"^\s*import\b", CONTINUAR_JS, re.M)


# ── Academy abre un módulo desde un enlace ───────────────────────────────────

def test_academy_lee_el_modulo_antes_de_cualquier_await_y_lo_valida():
    render = ACADEMY_JS[ACADEMY_JS.index("export async function render"):]
    render = render[:render.index("\n}\n")]
    assert render.index("get('modulo')") < render.index("await "), "el parámetro se lee después de un await"
    rama = render[render.index("moduloPedido &&"):]
    assert r"/^\d{1,3}$/.test(moduloPedido)" in rama
    assert "MODULES.find(x => x.id === Number(moduloPedido))" in rama
    # Sin esperar al progreso, el módulo saldría con todo sin leer.
    assert rama.index("await progreso;") < rama.index("await renderModuleDetail(container, m);")


# ── Una tarjeta por cada sección del menú ────────────────────────────────────

MENU = re.findall(r"^\s+\{ path: '(/[a-z-]*)',", SIDEBAR_JS[SIDEBAR_JS.index("NAV_ITEMS"):], re.M)
TARJETAS = re.findall(r"^\s+\{ path: '(/[a-z-]+)',\s+icon:", DASHBOARD_JS[DASHBOARD_JS.index("const modules = ["):], re.M)


def test_menu_y_tarjetas_se_han_leido():
    assert len(MENU) >= 23 and len(TARJETAS) >= 22


def test_cada_seccion_del_menu_tiene_su_tarjeta():
    """EL test del enlazado: una sección nueva en el menú lateral sin tarjeta
    en el Dashboard lo tumba."""
    faltan = [p for p in MENU if p != "/" and p not in TARJETAS]
    assert not faltan, f"secciones del menú sin tarjeta en el Dashboard: {faltan}"


def test_ninguna_tarjeta_lleva_a_una_seccion_que_no_existe():
    assert not set(TARJETAS) - set(MENU), set(TARJETAS) - set(MENU)
    assert len(TARJETAS) == len(set(TARJETAS)), "tarjeta repetida"


def test_el_numero_de_modulos_no_esta_escrito_a_mano():
    """Decía «22 módulos» con 33 publicados."""
    assert "' módulos de formación'" in DASHBOARD_JS and "MODULES.length" in DASHBOARD_JS
    assert not re.search(r"\d+ módulos de", DASHBOARD_JS)


# ── Comportamiento de siguientePaso, ejecutado en Node (en CI siempre está) ──

_COMPROBAR = r"""
import { siguientePaso } from './continuar.mjs';
const cat = { orden: [0, 1, 5, 2], modulos: {
    0: { title: 'Intro', lecciones: [{ key: '0-1', title: 'a' }, { key: '0-2', title: 'b' }] },
    1: { title: 'Uno',   lecciones: [{ key: '1-1', title: 'c' }, { key: '1-2', title: 'd' }] },
    2: { title: 'Dos',   lecciones: [{ key: '2-1', title: 'e' }] },
    5: { title: 'Cinco', lecciones: [{ key: '5-1', title: 'f' }, { key: '5-2', title: 'g' }] },
}};
const cert = (pend, emitido = null) => ({ pendientes: pend.map(m => (typeof m === 'object' ? m : { modulo: m, quiz: null })),
    modulos_completos: 4 - pend.length, modulos_total: 4, emitido });
const r = {};
// `?? null` en cada campo: JSON.stringify OMITE los undefined, y el caso del
// certificado (sin módulo ni lección) llegaría a Python con claves de menos.
const f = (nombre, prog, c) => { const p = siguientePaso(prog, c, cat); r[nombre] = p && {
    tipo: p.tipo, modulo: p.modulo ? p.modulo.id : null, leccion: p.leccion ? p.leccion.key : null,
    leidas: p.leidas ?? null, total: p.total ?? null, quiz: p.quiz ?? null }; };
f('empezar',       { lessons: [], ultima: null },            cert([0, 1, 5, 2]));
f('seguir',        { lessons: ['1-1'], ultima: '1-1' },      cert([0, 1, 5, 2]));
f('siguienteFase', { lessons: ['0-1', '0-2', '1-1', '1-2'], ultima: '1-2' }, cert([5, 2]));
f('vuelta',        { lessons: ['2-1', '5-1', '5-2'], ultima: '2-1' },         cert([0, 1]));
f('quiz',          { lessons: ['5-1', '5-2'], ultima: '5-2' }, cert([{ modulo: 5, quiz: 'sin hacer' }, 0, 1, 2]));
f('certificado',   { lessons: ['0-1'], ultima: '0-1' },      cert([]));
f('yaLoTiene',     { lessons: ['0-1'], ultima: '0-1' },      cert([], { codigo: 'RSU-X' }));
f('nuevo',         { lessons: ['0-1', '0-2', '1-1', '1-2', '5-1', '5-2'], ultima: '5-2' }, cert([2], { codigo: 'RSU-X' }));
f('noCuadra',      { lessons: ['0-1', '0-2'], ultima: '0-2' }, cert([0]));
console.log(JSON.stringify(r));
"""

_ESPERADO = {
    "empezar":       {"tipo": "empezar", "modulo": 0, "leccion": "0-1", "leidas": 0, "total": 2, "quiz": None},
    "seguir":        {"tipo": "seguir", "modulo": 1, "leccion": "1-2", "leidas": 1, "total": 2, "quiz": None},
    # Terminado el 1, el siguiente en el orden de Academy es el 5, no el 2.
    "siguienteFase": {"tipo": "seguir", "modulo": 5, "leccion": "5-1", "leidas": 0, "total": 2, "quiz": None},
    # Terminado el último, vuelve al principio a por lo que quedó atrás.
    "vuelta":        {"tipo": "seguir", "modulo": 0, "leccion": "0-1", "leidas": 0, "total": 2, "quiz": None},
    "quiz":          {"tipo": "quiz", "modulo": 5, "leccion": None, "leidas": 2, "total": 2, "quiz": "sin hacer"},
    "certificado":   {"tipo": "certificado", "modulo": None, "leccion": None, "leidas": None, "total": None, "quiz": None},
    "yaLoTiene":     None,
    "nuevo":         {"tipo": "nuevo", "modulo": 2, "leccion": "2-1", "leidas": 0, "total": 1, "quiz": None},
    # El servidor dice que falta algo y aquí no se ve qué: nada, mejor que algo que no cuadra.
    "noCuadra":      None,
}


def _node():
    for nombre in ("node", "node.exe"):
        ruta = shutil.which(nombre)
        if ruta:
            return ruta
    return None


@pytest.mark.skipif(_node() is None, reason="Node no está instalado en esta máquina")
def test_por_donde_sigue_cada_uno():
    """EL test de la tarjeta: se ejecuta el módulo de verdad."""
    with tempfile.TemporaryDirectory() as tmp:
        shutil.copyfile(os.path.join(RAIZ, "frontend", "pages", "academy_continuar.js"),
                        os.path.join(tmp, "continuar.mjs"))
        with open(os.path.join(tmp, "comprobar.mjs"), "w", encoding="utf-8") as f:
            f.write(_COMPROBAR)
        r = subprocess.run([_node(), "comprobar.mjs"], cwd=tmp, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    obtenido = json.loads(r.stdout)
    for caso, esperado in _ESPERADO.items():
        assert obtenido[caso] == esperado, f"{caso}: {obtenido[caso]} != {esperado}"


def test_el_menu_lleva_iconos_y_no_letras():
    """Pedido del usuario el 13/09: iconos en todas las secciones. Una letra
    («D», «Ac») o dos secciones con el mismo icono (Equipo y Comunidad
    compartían 👥; RS/RW y Roadmap, la «R») hacen que el menú no se lea de un
    vistazo, que es para lo que está el icono."""
    iconos = re.findall(r"^\s+\{ path: '(/[a-z-]*)',.*?icon: '([^']+)'",
                        SIDEBAR_JS[SIDEBAR_JS.index("NAV_ITEMS"):], re.M)
    assert iconos, "no se encuentran los iconos del menú"
    letras = [p for p, i in iconos if re.fullmatch(r"[A-Za-z]{1,3}", i)]
    assert not letras, f"secciones con letras en vez de icono: {letras}"
    repetidos = {i for _, i in iconos if [x for _, x in iconos].count(i) > 1}
    assert not repetidos, f"iconos repetidos en el menú: {repetidos}"
