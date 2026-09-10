"""
Certificado de finalización de RSU Academy (Páginas Contenido #23).

DECISIONES DEL USUARIO, 10/09/2026: un solo certificado al completarlo todo;
cada módulo exige todas sus lecciones leídas y su quiz con un 70% o más de
aciertos a la primera (cuenta el mejor intento); la Guía de la Terminal entra;
PDF con código único, sin página pública de verificación hasta tener HTTPS.

LO QUE ATA ESTE FICHERO, además de las reglas:

  - Que el servidor lee el catálogo REAL de los mismos ficheros que pinta la
    pantalla. Contado el 10/09: 33 módulos, 149 lecciones, 259 preguntas. El
    lector se validó contra un segundo recuento —260 `{ q:` en el fichero— y la
    diferencia es el ejemplo del comentario de cabecera, que NO es una pregunta.
  - Que un certificado emitido no caduca: ni si crece el catálogo (la Guía se
    irá ampliando) ni si la persona reinicia su progreso.
  - Que el PDF sale en UNA página. La primera maqueta, con divs anidados,
    xhtml2pdf la partió en dos y le puso borde a cada bloque.

LO QUE NO ATA, porque no es verdad: que no se pueda hacer trampa. El progreso
lo reporta el navegador; el certificado es tan fiable como ese progreso.

Uso:
    cd backend
    python -m pytest tests/test_academy_certificado.py -v
"""
import io
import os
import re
import sqlite3
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services import academy_certificado as C  # noqa: E402


def _cat(*modulos, preguntas=7):
    """Catálogo pequeño: {modulo: n_lecciones}."""
    return {m: {"lecciones": [f"{m}-{i}" for i in range(1, n + 1)], "preguntas": preguntas}
            for m, n in modulos}


def _todo(cat, score=None):
    leidas = [k for c in cat.values() for k in c["lecciones"]]
    quizzes = {str(m): {"score": c["preguntas"] if score is None else score, "total": c["preguntas"]}
               for m, c in cat.items()}
    return leidas, quizzes


# ── El catálogo real ─────────────────────────────────────────────────────────

def test_el_catalogo_se_lee_de_los_ficheros_de_la_pantalla():
    """Con cotas inferiores y no cifras exactas: el contenido crece, y un test
    que fallara cada vez que Elia propone una lección no serviría de nada."""
    cat = C.catalogo()
    assert len(cat) >= 33
    assert sum(len(c["lecciones"]) for c in cat.values()) >= 149
    assert all(c["preguntas"] > 0 for c in cat.values()), (
        "hay un módulo sin quiz: o se ha quedado sin él, o el lector ya no lo encuentra")


def test_la_Guia_de_la_Terminal_esta_dentro():
    """Decisión del usuario. Los módulos 26 a 32 son la Guía."""
    cat = C.catalogo()
    assert all(m in cat for m in range(26, 33))


def test_el_recuento_de_preguntas_cuadra_por_otro_camino():
    """Segundo recuento: todas las `{ q:` que NO están en un comentario. El
    ejemplo de la cabecera del fichero no es una pregunta."""
    texto = io.open(C.QUIZZES, encoding="utf-8").read()
    reales = sum(len(re.findall(r"\{\s*q\s*:", l)) for l in texto.splitlines()
                 if not l.strip().startswith("//"))
    assert sum(c["preguntas"] for c in C.catalogo().values()) == reales


def test_el_catalogo_se_relee_si_cambian_los_ficheros(monkeypatch, tmp_path):
    """Un despliegue con un módulo nuevo tiene que exigirlo sin reiniciar."""
    man, qz = tmp_path / "m.js", tmp_path / "q.js"
    man.write_text("export const LESSON_INDEX = {\n    '0-1': {},\n};\n", encoding="utf-8")
    qz.write_text("export const QUIZZES = {\n    0: {\n        questions: [ { q: 'a' } ]\n    },\n};\n",
                  encoding="utf-8")
    monkeypatch.setattr(C, "MANIFEST", str(man))
    monkeypatch.setattr(C, "QUIZZES", str(qz))
    monkeypatch.setattr(C, "_cache", {"clave": None, "catalogo": None})
    assert list(C.catalogo()) == [0]
    man.write_text("export const LESSON_INDEX = {\n    '0-1': {},\n    '1-1': {},\n};\n", encoding="utf-8")
    os.utime(man, (os.path.getatime(man), os.path.getmtime(man) + 5))
    assert sorted(C.catalogo()) == [0, 1]


