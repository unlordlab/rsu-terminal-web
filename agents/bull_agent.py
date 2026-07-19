"""
Agente Bull — genera tesis alcistas para tickers que cumplen criterios
CANSLIM y han sufrido una corrección reciente, usando el prompt de
análisis de Marc (agents/bull_prompt.py). Cada resultado queda en estado
'pending' esperando aprobación en el panel de admin (pestaña TESIS
PENDIENTES) — el agente NUNCA publica solo, ver conversación 17/07/2026.

Soporta DOS proveedores, intercambiables con --provider:

  --provider gemini (por defecto, gratis)
      Usa Google AI Studio / Gemini con los tools `googleSearch` y
      `url_context`. ⚠️ AVISO IMPORTANTE: `url_context` prioriza una
      caché interna indexada de Google antes que visitar la página en
      vivo, y en pruebas independientes se ha visto devolver contenido
      desactualizado sin avisar. Esto choca de frente con el Protocolo
      de Frescura de Datos del prompt (Pasos 1-4), que existe
      precisamente para evitar precios viejos. Usar SOLO para probar la
      mecánica del pipeline (selección de candidatos, cola de
      aprobación, panel de admin) — NO fiarse del precio/dato de mercado
      de estas tesis sin verificarlo a mano antes de aprobar.

  --provider claude (para producción real)
      Usa la API de Claude con `web_search` y `web_fetch` (éste último
      en beta, cabecera anthropic-beta requerida). Sin el problema de
      caché de Gemini — hace fetch en vivo de verdad.

Control de límites (ver conversación 17/07/2026 — "que tenga en cuenta
los límites de tokens y demás"):
  - Límite diario de peticiones por proveedor (persistido en un fichero
    de estado sencillo, se resetea cada día).
  - max_output_tokens explícito en cada llamada.
  - Reintento con backoff si la API devuelve un 429 (límite de ritmo).
  - Pausa entre tickers dentro de la misma ejecución para no saturar el
    límite de peticiones/minuto.

Uso:
    cd backend
    python3 ../agents/bull_agent.py --max 1                     # Gemini, prueba
    python3 ../agents/bull_agent.py --max 1 --provider claude   # Claude, real
"""
import sys
import os
import re
import json
import time
import argparse
from datetime import datetime, date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
sys.path.insert(0, os.path.dirname(__file__))

from config import settings  # noqa: E402
from services.canslim_service import scan_canslim  # noqa: E402
from services.tesis_service import create_tesis, recent_tickers_with_tesis  # noqa: E402
from bull_prompt import PROMPT_TEMPLATE  # noqa: E402
from services.meeting_room_service import get_pendientes_para, marcar_procesado, responder  # noqa: E402

# ── Criterio de selección de candidatos ─────────────────────────────────
# CANSLIM score >= 40 (ya lo exige scan_canslim) + corrección real desde
# el máximo de 52 semanas — ni pegado al high (momentum puro) ni tan
# hundido que sea rotura de tendencia.
PCT_FROM_HIGH_MIN = -25
PCT_FROM_HIGH_MAX = -8

# ── Límites por proveedor (ajustar si Google/Anthropic cambian sus cuotas) ──
LIMITS = {
    "gemini": {
        # Las fuentes públicas no coinciden exactamente entre sí sobre la
        # cuota diaria real de gemini-2.5-flash a fecha de hoy (17/07/2026)
        # -- varía entre 250 y 1.500/dia segun la fuente. Se deja un valor
        # conservador; confirma el numero real en ai.google.dev/pricing
        # antes de asumir que hay mas margen del que realmente hay.
        "max_requests_per_day": 200,
        "max_output_tokens": 32000,     # subido de 16.000 -- el informe con tablas y
                                         # formato markdown puede pesar mas de lo que
                                         # sugieren las 4.000-6.500 palabras "en texto"
        "pausa_entre_tickers_seg": 10,
    },
    "claude": {
        "max_requests_per_day": 200,    # límite propio, conservador — es de pago
        "max_output_tokens": 32000,
        "pausa_entre_tickers_seg": 3,
    },
}

STATE_FILE = os.path.join(os.path.dirname(__file__), '.bull_agent_state.json')


def _cargar_estado() -> dict:
    hoy = date.today().isoformat()
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                estado = json.load(f)
            if estado.get('fecha') == hoy:
                return estado
        except Exception:
            pass
    return {"fecha": hoy, "peticiones": {}}


def _guardar_estado(estado: dict):
    try:
        with open(STATE_FILE, 'w') as f:
            json.dump(estado, f)
    except Exception as e:
        print(f"[Bull] Aviso: no se pudo guardar el estado de límites ({e})")


