"""
La curva de tipos decía «✓ NORMAL» sin tener el dato con el que juzgarla.

LO QUE VIO EL USUARIO, 21/08/2026, en su propia pantalla:

    SPREAD 10Y - 2Y:  N/D
                      ✓ NORMAL
    Curva normal — expectativas de crecimiento económico saludable

Un veredicto tranquilizador, con su explicación macroeconómica, **debajo de un
N/D**. Y no era un caso raro: pasaba todos los días.

POR QUÉ NO HABÍA 2Y. El código lo pedía a `^TU` y a `SHY` bajo un comentario
que decía «símbolo correcto». `^TU` es el FUTURO del bono a 2 años y `SHY` un
ETF: los dos devuelven un PRECIO, no un tipo. Un guard (`1.0 < v < 10.0`) los
rechazaba -- eso estaba bien-- pero el efecto neto era que **el 2Y no se
obtenía nunca**: ni salía en la curva, ni se podía calcular el spread 10Y-2Y,
que es el más mirado de todos. Comprobado el 21/08: `^TU` deslistado y `SHY`
devolviendo 82,02.

La serie oficial (`DGS2` de FRED) estaba a una línea: este mismo bloque ya
usaba `fred_csv` para DGS3MO y DGS10.

LA LECCIÓN, que es la que se ata aquí: un booleano de dos estados para algo que
tiene TRES (invertida / normal / no se sabe) convierte «no hay dato» en una
afirmación. Y la afirmación por defecto fue la tranquilizadora.

Uso:
    cd backend
    python -m pytest tests/test_market_curva_tipos.py -v
"""
import os
import sys
from unittest.mock import MagicMock, patch

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import services.market_service as M  # noqa: E402

FRED = {
    'DGS2':   [('2026-08-19', 4.19)],
    'DGS3MO': [('2026-08-19', 3.86)],
    'DGS5':   [('2026-08-19', 4.35)],
    'DGS10':  [('2026-08-19', 4.65)],
    'DGS30':  [('2026-08-19', 5.19)],
    'WALCL':  [(f'2026-0{6 + i // 4}-{1 + i:02d}', 6_700_000 + i * 100) for i in range(1, 8)],
    'WTREGEN': [('2026-08-19', 950_000)],
    'RRPONTSYD': [('2026-08-19', 0.0)],
    'FEDFUNDS': [], 'CPIAUCSL': [], 'UNRATE': [], 'PCEPILFE': [],
}


def _macro(fred=None, precio_yf=4.65):
    """get_fed_macro() con FRED y yfinance simulados. _fetch_yields vive
    anidada dentro, así que se prueba a través de la función pública.

    OJO CON DE DÓNDE VIENE CADA PUNTO, que se descubrió escribiendo esto: la
    curva MEZCLA proveedores. El 3M y (desde hoy) el 2Y salen de FRED; el 5Y,
    el 10Y y el 30Y de yfinance (^FVX, ^TNX, ^TYX). Por eso el 10Y de la
    pantalla (4,70%) y el DGS10 de FRED (4,65%) no coinciden exactamente."""
    datos = dict(FRED)
    datos.update(fred or {})
    tk = MagicMock()
    tk.history.return_value = (pd.DataFrame({"Close": [precio_yf]})
                               if precio_yf is not None else pd.DataFrame())
    with patch("services.cache.cache.get", return_value=None), \
         patch("services.cache.cache.set"), \
         patch.object(M, "fred_csv", side_effect=lambda sid, *a, **k: datos.get(sid, [])), \
         patch.object(M.yf, "Ticker", return_value=tk):
        return M.get_fed_macro()


# ── El 2Y ────────────────────────────────────────────────────────────────────

def test_el_2Y_sale_de_FRED_y_aparece_en_la_curva():
    """EL test. Antes no aparecía nunca."""
    y = _macro()["yields"]
    assert y["Y2Y"] == 4.19, "el 2 años sigue sin obtenerse"
    assert y["Y3M"] == 3.86, "el 3 meses lo pisa FRED (DGS3MO) sobre el de yfinance"
    assert y["Y10Y"] == 4.65


def test_el_spread_10_2_se_puede_calcular():
    y = _macro()["yields"]
    assert y["spread_10_2"] == round(4.65 - 4.19, 3)
    assert y["inverted"] is False, "con 10Y por encima del 2Y la curva es normal"


def test_un_2Y_por_encima_del_10Y_se_declara_invertida():
    y = _macro(fred={'DGS2': [('2026-08-19', 5.10)]})["yields"]
    assert y["spread_10_2"] < 0
    assert y["inverted"] is True


# ── Sin dato no hay veredicto ────────────────────────────────────────────────