# ── Quién ha completado qué ──────────────────────────────────────────────────

def test_sin_nada_hecho_no_es_elegible_y_falta_todo():
    cat = _cat((0, 4), (1, 5))
    e = C.evaluar([], {}, cat)
    assert not e["elegible"] and e["modulos_completos"] == 0
    assert [p["modulo"] for p in e["pendientes"]] == [0, 1]
    assert e["pendientes"][0]["quiz"] == "sin hacer"


def test_todo_leido_y_todos_los_quizzes_bien_ES_elegible():
    cat = _cat((0, 4), (1, 5))
    e = C.evaluar(*_todo(cat), cat)
    assert e["elegible"] and e["pendientes"] == []
    assert e["modulos_total"] == 2 and e["lecciones_total"] == 9


def test_el_70_exacto_aprueba_y_uno_menos_no():
    """EL test del umbral. 7/10 es un 70% justo."""
    cat = _cat((0, 1), preguntas=10)
    leidas, _ = _todo(cat)
    assert C.evaluar(leidas, {"0": {"score": 7, "total": 10}}, cat)["elegible"]
    e = C.evaluar(leidas, {"0": {"score": 6, "total": 10}}, cat)
    assert not e["elegible"]
    assert "6/10" in e["pendientes"][0]["quiz"]


def test_una_sola_leccion_sin_leer_lo_impide():
    cat = _cat((0, 4))
    leidas, quizzes = _todo(cat)
    e = C.evaluar(leidas[:-1], quizzes, cat)
    assert not e["elegible"] and e["pendientes"][0]["lecciones_faltan"] == 1


def test_leer_todo_sin_hacer_el_quiz_no_basta():
    """Un certificado que solo exige desplazar la página no certifica nada."""
    cat = _cat((0, 4))
    leidas, _ = _todo(cat)
    assert not C.evaluar(leidas, {}, cat)["elegible"]


def test_un_modulo_sin_quiz_solo_exige_sus_lecciones():
    cat = _cat((0, 2), preguntas=0)
    assert C.evaluar(["0-1", "0-2"], {}, cat)["elegible"]


def test_un_quiz_con_total_cero_no_aprueba():
    """Un total de 0 dividiría por cero; y no es un quiz hecho."""
    cat = _cat((0, 1))
    assert not C.evaluar(["0-1"], {"0": {"score": 0, "total": 0}}, cat)["elegible"]


# ── El certificado emitido ───────────────────────────────────────────────────

@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    C.init_db(c)
    return c


def test_sin_haberlo_completado_NO_se_emite(conn):
    e = C.evaluar([], {}, _cat((0, 1)))
    with pytest.raises(PermissionError):
        C.emitir(conn, 1, "Ana López", e)
    assert C.leer(conn, 1) is None


def test_se_emite_con_codigo_valido(conn):
    cat = _cat((0, 1))
    cert = C.emitir(conn, 1, "Ana López", C.evaluar(*_todo(cat), cat))
    assert C.CODIGO_RE.match(cert["codigo"]), cert["codigo"]
    assert cert["modulos"] == 1 and cert["lecciones"] == 1


def test_pedirlo_otra_vez_corrige_el_nombre_SIN_cambiar_codigo_ni_fecha(conn):
    cat = _cat((0, 1))
    e = C.evaluar(*_todo(cat), cat)
    a = C.emitir(conn, 1, "Ana Lopez", e)
    b = C.emitir(conn, 1, "Ana López", e)
    assert (b["codigo"], b["emitido_at"]) == (a["codigo"], a["emitido_at"])
    assert C.leer(conn, 1)["nombre"] == "Ana López"


def test_un_certificado_emitido_NO_caduca_si_crece_el_catalogo(conn):
    """La Guía se irá ampliando. A quien ya lo tiene no le afecta."""
    cat = _cat((0, 1))
    C.emitir(conn, 1, "Ana López", C.evaluar(*_todo(cat), cat))
    mas_grande = _cat((0, 1), (40, 3))
    e = C.evaluar(*_todo(cat), mas_grande)
    assert not e["elegible"], "el módulo nuevo tendría que faltarle a quien no lo tiene"
    assert C.emitir(conn, 1, "Ana López", e)["codigo"] == C.leer(conn, 1)["codigo"]


