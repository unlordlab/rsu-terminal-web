"""
Certificado de finalización de RSU Academy (Páginas Contenido #23).

DECISIONES DEL USUARIO, 10/09/2026:
  - UN solo certificado, al completar TODA la Academy.
  - Un módulo está completo con TODAS sus lecciones leídas hasta el final Y su
    quiz superado con un 70% o más (cuenta el mejor intento).
  - La Guía de la Terminal ENTRA. Consecuencia, dicha al decidirlo: cada
    módulo nuevo que se añada se suma a lo que falta para quien aún no lo
    tenga. A quien ya lo tiene no le afecta: un certificado emitido no caduca.
  - PDF con código único. La página pública de verificación queda para cuando
    haya dominio y HTTPS: hoy iría por HTTP sobre una IP y dejaría nombres a la
    vista de cualquiera con un código.

QUIÉN DECIDE QUE ESTÁ COMPLETO: EL SERVIDOR, contra el catálogo REAL. El
backend no conocía el catálogo (vivía entero en el frontend), así que se lee
de los MISMOS ficheros que pinta la pantalla —academy_manifest.js y
academy_quizzes.js— en vez de mantener una segunda lista que acabaría
desincronizada. Si mañana entra un módulo nuevo, cuenta solo.

LO QUE ESTO NO ES: una prueba contra trampas. El progreso lo reporta el
navegador (la lección se marca al llegar al final; el quiz se corrige en el
cliente), así que el certificado es tan fiable como ese progreso. Blindarlo
exigiría corregir los quizzes en el servidor.

SOBRE EL 70%: el quiz no deja avanzar sin acertar, así que al final todos lo
aciertan todo. Lo que se guarda es cuántas acertó A LA PRIMERA, y cuenta el
mejor intento: quien repita el quiz acaba llegando. Es deliberado, se aprende
repitiendo.
"""
import html
import io
import os
import re
import secrets
import sqlite3
from datetime import datetime, timezone

PAGES = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "pages")
MANIFEST = os.path.join(PAGES, "academy_manifest.js")
QUIZZES = os.path.join(PAGES, "academy_quizzes.js")

UMBRAL_QUIZ = 0.70

# Sin caracteres que se confundan al leerlos en un papel: ni 0/O ni 1/I/L.
# Letras DELANTE de los dígitos a propósito: con los ocho dígitos seguidos de
# la primera letra, la cadena tiene la forma de un DNI, y el test que vigila
# que el DNI del titular no acabe en este repositorio público la marcaba. Se
# cambia el código, no el test.
_ALFABETO = "ABCDEFGHJKMNPQRSTUVWXYZ" + "23456789"
CODIGO_RE = re.compile(r"^RSU-[A-HJKMNP-Z2-9]{4}-[A-HJKMNP-Z2-9]{4}$")

NOMBRE_MIN, NOMBRE_MAX = 3, 60
# Letras de cualquier alfabeto (José, Núria, Ølsen), separadas por espacio,
# apóstrofo, guion o punto. Nada de dígitos ni de < > & ": va a un PDF que se
# enseña y se comparte.
_NOMBRE_RE = re.compile(r"^[^\W\d_]+(?:[ .'\-]+[^\W\d_]+)*\.?$")


# ── El catálogo, leído de lo que pinta la pantalla ───────────────────────────

_cache = {"clave": None, "catalogo": None}


def _lecciones_por_modulo(texto: str) -> dict:
    """{modulo: [claves]} a partir de las claves '<modulo>-<indice>' del
    manifiesto (GENERADO por scripts/gen_academy_manifest.py)."""
    por_modulo = {}
    for m, i in re.findall(r"'(\d+)-(\d+)'\s*:", texto):
        por_modulo.setdefault(int(m), []).append(f"{m}-{i}")
    return por_modulo


def _preguntas_por_modulo(texto: str) -> dict:
    """{modulo: nº de preguntas}. Cada módulo abre con `    <id>: {` y cada
    pregunta con `{ q:`. Se cuentan las preguntas entre la cabecera de un
    módulo y la del siguiente."""
    cabeceras = [(m.start(), int(m.group(1)))
                 for m in re.finditer(r"^\s{2,8}'?(\d+)'?\s*:\s*\{", texto, re.M)]
    fuera = {}
    for n, (inicio, modulo) in enumerate(cabeceras):
        fin = cabeceras[n + 1][0] if n + 1 < len(cabeceras) else len(texto)
        fuera[modulo] = len(re.findall(r"\{\s*q\s*:", texto[inicio:fin]))
    return fuera


