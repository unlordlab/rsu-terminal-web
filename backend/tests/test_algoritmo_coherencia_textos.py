"""
Los puntos que ANUNCIA cada línea de "análisis de condiciones" tienen que
coincidir con los que de verdad suma el score.

BUG REAL QUE MOTIVA ESTE FICHERO (31/07/2026): al reescalar el score de 90 a
100 se ajustaron los tramos internos de cada factor con reemplazos de texto, y
seis líneas quedaron descuadradas — decían "(+11)" sumando 10, "(+6)" sumando
7, "(+7)" sumando 8. Nadie lo habría notado mirando la pantalla: los números
son plausibles y el total sigue cuadrando con la suma de los factores, no con
lo que dicen los textos.

Es exactamente el tipo de error que un test barato caza y una revisión visual
no. Lee el fuente y compara cada literal con la asignación de su misma línea.

Uso:
    cd backend
    python -m pytest tests/test_algoritmo_coherencia_textos.py -v
"""
import io
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

RUTA = os.path.join(os.path.dirname(__file__), '..', 'services', 'rsu_algoritmo_service.py')

# `x_score = 13; detalles.append(f"... (+13)")` — asignación y texto en la
# misma línea, que es como está escrito todo el bloque de factores.
_LINEA = re.compile(r'(\w+_score)\s*=\s*(-?\d+);\s*detalles\.append\(f?"[^"]*\(([+-]\d+)\)"\)')


def _lineas_con_puntos():
    fuente = io.open(RUTA, encoding='utf-8').read()
    return [(m.group(1), int(m.group(2)), int(m.group(3)))
            for m in _LINEA.finditer(fuente)]


def test_hay_lineas_que_comprobar():
    """Si el refactor cambia la forma de escribir esto, el test no debe pasar
    en silencio por no encontrar nada que mirar."""
    assert len(_lineas_con_puntos()) >= 12


def test_los_puntos_anunciados_coinciden_con_los_sumados():
    fallos = [
        f"{var} asigna {valor} pero el texto anuncia {texto:+d}"
        for var, valor, texto in _lineas_con_puntos()
        if valor != texto
    ]
    assert not fallos, "Textos descuadrados:\n  " + "\n  ".join(fallos)


def test_los_umbrales_del_texto_salen_de_las_constantes():
    """El texto de régimen decía "umbral 54" / "umbral 63" a fuego y se quedó
    obsoleto al pasar a 60/70. Ahora interpola las constantes: si alguien
    vuelve a escribir el número a mano, esto lo caza."""
    fuente = io.open(RUTA, encoding='utf-8').read()
    bloque = fuente[fuente.index('# 6. Régimen de mercado'):]
    bloque = bloque[:bloque.index('gatekeeper_a')]
    assert 'UMBRAL_VERDE_BAJISTA' in bloque
    assert 'UMBRAL_VERDE_ALCISTA' in bloque
    assert 'umbral 54' not in bloque and 'umbral 63' not in bloque


def test_el_maximo_alcanzable_son_100_puntos():
    """Los cinco factores que puntúan suman 100 exactos (la SMA200 no cuenta,
    solo decide el umbral). Si alguien retoca un peso sin recolocar el resto,
    el score deja de leerse como un porcentaje."""
    fuente = io.open(RUTA, encoding='utf-8').read()
    esperado = {'RSI': 20, 'VIX': 24, 'Breadth': 20, 'Volume': 14, 'EMA200W': 22}
    for factor, tope in esperado.items():
        patron = re.compile(r"metricas\['%s'\]\s*=\s*\{[^}]*?\"max\":\s*(\d+)" % factor, re.S)
        encontrados = {int(m) for m in patron.findall(fuente)}
        assert encontrados == {tope}, f"{factor}: max {encontrados}, se esperaba {{{tope}}}"
    assert sum(esperado.values()) == 100