def test_reiniciar_el_progreso_NO_borra_el_certificado(monkeypatch, tmp_path):
    from services import academy_service as A
    monkeypatch.setattr(A, "DB_PATH", str(tmp_path / "u.db"))
    A.init_db()
    cat = _cat((0, 1))
    monkeypatch.setattr(C, "catalogo", lambda: cat)
    A.marcar_leccion(1, "0-1")
    A.marcar_quiz(1, 0, 7, 7)
    assert A.emitir_certificado(1, "Ana López")["ok"]
    A.reiniciar_progreso(1)
    estado = A.estado_certificado(1)
    assert estado["emitido"] is not None and not estado["elegible"]


def test_el_codigo_se_rehace_si_choca(monkeypatch):
    usados = []
    assert C.CODIGO_RE.match(C.nuevo_codigo(lambda c: usados.append(c) or len(usados) < 3))
    assert len(usados) == 3


def test_los_codigos_son_ALEATORIOS_de_verdad():
    """Los de formato pasaban con un código constante: el sabotaje se escapó.
    Con 31^8 combinaciones, 300 códigos repetidos es imposible salvo que no
    sean aleatorios — y un código adivinable permitiría inventarse uno."""
    codigos = {C.nuevo_codigo(lambda x: False) for _ in range(300)}
    assert len(codigos) == 300


def test_el_codigo_no_lleva_caracteres_ambiguos():
    """Se lee en un papel: ni 0/O ni 1/I/L."""
    for _ in range(200):
        c = C.nuevo_codigo(lambda x: False)
        assert not set(c[4:].replace("-", "")) & set("01OIL"), c


# ── El nombre ────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("nombre", ["Ana López", "José María Núñez-Ölsen", "Núria d'Alòs",
                                    "Marc Escriba Roig", "Mª Pérez"])
def test_nombres_reales_valen(nombre):
    assert C.validar_nombre(nombre) == nombre


def test_los_espacios_de_mas_se_limpian():
    assert C.validar_nombre("  Ana    López  ") == "Ana López"


@pytest.mark.parametrize("nombre", ["", "Al", "<script>", "Ana <b>", "R2D2", "a" * 61,
                                    'Ana" onload="x', "Ana & Co"])
def test_lo_que_no_es_un_nombre_se_rechaza(nombre):
    with pytest.raises(ValueError):
        C.validar_nombre(nombre)


# ── El PDF ───────────────────────────────────────────────────────────────────

def _paginas(pdf):
    return pdf.count(b"/Type /Page") - pdf.count(b"/Type /Pages")


def test_el_pdf_sale_en_UNA_pagina():
    """La primera maqueta, con divs anidados, xhtml2pdf la partió en dos."""
    pdf = C.generar_pdf({"nombre": "José María Núñez-Ölsen", "codigo": "RSU-UFYY-NW3N",
                         "emitido_at": "2026-09-10T12:00:00+00:00", "modulos": 33, "lecciones": 149})
    assert pdf.startswith(b"%PDF")
    assert _paginas(pdf) == 1


def test_el_nombre_mas_largo_permitido_tambien_cabe_en_una_pagina():
    pdf = C.generar_pdf({"nombre": "Maximiliano " * 5, "codigo": "RSU-UFYY-NW3N",
                         "emitido_at": "2026-09-10T12:00:00+00:00", "modulos": 33, "lecciones": 149})
    assert _paginas(pdf) == 1


def test_el_pdf_escapa_el_nombre_aunque_ya_venga_validado():
    """Dos defensas: este PDF se comparte."""
    pdf = C.generar_pdf({"nombre": "</p><p style='font-size:90px'>X", "codigo": "RSU-UFYY-NW3N",
                         "emitido_at": "2026-09-10T12:00:00+00:00", "modulos": 1, "lecciones": 1})
    assert _paginas(pdf) == 1


# ── Los endpoints ────────────────────────────────────────────────────────────

