"""
El contenido de Academy se sostiene: cada gráfico citado existe y se dibuja,
cada lección está donde dice estar, y el módulo 33 (VSA) en su sitio.

EL CASO, 11/09/2026. Al añadir el módulo 33 —Volume Spread Analysis, 5
lecciones y 9 gráficos nuevos— no había nada que comprobara lo más básico del
contenido: una lección que cita un gráfico que no está registrado no falla en
ningún lado, enseña un recuadro gris con «Gráfico: nombre» en vez del dibujo.
Tampoco se comprobaba que los 376 gráficos se dibujaran sin un `NaN` en una
coordenada (un SVG con NaN se pinta roto o vacío, sin error en la consola).

Contado al escribirlo: 154 lecciones, 376 gráficos citados, ninguno roto.

Uso:
    cd backend
    python -m pytest tests/test_academy_contenido.py -v
"""
import io
import json
import os
import re
import shutil
import subprocess
import tempfile

import pytest

RAIZ = os.path.join(os.path.dirname(__file__), "..", "..")
PAGINAS = os.path.join(RAIZ, "frontend", "pages")


def _js(nombre):
    return io.open(os.path.join(PAGINAS, nombre), encoding="utf-8").read()


LECCIONES = _js("academy_lessons.js")
GRAFICOS = _js("academy_charts.js")
QUIZZES = _js("academy_quizzes.js")
MODULOS = _js("academy_modulos.js")

CITADOS = re.findall(r"type: 'chart', id: '([a-z0-9_]+)'", LECCIONES)
REGISTRO = GRAFICOS[GRAFICOS.index("export const CHARTS = {"):]
REGISTRADOS = set(re.findall(r"\b([a-z][a-z0-9_]*)\b", REGISTRO)) - {"export", "const"}
DEFINIDOS = set(re.findall(r"^function ([a-z][a-z0-9_]*)\(", GRAFICOS, re.M))
CLAVES = re.findall(r"^    '(\d+-\d+)': \{\s*moduleId: (\d+),\s*lessonIndex: (\d+),", LECCIONES, re.M)


def test_se_ha_leido_el_contenido():
    assert len(CITADOS) >= 376 and len(CLAVES) >= 154 and len(DEFINIDOS) >= 300


def test_cada_grafico_citado_esta_registrado():
    """EL test: si no, la lección enseña «Gráfico: nombre» en vez del dibujo."""
    faltan = sorted(set(CITADOS) - REGISTRADOS)
    assert not faltan, f"gráficos citados en una lección y no registrados en CHARTS: {faltan}"


def test_cada_grafico_registrado_esta_definido():
    assert not REGISTRADOS - DEFINIDOS, sorted(REGISTRADOS - DEFINIDOS)


def test_un_grafico_roto_no_impide_abrir_la_leccion():
    """La 8-4 estuvo dos meses sin poder abrirse porque su primer gráfico
    lanzaba un error y nada lo recogía. Y como el certificado exige leer
    todas las lecciones, nadie podía conseguirlo. Ahora un gráfico que falla
    deja un hueco y la lección se abre igual."""
    academy = _js("academy.js")
    caso = academy[academy.index("case 'chart': {"):]
    caso = caso[:caso.index("case 'divider'")]
    assert re.search(r"try \{ return `<div class=\"ac-chart\">\$\{chartFn\(\)\}</div>`; \}", caso)
    assert "catch (e)" in caso and "return hueco;" in caso


def test_cada_leccion_esta_donde_dice_su_clave():
    """'33-2' tiene que ser moduleId 33 y lessonIndex 1: el progreso y el
    certificado cuentan por la clave, y la pantalla por los dos campos."""
    mal = [k for k, m, i in CLAVES if k != f"{m}-{int(i) + 1}"]
    assert not mal, mal
    assert len({k for k, _, _ in CLAVES}) == len(CLAVES), "lección repetida"


