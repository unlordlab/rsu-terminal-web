"""
Auditoría del briefing del 18/09/2026: el tipo de la Fed del mes pasado y un «consenso» que no era de ningún dato.

EL CASO. Dos días después de que la Fed subiera al 3,75-4,00%, el prompt seguía
diciendo «Fed Funds actual 3,63%»: se leía `FEDFUNDS`, la MEDIA MENSUAL de
agosto. Con el bono a 3 meses en 3,96 salía un «gap» de −0,33 pp y el briefing
escribió que el mercado «espera subidas en 3 meses» y que «la Fed mantendrá los
tipos altos», sin nombrar la subida (#79). Con el rango del día (punto medio
3,875) el gap es −0,08: sin cambios.

Y «Aquí es donde el briefing se separa del consenso» —la opinión del mercado,
no la previsión de un dato— cayó como «CONSENSO INVENTADO» y costó un
reintento que no mejoró nada (#80).

Uso:
    cd backend
    python -m pytest tests/test_briefing_auditoria_1809.py -v
"""
import inspect
import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'scripts'))

import daily_briefing as D  # noqa: E402


def _fred(valores):
    return lambda serie: valores.get(serie)


# ── #79 El tipo de la Fed de hoy ─────────────────────────────────────────────

def test_EL_CASO_con_el_rango_de_hoy_no_sale_que_se_esperen_subidas():
    p = D.proxy_fed_funds(3.96, _fred({"DFEDTARL": ("2026-09-18", 3.75), "DFEDTARU": ("2026-09-18", 4.00),
                                       "FEDFUNDS": ("2026-08-01", 3.63)}))
    assert p["fed_funds_now"] == 3.875 and p["rango_objetivo"] == (3.75, 4.00)
    assert p["implied_gap_pct"] == -0.08 and p["interpretation"] == "sin cambios significativos"
    assert p["fuente"] == "rango objetivo a 2026-09-18"


def test_el_caso_de_partida_con_la_media_mensual_decia_subidas():
    p = D.proxy_fed_funds(3.96, _fred({"FEDFUNDS": ("2026-08-01", 3.63)}))
    assert p["implied_gap_pct"] == -0.33 and p["interpretation"] == "subidas"
    assert p["rango_objetivo"] is None and p["fuente"] == "media mensual de 2026-08", (
        "si se cae al mensual, tiene que decir que es una media")


def test_sin_3m_o_sin_tipo_no_hay_proxy():
    assert D.proxy_fed_funds(None, _fred({"FEDFUNDS": ("2026-08-01", 3.63)})) is None
    assert D.proxy_fed_funds(3.96, _fred({})) is None


def test_el_prompt_dice_el_rango_y_no_un_tipo_suelto():
    md = {"date": "2026-09-18", "time": "07:00 UTC", "calendar": [],
          "sesion": {"fecha": "2026-09-17", "en_curso": False, "hora_et": "03:00"},
          "fed_funds_proxy": D.proxy_fed_funds(3.96, _fred({"DFEDTARL": ("2026-09-18", 3.75),
                                                           "DFEDTARU": ("2026-09-18", 4.00)}))}
    prompt = D.build_prompt(md, [], [], [], {}, [], [])
    assert "rango objetivo: 3.75-4.00%" in prompt
    assert "Fed Funds actual" not in prompt


def test_fred_ultimo_se_salta_los_dias_sin_dato():
    """FRED marca con «.» los días sin observación."""
    r = MagicMock(status_code=200, text="observation_date,DFEDTARU\n2026-09-17,4.00\n2026-09-18,.\n")
    with patch.object(D.requests, "get", return_value=r):
        assert D._fred_ultimo("DFEDTARU") == ("2026-09-17", 4.0)
    with patch.object(D.requests, "get", return_value=MagicMock(status_code=500, text="")):
        assert D._fred_ultimo("DFEDTARU") is None


def test_get_market_data_usa_el_proxy_nuevo():
    assert 'proxy_fed_funds(data.get("IRX", {}).get("price"))' in inspect.getsource(D.get_market_data)


# ── #80 «El consenso» del mercado no es el de un dato ────────────────────────

def test_EL_CASO_separarse_del_consenso_no_es_inventar_un_consenso():
    texto = "Aquí es donde el briefing se separa del consenso. El S&P 500 subió un 1,14% el jueves."
    otros = D.revisar_briefing(texto, "", "", [])["otros"]
    assert not [o for o in otros if "CONSENSO INVENTADO" in o], otros


def test_el_consenso_de_un_dato_sin_calendario_sigue_cayendo():
    """El caso del 08/09: el empleo de FRED no trae consenso."""
    texto = "Las nóminas de 162k quedaron por debajo del consenso."
    otros = D.revisar_briefing(texto, "", "", [])["otros"]
    assert [o for o in otros if "CONSENSO INVENTADO" in o]


def test_el_consenso_con_cifra_sigue_cayendo():
    otros = D.revisar_briefing("El dato superó el consenso del 0,4%.", "", "", [])["otros"]
    assert [o for o in otros if "CONSENSO INVENTADO" in o]