@pytest.fixture
def cliente(monkeypatch, tmp_path):
    from fastapi.testclient import TestClient
    from auth import verify_token
    from main import app
    from services import academy_service as A, users_service
    monkeypatch.setattr(A, "DB_PATH", str(tmp_path / "u.db"))
    A.init_db()
    monkeypatch.setattr(users_service, "get_user_id", lambda payload: 7)
    monkeypatch.setattr(C, "catalogo", lambda: _cat((0, 1)))
    app.dependency_overrides[verify_token] = lambda: {"sub": "a@b.c", "tier": "free"}
    try:
        with TestClient(app) as c:
            yield c, A
    finally:
        app.dependency_overrides.clear()


def test_sin_certificado_el_pdf_da_404(cliente):
    c, _ = cliente
    assert c.get("/api/v1/academy/certificado/pdf").status_code == 404


def test_de_punta_a_punta(cliente):
    c, A = cliente
    assert c.get("/api/v1/academy/certificado").json()["elegible"] is False
    assert c.post("/api/v1/academy/certificado", json={"nombre": "Ana López"}).json()["ok"] is False
    A.marcar_leccion(7, "0-1")
    A.marcar_quiz(7, 0, 5, 7)
    r = c.post("/api/v1/academy/certificado", json={"nombre": "Ana López"}).json()
    assert r["ok"] and C.CODIGO_RE.match(r["emitido"]["codigo"])
    pdf = c.get("/api/v1/academy/certificado/pdf")
    assert pdf.status_code == 200 and pdf.headers["content-type"] == "application/pdf"
    assert r["emitido"]["codigo"] in pdf.headers["content-disposition"]


def test_un_nombre_invalido_vuelve_como_error_legible(cliente):
    c, A = cliente
    A.marcar_leccion(7, "0-1")
    A.marcar_quiz(7, 0, 7, 7)
    r = c.post("/api/v1/academy/certificado", json={"nombre": "<script>"}).json()
    assert r["ok"] is False and "letras" in r["error"]


# ── La pantalla ──────────────────────────────────────────────────────────────

def test_la_pantalla_pinta_lo_que_decide_el_servidor():
    """El comportamiento de la tarjeta se verificó en el navegador (tres
    estados, error de nombre con role=alert, emisión y descarga). Aquí se ata
    que siga enganchada al índice y que NO calcule la regla por su cuenta: una
    segunda regla en el cliente podría no coincidir con la que emite."""
    js = io.open(os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "pages",
                              "academy.js"), encoding="utf-8").read()
    # SOLO el cuerpo de render(), hasta su llave de cierre. Mi primera versión
    # cortaba hasta `cleanup`, y en medio está la DEFINICIÓN de
    # cargarCertificado: quitar la llamada no lo notaba.
    inicio = js.index("export async function render")
    render = js[inicio:js.index("\n}\n", inicio)]
    assert 'id="ac-certificado"' in render
    assert re.search(r"^\s+cargarCertificado\(container\);", render, re.M), (
        "render() ya no carga la tarjeta del certificado")
    assert "/api/v1/academy/certificado" in js
    codigo = "\n".join(l for l in js.splitlines() if not l.strip().startswith("//"))
    assert "0.7" not in codigo and "70 /" not in codigo, "la pantalla calcula el umbral por su cuenta"


# ── El panel de admin: verificar un código y ver quién lo tiene ──────────────
#
# Pedido por el usuario el 10/09/2026: el código del certificado no servía para
# nada mientras no hubiera página pública de verificación. Ahora el admin puede
# comprobarlo desde su panel, sin exponer nombres al público.

@pytest.mark.parametrize("tecleado", ["RSU-FRXY-YGKB", "rsu-frxy-ygkb", "rsu frxy ygkb",
                                      "FRXYYGKB", "frxy-ygkb", " RSU FRXY YGKB "])
def test_el_codigo_se_encuentra_lo_escriba_como_lo_escriba(tecleado):
    """Se lee en un papel y se teclea a mano: minúsculas, espacios, sin guiones
    o sin el RSU- delante."""
    assert C.normalizar_codigo(tecleado) == "RSU-FRXY-YGKB"


@pytest.mark.parametrize("basura", ["", "hola", "RSU-FRXY", "RSU-FRXY-YGKB-XX", "RSU-0000-0000"])
def test_lo_que_no_es_un_codigo_no_se_normaliza(basura):
    """«RSU-0000-0000» tiene la longitud pero lleva ceros, que el alfabeto no
    usa: no puede ser un código emitido."""
    assert C.normalizar_codigo(basura) is None