def _comprobar_y_registrar_peticion(provider: str) -> bool:
    """Devuelve False si ya se alcanzó el límite diario de ese proveedor."""
    estado = _cargar_estado()
    usadas = estado["peticiones"].get(provider, 0)
    limite = LIMITS[provider]["max_requests_per_day"]
    if usadas >= limite:
        print(f"[Bull] Límite diario de {provider} alcanzado ({usadas}/{limite}). Abortando por hoy.")
        return False
    estado["peticiones"][provider] = usadas + 1
    _guardar_estado(estado)
    return True


def select_candidates(max_candidates: int = 3) -> list:
    result = scan_canslim(min_score=40, max_results=100)
    if not result.get("ok"):
        print("[Bull] scan_canslim() no devolvió resultados válidos.")
        return []

    ya_analizados = recent_tickers_with_tesis(days=60)

    candidatos = [
        c for c in result["candidates"]
        if PCT_FROM_HIGH_MIN <= c.get("pct_from_high", 0) <= PCT_FROM_HIGH_MAX
        and c["ticker"] not in ya_analizados
    ]
    candidatos.sort(key=lambda c: -c["score"])
    return candidatos[:max_candidates]


def _extraer_titulo_y_nombre(texto: str) -> tuple[str, str]:
    m = re.search(r"^\*\*(.+?)—(.+?)—(.+?)\*\*", texto, re.MULTILINE)
    if m:
        nombre = m.group(2).strip()
        titulo_completo = (m.group(1) + "—" + m.group(2) + "—" + m.group(3)).strip()
        return titulo_completo, nombre
    for line in texto.splitlines():
        if line.strip():
            return line.strip()[:200], ""
    return "(sin título)", ""


def _extraer_resumen(texto: str) -> str:
    m = re.search(r"\*\*1\. EXPLICACIÓN SIMPLE\*\*\s*\n(.+?)(?=\n\*\*2\.|\Z)", texto, re.DOTALL)
    if m:
        return re.sub(r"\s+", " ", m.group(1)).strip()[:300]
    return ""


def _extraer_precio_objetivo(texto: str) -> float | None:
    """Heurística, no exacta: busca la sección 13 (Precios Objetivo de
    Analistas) y coge la última cifra en dólares mencionada ahí — suele
    ser el target más reciente en la tabla. No es infalible (el informe lo
    escribe un LLM, el formato de tabla puede variar) — revisa el precio
    objetivo en el panel de admin antes de dar por buena la cifra."""
    m = re.search(r"\*\*13\. PRECIOS OBJETIVO DE ANALISTAS\*\*(.+?)(?=\n\*\*14\.|\Z)", texto, re.DOTALL)
    bloque = m.group(1) if m else texto
    precios = re.findall(r"\$\s?([0-9]+(?:[.,][0-9]+)?)", bloque)
    if not precios:
        return None
    try:
        return float(precios[-1].replace(",", "."))
    except Exception:
        return None


def _obtener_sector(ticker: str) -> str:
    try:
        import yfinance as yf
        info = yf.Ticker(ticker).info
        return info.get("sector", "") or ""
    except Exception:
        return ""


# ── Llamada a Gemini (prueba gratuita) ──────────────────────────────────

def _generar_con_gemini(ticker: str) -> str:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=settings.gemini_api_key)
    prompt = PROMPT_TEMPLATE.format(ticker=ticker)

    intentos = 0
    while True:
        intentos += 1
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",  # NO uses "pro" — su tier gratuito es de
                                            # solo 50-100 peticiones/dia, no sostenible.
                                            # Flash es el modelo con cuota generosa de
                                            # verdad (los ~1.500/dia). Se pierde algo de
                                            # fidelidad a un prompt tan largo y exigente
                                            # frente a Pro/Claude, es el precio de ser
                                            # gratis y sostenible.
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[
                        types.Tool(google_search=types.GoogleSearch()),
                        types.Tool(url_context=types.UrlContext()),
                    ],
                    max_output_tokens=LIMITS["gemini"]["max_output_tokens"],
                ),
            )
            finish_reason = None
            try:
                finish_reason = response.candidates[0].finish_reason
            except Exception:
                pass
            if finish_reason and str(finish_reason).upper() not in ("STOP", "1", "FINISHREASON.STOP"):
                print(f"[Bull] AVISO: la respuesta de Gemini terminó por '{finish_reason}', no por fin natural "
                      f"— es posible que el informe esté cortado (revísalo antes de aprobar).")
            return response.text
        except Exception as e:
            if "429" in str(e) and intentos < 4:
                espera = 15 * intentos
                print(f"[Bull] Rate limit de Gemini, esperando {espera}s (intento {intentos}/3)...")
                time.sleep(espera)
                continue
            raise


