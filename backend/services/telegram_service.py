"""
Envío de mensajes por Telegram — compartido entre Algoritmo (cambios de
semáforo) y Cartera (entradas/salidas de posición). Antes vivía duplicado
dentro de algoritmo_tracking_service.py; se extrae aquí para que Cartera lo
reutilice sin copiar el código.
"""
import os
import requests


def enviar_telegram(mensaje: str) -> bool:
    """Envía un mensaje a Telegram vía la API de bots (sendMessage). Requiere
    TELEGRAM_BOT_TOKEN y TELEGRAM_CHAT_ID en .env — si no están configurados,
    no hace nada (no rompe el resto del flujo)."""
    from config import settings
    token   = getattr(settings, "telegram_bot_token", "")
    chat_id = getattr(settings, "telegram_chat_id", "")
    if not token or not chat_id:
        print("[Telegram] Sin TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID configurados — mensaje no enviado")
        return False
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": mensaje, "parse_mode": "Markdown"},
            timeout=10
        )
        if r.status_code != 200:
            print(f"[Telegram] La API respondió HTTP {r.status_code}: {r.text[:200]}")
            return False
        return True
    except Exception as e:
        print(f"[Telegram] Error enviando mensaje: {type(e).__name__}: {e}")
        return False


GAEL_PHOTO_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "assets", "team", "gael.jpg")


def enviar_telegram_foto(caption: str, photo_path: str) -> bool:
    """Envía una foto con pie de texto vía la API de bots (sendPhoto) —
    usado por Gael para anunciar tesis con su imagen. Mismo patrón de
    configuración que enviar_telegram()."""
    from config import settings
    token = getattr(settings, "telegram_bot_token", "")
    chat_id = getattr(settings, "telegram_chat_id", "")
    if not token or not chat_id:
        print("[Telegram] Sin TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID configurados — foto no enviada")
        return False
    try:
        with open(photo_path, "rb") as f:
            r = requests.post(
                f"https://api.telegram.org/bot{token}/sendPhoto",
                data={"chat_id": chat_id, "caption": caption, "parse_mode": "Markdown"},
                files={"photo": f},
                timeout=15
            )
        if r.status_code != 200:
            print(f"[Telegram] sendPhoto respondió HTTP {r.status_code}: {r.text[:200]}")
            return False
        return True
    except Exception as e:
        print(f"[Telegram] Error enviando foto: {type(e).__name__}: {e}")
        return False


def anunciar_mejor_tesis_semana(candidatos: list) -> bool:
    """Elige la mejor tesis de Bull aprobada en la última semana y la
    anuncia en Telegram con la foto de Gael -- pensado para correr una
    vez, el domingo por la mañana, en vez de notificar cada aprobación
    por separado. `candidatos` es la lista de tesis (dicts) ya filtrada
    por get_approved_bull_tesis_last_days()."""
    from config import settings
    import requests as _requests

    if not candidatos:
        print("[Telegram] Sin tesis aprobadas esta semana — no se envía resumen semanal.")
        return False

    if len(candidatos) == 1:
        elegida = candidatos[0]
        justificacion = "la única de la semana, así que gana por defecto"
    else:
        resumen_candidatas = "\n".join(
            f"- {c['ticker']} ({c['rating']}): {c.get('titulo', '')} — {c.get('criterio', '')}"
            for c in candidatos
        )
        elegida = candidatos[0]  # fallback si Groq falla
        justificacion = "la más sólida de la semana"
        if getattr(settings, "groq_api_key", ""):
            prompt = (
                f"Eres Gael, 'El Bull', el agente de tesis alcistas de RSU Terminal. Esta semana "
                f"escribiste {len(candidatos)} tesis que tu jefe (unlord) aprobó:\n\n{resumen_candidatas}\n\n"
                f"Elige la QUE MÁS TE CONVENCE de verdad (no la más ruidosa, la de mejor risk/reward "
                f"según lo que sabes de cada una) y responde EXCLUSIVAMENTE con el ticker exacto de tu "
                f"elegida, sin nada más, ni explicación, ni puntuación."
            )
            try:
                r = _requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {settings.groq_api_key}", "Content-Type": "application/json"},
                    json={
                        "model": "qwen/qwen3.6-27b",
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 20,
                        "temperature": 0.3,
                        "reasoning_effort": "none",
                        "reasoning_format": "hidden",
                    },
                    timeout=30,
                )
                if r.status_code == 200:
                    ticker_elegido = r.json()["choices"][0]["message"]["content"].strip().upper()
                    match = next((c for c in candidatos if c["ticker"].upper() == ticker_elegido), None)
                    if match:
                        elegida = match
            except Exception as e:
                print(f"[Telegram] No se pudo elegir la mejor tesis con Groq ({type(e).__name__}: {e}), usando la primera")

    prompt_anuncio = (
        f"Eres Gael, 'El Bull', el agente de tesis alcistas de RSU Terminal. Es domingo por la mañana. "
        f"De las tesis que escribiste esta semana ({len(candidatos)} en total, todas aprobadas por tu jefe unlord), "
        f"has elegido *{elegida['ticker']}* como tu favorita ({justificacion}). Escribe UN mensaje corto "
        f"(3-4 frases máximo) para el grupo de Telegram de la comunidad, con humor, en tu personaje de "
        f"optimista compulsivo, presentando esta como tu 'pick de la semana'. Menciona brevemente el "
        f"título: '{elegida.get('titulo', '')}'. NO uses hashtags ni emojis en exceso (máximo 1-2). "
        f"Responde SOLO con el mensaje, sin comillas ni explicación."
    )
    texto = f"🐂 *Pick de la semana de Gael:* {elegida['ticker']} — {elegida.get('titulo', '')}"
    if getattr(settings, "groq_api_key", ""):
        try:
            r = _requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {settings.groq_api_key}", "Content-Type": "application/json"},
                json={
                    "model": "qwen/qwen3.6-27b",
                    "messages": [{"role": "user", "content": prompt_anuncio}],
                    "max_tokens": 250,
                    "temperature": 0.8,
                    "reasoning_effort": "none",
                    "reasoning_format": "hidden",
                },
                timeout=30,
            )
            if r.status_code == 200:
                texto = r.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print(f"[Telegram] No se pudo generar el texto del resumen semanal ({type(e).__name__}: {e}), usando fallback")

    if not os.path.exists(GAEL_PHOTO_PATH):
        print(f"[Telegram] No se encontró la foto de Gael en {GAEL_PHOTO_PATH} — enviando solo texto")
        return enviar_telegram(texto)
    return enviar_telegram_foto(texto, GAEL_PHOTO_PATH)
    """Envía una foto con pie de texto vía la API de bots (sendPhoto) —
    usado por el agente Bull para anunciar tesis aprobadas con la imagen
    de Gael. Mismo patrón de configuración que enviar_telegram()."""
    from config import settings
    token = getattr(settings, "telegram_bot_token", "")
    chat_id = getattr(settings, "telegram_chat_id", "")
    if not token or not chat_id:
        print("[Telegram] Sin TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID configurados — foto no enviada")
        return False
    try:
        with open(photo_path, "rb") as f:
            r = requests.post(
                f"https://api.telegram.org/bot{token}/sendPhoto",
                data={"chat_id": chat_id, "caption": caption, "parse_mode": "Markdown"},
                files={"photo": f},
                timeout=15
            )
        if r.status_code != 200:
            print(f"[Telegram] sendPhoto respondió HTTP {r.status_code}: {r.text[:200]}")
            return False
        return True
    except Exception as e:
        print(f"[Telegram] Error enviando foto: {type(e).__name__}: {e}")
        return False