"""
Genera frontend/pages/academy_manifest.js a partir de academy_lessons.js.

Por qué existe: academy_lessons.js pesa ~525 KB y academy_charts.js ~684 KB.
Antes ambos se importaban de forma ESTÁTICA en academy.js, así que entrar en
Academy descargaba ~1,3 MB aunque el usuario solo quisiera ver el índice de
módulos. El índice, sin embargo, solo necesita saber TRES cosas de cada
lección: que existe, su título, y su extensión (para el tiempo de lectura y
para el denominador de la barra de progreso).

Este script extrae exactamente eso a un fichero de ~8 KB que sí se importa
estáticamente; LESSONS/CHARTS/QUIZZES pasan a import dinámico bajo demanda.

Uso (tras añadir o editar lecciones en academy_lessons.js):
    python scripts/gen_academy_manifest.py

El recuento de palabras sale del contenido real de cada lección (literales de
texto, sin etiquetas HTML) -- es lo que alimenta el "~X min de lectura" que
sustituyó a las duraciones de vídeo heredadas de una versión anterior de
Academy en la que las lecciones iban a ser vídeos que nunca se grabaron.
"""
import os
import re

BASE          = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LESSONS_PATH  = os.path.join(BASE, "frontend", "pages", "academy_lessons.js")
MANIFEST_PATH = os.path.join(BASE, "frontend", "pages", "academy_manifest.js")

PALABRAS_POR_MINUTO = 200   # ritmo de lectura habitual para texto divulgativo

# Clave de lección de primer nivel: "    '12-3': {"
RE_CLAVE   = re.compile(r"^    '(\d+-\d+)':\s*\{", re.MULTILINE)
RE_TITULO  = re.compile(r"title:\s*'((?:[^'\\]|\\.)*)'")
# Literales de cadena JS (comillas simples, con escapes) -- de ahí sale el texto
RE_LITERAL = re.compile(r"'(?:[^'\\]|\\.)*'")
RE_TAG     = re.compile(r"<[^>]+>")
RE_PALABRA = re.compile(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9]+")


def _contar_palabras(bloque: str) -> int:
    texto = " ".join(lit[1:-1] for lit in RE_LITERAL.findall(bloque))
    texto = RE_TAG.sub(" ", texto)
    return len(RE_PALABRA.findall(texto))


def generar() -> dict:
    with open(LESSONS_PATH, encoding="utf-8") as f:
        src = f.read()

    marcas = [(m.group(1), m.start()) for m in RE_CLAVE.finditer(src)]
    if not marcas:
        raise SystemExit("No se encontró ninguna lección — ¿cambió el formato de academy_lessons.js?")

    entradas = {}
    for i, (clave, ini) in enumerate(marcas):
        fin    = marcas[i + 1][1] if i + 1 < len(marcas) else len(src)
        bloque = src[ini:fin]
        titulo = RE_TITULO.search(bloque)
        if not titulo:
            print(f"  ! {clave}: sin título, se omite")
            continue
        entradas[clave] = {
            "titulo":   titulo.group(1).replace("\\'", "'"),
            "palabras": _contar_palabras(bloque),
        }
    return entradas


def escribir(entradas: dict) -> None:
    def orden(clave):
        mod, lec = clave.split("-")
        return (int(mod), int(lec))

    lineas = [
        "// ─────────────────────────────────────────────────────────────────────────────",
        "// RSU ACADEMY — Manifiesto de lecciones (GENERADO, no editar a mano)",
        "//",
        "// Índice ligero de academy_lessons.js: qué lecciones existen, su título y su",
        "// extensión. Se importa de forma ESTÁTICA en academy.js para poder pintar el",
        "// índice de módulos, el tiempo de lectura y la barra de progreso sin cargar",
        "// los ~525 KB de contenido ni los ~684 KB de gráficos.",
        "//",
        "// Regenerar tras añadir o editar lecciones:  python scripts/gen_academy_manifest.py",
        "// ─────────────────────────────────────────────────────────────────────────────",
        "",
        "export const PALABRAS_POR_MINUTO = %d;" % PALABRAS_POR_MINUTO,
        "",
        "export const LESSON_INDEX = {",
    ]
    for clave in sorted(entradas, key=orden):
        e = entradas[clave]
        titulo = e["titulo"].replace("\\", "\\\\").replace("'", "\\'")
        lineas.append("    '%s': { title: '%s', words: %d }," % (clave, titulo, e["palabras"]))
    lineas += ["};", ""]

    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lineas))


if __name__ == "__main__":
    entradas = generar()
    escribir(entradas)
    total = sum(e["palabras"] for e in entradas.values())
    kb    = os.path.getsize(MANIFEST_PATH) / 1024
    print(f"✅ {len(entradas)} lecciones · {total:,} palabras · ~{total // PALABRAS_POR_MINUTO} min de lectura")
    print(f"   {MANIFEST_PATH} ({kb:.1f} KB)")