def test_sin_2Y_la_curva_NO_se_declara_normal():
    """EL otro test, y el que motiva el fichero: `inverted` tiene que ser None,
    no False. False se pintaba como «✓ NORMAL · expectativas de crecimiento
    económico saludable» debajo de un N/D."""
    y = _macro(fred={'DGS2': []})["yields"]
    assert y["Y2Y"] is None
    assert y["spread_10_2"] is None
    assert y["inverted"] is None, (
        "sin el tipo a 2 años se está afirmando que la curva es normal")


def test_sin_10Y_tampoco_hay_veredicto():
    """Si el 10Y no llega por ninguna de las dos vias, el veredicto tiene que
    desaparecer igual que sin el 2Y."""
    y = _macro(fred={'DGS10': []}, precio_yf=None)["yields"]
    assert y["Y10Y"] is None
    assert y["spread_10_2"] is None and y["inverted"] is None


def test_la_pantalla_distingue_los_TRES_estados():
    """Que el backend mande None no sirve de nada si la pantalla lo pinta como
    «normal». Aquí se mira el código que construye la etiqueta."""
    ruta = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "pages", "market.js")
    with open(ruta, encoding="utf-8") as fh:
        fuente = fh.read()
    assert "inverted == null" in fuente or "inverted === null" in fuente, (
        "la pantalla no distingue «sin dato» de «no invertida»")
    assert "SIN DATO" in fuente


# ── Liquidez neta ────────────────────────────────────────────────────────────

def test_sin_TGA_no_se_inventa_una_liquidez_neta():
    """Restar cero de un balance de 6,7 billones da una liquidez neta inflada
    en cientos de miles de millones, con la misma pinta que una buena."""
    b = _macro(fred={'WTREGEN': []})["balance"]
    assert b["net_liq"] == "N/D"
    assert b["tga"] == "N/D"
    assert b["net_liq_num"] is None


def test_sin_RRP_tampoco():
    b = _macro(fred={'RRPONTSYD': []})["balance"]
    assert b["net_liq"] == "N/D" and b["rrp"] == "N/D"


def test_con_los_tres_datos_la_liquidez_neta_se_calcula():
    b = _macro()["balance"]
    assert b["net_liq_num"] is not None
    assert b["net_liq"].endswith("T")


# ── Una sola fuente para toda la curva ───────────────────────────────────────

def test_los_cinco_puntos_salen_de_FRED():
    """Hasta el 21/08 el 3M y el 2Y venian de FRED y el 5Y/10Y/30Y de yfinance:
    cinco puntos de una misma curva medidos por dos proveedores, con momentos y
    convenciones distintas. Se notaba -- el 10Y de pantalla marcaba 4,70%
    mientras DGS10 decia 4,65%-- y el pie del modulo afirma «Fuente: FRED»
    para todo. Un spread entre dos puntos de proveedores distintos hereda esa
    diferencia sin que nadie la vea."""
    y = _macro()["yields"]
    assert y["Y5Y"] == 4.35 and y["Y30Y"] == 5.19, "no se estan leyendo DGS5/DGS30"
    assert set(y["fuentes"].values()) == {"FRED"}
    assert y["curva_mixta"] is False


def test_si_una_serie_de_FRED_falla_se_usa_el_respaldo_y_SE_DICE():
    """Un punto de otra fuente es mejor que un hueco -- pero callarlo no. La
    pantalla avisa de cuales no vienen de FRED."""
    y = _macro(fred={'DGS10': []})["yields"]
    assert y["Y10Y"] == 4.65, "no ha tirado del respaldo de yfinance"
    assert y["fuentes"]["Y10Y"] == "yfinance"
    assert y["fuentes"]["Y2Y"] == "FRED"
    assert y["curva_mixta"] is True


def test_el_2Y_no_tiene_respaldo_en_yfinance_a_proposito():
    """Los simbolos que se probaban (^TU, SHY) devuelven PRECIOS, no tipos: no
    sirvieron nunca. Volver a colgar el 2Y de ahi seria repetir el fallo."""
    y = _macro(fred={'DGS2': []})["yields"]
    assert y["Y2Y"] is None, (
        "el 2Y ha salido de yfinance: esos simbolos devuelven precios de un "
        "futuro y de un ETF, no un tipo de interes")


def test_la_pantalla_avisa_cuando_la_curva_mezcla_proveedores():
    ruta = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "pages", "market.js")
    with open(ruta, encoding="utf-8") as fh:
        fuente = fh.read()
    assert "no viene de FRED" in fuente, (
        "la pantalla no dice nada cuando un punto de la curva sale de otro "
        "proveedor")
