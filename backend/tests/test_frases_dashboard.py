"""
La frase del día del Dashboard: cada autor con su fuente, y de verdad del día.

EL CASO, Páginas Contenido #8, 10/09/2026. Dos problemas:

1. ATRIBUCIONES. De las 5 frases con autor, rastreadas hasta el original:
   - «El mercado puede permanecer irracional…» — «Keynes». No hay constancia de
     que Keynes la dijera ni la escribiera; la primera fuente conocida es el
     economista A. Gary Shilling, 1986 (Quote Investigator).
   - «El mercado no te gana; te ganas tú mismo al no poder controlar tus
     emociones» — «Livermore». Paráfrasis moderna. El original es de
     «Reminiscences of a Stock Operator» (Edwin Lefèvre, 1923), la vida de
     Livermore novelada, y habla de no saber quedarse quieto, no de emociones.
   - «transferir dinero de los impacientes a los pacientes» — Buffett, pero
     parafraseado. Lo que escribió (carta a los accionistas de 1991) es que la
     bolsa es un «centro de reubicación» donde el dinero pasa «de los activos a
     los pacientes».
   - La de «Engels» (la bolsa como árbol que se sacude) no aparece en ninguna
     fuente, ni en inglés ni en alemán. Se quitó y el usuario pidió volver a
     ponerla: va con su nombre y con «atribuida» en pantalla.
   - Marx: real (carta a su tío Lion Philips, 25/06/1864) pero recortada sin
     avisar y con «sus enemigos» donde el original dice «el enemigo».
   - Buffett, «guerra de clases»: real (a Ben Stein, NYT, 26/11/2006).
   Ahora cada frase con autor lleva su fuente en pantalla.

2. «FRASE DEL DÍA» QUE NO ERA DEL DÍA. Salía al azar y se guardaba por pestaña
   (sessionStorage): cada usuario veía una distinta, y cambiaba al abrir otra
   pestaña, no al cambiar el día. Ahora sale por el día de Madrid: la misma
   para todos ese día, y días seguidos dan frases seguidas.

Verificado en el navegador: el Dashboard pinta la frase de hoy con su fuente;
a las 23:59 y a las 00:01 de Madrid salen días distintos, en verano y en
invierno; diez días seguidos dan las diez frases.

Uso:
    cd backend
    python -m pytest tests/test_frases_dashboard.py -v
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
RUTA_FRASES = os.path.join(RAIZ, "frontend", "pages", "dashboard_frases.js")
FRASES_JS = io.open(RUTA_FRASES, encoding="utf-8").read()
DASHBOARD_JS = io.open(os.path.join(RAIZ, "frontend", "pages", "dashboard.js"), encoding="utf-8").read()

_CADENA = r"'((?:[^'\\]|\\.)*)'"
FRASES = re.findall(r"\{\s*texto: " + _CADENA + r",\s*autor: " + _CADENA
                    + r",\s*fuente: " + _CADENA + r",\s*\}", FRASES_JS)

# Cada autor que sale en pantalla, con la fuente que se comprobó. Una frase con
# un autor que no esté aquí no pasa: primero se rastrea, luego se apunta.
FUENTES_COMPROBADAS = {
    ("Warren Buffett", "a Ben Stein, The New York Times, 26 de noviembre de 2006"),
    ("Warren Buffett", "carta a los accionistas de Berkshire Hathaway, 1991"),
    ("Edwin Lefèvre", "«Reminiscences of a Stock Operator» (1923), la vida de Jesse Livermore novelada"),
    ("A. Gary Shilling", "economista, 1986. Se suele atribuir a Keynes, pero no hay constancia de que él la dijera ni la escribiera"),
    ("Karl Marx", "carta a su tío Lion Philips, 25 de junio de 1864"),
    # Añadidas a petición del usuario el 10/09, cada una comprobada en el original.
    ("Adam Smith", "«La riqueza de las naciones» (1776), libro I, capítulo 10"),
    ("Warren Buffett", "carta a los accionistas de Berkshire Hathaway, 1986"),
    ("John Maynard Keynes", "«Teoría general del empleo, el interés y el dinero» (1936), capítulo 12"),
    ("Mark Twain", "«Pudd’nhead Wilson» (1894), capítulo 13"),
    ("Karl Marx", "«El capital», volumen I (1867), capítulo 10"),
    ("John Kenneth Galbraith", "«Breve historia de la euforia financiera» (1990)"),
    ("Warren Buffett", "carta a los accionistas de Berkshire Hathaway, 2001"),
    ("Friedrich Engels", "«La Bolsa», suplemento al volumen III de «El capital» (1895)"),
    ("Karl Marx", "«El capital», volumen III (1894), capítulo 27"),
}

# Las que se buscaron y NO se encontraron. Salen con nombre porque así lo
# decidió el usuario, pero la pantalla dice que son atribuidas.
ATRIBUIDAS_SIN_FUENTE = {
    ("Friedrich Engels", "atribuida; no se ha localizado en sus obras"),
    ("John Templeton", "atribuida; no se ha localizado dónde lo dijo o lo escribió"),
}


def test_las_frases_se_han_leido_enteras():
    """Si el patrón se saltara alguna, los tests de abajo no la mirarían."""
    assert len(FRASES) == FRASES_JS.count("texto:") >= 21


def test_cada_autor_lleva_la_fuente_que_se_comprobo():
    """EL test de las atribuciones: cada autor, o con la fuente que se
    comprobó, o apuntado como atribuido sin fuente."""
    conocidas = FUENTES_COMPROBADAS | ATRIBUIDAS_SIN_FUENTE
    sin_comprobar = [(a, f) for _, a, f in FRASES if a and (a, f) not in conocidas]
    assert not sin_comprobar, f"autor sin fuente comprobada: {sin_comprobar}"


def test_una_atribuida_lo_dice_en_pantalla():
    assert all(f.startswith("atribuida") for _, f in ATRIBUIDAS_SIN_FUENTE)
    assert not FUENTES_COMPROBADAS & ATRIBUIDAS_SIN_FUENTE


def test_ninguna_fuente_apuntada_se_queda_huerfana():
    usadas = {(a, f) for _, a, f in FRASES if a}
    sobran = (FUENTES_COMPROBADAS | ATRIBUIDAS_SIN_FUENTE) - usadas
    assert not sobran, sobran


def test_una_frase_sin_autor_no_lleva_fuente():
    """Un dicho de mercado no tiene fuente; una fuente sin autor no se pinta."""
    assert not [t for t, a, f in FRASES if f and not a]


def test_no_vuelven_las_atribuciones_falsas():
    autores = {a for _, a, _ in FRASES}
    # Keynes sí sale, con la del casino, que es suya. La de «irracional… solvente» no.
    irracional = [a for t, a, _ in FRASES if "irracional" in t]
    assert irracional == ["A. Gary Shilling"], irracional
    # El pasaje es del libro de Lefèvre, no de algo que escribiera Livermore.
    assert "Jesse Livermore" not in autores
    textos = " ".join(t for t, _, _ in FRASES)
    assert "controlar tus emociones" not in textos
    assert "de los impacientes a los pacientes" not in textos


def test_el_dashboard_pinta_la_frase_del_dia_escapada():
    render = DASHBOARD_JS[DASHBOARD_JS.index("function renderDailyQuote"):]
    render = render[:render.index("\n}\n")]
    assert "fraseDelDia()" in render
    for campo in ("esc(texto)", "esc(autor)", "esc(fuente)"):
        assert campo in render, campo
    assert "DAILY_QUOTES" not in DASHBOARD_JS
    assert "rsu_daily_quote" not in DASHBOARD_JS


def test_el_modulo_de_frases_no_tiene_imports():
    """Así se puede ejecutar fuera del navegador (el test de abajo)."""
    assert not re.search(r"^\s*import\b", FRASES_JS, re.M)


# ── Comportamiento, ejecutado en Node (en CI siempre está: lo exige
#    test_javascript_compila.test_en_CI_tiene_que_haber_Node) ──────────────────

_COMPROBAR = r"""
import { FRASES, fraseDelDia, diaDeMadrid } from './frases.mjs';
const d = (s) => new Date(s);
const fallos = [];
const idx = (f) => FRASES.indexOf(f);

