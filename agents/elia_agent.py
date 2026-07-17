"""
Agente Elia — revisa el contenido existente de Academy y propone mejoras,
o redacta lecciones nuevas sobre temas no cubiertos. Usa Groq (modelo
qwen/qwen3.6-27b, el mismo ya probado en producción para el Daily
Briefing) — no necesita navegar la web, es tarea de redacción pedagógica
sobre contenido que ya conoce el modelo o que se le da como contexto.

Cada propuesta queda en estado 'pending' en su propia cola de aprobación
(academy_review.db) — el agente NUNCA edita academy_lessons.js
directamente. Tú revisas en /admin → ACADEMY PENDIENTE, y si apruebas,
copias el bloque ya formateado dentro de academy_lessons.js a mano y lo
subes por tu flujo normal de git. Ver conversación 17/07/2026.

Uso:
    cd backend
    python3 ../agents/elia_agent.py --tipo revision      # revisa 1 leccion existente
    python3 ../agents/elia_agent.py --tipo nueva          # propone 1 leccion nueva
    python3 ../agents/elia_agent.py --tipo random         # elige al azar entre las dos (por defecto)
"""
import sys
import os
import re
import json
import random
import argparse
import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from config import settings  # noqa: E402
from services.academy_review_service import create_review  # noqa: E402

LESSONS_FILE = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'pages', 'academy_lessons.js')
MODEL = "qwen/qwen3.6-27b"

TIPOS_BLOQUE_PERMITIDOS = ['text', 'tip', 'warning', 'concept', 'steps', 'table', 'divider']
# NOTA: se excluye 'chart' a propósito -- Elia no puede generar los SVG
# de academy_charts.js, así que no debe proponer bloques que dependan de
# un gráfico que no existe.


def _extraer_lecciones_existentes() -> list:
    with open(LESSONS_FILE, encoding='utf-8') as f:
        content = f.read()
    pattern = re.compile(
        r"        moduleId: (\d+),\s*\n        lessonIndex: (\d+),\s*\n"
        r"        title: '(.+?)',\s*\n        duration: '(.+?)',\s*\n"
        r"        intro: '(.+?)',",
        re.MULTILINE
    )
    lecciones = []
    for m in pattern.finditer(content):
        lecciones.append({
            "moduleId": int(m.group(1)), "lessonIndex": int(m.group(2)),
            "title": m.group(3), "duration": m.group(4), "intro": m.group(5),
        })
    return lecciones


def _llamar_groq(prompt: str) -> str:
    if not settings.groq_api_key:
        raise ValueError("GROQ_API_KEY no configurada")

    r = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {settings.groq_api_key}", "Content-Type": "application/json"},
        json={
            "model": MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 3000,
            "temperature": 0.4,
            "reasoning_effort": "none",     # mismo motivo que en daily_briefing.py:
            "reasoning_format": "hidden",   # tarea de redacción, no de razonamiento paso a paso
        },
        timeout=120,
    )
    if r.status_code != 200:
        raise ValueError(f"Groq error {r.status_code}: {r.text[:300]}")
    return r.json()["choices"][0]["message"]["content"]


def _extraer_json(texto: str) -> dict:
    """El modelo puede envolver el JSON en ```json ... ``` o añadir texto
    alrededor -- se extrae el primer bloque {...} balanceado."""
    texto = re.sub(r"^```json\s*|\s*```$", "", texto.strip(), flags=re.MULTILINE)
    inicio = texto.find("{")
    if inicio == -1:
        raise ValueError("No se encontró JSON en la respuesta del modelo")
    profundidad = 0
    for i in range(inicio, len(texto)):
        if texto[i] == "{":
            profundidad += 1
        elif texto[i] == "}":
            profundidad -= 1
            if profundidad == 0:
                return json.loads(texto[inicio:i + 1])
    raise ValueError("JSON no balanceado en la respuesta del modelo")


def _formatear_bloque_js(leccion: dict) -> str:
    """Convierte el dict a un texto JS listo para pegar en el objeto
    LESSONS de academy_lessons.js -- no es JSON puro (comillas simples,
    sin comillas en las claves), coherente con el estilo del resto del
    archivo."""
    return json.dumps(leccion, ensure_ascii=False, indent=4)


