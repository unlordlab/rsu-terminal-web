"""
spxl_phase_monitor.py — avisa por Telegram cuando SPXL entra en una fase
de compra nueva (o vuelve a STAND BY tras cerrar un ciclo).

Compara la fase actual contra la última fase conocida (guardada en un
fichero de estado) y solo notifica si ha cambiado -- para no repetir el
aviso en cada ejecución mientras la fase se mantiene igual.

Uso (pensado para cron, cada 30 min en horario de mercado):
    cd backend
    python3 ../agents/spxl_phase_monitor.py
"""
import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from services.spxl_service import get_spxl_live, PHASE_DROPS, PHASE_ALLOC  # noqa: E402
from services.telegram_service import enviar_telegram  # noqa: E402

STATE_FILE = os.path.join(os.path.dirname(__file__), '.spxl_phase_state.json')


def _leer_ultima_fase() -> int:
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE) as f:
                return json.load(f).get("phase_idx", -1)
        except Exception:
            pass
    return -1


def _guardar_fase(phase_idx: int):
    try:
        with open(STATE_FILE, 'w') as f:
            json.dump({"phase_idx": phase_idx}, f)
    except Exception as e:
        print(f"[SPXL Monitor] No se pudo guardar el estado: {e}")


def main():
    data = get_spxl_live()
    if not data.get("ok"):
        print(f"[SPXL Monitor] get_spxl_live() falló: {data.get('error')}")
        return

    fase_actual = data["phase"]  # "STAND BY" o "FASE N"
    phase_idx_actual = -1 if fase_actual == "STAND BY" else int(fase_actual.split()[-1]) - 1

    phase_idx_anterior = _leer_ultima_fase()

    print(f"[SPXL Monitor] Fase anterior: {phase_idx_anterior} | Fase actual: {phase_idx_actual}")

    if phase_idx_actual == phase_idx_anterior:
        print("[SPXL Monitor] Sin cambios, no se notifica.")
        return

    if phase_idx_actual > phase_idx_anterior:
        # Se ha activado una fase nueva (o varias de golpe, en una caída muy rápida)
        pct_alloc = PHASE_ALLOC[phase_idx_actual] * 100
        drop_pct  = PHASE_DROPS[phase_idx_actual] * 100
        texto = (
            f"🟢 *SPXL — Fase {phase_idx_actual + 1} activada*\n\n"
            f"Precio actual: ${data['price']:.2f} ({data['dd_pct']:.1f}% vs. referencia)\n"
            f"Caída que ha disparado esta fase: -{drop_pct:.0f}%\n"
            f"Asignación de esta fase: *{pct_alloc:.0f}%* del capital destinado a la estrategia\n\n"
            f"Revisa la sección SPXL en la terminal para ver el plan completo."
        )
    else:
        # phase_idx_actual == -1: se ha vuelto a STAND BY (un ciclo se cerró)
        texto = (
            f"⚪ *SPXL — Vuelta a STAND BY*\n\n"
            f"El ciclo de compras se ha cerrado. Precio actual: ${data['price']:.2f}\n"
            f"Sin fases activas — esperando la siguiente caída para volver a empezar."
        )

    ok = enviar_telegram(texto)
    print("[SPXL Monitor] Notificación enviada." if ok else "[SPXL Monitor] Fallo al enviar la notificación.")

    _guardar_fase(phase_idx_actual)


if __name__ == "__main__":
    main()