"""
Agente Laia — Comité de Ética de RSU Terminal. Activista, utópica, con
principios insobornables, cree en serio en el Manifiesto RSU (ver
frontend/pages/manifest.js). No genera contenido ni pide aprobación —
su trabajo es cuestionar lo que ya existe, incluido tu propio criterio.
Corre una vez por semana (domingo, junto a Gael) y envía su veredicto
directo a Telegram, sin pasar por ninguna cola de revisión.

Dos auditorías en esta v1, elegidas porque son las que se pueden medir
bien con los datos que ya existen:

  A) Lenguaje de hype en las tesis de Bull aprobadas esta semana —
     contra el pilar del Manifiesto "realismo operativo" (dominar el
     lenguaje del mercado, no perseguir el hype).

  B) Sesgo de aprobación — ¿apruebas más rápido las tesis sobre tickers
     que ya tienes en Cartera? — contra "solidaridad técnica" (el
     criterio no debería estar sesgado ni siquiera por comodidad propia).

Pendiente para más adelante (necesitan que se acumulen datos con el
tiempo, no tiene sentido pedírselo a una semana vista):
  - El Notario del Fracaso (post-mortem de tesis que salieron mal)
  - Balance especulativo semanal (LOTTERY/Reddit Pulse vs. CORE)

Uso:
    cd backend
    python3 ../agents/laia_ethics_agent.py
"""
import sys
import os
import re

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from config import settings  # noqa: E402
from services.tesis_service import get_approved_bull_tesis_last_days  # noqa: E402
from services.cartera_service import get_cartera  # noqa: E402
from services.telegram_service import enviar_telegram_foto, enviar_telegram  # noqa: E402
from services.laia_ethics_service import guardar_veredicto  # noqa: E402

LAIA_PHOTO_PATH = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'assets', 'team', 'laia.jpg')

# Palabras/patrones de hype que chocan con "realismo operativo" -- no es una
# lista exhaustiva ni un análisis semántico, es una señal de alarma simple
# y barata (sin gastar tokens de API en esto).
HYPE_PATTERNS = [
    r"\b10x\b", r"\b20x\b", r"\bmoonshot\b", r"no te lo pierdas",
    r"oportunidad única", r"va a explotar", r"esto va a volar",
    r"\bboom\b", r"increíble potencial", r"potencial explosivo",
    r"!!+",  # exclamaciones múltiples
]


def _auditar_lenguaje_hype(candidatos: list) -> dict:
    hallazgos = []
    for c in candidatos:
        contenido = (c.get("contenido") or "").lower()
        hits = []
        for pattern in HYPE_PATTERNS:
            matches = re.findall(pattern, contenido, re.IGNORECASE)
            if matches:
                hits.append((pattern, len(matches)))
        if hits:
            hallazgos.append({"ticker": c["ticker"], "hits": hits, "total": sum(h[1] for h in hits)})
    return {"hallazgos": hallazgos, "total_tesis": len(candidatos)}


def _auditar_sesgo_aprobacion(candidatos: list) -> dict:
    try:
        cartera_data = get_cartera()
        tickers_cartera = {p["ticker"].upper() for p in cartera_data.get("abiertas", [])}
    except Exception:
        tickers_cartera = set()

    con_posicion = []
    sin_posicion = []
    for c in candidatos:
        if not c.get("approved_at") or not c.get("created_at"):
            continue
        delay = c["approved_at"] - c["created_at"]
        if c["ticker"].upper() in tickers_cartera:
            con_posicion.append(delay)
        else:
            sin_posicion.append(delay)

    resultado = {"con_posicion_n": len(con_posicion), "sin_posicion_n": len(sin_posicion)}
    if con_posicion and sin_posicion:
        avg_con = sum(con_posicion) / len(con_posicion)
        avg_sin = sum(sin_posicion) / len(sin_posicion)
        resultado["avg_con_posicion_min"] = round(avg_con / 60, 1)
        resultado["avg_sin_posicion_min"] = round(avg_sin / 60, 1)
        resultado["sesgo_detectado"] = avg_con < avg_sin * 0.5  # aprueba menos de la mitad de rápido
    else:
        resultado["sesgo_detectado"] = False
        resultado["motivo"] = "Muestra insuficiente esta semana para comparar (hace falta al menos 1 de cada grupo)"
    return resultado