def catalogo() -> dict:
    """{modulo: {"lecciones": [...], "preguntas": n}} con TODOS los módulos
    que tienen lecciones. Se relee si cambian los ficheros (fecha de
    modificación), así un despliegue con contenido nuevo no necesita
    reiniciar nada para que el certificado lo exija."""
    clave = tuple(os.path.getmtime(p) for p in (MANIFEST, QUIZZES))
    if _cache["clave"] == clave:
        return _cache["catalogo"]
    with io.open(MANIFEST, encoding="utf-8") as f:
        lecciones = _lecciones_por_modulo(f.read())
    with io.open(QUIZZES, encoding="utf-8") as f:
        preguntas = _preguntas_por_modulo(f.read())
    cat = {m: {"lecciones": sorted(ls, key=lambda k: int(k.split("-")[1])),
               "preguntas": preguntas.get(m, 0)}
           for m, ls in lecciones.items()}
    _cache.update(clave=clave, catalogo=cat)
    return cat


# ── Quién ha completado qué ──────────────────────────────────────────────────

def evaluar(lecciones_leidas, quizzes: dict, cat: dict = None) -> dict:
    """Qué le falta a alguien para el certificado, módulo a módulo.

    `quizzes` es {"12": {"score", "total"}} tal como lo guarda el progreso.
    Un módulo sin quiz en el catálogo solo exige sus lecciones.
    """
    cat = catalogo() if cat is None else cat
    leidas = set(lecciones_leidas or [])
    pendientes = []
    for m in sorted(cat):
        faltan = [k for k in cat[m]["lecciones"] if k not in leidas]
        q = (quizzes or {}).get(str(m))
        estado_quiz = None
        if cat[m]["preguntas"]:
            if not q:
                estado_quiz = "sin hacer"
            elif q["total"] <= 0 or q["score"] / q["total"] < UMBRAL_QUIZ:
                estado_quiz = f"{q['score']}/{q['total']} a la primera, hace falta un 70%"
        if faltan or estado_quiz:
            pendientes.append({"modulo": m, "lecciones_faltan": len(faltan),
                               "lecciones_total": len(cat[m]["lecciones"]),
                               "quiz": estado_quiz})
    return {
        "elegible": not pendientes,
        "modulos_total": len(cat),
        "modulos_completos": len(cat) - len(pendientes),
        "lecciones_total": sum(len(c["lecciones"]) for c in cat.values()),
        "umbral_quiz": UMBRAL_QUIZ,
        "pendientes": pendientes,
    }


# ── El certificado emitido ───────────────────────────────────────────────────