// Cambia a medianoche de Madrid: 22:00 UTC en verano, 23:00 UTC en invierno.
if (diaDeMadrid(d('2026-09-10T22:01:00Z')) - diaDeMadrid(d('2026-09-10T21:59:00Z')) !== 1)
    fallos.push('verano: no cambia a medianoche de Madrid');
if (diaDeMadrid(d('2026-01-15T23:01:00Z')) - diaDeMadrid(d('2026-01-15T22:59:00Z')) !== 1)
    fallos.push('invierno: no cambia a medianoche de Madrid');

// Todo el día de Madrid, la misma frase.
if (fraseDelDia(d('2026-09-09T22:01:00Z')) !== fraseDelDia(d('2026-09-10T21:59:00Z')))
    fallos.push('la frase cambia dentro del mismo día de Madrid');

// Nada de azar: el mismo instante da siempre la misma.
const fija = d('2026-09-10T12:00:00Z');
for (let i = 0; i < 50; i++) if (fraseDelDia(fija) !== fraseDelDia(fija)) { fallos.push('aleatoria'); break; }

// Días seguidos, frases seguidas: en N días salen las N, también al cambiar de año.
for (const inicio of [Date.UTC(2026, 8, 10, 12), Date.UTC(2026, 11, 28, 12)]) {
    const vistas = new Set();
    for (let i = 0; i < FRASES.length; i++) vistas.add(idx(fraseDelDia(new Date(inicio + i * 86400000))));
    if (vistas.size !== FRASES.length) fallos.push('en ' + FRASES.length + ' días seguidos se repite alguna');
}