def _generar_veredicto_laia(hype_result: dict, sesgo_result: dict) -> str:
    hallazgos_txt = ""
    if hype_result["hallazgos"]:
        hallazgos_txt = "; ".join(f"{h['ticker']} ({h['total']} señales)" for h in hype_result["hallazgos"])
    else:
        hallazgos_txt = "ninguna esta semana"

    sesgo_txt = "sin datos suficientes para comparar"
    if sesgo_result.get("avg_con_posicion_min") is not None:
        sesgo_txt = (
            f"tesis sobre tickers que ya tenías en cartera: aprobadas en {sesgo_result['avg_con_posicion_min']} min de media; "
            f"tesis sobre tickers nuevos: {sesgo_result['avg_sin_posicion_min']} min de media. "
            f"Sesgo detectado: {'SÍ' if sesgo_result['sesgo_detectado'] else 'no'}"
        )

    prompt = (
        f"Eres Laia, el Comité de Ética de RSU Terminal. Tu personalidad: activista, utópica, con un punto de "
        f"mala leche, y crees en serio en el Manifiesto RSU (sus pilares: 'seguir el rastro', 'solidaridad "
        f"técnica' -- democratizar el conocimiento del trading, no que sea propiedad de las élites -- y "
        f"'realismo operativo' -- dominar el lenguaje del mercado, no perseguir el hype). Tienes principios "
        f"insobornables y no le debes lealtad a nadie del equipo, ni siquiera a unlord (tu jefe).\n\n"
        f"Esta semana revisaste dos cosas:\n\n"
        f"1. LENGUAJE DE HYPE en las tesis de Bull: {hallazgos_txt}\n"
        f"2. SESGO EN LAS APROBACIONES de unlord: {sesgo_txt}\n\n"
        f"Escribe tu veredicto semanal (4-6 frases) para el grupo de Telegram de la comunidad, en tu personaje "
        f"-- directa, sin diplomacia, citando el Manifiesto si viene al caso. Si no encontraste nada grave, dilo "
        f"también con tu propia voz (no tienes que inventar un problema si no lo hay, pero tampoco lo celebres "
        f"con excesivo entusiasmo, no es tu estilo). Responde SOLO con el mensaje, sin comillas ni explicación."
    )

    if not getattr(settings, "groq_api_key", ""):
        return f"🔴 Auditoría de Laia: hype detectado en {hallazgos_txt}. Sesgo: {sesgo_txt}"

    import requests
    try:
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {settings.groq_api_key}", "Content-Type": "application/json"},
            json={
                "model": "qwen/qwen3.6-27b",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 300,
                "temperature": 0.75,
                "reasoning_effort": "none",
                "reasoning_format": "hidden",
            },
            timeout=30,
        )
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"[Laia] No se pudo generar el veredicto con Groq ({type(e).__name__}: {e}), usando fallback")

    return f"🔴 Auditoría de Laia: hype detectado en {hallazgos_txt}. Sesgo: {sesgo_txt}"


def main():
    candidatos = get_approved_bull_tesis_last_days(days=7)
    print(f"[Laia] {len(candidatos)} tesis de Bull aprobadas esta semana a auditar.")

    hype_result = _auditar_lenguaje_hype(candidatos)
    print(f"[Laia] Auditoría de lenguaje: {len(hype_result['hallazgos'])} tesis con señales de hype.")

    sesgo_result = _auditar_sesgo_aprobacion(candidatos)
    print(f"[Laia] Auditoría de sesgo: {sesgo_result}")

    texto = _generar_veredicto_laia(hype_result, sesgo_result)
    texto = f"⚖️ *Comité de Ética — Laia*\n\n{texto}"

    if os.path.exists(LAIA_PHOTO_PATH):
        ok = enviar_telegram_foto(texto, LAIA_PHOTO_PATH)
    else:
        print(f"[Laia] No se encontró la foto en {LAIA_PHOTO_PATH} — enviando solo texto")
        ok = enviar_telegram(texto)

    try:
        guardar_veredicto(texto, hype_result, sesgo_result, len(candidatos), ok)
        print("[Laia] Veredicto guardado en el histórico.")
    except Exception as e:
        print(f"[Laia] No se pudo guardar el veredicto en el histórico ({type(e).__name__}: {e})")

    print("[Laia] Veredicto enviado a Telegram." if ok else "[Laia] No se pudo enviar el veredicto.")


if __name__ == "__main__":
    main()