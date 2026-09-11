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
# Sin los comentarios: «// Módulo 34 (gaps)» metía «gaps» como si fuera un gráfico.
REGISTRO = "\n".join(l.split("//")[0] for l in GRAFICOS[GRAFICOS.index("export const CHARTS = {"):].splitlines())
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
    bloque = LECCIONES[LECCIONES.index("'33-1': {"):LECCIONES.index("'34-1': {")]
    vsa = [c for c in re.findall(r"type: 'chart', id: '([a-z0-9_]+)'", bloque)]
    assert len(vsa) == 9 and all(c.startswith("vsa_") for c in vsa)


@pytest.mark.parametrize("modulo", [33, 34, 35])
def test_el_quiz_de_los_modulos_nuevos_esta_bien_formado(modulo):
    bloque = QUIZZES[QUIZZES.index(f"    {modulo}: {{"):]
    siguiente = re.search(r"^    \d+: \{", bloque[10:], re.M)
    bloque = bloque[:siguiente.start() + 10] if siguiente else bloque
    preguntas = re.findall(r"\{ q: '(.+?)', options: \[(.+?)\], correct: (\d), explanation: '(.+?)' \}", bloque)
    assert 10 <= len(preguntas) <= 12, len(preguntas)
    for q, opciones, correcta, explicacion in preguntas:
        n = len(re.findall(r"'(?:[^'\\]|\\.)*'", opciones))
        assert n == 4 and int(correcta) < n and len(explicacion) > 30, q
    # Que la buena no caiga siempre en el mismo sitio: se aprendería la posición.
    posiciones = [int(c) for _, _, c, _ in preguntas]
    assert max(posiciones.count(p) for p in set(posiciones)) <= 4, posiciones


# ── El módulo 34: Trading de Gaps ─────────────────────────────────────────────

def test_los_gaps_van_detras_del_modulo_de_confirmacion():
    """La lección 19-5 ya presenta los tres tipos clásicos como confirmación
    de una entrada; el módulo 34 remite a ella y va justo detrás."""
    fase3 = re.search(r"FASE 3[^\n]*modules:\[([\d,\s]+)\]", MODULOS).group(1)
    orden = [int(x) for x in fase3.split(",")]
    assert orden.index(34) == orden.index(19) + 1, orden
    assert "lección 19-5" in LECCIONES[LECCIONES.index("'34-1': {"):]


def test_los_gaps_tienen_sus_cinco_lecciones_y_sus_graficos():
    assert [k for k, m, _ in CLAVES if m == "34"] == ["34-1", "34-2", "34-3", "34-4", "34-5"]
    bloque = LECCIONES[LECCIONES.index("'34-1': {"):LECCIONES.index("'35-1': {")]
    graficos = re.findall(r"type: 'chart', id: '([a-z0-9_]+)'", bloque)
    assert len(set(graficos)) == 10 and all(g.startswith("gap_") for g in graficos), graficos


def test_las_estrategias_del_dia_dicen_que_son_intradia():
    """Varias estrategias son de velas de 5 minutos y la terminal no tiene
    gráficos intradía: la lección lo dice y da la versión en diario."""
    bloque = LECCIONES[LECCIONES.index("'34-4': {"):LECCIONES.index("'34-5': {")]
    assert "velas de 5 minutos" in bloque and "gráfico diario" in bloque


def test_la_tabla_del_relleno_y_su_grafico_dicen_lo_mismo():
    """Las cifras de relleno se midieron el 11/09/2026 (S&P 500, 2023-2026,
    7.015 gaps de al menos un 1%) y están escritas dos veces: en el gráfico y
    en la tabla de la lección 34-3. Si se vuelven a medir y solo se cambia
    una, se contradirían en la misma pantalla."""
    fn = GRAFICOS[GRAFICOS.index("function gap_relleno_estadistica()"):]
    fn = fn[:fn.index("\n}\n")]
    series = [[int(x) for x in grupo.split(",")] for grupo in re.findall(r"v: \[([\d,\s]+)\]", fn)]
    leccion = LECCIONES[LECCIONES.index("'34-3': {"):LECCIONES.index("'34-4': {")]
    filas = re.findall(r"\['(?:<b>)?(1 día|1 semana|1 mes|3 meses|1 año)(?:</b>)?', '(?:<b>)?(\d+)%(?:</b>)?', '(\d+)%', '(\d+)%'\]", leccion)
    assert len(filas) == 5 and len(series) == 3
    for k in range(3):
        assert [int(f[k + 1]) for f in filas] == series[k], (k, filas, series)


# ── El módulo 35: Cómo operan las instituciones ──────────────────────────────

def test_las_instituciones_abren_la_fase_2():
    """Es el porqué de lo que viene detrás: zonas de oferta y demanda (5),
    volumen (8) y el dinero profesional del VSA (33)."""
    fase2 = re.search(r"FASE 2[^\n]*modules:\[([\d,\s]+)\]", MODULOS).group(1)
    orden = [int(x) for x in fase2.split(",")]
    assert orden[0] == 35 and orden.index(35) < orden.index(5) < orden.index(33), orden


def test_las_instituciones_tienen_sus_cinco_lecciones_y_sus_graficos():
    assert [k for k, m, _ in CLAVES if m == "35"] == ["35-1", "35-2", "35-3", "35-4", "35-5"]
    bloque = LECCIONES[LECCIONES.index("'35-1': {"):]
    graficos = re.findall(r"type: 'chart', id: '([a-z0-9_]+)'", bloque)
    assert len(set(graficos)) == 8 and all(g.startswith("inst_") for g in graficos), graficos
    for algoritmo in ("VWAP", "TWAP", "POV", "precio de llegada"):
        assert algoritmo in bloque, algoritmo


def test_la_curva_del_dia_es_la_que_mide_la_terminal():
    """El gráfico del volumen por media hora y el texto de la lección 35-3
    salen de la curva MEDIDA en shared/time_utils.py (_CURVA_VOLUMEN), la que
    usan las alertas de RVOL. Si alguien la vuelve a medir, esto avisa de que
    el gráfico y la lección se han quedado atrás."""
    import sys
    sys.path.insert(0, os.path.join(RAIZ, "shared"))
    from time_utils import _CURVA_VOLUMEN
    puntos = sorted(_CURVA_VOLUMEN)

    def acumulado(minuto):
        for a, b in zip(puntos, puntos[1:]):
            if minuto <= b:
                return _CURVA_VOLUMEN[a] + (_CURVA_VOLUMEN[b] - _CURVA_VOLUMEN[a]) * (minuto - a) / (b - a)
        return 1.0

    medidos = [round((acumulado(m) - acumulado(m - 30) if m > 30 else acumulado(30)) * 100, 1)
               for m in range(30, 391, 30)]
    fn = GRAFICOS[GRAFICOS.index("function inst_curva_u()"):]
    fn = fn[:fn.index("\n}\n")]
    grafico = [float(x) for x in re.search(r"const vol = \[([\d.,\s]+)\];", fn).group(1).split(",")]
    assert len(grafico) == 13
    assert all(abs(a - b) <= 0.2 for a, b in zip(grafico, medidos)), (grafico, medidos)
    leccion = LECCIONES[LECCIONES.index("'35-3': {"):LECCIONES.index("'35-4': {")]
    assert f"cerca del {round(grafico[0])}%" in leccion and f"cerca del {round(grafico[-1])}%" in leccion


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
