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
    "groq": {
        # groq/compound usa GPT-OSS-120B + Llama 4 por dentro, NO el mismo
        # modelo qwen3.6-27b que usa Elia -- en principio no deberían
        # competir por la misma cuota (Groq limita por modelo, no por
        # cuenta entera), pero confírmalo en console.groq.com si ves
        # fallos de límite en cualquiera de los dos agentes.
        "max_requests_per_day": 100,    # conservador hasta ver el limite real en la practica
        "max_output_tokens": 8000,
        "pausa_entre_tickers_seg": 5,
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


def _extraer_precio_objetivo(texto: str, ticker: str = None) -> float | None:
    """Heurística, no exacta: busca la sección 13 (Precios Objetivo de
    Analistas) y coge la última cifra en dólares mencionada ahí — suele
    ser el target más reciente en la tabla. No es infalible (el informe lo
    escribe un LLM, el formato de tabla puede variar) — revisa el precio
    objetivo en el panel de admin antes de dar por buena la cifra.

    Validación añadida: si se pasa el ticker, se compara contra el precio
    real en vivo -- un precio objetivo por DEBAJO del precio actual no
    tiene sentido en una tesis alcista (BUY), así que se descarta en vez
    de mostrar un número que confunda. Ver conversación 18/07/2026."""
    m = re.search(r"\*\*13\. PRECIOS OBJETIVO DE ANALISTAS\*\*(.+?)(?=\n\*\*14\.|\Z)", texto, re.DOTALL)
    bloque = m.group(1) if m else texto
    precios = re.findall(r"\$\s?([0-9]+(?:[.,][0-9]+)?)", bloque)
    if not precios:
        return None
    try:
        objetivo = float(precios[-1].replace(",", "."))
    except Exception:
        return None

    if ticker:
        try:
            import yfinance as yf
            precio_actual = yf.Ticker(ticker).fast_info.last_price
            if precio_actual and objetivo <= precio_actual:
                print(f"[Bull] Precio objetivo descartado para {ticker}: ${objetivo} no supera el precio actual (${precio_actual:.2f}) — probable error de extracción del texto.")
                return None
        except Exception:
            pass  # si falla la comprobación en vivo, se deja pasar el valor extraído tal cual

    return objetivo


def _obtener_datos_verificados(ticker: str) -> str:
    """Recopila los datos numéricos básicos directamente de yfinance (la
    misma fuente que usa el resto de la terminal, fiable) y los formatea
    como bloque de contexto para inyectar al principio del prompt. Así el
    modelo NO tiene que "encontrar" estos números por su cuenta vía
    búsqueda web -- que es precisamente donde más falla (datos que no
    llega a recuperar, o que mezcla con su conocimiento desactualizado de
    entrenamiento). La búsqueda web se reserva para lo que sí necesita
    investigar de verdad: noticias, catalizadores, contexto cualitativo.
    Ver conversación 18/07/2026."""
    try:
        import yfinance as yf
        tk = yf.Ticker(ticker)
        info = tk.info
        fi = tk.fast_info

        precio_actual = fi.last_price if hasattr(fi, "last_price") else info.get("currentPrice")
        campos = {
            "Precio actual":              f"${precio_actual:.2f}" if precio_actual else None,
            "Máximo 52 semanas":          f"${info.get('fiftyTwoWeekHigh')}" if info.get("fiftyTwoWeekHigh") else None,
            "Mínimo 52 semanas":          f"${info.get('fiftyTwoWeekLow')}" if info.get("fiftyTwoWeekLow") else None,
            "Market Cap":                 f"${info.get('marketCap'):,}" if info.get("marketCap") else None,
            "P/E (trailing)":             info.get("trailingPE"),
            "P/E (forward)":              info.get("forwardPE"),
            "PEG ratio":                  info.get("pegRatio"),
            "Margen bruto":               f"{info.get('grossMargins')*100:.1f}%" if info.get("grossMargins") else None,
            "Margen operativo":           f"{info.get('operatingMargins')*100:.1f}%" if info.get("operatingMargins") else None,
            "Crecimiento ingresos (YoY)": f"{info.get('revenueGrowth')*100:.1f}%" if info.get("revenueGrowth") else None,
            "Deuda/Equity":               info.get("debtToEquity"),
            "Beta":                       info.get("beta"),
            "Volumen medio":              f"{info.get('averageVolume'):,}" if info.get("averageVolume") else None,
            "Sector":                     info.get("sector"),
            "Industria":                  info.get("industry"),
        }
        lineas = [f"- {k}: {v}" for k, v in campos.items() if v is not None]
        if not lineas:
            return ""

        fecha_hoy = datetime.now().strftime("%d/%m/%Y")
        return (
            f"**DATOS VERIFICADOS (Yahoo Finance, a fecha de hoy {fecha_hoy}) — úsalos como base, "
            f"NO los sustituyas por otra cifra que encuentres en la búsqueda ni por tu conocimiento "
            f"de entrenamiento, que puede estar desactualizado:**\n\n"
            + "\n".join(lineas) +
            f"\n\nPara contexto cualitativo adicional (catalizadores recientes, sentimiento, ratios "
            f"complementarios), puedes consultar también https://finviz.com/quote.ashx?t={ticker} "
            f"y fuentes de noticias recientes -- pero los datos numéricos de arriba ya están verificados, "
            f"no hace falta que los vuelvas a buscar.\n\n---\n\n"
        )
    except Exception as e:
        print(f"[Bull] No se pudieron obtener datos verificados de yfinance para {ticker}: {type(e).__name__}: {e}")
        return ""


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
    prompt = _obtener_datos_verificados(ticker) + PROMPT_TEMPLATE.format(ticker=ticker)

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


# ── Llamada a Groq (experimental — estilo Qwen/GPT-OSS, en pruebas) ─────
# IMPORTANTE: las herramientas de búsqueda web de Groq SOLO funcionan con
# su sistema "groq/compound", que por dentro usa GPT-OSS-120B y Llama 4
# -- NO es el mismo modelo qwen/qwen3.6-27b que usa Elia. No se puede
# tener a la vez el estilo de escritura de Qwen y búsqueda web real en
# Groq; son dos cosas distintas. Esto usa Compound (con búsqueda),
# aceptando que el estilo será distinto al de Elia. Ver conversación
# 18/07/2026.

def _generar_con_groq(ticker: str) -> str:
    import requests

    prompt = _obtener_datos_verificados(ticker) + PROMPT_TEMPLATE.format(ticker=ticker)

    intentos = 0
    while True:
        intentos += 1
        try:
            r = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {settings.groq_api_key}", "Content-Type": "application/json"},
                json={
                    "model": "groq/compound",
                    "messages": [{"role": "user", "content": prompt}],
                    "compound_custom": {"tools": {"enabled_tools": ["web_search", "visit_website"]}},
                    "max_tokens": LIMITS.get("groq", {}).get("max_output_tokens", 8000),
                },
                timeout=120,
            )
            if r.status_code == 429 and intentos < 4:
                espera = 15 * intentos
                print(f"[Bull] Rate limit de Groq, esperando {espera}s (intento {intentos}/3)...")
                time.sleep(espera)
                continue
            r.raise_for_status()
            data = r.json()
            return data["choices"][0]["message"]["content"]
        except requests.HTTPError:
            raise
        except Exception as e:
            if intentos < 4:
                time.sleep(10)
                continue
            raise


