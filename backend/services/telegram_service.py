"""
Envío de mensajes por Telegram — compartido entre Algoritmo (cambios de
semáforo) y Cartera (entradas/salidas de posición). Antes vivía duplicado
dentro de algoritmo_tracking_service.py; se extrae aquí para que Cartera lo
reutilice sin copiar el código.
"""
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