"""
Chatbot de ayuda de RSU Terminal — responde preguntas sobre la metodología del
algoritmo, las funcionalidades de la terminal, y el contenido de la Academia.

DISEÑO — por qué NO es un RAG con embeddings:
El corpus completo (108 lecciones de la Academia + 100 tooltips) son ~123.000
tokens — cabe de sobra en el contexto de cualquier LLM moderno, pero mandarlo
ENTERO en cada mensaje sería lento, caro, y peor para la calidad de respuesta
(los modelos "se pierden" con contextos muy largos e irrelevantes). En vez de
montar una base de datos vectorial (infraestructura nueva, coste de embeddings
por cada chunk), se usa una búsqueda por solapamiento de palabras clave con
ponderación tipo IDF — más simple, sin dependencias nuevas, y sobra para un
corpus de este tamaño y este dominio (preguntas de usuarios reales sobre la
propia terminal, no búsqueda semántica abierta).

ANTI-ALUCINACIÓN: misma lección aprendida con el Daily Briefing (ver
scripts/daily_briefing.py) — el prompt instruye explícitamente a no inventar
funcionalidades, cifras o nombres que no estén en el contexto recuperado, y a
decir "no lo sé" en vez de rellenar el hueco con algo plausible.
"""
import sqlite3
import os
import re
import json
import math
import requests
from datetime import datetime
from collections import Counter

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'chat_historial.db')
KB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'chat_knowledge_base.json')

MODEL = "openai/gpt-oss-20b"
# CAMBIO (14/07/2026): llama-3.1-8b-instant fue descontinuado por Groq el
# 17-jun-2026 — su reemplazo oficial recomendado es este modelo. Sigue siendo
# un modelo DISTINTO al del Daily Briefing (qwen/qwen3.6-27b), así que
# mantiene su propio cupo de tokens/día separado (ver razonamiento completo
# más abajo en _llamar_groq).

STOPWORDS = {
    "el","la","los","las","un","una","unos","unas","de","del","al","a","ante","bajo",
    "con","contra","desde","en","entre","hacia","hasta","para","por","según","sin",
    "sobre","tras","que","qué","como","cómo","cual","cuál","cuando","cuándo","donde",
    "dónde","es","son","soy","eres","ser","estar","está","están","hay","he","has","ha",
    "y","o","u","pero","porque","si","no","se","su","sus","mi","mis","tu","tus","le",
    "les","lo","me","te","nos","este","esta","estos","estas","ese","esa","esos","esas",
    "muy","más","menos","también","yo","tú","él","ella","nosotros","vosotros","ellos",
    "puede","puedo","podría","quiero","quisiera","gracias","hola","dime","explica",
}


