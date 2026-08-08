"""
Test del ratio put/call de CBOE (services/putcall_service.py).

Esta pieza es raspado de una página, no una API con contrato, así que lo que
hay que fijar no es tanto el número como el COMPORTAMIENTO ANTE EL FALLO: si
CBOE cambia su web, el módulo tiene que callarse, no publicar cualquier cifra
que haya pescado del HTML.

Uso:
    cd backend
    python -m pytest tests/test_putcall.py -v
"""
import sys, os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'shared'))

from services.putcall_service import _extraer, get_put_call_ratio  # noqa: E402

# Trozo real del HTML que sirve CBOE, con el JSON escapado dentro de un script.
HTML_REAL = (
    r'<script>self.__next_f.push([1,"24:[\"$\",\"$L32\",null,{\"data\":{\"optionsData\":'
    r'{\"ratios\":[{\"name\":\"TOTAL PUT/CALL RATIO\",\"value\":\"0.76\"},'
    r'{\"name\":\"INDEX PUT/CALL RATIO\",\"value\":\"0.98\"},'
    r'{\"name\":\"EXCHANGE TRADED PRODUCTS PUT/CALL RATIO\",\"value\":\"0.79\"},'
    r'{\"name\":\"EQUITY PUT/CALL RATIO\",\"value\":\"0.54\"},'
    r'{\"name\":\"CBOE VOLATILITY INDEX (VIX) PUT/CALL RATIO\",\"value\":\"0.29\"}]}}}]"])</script>'
)


def test_saca_los_cinco_ratios_del_html_real():
    r = _extraer(HTML_REAL)
    assert r == {"total": 0.76, "indices": 0.98, "etfs": 0.79,
                 "acciones": 0.54, "vix": 0.29}


def test_si_cambia_la_pagina_no_se_inventa_nada():
    assert _extraer("") == {}
    assert _extraer("<html>una pagina cualquiera</html>") == {}
    # El nombre cambia -> ese ratio no se publica, en vez de pescar otro numero
    assert "total" not in _extraer(HTML_REAL.replace("TOTAL PUT/CALL RATIO", "TOTAL P/C"))


def test_un_valor_imposible_se_descarta():
    """Si la extraccion pesca un numero que no puede ser un ratio put/call
    (historicamente se mueve entre 0,3 y 2 largos), se tira: publicar un 99
    seria peor que no publicar nada."""
    assert _extraer(HTML_REAL.replace(r'\"0.76\"', r'\"99.9\"')).get("total") is None
    assert _extraer(HTML_REAL.replace(r'\"0.76\"', r'\"0.0\"')).get("total") is None


def test_sin_el_total_no_hay_tarjeta():
    """El numero grande es el total; sin el, la respuesta es ok:False y el
    frontend omite la franja entera."""
    resp = MagicMock(status_code=200,
                     text=HTML_REAL.replace("TOTAL PUT/CALL RATIO", "OTRA COSA"))
    with patch("services.putcall_service.requests.get", return_value=resp):
        r = get_put_call_ratio()
    assert r["ok"] is False


def test_un_fallo_de_red_no_lanza():
    with patch("services.putcall_service.requests.get", side_effect=Exception("sin red")):
        r = get_put_call_ratio()
    assert r["ok"] is False and "sin red" in r["error"]


def test_las_zonas_usan_los_cortes_convencionales():
    resp = MagicMock(status_code=200, text=HTML_REAL)
    with patch("services.putcall_service.requests.get", return_value=resp), \
         patch("services.cache.cache.set"):
        assert get_put_call_ratio()["zona"] == "normal"          # 0.76

    for valor, esperada in ((r'\"1.10\"', "miedo"), (r'\"0.55\"', "complacencia"),
                            (r'\"1.00\"', "miedo"), (r'\"0.70\"', "complacencia")):
        resp = MagicMock(status_code=200, text=HTML_REAL.replace(r'\"0.76\"', valor))
        with patch("services.putcall_service.requests.get", return_value=resp), \
             patch("services.cache.cache.set"):
            assert get_put_call_ratio()["zona"] == esperada, f"{valor} debía ser {esperada}"
