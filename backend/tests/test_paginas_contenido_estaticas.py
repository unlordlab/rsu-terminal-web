"""
Páginas Contenido #13 y #17, comprobados el 11/09/2026.

#13 — El Dashboard añadía un <style> idéntico al <head> cada vez que se volvía
a él. Comprobado en el navegador: cinco visitas, cinco bloques iguales. Ahora
se crea una sola vez, con el mismo patrón que manifest.js y academy.js; tras
el cambio, cinco visitas dejan uno.

#17 — Equipo y Roadmap no escapan lo que pintan, y no hace falta: todo su
contenido es texto fijo del propio fichero. Comprobado que ninguno lee nada de
fuera (ni la red, ni la URL). Este test es la condición para que siga siendo
verdad: el día que una de las dos pinte datos de fuera, tiene que escaparlos.

Uso:
    cd backend
    python -m pytest tests/test_paginas_contenido_estaticas.py -v
"""
import io
import os
import re

import pytest

RAIZ = os.path.join(os.path.dirname(__file__), "..", "..")


def _js(nombre):
    return io.open(os.path.join(RAIZ, "frontend", "pages", nombre), encoding="utf-8").read()


def test_el_dashboard_crea_su_estilo_una_sola_vez():
    js = _js("dashboard.js")
    render = js[js.index("export async function render"):]
    render = render[:render.index("\n}\n")]
    crea = render.index("document.createElement('style')")
    guarda = render.rfind("if (!document.getElementById('dashboard-styles'))", 0, crea)
    assert guarda != -1, "el <style> del Dashboard se vuelve a crear en cada visita"
    assert "style.id = 'dashboard-styles';" in render


LEER_DE_FUERA = re.compile(r"\bfetch\(|\bapi\(|authHeader|URLSearchParams|location\.(search|hash)|localStorage|WebSocket")


@pytest.mark.parametrize("pagina", ["equipo.js", "roadmap.js"])
def test_las_paginas_que_no_escapan_no_leen_nada_de_fuera(pagina):
    js = _js(pagina)
    lee = LEER_DE_FUERA.search(js)
    if lee:
        assert "esc(" in js, (
            f"{pagina} ahora lee datos de fuera ({lee.group(0)}) y no escapa nada: "
            f"lo que pinte tiene que pasar por esc() de core/ui.js")