def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = _conn()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS mensajes (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario    TEXT NOT NULL,
            rol        TEXT NOT NULL,   -- 'user' | 'assistant'
            mensaje    TEXT NOT NULL,
            creado_en  TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()


# ── BASE DE CONOCIMIENTO Y BÚSQUEDA ─────────────────────────────────────────

def _cargar_kb():
    try:
        with open(KB_PATH, encoding='utf-8') as f:
            chunks = json.load(f)
        print(f"[Chat] Base de conocimiento cargada: {len(chunks)} chunks")
        return chunks
    except Exception as e:
        print(f"[Chat] ERROR cargando base de conocimiento: {type(e).__name__}: {e}")
        return []

_KB = _cargar_kb()


def _tokenizar(texto):
    texto = texto.lower()
    # normalizar acentos comunes en español, para que "metodologia" encuentre "metodología"
    for a, b in [('á','a'),('é','e'),('í','i'),('ó','o'),('ú','u'),('ñ','n')]:
        texto = texto.replace(a, b)
    palabras = re.findall(r'[a-z0-9]+', texto)
    return [p for p in palabras if len(p) > 2 and p not in STOPWORDS]


# Precalcular tokens y frecuencia documental de cada chunk una sola vez, no en
# cada búsqueda — con 209 chunks es barato, pero no hay razón para repetirlo.
def _precalcular_indice(chunks):
    doc_tokens = []
    df = Counter()  # en cuántos chunks aparece cada palabra (document frequency)
    for c in chunks:
        texto_completo = c['titulo'] + ' ' + c['titulo'] + ' ' + c['texto']  # título cuenta doble
        tokens = _tokenizar(texto_completo)
        doc_tokens.append(Counter(tokens))
        for palabra in set(tokens):
            df[palabra] += 1
    return doc_tokens, df

_DOC_TOKENS, _DF = _precalcular_indice(_KB) if _KB else ([], Counter())
_N_DOCS = len(_KB)


def _buscar_chunks_relevantes(pregunta, top_k=6):
    """Puntuación tipo TF-IDF simplificada: cuenta solapamiento de palabras
    entre la pregunta y cada chunk, ponderando más las palabras que aparecen
    en pocos chunks (más específicas/discriminativas) que las que aparecen
    en casi todos (términos genéricos del dominio, poco útiles para elegir
    ENTRE chunks)."""
    if not _KB:
        return []
    palabras_pregunta = set(_tokenizar(pregunta))
    if not palabras_pregunta:
        return []

    puntuaciones = []
    for i, doc_count in enumerate(_DOC_TOKENS):
        score = 0.0
        for palabra in palabras_pregunta:
            if palabra in doc_count:
                idf = math.log(_N_DOCS / (1 + _DF.get(palabra, 0)))
                score += doc_count[palabra] * max(idf, 0.1)
        if score > 0:
            puntuaciones.append((score, i))

    puntuaciones.sort(key=lambda x: x[0], reverse=True)
    return [_KB[i] for _, i in puntuaciones[:top_k]]


# ── CONSTRUCCIÓN DEL PROMPT Y LLAMADA A GROQ ────────────────────────────────

def _construir_system_prompt(chunks_relevantes):
    if chunks_relevantes:
        # Cada chunk se trunca — no hace falta el texto completo de una lección
        # de 40 líneas para responder una pregunta puntual, y cada carácter de
        # más reduce el margen para que varios usuarios chateen a la vez dentro
        # del mismo presupuesto de tokens/minuto compartido de Groq.
        MAX_CHARS_POR_CHUNK = 700
        contexto = "\n\n---\n\n".join(
            f"[Fuente: {c['fuente']} — {c['titulo']}]\n{c['texto'][:MAX_CHARS_POR_CHUNK]}" for c in chunks_relevantes
        )
    else:
        contexto = "(No se encontró contenido específico de la base de conocimiento para esta pregunta.)"

    return f"""Eres el asistente de ayuda de RSU Terminal, una plataforma de análisis bursátil para una comunidad de ~100 traders. Respondes preguntas sobre: la metodología RSU (el algoritmo de detección de fondos, gatekeepers, filtro de crédito, etc.), las funcionalidades de la terminal (qué hace cada sección: Mercado, Algoritmo, Cartera, Scanner, Research, Academia...), y el contenido educativo de la Academia.

TONO: Directo, claro, en español. Trata al usuario como alguien con conocimiento básico-intermedio de trading — no le expliques qué es una acción, pero sí explícale bien los conceptos específicos de RSU Terminal.

REGLA MÁS IMPORTANTE — NO INVENTES NADA:
Solo puedes responder con información que esté en el CONTEXTO RECUPERADO de abajo, o que sea conocimiento general de trading/mercados ampliamente aceptado (ej. qué es el RSI, qué es una media móvil). Si la pregunta es sobre una funcionalidad, cifra, o detalle ESPECÍFICO de RSU Terminal que no aparece en el contexto, di explícitamente que no tienes esa información ahora mismo y sugiere revisar la sección correspondiente de la terminal o preguntar al equipo — NUNCA inventes el nombre de una funcionalidad, un número, o un comportamiento que no esté confirmado en el contexto. Es preferible decir "no tengo ese dato" que dar una respuesta incorrecta con seguridad.

CONTEXTO RECUPERADO (de la base de conocimiento de RSU Terminal — Academia y tooltips):
{contexto}

Responde la pregunta del usuario basándote en este contexto. Si la pregunta no tiene relación con RSU Terminal ni con trading/mercados en general, redirige amablemente al tema."""


def _llamar_groq(system_prompt, historial_mensajes, mensaje_nuevo):
    from config import settings
    key = getattr(settings, "groq_api_key", "")
    if not key:
        raise ValueError("groq_api_key no configurada")

    messages = [{"role": "system", "content": system_prompt}]
    for m in historial_mensajes:
        messages.append({"role": m['rol'], "content": m['mensaje']})
    messages.append({"role": "user", "content": mensaje_nuevo})

    r = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={
            "model":             MODEL,
            "messages":          messages,
            "max_tokens":        500,   # respuesta de chat concisa — no un briefing de 3000 palabras
            "temperature":       0.3,   # precisión sobre creatividad, esto responde con hechos de la terminal
            "reasoning_effort":  "low",  # gpt-oss NO acepta "none" como qwen — "low" es el más rápido disponible
            "include_reasoning": False,  # gpt-oss NO soporta reasoning_format (eso es de qwen) — este es su equivalente
        },
        timeout=30,
    )
    if r.status_code == 429:
        raise ValueError("RATE_LIMIT")
    if r.status_code != 200:
        raise ValueError(f"Groq error {r.status_code}: {r.text[:200]}")
    return r.json()["choices"][0]["message"]["content"]