def test_cada_modulo_tiene_su_quiz():
    ids = {int(x) for x in re.findall(r"^\s+\{ id:(\d+),", MODULOS, re.M)}
    con_quiz = {int(x) for x in re.findall(r"^    (\d+): \{", QUIZZES, re.M)}
    assert ids and not ids - con_quiz, sorted(ids - con_quiz)


# ── El módulo 33: Volume Spread Analysis ─────────────────────────────────────

def test_el_VSA_va_detras_del_modulo_de_volumen():
    """Se apoya en el módulo 8 (volumen básico y clímax) y remite a él en vez
    de repetirlo: tiene que venir justo después."""
    fase2 = re.search(r"FASE 2[^\n]*modules:\[([\d,\s]+)\]", MODULOS).group(1)
    orden = [int(x) for x in fase2.split(",")]
    assert orden.index(33) == orden.index(8) + 1, orden


def test_el_VSA_tiene_sus_cinco_lecciones_y_sus_graficos():
    claves = [k for k, m, _ in CLAVES if m == "33"]
    assert claves == ["33-1", "33-2", "33-3", "33-4", "33-5"]
    bloque = LECCIONES[LECCIONES.index("'33-1': {"):]
    vsa = [c for c in re.findall(r"type: 'chart', id: '([a-z0-9_]+)'", bloque)]
    assert len(vsa) == 9 and all(c.startswith("vsa_") for c in vsa)


def test_el_quiz_del_VSA_esta_bien_formado():
    bloque = QUIZZES[QUIZZES.index("    33: {"):]
    preguntas = re.findall(r"\{ q: '(.+?)', options: \[(.+?)\], correct: (\d), explanation: '(.+?)' \}", bloque)
    assert len(preguntas) == 10
    for q, opciones, correcta, explicacion in preguntas:
        n = len(re.findall(r"'(?:[^'\\]|\\.)*'", opciones))
        assert n == 4 and int(correcta) < n and len(explicacion) > 30, q
    # Que la buena no caiga siempre en el mismo sitio: se aprendería la posición.
    posiciones = [int(c) for _, _, c, _ in preguntas]
    assert max(posiciones.count(p) for p in set(posiciones)) <= 4, posiciones


# ── Todos los gráficos se dibujan, ejecutados en Node (en CI siempre está) ──

_DIBUJAR = r"""
import { CHARTS } from './graficos.mjs';
const rotos = [];
for (const [id, fn] of Object.entries(CHARTS)) {
    let svg;
    try { svg = fn(); } catch (e) { rotos.push(id + ': ' + e.message); continue; }
    if (typeof svg !== 'string' || !svg.trim().startsWith('<svg')) rotos.push(id + ': no devuelve un SVG');
    else if (/NaN|undefined|Infinity/.test(svg)) rotos.push(id + ': ' + (svg.match(/.{0,40}(NaN|undefined|Infinity).{0,20}/) || [''])[0]);
}
console.log(JSON.stringify({ total: Object.keys(CHARTS).length, rotos }));
"""


def _node():
    for nombre in ("node", "node.exe"):
        ruta = shutil.which(nombre)
        if ruta:
            return ruta
    return None


@pytest.mark.skipif(_node() is None, reason="Node no está instalado en esta máquina")
def test_cada_grafico_se_dibuja_sin_NaN():
    assert not re.search(r"^\s*import\b", GRAFICOS, re.M), "academy_charts.js ya no se puede ejecutar suelto"
    with tempfile.TemporaryDirectory() as tmp:
        shutil.copyfile(os.path.join(PAGINAS, "academy_charts.js"), os.path.join(tmp, "graficos.mjs"))
        with open(os.path.join(tmp, "dibujar.mjs"), "w", encoding="utf-8") as f:
            f.write(_DIBUJAR)
        r = subprocess.run([_node(), "dibujar.mjs"], cwd=tmp, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    res = json.loads(r.stdout)
    assert res["total"] >= 300
    assert not res["rotos"], "gráficos que no se dibujan bien:\n  " + "\n  ".join(res["rotos"])