# ── Llamada a Claude (producción real) ──────────────────────────────────

def _generar_con_claude(ticker: str) -> str:
    import anthropic

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    prompt = _obtener_datos_verificados(ticker) + PROMPT_TEMPLATE.format(ticker=ticker)

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
    elif provider == "groq":
        texto = _generar_con_groq(ticker)
    else:
        texto = _generar_con_claude(ticker)

    if not texto or not texto.strip():
        raise ValueError("Respuesta vacía de la API (revisa si los tools fallaron)")

    # El aviso de "tesis de prueba" ya NO se mete dentro del contenido --
    # se quedaba pegado para siempre en el texto, visible también para los
    # usuarios una vez aprobada y publicada. Ahora el campo `fuente`
    # (agente_bull_gemini vs agente_bull_claude) ya distingue el origen,
    # y es el panel de administración el que muestra el aviso de forma
    # condicional SOLO en la revisión pendiente, nunca en lo publicado.
    # Ver conversación 18/07/2026.

    titulo, nombre = _extraer_titulo_y_nombre(texto)
    resumen = _extraer_resumen(texto)
    sector = _obtener_sector(ticker)
    precio_objetivo = _extraer_precio_objetivo(texto, ticker)

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
    parser.add_argument("--provider", choices=["gemini", "claude", "groq"], default="gemini",
                         help="gemini = prueba gratuita (por defecto), claude = producción real, groq = experimental (groq/compound, con búsqueda web)")
    args = parser.parse_args()

    provider = args.provider

    if provider == "gemini" and not settings.gemini_api_key:
        print("[Bull] Falta GEMINI_API_KEY en el .env — abortando.")
        return
    if provider == "claude" and not settings.anthropic_api_key:
        print("[Bull] Falta ANTHROPIC_API_KEY en el .env — abortando.")
        return
    if provider == "groq" and not settings.groq_api_key:
        print("[Bull] Falta GROQ_API_KEY en el .env — abortando.")
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