def init_db(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS academy_certificado (
            user_id    INTEGER PRIMARY KEY,
            codigo     TEXT UNIQUE NOT NULL,
            nombre     TEXT NOT NULL,
            emitido_at TEXT NOT NULL,   -- la primera vez; corregir el nombre no la cambia
            modulos    INTEGER NOT NULL,  -- lo que exigía el catálogo AL EMITIRSE
            lecciones  INTEGER NOT NULL
        )
    """)


def validar_nombre(nombre):
    """El nombre limpio, o un ValueError que se puede enseñar tal cual."""
    n = " ".join(str(nombre or "").split())
    if len(n) < NOMBRE_MIN:
        raise ValueError("Escribe tu nombre tal como quieres que aparezca en el certificado")
    if len(n) > NOMBRE_MAX:
        raise ValueError(f"El nombre no puede pasar de {NOMBRE_MAX} caracteres")
    if not _NOMBRE_RE.match(n):
        raise ValueError("El nombre solo puede llevar letras, espacios, puntos, guiones y apóstrofos")
    return n


def nuevo_codigo(existe) -> str:
    """RSU-XXXX-XXXX, aleatorio de verdad (`secrets`, no `random`): el código
    es lo que identifica un certificado, y no tiene que poder adivinarse."""
    for _ in range(20):
        c = "RSU-" + "".join(secrets.choice(_ALFABETO) for _ in range(4)) \
            + "-" + "".join(secrets.choice(_ALFABETO) for _ in range(4))
        if not existe(c):
            return c
    raise RuntimeError("No se pudo generar un código único")


def leer(conn, user_id):
    fila = conn.execute("SELECT * FROM academy_certificado WHERE user_id = ?", (user_id,)).fetchone()
    return dict(fila) if fila else None


def emitir(conn, user_id: int, nombre: str, evaluacion: dict) -> dict:
    """Emite el certificado, o corrige el nombre si ya existía (mismo código y
    misma fecha). Quien ya lo tiene no necesita volver a cumplir: el catálogo
    puede haber crecido desde entonces, y un certificado no caduca."""
    nombre = validar_nombre(nombre)
    previo = leer(conn, user_id)
    if previo:
        conn.execute("UPDATE academy_certificado SET nombre = ? WHERE user_id = ?", (nombre, user_id))
        return dict(previo, nombre=nombre)
    if not evaluacion["elegible"]:
        raise PermissionError("Todavía no has completado todos los módulos")
    codigo = nuevo_codigo(lambda c: conn.execute(
        "SELECT 1 FROM academy_certificado WHERE codigo = ?", (c,)).fetchone() is not None)
    fila = {"user_id": user_id, "codigo": codigo, "nombre": nombre,
            "emitido_at": datetime.now(timezone.utc).isoformat(),
            "modulos": evaluacion["modulos_total"], "lecciones": evaluacion["lecciones_total"]}
    conn.execute("INSERT INTO academy_certificado (user_id, codigo, nombre, emitido_at, modulos, lecciones) "
                 "VALUES (:user_id, :codigo, :nombre, :emitido_at, :modulos, :lecciones)", fila)
    return fila


# ── El PDF ───────────────────────────────────────────────────────────────────

_MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
          "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def _fecha_larga(iso: str) -> str:
    d = datetime.fromisoformat(iso)
    return f"{d.day} de {_MESES[d.month - 1]} de {d.year}"


def generar_pdf(cert: dict) -> bytes:
    """Mismo motor que las tesis (xhtml2pdf, puro Python). El nombre se escapa
    aunque ya esté validado: dos defensas, porque este PDF se comparte."""
    from xhtml2pdf import pisa

    nombre = html.escape(cert["nombre"])
    codigo = html.escape(cert["codigo"])
    fecha = _fecha_larga(cert["emitido_at"])
    # MAQUETA CON TABLA, NO CON DIVS ANIDADOS. La primera versión usaba dos
    # divs con borde, uno dentro de otro: xhtml2pdf le puso el borde a CADA
    # bloque interior y partió el certificado en dos páginas. Una tabla de una
    # celda como marco y párrafos dentro es lo que interpreta bien.
    doc = f"""<html><head><style>
    @page {{ size: A4 landscape; margin: 1.3cm; }}
    body {{ font-family: Helvetica, Arial, sans-serif; color: #1a1a1a; }}
    p {{ margin: 0; padding: 0; text-align: center; }}
    .marca {{ font-size: 10px; color: #0a5c36; }}
    .titulo {{ font-size: 32px; color: #111; padding-top: 34px; }}
    .sub {{ font-size: 10px; color: #777; padding-top: 4px; }}
    .otorga {{ font-size: 12px; color: #555; padding-top: 58px; }}
    .nombre {{ font-size: 34px; color: #0a5c36; font-weight: bold; padding-top: 12px; }}
    .texto {{ font-size: 12px; color: #333; padding-top: 34px; }}
    .pie {{ font-size: 10px; color: #555; padding-top: 88px; }}
    .aviso {{ font-size: 7px; color: #999; padding-top: 14px; }}
</style></head><body>
<table width="100%" cellpadding="5" style="border: 3px solid #0a5c36;"><tr><td>
<table width="100%" cellpadding="0" style="border: 1px solid #0a5c36;"><tr>
<td style="padding: 96px 50px 64px 50px;">
    <p class="marca">R S U &nbsp; T E R M I N A L &nbsp;&middot;&nbsp; R S U &nbsp; A C A D E M Y</p>
    <p class="titulo">Certificado de finalización</p>
    <p class="sub">FORMACIÓN EN ANÁLISIS Y METODOLOGÍA DE MERCADO</p>
    <p class="otorga">Se otorga a</p>
    <p class="nombre">{nombre}</p>
    <p class="texto">por completar los {cert['modulos']} módulos y las {cert['lecciones']} lecciones de RSU Academy,<br/>
    superando la evaluación de cada módulo con al menos un 70% de aciertos a la primera.</p>
    <p class="pie">Emitido el {fecha} &nbsp;&middot;&nbsp; Código de verificación: <b>{codigo}</b></p>
    <p class="aviso">Formación de carácter educativo impartida en RSU Terminal. No es una titulación oficial ni
    acredita para prestar asesoramiento financiero o de inversión.</p>
</td></tr></table>
</td></tr></table>
</body></html>"""
    buffer = io.BytesIO()
    resultado = pisa.CreatePDF(doc, dest=buffer)
    if resultado.err:
        raise RuntimeError("No se pudo generar el PDF del certificado")
    return buffer.getvalue()
