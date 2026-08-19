"""
Options Flow: el aviso de que el escaneo ha fallado no decía qué había fallado.

EL CASO QUE LO MOTIVA. El usuario recibió por Telegram esto y nada más:

    «Options Flow: el scan diario ha fallado. Hoy no se guardan cadenas de
    opciones -- ese dato NO se puede recuperar despues. (run 32079726454).»

Para saber si había sido la clave de administrador, el VPS caído o el propio
escaneo, había que entrar a GitHub a leer los registros de la ejecución. El
estado HTTP y el cuerpo de la respuesta YA estaban ahí (`$status` y
`/tmp/resp.json`), solo que en un paso distinto del que mandaba el aviso.

Y al abrirlo apareció algo peor, que es lo que se protege desde el backend en
este fichero: **un escaneo fallido devolvía HTTP 200**. `run_and_save_scan()`
respondía `{"ok": False}` con código 200, y el disparador solo miraba el
código -- así que un escaneo caído se apuntaba como bueno y el aviso ni
siquiera salía. Es el mismo fallo mudo que ya costó caro con la ruta
inexistente que devolvía 200 con `null` (hallazgo #27).

Lo mismo con la cobertura: el cuerpo decía cuántas filas se habían insertado,
y un día en el que se leyera media lista devolvía exactamente lo mismo que un
día sano. Ahora el cuerpo lleva los números con los que el disparador puede
avisar de lo que de verdad ha pasado.

Uso:
    cd backend
    python -m pytest tests/test_options_scan_aviso.py -v
"""
import os
import time
import sys
from unittest.mock import patch

from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import services.options_service as O  # noqa: E402
from main import app  # noqa: E402
from config import settings  # noqa: E402

CLAVE = {"X-Admin-Key": settings.admin_key}


def setup_function():
    # Ver el comentario en test_options_scan_asincrono.py: el limitador es
    # compartido y agotarlo hace fallar a los tests de después.
    from middleware.rate_limit import _store
    _store.clear()


def _flow_ok(**extra):
    base = {
        "ok": True, "scanned": 579, "respondidos": 575, "oi_cero": 3,
        "sin_direccion": 40, "scan_date": "2026-08-18",
        "calls_bought": [], "puts_bought": [], "calls_sold": [], "puts_sold": [],
        "oi_filas": [],
    }
    base.update(extra)
    return base


# ── El cuerpo tiene que traer con qué avisar ─────────────────────────────────

def test_el_resultado_trae_la_cobertura_no_solo_las_filas_insertadas():
    """Sin estos números, un día en el que se lea media lista devuelve lo
    mismo que un día sano y el disparador no tiene con qué avisar."""
    with patch.object(O, "get_options_flow", return_value=_flow_ok()), \
         patch.object(O, "save_current_scan", return_value={"ok": True, "inserted": 12, "total": 20}), \
         patch.object(O, "purgar_antiguos", return_value=0), \
         patch.object(O, "get_scan_log", return_value={"incompleto": False}):
        r = O.run_and_save_scan()
    assert r["pedidos"] == 579
    assert r["respondidos"] == 575
    assert r["cobertura_pct"] == 99.3
    assert r["sin_direccion"] == 40
    assert r["scan_date"] == "2026-08-18"
    assert r["incompleto"] is False


def test_un_dia_incompleto_se_declara_en_la_respuesta():
    """El backend ya sabe si el día sirve (`incompleto`). Antes ese juicio se
    quedaba en la base de datos, donde el disparador no lo ve."""
    with patch.object(O, "get_options_flow", return_value=_flow_ok(respondidos=300)), \
         patch.object(O, "save_current_scan", return_value={"ok": True, "inserted": 3, "total": 3}), \
         patch.object(O, "purgar_antiguos", return_value=0), \
         patch.object(O, "get_scan_log", return_value={"incompleto": True}):
        r = O.run_and_save_scan()
    assert r["incompleto"] is True
    assert r["cobertura_pct"] == 51.8


def test_un_escaneo_fallido_dice_por_que():
    with patch.object(O, "get_options_flow",
                      return_value={"ok": False, "error": "Yahoo no responde"}):
        r = O.run_and_save_scan()
    assert r["ok"] is False
    assert "Yahoo" in r["error"], "el motivo tiene que viajar, no perderse"


# ── Y un escaneo fallido tiene que fallar también por HTTP ───────────────────

def test_un_escaneo_fallido_sigue_sin_poder_parecer_un_exito():
    """Lo que este test protege NO ha cambiado: un escaneo que falla no puede
    apuntarse como bueno. Lo que ha cambiado el 19/08 es DÓNDE se ve.

    El disparo dejó de ser síncrono porque Nginx cortaba a los 60 s una
    petición de 15 minutos (ver test_options_scan_asincrono.py). Ahora el POST
    responde 202 al ARRANCAR -- que no es una afirmación sobre el resultado --
    y el fallo aparece en /scan-estado, que es lo que el disparador evalúa."""
    with patch("services.options_service.run_and_save_scan",
               return_value={"ok": False, "error": "Yahoo no responde"}):
        with TestClient(app) as c:
            resp = c.post("/api/v1/options/scan-now", headers=CLAVE)
            assert resp.status_code == 202, resp.status_code
            for _ in range(100):
                estado = c.get("/api/v1/options/scan-estado", headers=CLAVE).json()
                if not estado["en_curso"]:
                    break
                time.sleep(0.05)
    assert estado["en_curso"] is False
    assert "Yahoo" in (estado.get("error") or ""), (
        f"el fallo no llega al estado: {estado.get('error')}")


def test_un_escaneo_bueno_publica_sus_numeros_en_el_estado():
    """Los números de cobertura siguen llegando al disparador; ahora por
    /scan-estado en vez de por la respuesta del POST."""
    with patch("services.options_service.run_and_save_scan",
               return_value={"ok": True, "inserted": 12, "total": 20,
                             "pedidos": 579, "respondidos": 575,
                             "cobertura_pct": 99.3, "incompleto": False}):
        with TestClient(app) as c:
            assert c.post("/api/v1/options/scan-now", headers=CLAVE).status_code == 202
            for _ in range(100):
                estado = c.get("/api/v1/options/scan-estado", headers=CLAVE).json()
                if not estado["en_curso"]:
                    break
                time.sleep(0.05)
    assert estado["error"] is None
    r = estado["resultado"]
    assert r["cobertura_pct"] == 99.3 and r["incompleto"] is False


def test_si_ya_hay_un_escaneo_en_curso_tampoco_es_un_200():
    """Esta petición no ha hecho nada. Devolverla como 200 la apuntaba como un
    escaneo bueno del día."""
    import routers.options as R
    assert R._scan_lock.acquire(blocking=False)
    try:
        with TestClient(app) as c:
            resp = c.post("/api/v1/options/scan-now", headers=CLAVE)
    finally:
        R._scan_lock.release()
    assert resp.status_code == 409
    assert resp.json()["en_curso"] is True


def test_sin_clave_de_administrador_no_se_puede_disparar():
    """No se toca lo que ya protegía el endpoint (auditoría #4)."""
    with TestClient(app) as c:
        resp = c.post("/api/v1/options/scan-now")
    assert resp.status_code in (401, 403), resp.status_code