# ── Llamada a Claude (producción real) ──────────────────────────────────

def _generar_con_claude(ticker: str) -> str:
    import anthropic

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    prompt = PROMPT_TEMPLATE.format(ticker=ticker)

    intentos = 0
    while True:
        intentos += 1
        try:
            response = client.messages.create(
                model="claude-sonnet-5",
                max_tokens=LIMITS["claude"]["max_output_tokens"],
                messages=[{"role": "user", "content": prompt}],
                tools=[
                    {"type": "web_search_20250305", "name": "web_search"},
                    {"type": "web_fetch_20250910", "name": "web_fetch", "max_uses": 15},
                ],
                extra_headers={"anthropic-beta": "web-fetch-2025-09-10"},
            )
            return "".join(block.text for block in response.content if block.type == "text")
        except Exception as e:
            if "429" in str(e) and intentos < 4:
                espera = 15 * intentos
                print(f"[Bull] Rate limit de Claude, esperando {espera}s (intento {intentos}/3)...")
                time.sleep(espera)
                continue
            raise


def generar_tesis(ticker: str, provider: str) -> dict:
    if provider == "gemini":
        texto = _generar_con_gemini(ticker)
    else:
        texto = _generar_con_claude(ticker)

    if not texto or not texto.strip():
        raise ValueError("Respuesta vacía de la API (revisa si los tools fallaron)")

    if provider == "gemini":
        aviso = (
            "> ⚠️ **TESIS DE PRUEBA (generada con Gemini, no Claude).** "
            "El tool de lectura de páginas de Gemini puede devolver datos de precio "
            "desactualizados sin avisar — **verifica el precio actual a mano antes "
            "de aprobar esta tesis para publicación.**\n\n"
        )
        texto = aviso + texto

    titulo, nombre = _extraer_titulo_y_nombre(texto)
    resumen = _extraer_resumen(texto)
    sector = _obtener_sector(ticker)
    precio_objetivo = _extraer_precio_objetivo(texto)

    return {"contenido": texto, "titulo": titulo, "nombre": nombre, "resumen": resumen,
            "sector": sector, "precio_objetivo": precio_objetivo}


def _extraer_ticker_de_instruccion(mensaje: str) -> str | None:
    """Usa Groq (rápido y barato, no hace falta el modelo caro de Bull
    solo para esto) para extraer un ticker bursátil de una instrucción en
    lenguaje natural -- reconoce tanto el ticker directo ('mira NVDA')
    como el nombre de la empresa ('mira Nvidia')."""
    if not settings.groq_api_key:
        return None
    prompt = (
        f"Extrae el ticker bursátil (símbolo de cotización en bolsa de EE.UU., ej: AAPL, NVDA, TSLA) "
        f"mencionado en este mensaje. Si se menciona una empresa por su nombre en vez de su ticker, "
        f"identifica el ticker correcto.\n\nMensaje: \"{mensaje}\"\n\n"
        f"Responde EXCLUSIVAMENTE con el ticker en mayúsculas, sin nada más. Si no hay ningún ticker "
        f"o empresa identificable en el mensaje, responde exactamente: NINGUNO"
    )
    try:
        import requests
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {settings.groq_api_key}", "Content-Type": "application/json"},
            json={
                "model": "qwen/qwen3.6-27b",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 20,
                "temperature": 0,
                "reasoning_effort": "none",
                "reasoning_format": "hidden",
            },
            timeout=20,
        )
        if r.status_code == 200:
            ticker = r.json()["choices"][0]["message"]["content"].strip().upper()
            ticker = re.sub(r"[^A-Z]", "", ticker)  # por si acaso viene con puntuación de más
            if ticker and ticker != "NINGUNO" and 1 <= len(ticker) <= 6:
                return ticker
    except Exception as e:
        print(f"[Bull] No se pudo interpretar la instrucción del Meeting Room: {type(e).__name__}: {e}")
    return None