// Lo que ve cada uno depende del instante, no de su zona horaria.
const instantes = ['2026-09-10T21:59:00Z', '2026-09-10T22:01:00Z', '2026-03-29T00:30:00Z',
                   '2026-10-25T00:30:00Z', '2027-01-01T00:30:00Z'].map(s => idx(fraseDelDia(d(s))));
console.log(JSON.stringify({ fallos, instantes }));
"""


def _node():
    for nombre in ("node", "node.exe"):
        ruta = shutil.which(nombre)
        if ruta:
            return ruta
    return None


@pytest.mark.skipif(_node() is None, reason="Node no está instalado en esta máquina")
def test_la_frase_es_la_del_dia_de_Madrid_este_donde_este_cada_uno():
    """EL test de la rotación: se ejecuta el módulo de verdad, con el reloj
    del sistema en tres zonas horarias distintas."""
    resultados = {}
    with tempfile.TemporaryDirectory() as tmp:
        shutil.copyfile(RUTA_FRASES, os.path.join(tmp, "frases.mjs"))
        with open(os.path.join(tmp, "comprobar.mjs"), "w", encoding="utf-8") as f:
            f.write(_COMPROBAR)
        for zona in ("America/New_York", "Asia/Tokyo", "UTC"):
            r = subprocess.run([_node(), "comprobar.mjs"], cwd=tmp, capture_output=True,
                               text=True, env={**os.environ, "TZ": zona})
            assert r.returncode == 0, r.stderr
            resultados[zona] = json.loads(r.stdout)
    for zona, res in resultados.items():
        assert not res["fallos"], f"{zona}: {res['fallos']}"
    assert len({tuple(r["instantes"]) for r in resultados.values()}) == 1, resultados