def proponer_leccion_nueva(existentes: list) -> dict:
    resumen_existentes = "\n".join(f"- [{l['moduleId']}-{l['lessonIndex']}] {l['title']}: {l['intro'][:100]}" for l in existentes)

    prompt = f"""Eres Elia, responsable de contenido educativo de RSU Terminal, una plataforma de análisis bursátil para una comunidad de ~100 traders activos. Escribes en castellano, con tono claro y didáctico, sin jerga innecesaria.

Estas son las lecciones que YA EXISTEN en la Academia (no repitas estos temas):
{resumen_existentes}

Propón UNA lección NUEVA sobre un tema de trading/análisis bursátil que NO esté cubierto todavía y que aporte valor real a esta comunidad. Puede ser sobre metodología, gestión de riesgo, psicología de trading, un concepto técnico o fundamental concreto, etc.

Responde EXCLUSIVAMENTE con un JSON con esta forma exacta (sin texto antes ni después, sin comentarios):

{{
  "moduleId": <número de módulo entero, elige el que mejor encaje temáticamente con los módulos ya vistos>,
  "title": "<título corto y claro>",
  "duration": "<ej. '10 min'>",
  "intro": "<1-2 frases de introducción>",
  "sections": [
    {{
      "heading": "<título de la sección>",
      "blocks": [
        {{ "type": "text", "content": "<HTML simple, puede incluir <b> y <br>>" }},
        {{ "type": "concept", "title": "<título del concepto>", "content": "<explicación>" }},
        {{ "type": "tip", "content": "<consejo práctico>" }},
        {{ "type": "warning", "content": "<advertencia si aplica>" }},
        {{ "type": "steps", "items": ["paso 1", "paso 2"] }},
        {{ "type": "table", "headers": ["Col1","Col2"], "rows": [["a","b"]] }}
      ]
    }}
  ]
}}

Usa solo estos tipos de bloque: {', '.join(TIPOS_BLOQUE_PERMITIDOS)} (NO uses 'chart', no puedes generar gráficos). Incluye 2-4 secciones con contenido real y sustancial, no relleno."""

    respuesta = _llamar_groq(prompt)
    leccion = _extraer_json(respuesta)
    return leccion


def revisar_leccion_existente(existentes: list) -> dict:
    leccion = random.choice(existentes)

    prompt = f"""Eres Elia, responsable de contenido educativo de RSU Terminal, una plataforma de análisis bursátil para una comunidad de ~100 traders activos.

Revisa esta lección existente de la Academia:
Título: {leccion['title']}
Introducción actual: {leccion['intro']}

Propón UNA sección NUEVA que podría añadirse a esta lección para ampliarla o mejorarla -- algo que falte, un matiz importante, un ejemplo práctico, o una tabla comparativa útil que no esté ya cubierta por el título/intro.

Responde EXCLUSIVAMENTE con un JSON con esta forma exacta (sin texto antes ni después):

{{
  "heading": "<título de la sección nueva>",
  "blocks": [
    {{ "type": "text", "content": "<HTML simple>" }},
    {{ "type": "concept", "title": "<título>", "content": "<explicación>" }}
  ],
  "justificacion": "<1-2 frases explicando por qué esta sección aporta valor a la lección>"
}}

Usa solo estos tipos de bloque: {', '.join(TIPOS_BLOQUE_PERMITIDOS)}."""

    respuesta = _llamar_groq(prompt)
    seccion = _extraer_json(respuesta)
    return leccion, seccion


def main():
    parser = argparse.ArgumentParser(description="Agente Elia — revisa y amplía Academy")
    parser.add_argument("--tipo", choices=["revision", "nueva", "random"], default="random")
    args = parser.parse_args()

    if not settings.groq_api_key:
        print("[Elia] Falta GROQ_API_KEY en el .env — abortando.")
        return

    tipo = args.tipo
    if tipo == "random":
        tipo = random.choice(["revision", "nueva"])

    existentes = _extraer_lecciones_existentes()
    print(f"[Elia] {len(existentes)} lecciones existentes encontradas. Modo: {tipo}.")

    try:
        if tipo == "nueva":
            leccion = proponer_leccion_nueva(existentes)
            bloque_js = _formatear_bloque_js(leccion)
            review_id = create_review(
                tipo="nueva_leccion",
                titulo=leccion.get("title", "(sin título)"),
                bloque_js=bloque_js,
                resumen=leccion.get("intro", ""),
                modulo_id=leccion.get("moduleId"),
            )
            print(f"[Elia] Propuesta de lección nueva #{review_id} creada — pendiente de aprobación en /admin.")
        else:
            leccion, seccion = revisar_leccion_existente(existentes)
            bloque_js = _formatear_bloque_js(seccion)
            review_id = create_review(
                tipo="revision",
                titulo=f"Ampliación para: {leccion['title']}",
                bloque_js=bloque_js,
                resumen=seccion.get("justificacion", ""),
                leccion_ref=f"{leccion['moduleId']}-{leccion['lessonIndex']}",
            )
            print(f"[Elia] Propuesta de revisión #{review_id} para '{leccion['title']}' creada — pendiente de aprobación en /admin.")
    except Exception as e:
        print(f"[Elia] ERROR: {type(e).__name__}: {e}")


if __name__ == "__main__":
    main()