"""
Tesis Admin #23: el contenido de una tesis no se pinta ni se convierte a PDF
como HTML de fiar.

EL CASO. Lo escribe el agente Bull —un modelo de lenguaje que lee páginas
web— y aprobar una tesis es leerla, no revisar su HTML. Comprobado el
13/09/2026:
  · En la PÁGINA (tesis.js), con datos falsos, ticker, nombre, sector, autor,
    resumen y contenido ejecutaban código al abrir la galería o la tesis, y un
    enlace `javascript:` del markdown llegaba intacto. La URL del documento iba
    directa al `src` de un iframe.
  · En el PDF, un `<img>`, `<link>` o `@import` dentro del contenido hacía que
    el SERVIDOR pidiera esas direcciones (12 peticiones a un servidor de
    prueba para 4 recursos): cualquier dirección de la red interna del VPS.

La página se comprobó en el navegador antes y después; aquí queda el candado
estático del frontend y la prueba real del PDF.

Uso:
    cd backend
    python -m pytest tests/test_tesis_sin_html_crudo.py -v
"""
import http.server
import os
import re
import socketserver
import sys
import threading

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

TESIS_JS = os.path.join(os.path.dirname(__file__), '..', '..', 'frontend', 'pages', 'tesis.js')


def _js():
    with open(TESIS_JS, encoding='utf-8') as f:
        return f.read()


# ── Frontend ────────────────────────────────────────────────────────────────

# Campos de texto que llegan de la tesis. Ninguno puede ir pegado a un `+`:
# tienen que pasar antes por esc() (o por una función que escape por dentro).
CAMPOS_DE_TEXTO = ("ticker", "nombre", "resumen", "sector", "autor", "rating",
                   "imagen", "url_doc", "id", "fecha", "riesgo", "contenido",
                   "titulo", "rating_color")
# `+ (item.sector ? '…' + esc(item.sector) …)`: el campo como CONDICIÓN no
# se pinta, por eso se excluye cuando lo sigue un `?`.
_CONCAT_CAMPO = re.compile(r"\+\s*\(?\s*(?:data|item)\.(\w+)\b(?!\s*\?)")


def test_ningun_campo_de_texto_se_concatena_sin_escapar():
    # El nombre del archivo que se descarga no es HTML: se quita esa línea.
    js = "\n".join(l for l in _js().split("\n") if "a.download = " not in l)
    sueltos = sorted({m.group(1) for m in _CONCAT_CAMPO.finditer(js)
                      if m.group(1) in CAMPOS_DE_TEXTO})
    assert not sueltos, f"Campos concatenados sin esc(): {sueltos}"


def test_los_botones_de_rating_escapan():
    # Los ratings del filtro llegan del backend (SELECT DISTINCT rating).
    js = _js()
    filtros = js[js.index("function renderRatingFilters"):]
    filtros = filtros[:filtros.index("\n}\n")]
    assert not re.search(r"\+\s*r\s*\+", filtros), "Un rating concatenado sin esc()"
    assert filtros.count("esc(r)") == 2


def test_las_funciones_que_reciben_datos_escapan_por_dentro():
    js = _js()
    assert "esc(value || 'N/A')" in js, "metricCard debe escapar el valor"
    auto = js[js.index("function autoHeaderHtml"):]
    auto = auto[:auto.index("\n}\n")]
    for campo in ("ticker = esc(ticker)", "rating = esc(rating)", "esc((sector || '').toUpperCase())"):
        assert campo in auto, f"autoHeaderHtml sin escapar: {campo}"
    assert "colorSeguro(color" in auto


def test_el_markdown_no_usa_el_marked_global_y_escapa_el_html():
    js = _js()
    assert "marked.parse(" not in js, \
        "El marked global deja pasar el HTML crudo"
    assert "new window.marked.Marked(" in js
    assert re.search(r"html\(html\)\s*\{\s*return esc\(html\);\s*\}", js), \
        "El renderer de marked debe escapar el HTML crudo"
    for tipo in ("link", "image"):
        cuerpo = js[js.index(tipo + "(href, title, text)"):]
        cuerpo = cuerpo[:cuerpo.index("},")]
        assert "safeUrl(href) === '#'" in cuerpo, f"{tipo} sin validar la URL"


def test_el_iframe_solo_carga_google_docs_o_drive():
    js = _js()
    assert js.count("<iframe") == 1
    antes = js[:js.index("<iframe")].rsplit("\n", 2)[-2]
    assert "_DOC_EMBEBIBLE.test(data.url_doc)" in antes
    patron = re.search(r"const _DOC_EMBEBIBLE = /(.+)/i;", js).group(1)
    embebible = re.compile(patron.replace("\\/", "/"), re.I)
    assert embebible.match("https://docs.google.com/document/d/e/x/pub?embedded=true")
    assert embebible.match("https://drive.google.com/file/d/abc/preview")
    for mala in ("javascript:alert(1)", "http://docs.google.com/x",
                 "https://docs.google.com.malo.com/x", "https://evil.com/?https://docs.google.com/"):
        assert not embebible.match(mala), mala


# ── PDF ─────────────────────────────────────────────────────────────────────

def test_markdown_del_pdf_sin_html_crudo_ni_enlaces_raros():
    md = pytest.importorskip("markdown")
    from services.tesis_service import _markdown_sin_html
    html = _markdown_sin_html(md, (
        "# Titulo\n\n| a | b |\n|---|---|\n| **x** | <b>y</b> |\n\n"
        "```\n<script>1</script>\n```\n\n"
        "[ok](https://a.com) [mal](javascript:alert(1)) [MAL](JaVaScRiPt:x) [ent](&#106;avascript:x)\n\n"
        "<div onclick=x>bloque</div>\n\n<img src=x onerror=alert(1)>"
    ))
    assert "<h1>Titulo</h1>" in html
    assert "<table>" in html and "<strong>x</strong>" in html
    assert '<a href="https://a.com">ok</a>' in html
    assert "<b>" not in html and "<div" not in html and "<img src=x" not in html
    assert "&lt;div onclick=x&gt;" in html
    assert "&lt;script&gt;" in html
    assert not re.search(r'href="(?!https?:|mailto:|#)', html), html


def test_el_pdf_no_hace_que_el_servidor_pida_direcciones():
    pytest.importorskip("markdown")
    pytest.importorskip("xhtml2pdf")
    from services.tesis_service import generar_pdf_tesis
    peticiones = []

    class Registro(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            peticiones.append(self.path)
            self.send_response(404)
            self.end_headers()

        def log_message(self, *a):
            pass

    srv = socketserver.TCPServer(("127.0.0.1", 0), Registro)
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        contenido = (f'Hola\n\n<img src="{base}/img">\n\n'
                     f'<link rel="stylesheet" href="{base}/css">\n\n'
                     f'<style>@import url("{base}/import");</style>\n\n'
                     f'![a]({base}/markdown-img)\n\n'
                     '<a href="javascript:alert(1)">x</a> [y](javascript:alert(2))')
        pdf = generar_pdf_tesis({"ticker": "X", "titulo": "t", "autor": "a", "contenido": contenido})
    finally:
        srv.shutdown()
        srv.server_close()
    assert pdf.startswith(b"%PDF")
    assert peticiones == [], f"El servidor pidió: {peticiones}"
    assert b"javascript" not in pdf