def procesar_meeting_room(provider: str, max_mensajes: int = 3) -> int:
    """Revisa el buzón del Meeting Room antes del escaneo automático de
    siempre -- si Marc ha dejado instrucciones para Gael, se procesan
    con prioridad. Devuelve cuántas tesis se generaron así, para
    descontarlas del cupo normal de --max."""
    pendientes = get_pendientes_para("gael")
    if not pendientes:
        return 0

    print(f"[Bull] {len(pendientes)} mensaje(s) pendientes en el Meeting Room.")
    generadas = 0

    for msg in pendientes[:max_mensajes]:
        ticker = _extraer_ticker_de_instruccion(msg["mensaje"])
        if not ticker:
            marcar_procesado(msg["id"])
            responder("gael", f"No he sabido identificar ningún ticker en: \"{msg['mensaje']}\" — "
                               f"intenta ser más específico (ej: 'analiza NVDA' o 'mira Nvidia').")
            continue

        if not _comprobar_y_registrar_peticion(provider):
            print("[Bull] Límite diario alcanzado — el resto de mensajes del Meeting Room se quedan pendientes para mañana.")
            break

        print(f"[Bull] Instrucción del Meeting Room: generar tesis de {ticker} (pedido por Marc).")
        try:
            resultado = generar_tesis(ticker, provider)
            tesis_id = create_tesis(
                ticker=ticker,
                contenido=resultado["contenido"],
                rating="BUY",
                titulo=resultado["titulo"],
                nombre=resultado["nombre"],
                sector=resultado["sector"],
                resumen=resultado["resumen"],
                precio_objetivo=resultado["precio_objetivo"],
                autor=f"Agente Bull ({provider}) — a petición",
                fuente=f"agente_bull_{provider}",
                criterio=f"Petición directa vía Meeting Room: \"{msg['mensaje']}\"",
                status="pending",
            )
            marcar_procesado(msg["id"])
            responder("gael", f"Hecho — tesis de {ticker} generada (#{tesis_id}), esperando tu aprobación en TESIS PENDIENTES.")
            generadas += 1
        except Exception as e:
            marcar_procesado(msg["id"])
            responder("gael", f"No he podido generar la tesis de {ticker}: {type(e).__name__}. Lo intento de nuevo en la próxima ejecución si me lo vuelves a pedir.")
            print(f"[Bull] ERROR procesando instrucción del Meeting Room ({ticker}): {type(e).__name__}: {e}")

    return generadas


def main():
    parser = argparse.ArgumentParser(description="Agente Bull — genera tesis alcistas pendientes de aprobación")
    parser.add_argument("--max", type=int, default=1, help="Número máximo de tesis a generar en esta ejecución")
    parser.add_argument("--provider", choices=["gemini", "claude"], default="gemini",
                         help="gemini = prueba gratuita (por defecto), claude = producción real")
    args = parser.parse_args()

    provider = args.provider

    if provider == "gemini" and not settings.gemini_api_key:
        print("[Bull] Falta GEMINI_API_KEY en el .env — abortando.")
        return
    if provider == "claude" and not settings.anthropic_api_key:
        print("[Bull] Falta ANTHROPIC_API_KEY en el .env — abortando.")
        return

    generadas_meeting_room = procesar_meeting_room(provider)
    cupo_restante = max(0, args.max - generadas_meeting_room)

    if cupo_restante == 0:
        print(f"[Bull] Cupo de hoy ({args.max}) ya cubierto con peticiones del Meeting Room. Fin.")
        return

    candidatos = select_candidates(max_candidates=cupo_restante)
    if not candidatos:
        if generadas_meeting_room == 0:
            print("[Bull] Ningún candidato cumple hoy los criterios (CANSLIM + corrección -8%/-25% desde máximo).")
        return

    print(f"[Bull] Proveedor: {provider}. {len(candidatos)} candidatos: {[c['ticker'] for c in candidatos]}")

    for i, c in enumerate(candidatos):
        ticker = c["ticker"]

        if not _comprobar_y_registrar_peticion(provider):
            break

        criterio = f"CANSLIM score {c['score']}, {c['pct_from_high']:.1f}% desde máximo de 52 semanas"
        print(f"[Bull] Generando tesis para {ticker} ({criterio})...")
        try:
            resultado = generar_tesis(ticker, provider)
            tesis_id = create_tesis(
                ticker=ticker,
                contenido=resultado["contenido"],
                rating="BUY",
                titulo=resultado["titulo"],
                nombre=resultado["nombre"],
                sector=resultado["sector"],
                resumen=resultado["resumen"],
                precio_objetivo=resultado["precio_objetivo"],
                autor=f"Agente Bull ({provider})",
                fuente=f"agente_bull_{provider}",
                criterio=criterio,
                status="pending",
            )
            print(f"[Bull] Tesis #{tesis_id} para {ticker} creada — pendiente de aprobación en /admin.")
        except Exception as e:
            print(f"[Bull] ERROR generando tesis para {ticker}: {type(e).__name__}: {e}")

        if i < len(candidatos) - 1:
            time.sleep(LIMITS[provider]["pausa_entre_tickers_seg"])


if __name__ == "__main__":
    main()