# ── API PÚBLICA DEL SERVICIO ─────────────────────────────────────────────────

def enviar_mensaje(usuario: str, mensaje: str) -> dict:
    """Punto de entrada principal — recibe la pregunta de un usuario, recupera
    contexto relevante, llama al modelo con el historial reciente, guarda
    ambos mensajes, y devuelve la respuesta."""
    mensaje = (mensaje or "").strip()
    if not mensaje:
        return {"ok": False, "error": "Mensaje vacío"}
    if len(mensaje) > 2000:
        return {"ok": False, "error": "Mensaje demasiado largo (máx. 2000 caracteres)"}

    conn = _conn()
    ahora = datetime.utcnow().isoformat()

    # Últimos mensajes para dar continuidad a la conversación — recortado a 6
    # (3 intercambios), no 10, por el mismo motivo que el truncado de chunks:
    # cada token de contexto es presupuesto de tokens/minuto que no está
    # disponible para que otro usuario chatee en el mismo minuto.
    historial_rows = conn.execute(
        "SELECT rol, mensaje FROM mensajes WHERE usuario = ? ORDER BY id DESC LIMIT 6",
        (usuario,)
    ).fetchall()
    historial = [dict(r) for r in reversed(historial_rows)]

    chunks = _buscar_chunks_relevantes(mensaje, top_k=4)
    system_prompt = _construir_system_prompt(chunks)

    try:
        respuesta = _llamar_groq(system_prompt, historial, mensaje)
    except ValueError as e:
        conn.close()
        if str(e) == "RATE_LIMIT":
            print(f"[Chat] Rate limit de Groq alcanzado (usuario: {usuario})")
            return {"ok": False, "error": "Hay mucha gente preguntando ahora mismo — espera unos segundos y vuelve a intentarlo."}
        print(f"[Chat] Error llamando a Groq: {e}")
        return {"ok": False, "error": "El asistente no está disponible ahora mismo, inténtalo de nuevo en un momento."}
    except Exception as e:
        print(f"[Chat] Error llamando a Groq: {type(e).__name__}: {e}")
        conn.close()
        return {"ok": False, "error": "El asistente no está disponible ahora mismo, inténtalo de nuevo en un momento."}

    conn.execute("INSERT INTO mensajes (usuario, rol, mensaje, creado_en) VALUES (?,?,?,?)",
                 (usuario, "user", mensaje, ahora))
    conn.execute("INSERT INTO mensajes (usuario, rol, mensaje, creado_en) VALUES (?,?,?,?)",
                 (usuario, "assistant", respuesta, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()

    print(f"[Chat] {usuario}: pregunta respondida ({len(chunks)} chunks usados, {len(respuesta)} caracteres de respuesta)")
    return {"ok": True, "respuesta": respuesta}


def obtener_historial(usuario: str, limit: int = 50) -> list:
    conn = _conn()
    rows = conn.execute(
        "SELECT rol, mensaje, creado_en FROM mensajes WHERE usuario = ? ORDER BY id ASC LIMIT ?",
        (usuario, limit)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def borrar_historial(usuario: str) -> dict:
    conn = _conn()
    conn.execute("DELETE FROM mensajes WHERE usuario = ?", (usuario,))
    conn.commit()
    conn.close()
    return {"ok": True}


init_db()


# Cuánto se conserva el historial del chat. 30 días: sirve para dar contexto a
# una conversación en curso, no para guardar lo que alguien preguntó hace un
# año. Este número lo promete la política de privacidad -- cambiarlo aquí
# obliga a cambiarlo allí.
RETENCION_DIAS = 30


def purgar_antiguos() -> int:
    """Borra los mensajes de más de RETENCION_DIAS días.

    Hasta el 18/08/2026 el historial no se purgaba nunca: solo se borraba
    entero si alguien lo pedía a mano. Ver el comentario gemelo en
    analytics_service.purgar_antiguos()."""
    from datetime import datetime, timedelta, timezone
    corte = (datetime.now(timezone.utc) - timedelta(days=RETENCION_DIAS)).isoformat()
    try:
        conn = _conn()
    except Exception:
        return 0
    try:
        cur = conn.execute("DELETE FROM mensajes WHERE creado_en < ?", (corte,))
        n = cur.rowcount or 0
        conn.commit()
        if n:
            print(f"[Chat] Purgados {n} mensajes con más de {RETENCION_DIAS} días")
        return n
    except sqlite3.OperationalError:
        return 0
    finally:
        conn.close()