@pytest.fixture
def admin(monkeypatch, tmp_path):
    """Base temporal con dos usuarios con certificado y la clave de admin
    concedida; devuelve el cliente y el código de cada uno."""
    from fastapi.testclient import TestClient
    from auth import verify_admin_key
    from main import app
    from services import academy_service as A
    db = str(tmp_path / "u.db")
    monkeypatch.setattr(A, "DB_PATH", db)
    A.init_db()
    c = sqlite3.connect(db)
    c.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, email TEXT UNIQUE NOT NULL, "
              "password_hash TEXT NOT NULL, tier TEXT NOT NULL DEFAULT 'free', created_at TEXT NOT NULL)")
    c.executemany("INSERT INTO users (id, email, password_hash, created_at) VALUES (?, ?, 'x', '2026')",
                  [(1, "ana@ejemplo.com"), (2, "joan@ejemplo.com")])
    c.commit()
    c.close()
    monkeypatch.setattr(C, "catalogo", lambda: _cat((0, 1)))
    codigos = {}
    for uid, nombre in ((1, "Ana López"), (2, "Joan Puig")):
        A.marcar_leccion(uid, "0-1")
        A.marcar_quiz(uid, 0, 7, 7)
        codigos[uid] = A.emitir_certificado(uid, nombre)["emitido"]["codigo"]
    app.dependency_overrides[verify_admin_key] = lambda: None
    try:
        with TestClient(app) as cliente:
            yield cliente, codigos
    finally:
        app.dependency_overrides.clear()


def test_el_admin_ve_TODOS_los_certificados_con_su_email(admin):
    c, codigos = admin
    r = c.get("/api/v1/academy/admin/certificados").json()
    assert r["total"] == 2
    por_email = {i["email"]: (i["nombre"], i["codigo"]) for i in r["items"]}
    assert por_email == {"ana@ejemplo.com": ("Ana López", codigos[1]),
                         "joan@ejemplo.com": ("Joan Puig", codigos[2])}


def test_verifica_un_codigo_autentico_tecleado_a_mano(admin):
    c, codigos = admin
    tecleado = codigos[2].lower().replace("-", " ")
    r = c.get("/api/v1/academy/admin/certificados", params={"codigo": tecleado}).json()
    assert r["encontrado"] and r["certificado"]["nombre"] == "Joan Puig"
    assert r["codigo"] == codigos[2]


def test_un_codigo_inventado_NO_se_da_por_bueno(admin):
    c, _ = admin
    r = c.get("/api/v1/academy/admin/certificados", params={"codigo": "RSU-AAAA-BBBB"}).json()
    assert r["encontrado"] is False and r["certificado"] is None


def test_un_usuario_normal_NO_puede_ver_la_lista(monkeypatch, tmp_path):
    """EL test de seguridad: la lista lleva nombres y emails. Sin la clave de
    admin, aunque haya sesión de usuario, fuera."""
    from fastapi.testclient import TestClient
    from auth import verify_token
    from main import app
    app.dependency_overrides[verify_token] = lambda: {"sub": "a@b.c", "tier": "premium"}
    try:
        with TestClient(app) as c:
            r = c.get("/api/v1/academy/admin/certificados")
            r2 = c.get("/api/v1/academy/admin/certificados", params={"codigo": "RSU-AAAA-BBBB"})
    finally:
        app.dependency_overrides.clear()
    assert r.status_code in (401, 403), r.status_code
    assert r2.status_code in (401, 403), "la verificación de códigos también es solo de admin"


def test_el_panel_de_admin_tiene_la_pestana_y_la_pinta():
    """El comportamiento se verificó en el navegador con el admin.js real
    (lista, código tecleado a mano, inventado, y no-código). Aquí se ata que
    la pestaña existe y que el despachador la pinta."""
    js = io.open(os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "pages", "admin.js"),
                 encoding="utf-8").read()
    assert 'data-tab="certificados"' in js
    assert re.search(r"activeTab === 'certificados'\)\s*\{\s*await renderCertificadosPanel\(content\)", js)
    assert "/api/v1/academy/admin/certificados" in js
