"""
Envío de mensajes por Telegram — compartido entre Algoritmo (cambios de
semáforo) y Cartera (entradas/salidas de posición). Antes vivía duplicado
dentro de algoritmo_tracking_service.py; se extrae aquí para que Cartera lo
reutilice sin copiar el código.
"""
import os
import requests


def enviar_telegram(mensaje: str, chat_id: str = None) -> bool:
    """Envía un mensaje a Telegram vía la API de bots (sendMessage). Requiere
    TELEGRAM_BOT_TOKEN en .env — si no está configurado, no hace nada (no
    rompe el resto del flujo). Si no se pasa chat_id, usa el chat/canal fijo
    de operaciones (settings.telegram_chat_id) -- comportamiento idéntico al
    de siempre para los llamadores existentes (Algoritmo, Cartera, tesis
    semanal). Para notificar a un usuario concreto de Watchlist, se pasa su
    propio chat_id (ver users_service.get_telegram_chat_ids)."""
    from config import settings
    token = getattr(settings, "telegram_bot_token", "")
    dest  = chat_id or getattr(settings, "telegram_chat_id", "")
    if not token or not dest:
        print("[Telegram] Sin TELEGRAM_BOT_TOKEN/chat_id configurados — mensaje no enviado")
        return False
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": dest, "text": mensaje, "parse_mode": "Markdown"},
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
GAEL_PHOTO_SMALL_PATH = os.path.join(os.path.dirname(__file__), "..", "gael_telegram_small.jpg")


def _get_gael_photo_small() -> str:
    """Genera (una sola vez, se cachea en disco) una copia reducida de la
    foto de Gael para Telegram -- la original es un retrato grande
    (765x1024) y Telegram la mostraba ocupando toda la pantalla. Devuelve
    la ruta de la copia pequeña, o la original si Pillow falla por
    cualquier motivo (mejor una foto grande que ninguna)."""
    if os.path.exists(GAEL_PHOTO_SMALL_PATH):
        return GAEL_PHOTO_SMALL_PATH
    try:
        from PIL import Image
        img = Image.open(GAEL_PHOTO_PATH)
        img.thumbnail((320, 420))  # mantiene proporción, ~1/3 del tamaño original
        img.save(GAEL_PHOTO_SMALL_PATH, "JPEG", quality=85)
        return GAEL_PHOTO_SMALL_PATH
    except Exception as e:
        print(f"[Telegram] No se pudo redimensionar la foto de Gael ({type(e).__name__}: {e}), usando la original")
        return GAEL_PHOTO_PATH


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
        f"título: '{elegida.get('titulo', '')}'. Invita a la gente a leer el informe completo en la "
        f"sección Tesis de la terminal, buscando el ticker {elegida['ticker']}. NO uses hashtags ni "
        f"emojis en exceso (máximo 1-2), NO incluyas ningún enlace ni URL tú mismo (se añade aparte). "
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
        texto_final = f"{texto}\n\n📈 Léela entera en la sección Tesis: {settings.terminal_base_url}/tesis"
        return enviar_telegram(texto_final)
    texto_final = f"{texto}\n\n📈 Léela entera en la sección Tesis: {settings.terminal_base_url}/tesis"
    return enviar_telegram_foto(texto_final, _get_gael_photo_small())


# ── Vinculación de cuentas por usuario (Watchlist -> Telegram) ───────────────
# Un bot solo puede escribir a un chat_id si esa persona le escribió antes --
# restricción de la propia API de Telegram, no de este proyecto. Recibir esa
# interacción exige o bien un webhook (necesita HTTPS pública, que el VPS no
# tiene todavía) o long polling contra getUpdates (llamada saliente, sin
# puerto/HTTPS entrante) -- se usa long polling, mismo patrón de "bucle en
# segundo plano" ya usado en toda la terminal (ver routers/ws.py). Ver
# 25/07/2026.
_last_update_id = 0


def poll_and_process_updates() -> int:
    """Una pasada de long-polling: getUpdates bloquea hasta 25s en el lado
    de Telegram esperando un mensaje nuevo. Busca '/start <código>' (lo que
    manda Telegram automáticamente al abrir un enlace t.me/<bot>?start=...)
    y, si el código es válido, vincula la cuenta y confirma por Telegram.
    Devuelve cuántos updates se procesaron (solo para logging del bucle)."""
    global _last_update_id
    from config import settings
    token = getattr(settings, "telegram_bot_token", "")
    if not token:
        return 0
    try:
        r = requests.get(
            f"https://api.telegram.org/bot{token}/getUpdates",
            params={"offset": _last_update_id + 1, "timeout": 25},
            timeout=30,
        )
        if r.status_code != 200:
            return 0
        updates = r.json().get("result", [])
    except Exception as e:
        print(f"[Telegram] Error en getUpdates: {type(e).__name__}: {e}")
        return 0

    for upd in updates:
        _last_update_id = max(_last_update_id, upd.get("update_id", _last_update_id))
        msg     = upd.get("message") or {}
        text    = (msg.get("text") or "").strip()
        chat_id = msg.get("chat", {}).get("id")
        if not chat_id or not text.startswith("/start"):
            continue
        parts = text.split(maxsplit=1)
        if len(parts) != 2:
            continue
        from services.users_service import consume_telegram_link_code
        user_id = consume_telegram_link_code(parts[1].strip().upper(), str(chat_id))
        if user_id:
            enviar_telegram(
                "✅ Tu cuenta de RSU Terminal ha sido vinculada. A partir de ahora "
                "recibirás aquí tus alertas de Watchlist.", chat_id=chat_id)
        else:
            enviar_telegram(
                "⚠️ Código no reconocido o caducado. Genera uno nuevo desde "
                "*Mi Cuenta* en la terminal.", chat_id=chat_id)
    return len(updates)