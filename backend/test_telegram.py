"""
Prueba rápida de la conexión con Telegram — usa exactamente la misma función
que el sistema real (services.algoritmo_tracking_service._enviar_telegram),
así que si esto funciona, las notificaciones reales también funcionarán.

CÓMO USARLO:
1. Copia este archivo a la carpeta backend/ (junto a config.py, main.py, etc.)
2. Con el venv activado, desde esa carpeta:
       python test_telegram.py
3. Revisa tu Telegram — deberías recibir un mensaje de prueba en segundos.

No hace falta que uvicorn esté corriendo — es independiente.
"""
import sys

print("=" * 60)
print("Comprobando configuración...")

try:
    from config import settings
except Exception as e:
    print(f"❌ ERROR al importar config.py: {type(e).__name__}: {e}")
    sys.exit(1)

token   = getattr(settings, "telegram_bot_token", "")
chat_id = getattr(settings, "telegram_chat_id", "")

if not token:
    print("❌ TELEGRAM_BOT_TOKEN está vacío — revisa que esté en backend/.env")
    sys.exit(1)
if not chat_id:
    print("❌ TELEGRAM_CHAT_ID está vacío — revisa que esté en backend/.env")
    sys.exit(1)

print(f"✅ Token cargado: {token[:8]}...{token[-4:]}")
print(f"✅ Chat ID cargado: {chat_id}")
print()
print("Enviando mensaje de prueba...")

try:
    from services.algoritmo_tracking_service import _enviar_telegram
    enviado = _enviar_telegram(
        "🔧 *Prueba de conexión — RSU Algoritmo*\n\n"
        "Si ves este mensaje, la notificación de Telegram está bien configurada. "
        "El próximo cambio real de semáforo llegará con este mismo formato."
    )
except Exception as e:
    print(f"❌ ERROR inesperado: {type(e).__name__}: {e}")
    sys.exit(1)

print("=" * 60)
if enviado:
    print("✅ Mensaje enviado correctamente — revisa tu Telegram.")
else:
    print("❌ El envío falló — revisa el mensaje de error impreso arriba (viene de _enviar_telegram).")
    print("   Causas típicas: token incorrecto, chat_id incorrecto, o no le has escrito antes al bot.")
print("=" * 60)