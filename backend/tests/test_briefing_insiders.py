"""
Insider Flow sale del briefing: decisión del usuario el 10/09/2026.

POR QUÉ, en lo que se había visto. El bloque llegó a producir el peor
invento documentado del briefing. El 31/08/2026 al modelo le llegaron los
tickers desnudos (DKS, AMR, AMRC) y escribió:

    «la compra de insiders en energía (DKS, AMR) y defensa/industrial (AMRC)
     confirma que el capital inteligente está posicionándose para la duración
     del conflicto»

DKS es Dick's Sporting Goods, una tienda de artículos deportivos. Se arregló
pasando el nombre de la empresa (`nombre_corto`), pero el fondo seguía ahí: un
puñado de compras de directivos en cinco valores sueltos no dice nada del
mercado del día, y el modelo las usaba para CONFIRMAR la narrativa que ya
estaba montando. El 10/09 la segunda lectura volvió a citarlas —LILA, INBX,
GME— para concluir que «no son suficientes para revertir la tendencia», que
tampoco dice nada.

Y cuestan fichas en un prompt que lleva semanas sin caber en el nivel normal
(Newsfeed #28).

LO QUE ESTE FICHERO ATA:

  1. Que no llegue NADA de insiders al prompt, en las dos versiones del estilo.
  2. Que tampoco quede ninguna INVITACIÓN a hablar de ellos. El estilo ponía
     «Lo que dicen los insiders» como ejemplo de bloque: quitar el dato y dejar
     el ejemplo es pedirle al modelo que se lo invente, que es exactamente el
     fallo del 31/08 elevado al cuadrado.
  3. Que el script no siga llamando al backend para leerlos: sería una llamada
     con un token de servicio para tirar el resultado.

Insider Flow sigue existiendo como módulo de la terminal; lo que se quita es
su paso por el briefing.

Uso:
    cd backend
    python -m pytest tests/test_briefing_insiders.py -v
"""
import inspect
import io
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'scripts'))

import daily_briefing as D  # noqa: E402

RAIZ = os.path.join(os.path.dirname(__file__), "..", "..")
MD = {"date": "10/09/2026", "time": "07:54", "sectors": {}, "calendar": [],
      "sesion": {"en_curso": False, "fecha": "2026-09-09", "hora_et": "07:54"}}


@pytest.fixture(params=["v1", "v2"])
def version(request, monkeypatch):
    """Las DOS versiones del estilo: una regla quitada solo en la activa vuelve
    en cuanto alguien cambia `BRIEFING_PROMPT_VERSION`."""
    monkeypatch.setattr(D, "PROMPT_VERSION", request.param)
    return request.param


def test_el_prompt_no_menciona_insiders_en_ninguna_forma(version):
    """EL test. Sobre el prompt RENDERIDO, no sobre las constantes: si algún
    bloque se colara por otro camino, mirar las constantes no lo vería."""
    p = D.build_prompt(MD, [], [], [], {}, [], []).lower()
    assert "insider" not in p, (
        "el prompt sigue hablando de insiders: o llega el dato o queda una "
        "invitación a inventarlo")


def test_no_queda_el_ejemplo_de_bloque_que_invitaria_a_inventarlos(version):
    """La mitad que se olvida. Sin el dato, «Lo que dicen los insiders» como
    ejemplo de sección es una orden de rellenar el hueco."""
    p = D.build_prompt(MD, [], [], [], {}, [], [])
    assert "Lo que dicen los insiders" not in p


def test_build_prompt_ya_no_acepta_insiders():
    """Si el parámetro siguiera ahí, alguien volvería a pasarle algo y nada lo
    pintaría -- o peor, alguien volvería a pintarlo."""
    params = inspect.signature(D.build_prompt).parameters
    assert not any("insider" in n for n in params), list(params)


def test_el_script_ya_no_lee_insiders_del_backend():
    """Una llamada al backend con un token de servicio para tirar el resultado
    es coste y superficie sin nada a cambio."""
    assert not hasattr(D, "get_insider_clusters")
    assert not hasattr(D, "BRIEFING_AUTH_TOKEN")


def test_el_workflow_ya_no_pasa_el_token_de_servicio():
    """El YAML ES la configuración: aquí comprobar el texto es comprobar el
    comportamiento. Una línea comentada no cuenta como uso."""
    yml = io.open(os.path.join(RAIZ, ".github", "workflows", "daily_briefing.yml"),
                  encoding="utf-8").read()
    activas = [l for l in yml.splitlines() if not l.strip().startswith("#")]
    assert not any("BRIEFING_AUTH_TOKEN" in l for l in activas)
    assert not any("RSU_BACKEND_URL" in l for l in activas)


def test_el_comparador_de_modelos_tampoco_los_pide():
    """Construye el prompt real con los datos reales para comparar modelos: si
    siguiera pidiéndolos, reventaría al importar o compararía otro prompt."""
    fuente = io.open(os.path.join(RAIZ, "scripts", "comparar_modelos_briefing.py"),
                     encoding="utf-8").read()
    codigo = "\n".join(l for l in fuente.splitlines() if not l.strip().startswith("#"))
    assert "insider" not in codigo.lower()
