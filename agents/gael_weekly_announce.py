"""
gael_weekly_announce.py — resumen semanal de Gael para Telegram.

Corre una vez por semana (domingo por la mañana, vía cron) — mira todas
las tesis de Bull aprobadas en los últimos 7 días, elige la mejor (con
ayuda de Groq si hay más de una candidata) y la anuncia en el grupo de
Telegram con la foto de Gael. Así no se satura el grupo con una
notificación por cada tesis aprobada durante la semana.

Uso:
    cd backend
    python3 ../agents/gael_weekly_announce.py
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from services.tesis_service import get_approved_bull_tesis_last_days  # noqa: E402
from services.telegram_service import anunciar_mejor_tesis_semana  # noqa: E402


def main():
    candidatos = get_approved_bull_tesis_last_days(days=7)
    print(f"[GaelWeekly] {len(candidatos)} tesis de Bull aprobadas en los últimos 7 días.")
    ok = anunciar_mejor_tesis_semana(candidatos)
    if ok:
        print("[GaelWeekly] Resumen semanal enviado a Telegram.")
    else:
        print("[GaelWeekly] No se envió nada (sin candidatas o fallo de envío — ver logs arriba).")


if __name__ == "__main__":
    main()