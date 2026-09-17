"""
Auditoría del briefing del 17/09/2026: la Fed subió los tipos y el briefing no se enteró.

EL CASO. El 16/09 la Fed subió los tipos por primera vez en tres años. Al
briefing del 17 le llegaron cuatro titulares que lo decían y NINGUNA de las dos
lecturas lo mencionó. En modo «mínimo» —el de todos los días— entran 2 titulares
por lista y se cogían los 2 más recientes: migrantes afganos, Banco de
Inglaterra, Assad y aranceles a la UE. Los de la Fed eran de la noche anterior.
El calendario tampoco podía avisar: faireconomy no trae nunca el dato publicado.

Uso:
    cd backend
    python -m pytest tests/test_briefing_auditoria_1709.py -v
"""
import inspect
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'scripts'))

import daily_briefing as D  # noqa: E402


def _t(*titulares):
    return [{"headline": h, "source": "X", "time": ""} for h in titulares]


# Las dos listas reales del 17/09, en el orden en que llegaron (más reciente primero).
MERCADO_1709 = _t(
    "Bank of England set to defy Fed’s rate-hike lead, despite rising inflation",
    "Impoverished by war in Iran, Afghan migrants return to Taliban rule - Reuters",
    "Trump hopes Iran war nearing end as Houthi-Saudi fighting escalates - Reuters",
    "US allies fret over how Trump might play his Taiwan hand with Xi - Reuters",
    "Trump says 'hopefully we are towards end' of Iran war - Reuters",
    "US officials met Iran-backed Houthis in Oman over the weekend, sources say - Reuters",
    "Wall St ends lower after Fed hikes interest rates, sees more tightening ahead - Reuters",
    "Israel, Morocco agree to upgrade diplomatic ties, Israeli government says - Reuters",
)
MEDIOS_1709 = _t(
    "Assad regime planned US journalist's kidnap for weeks, BBC finds",
    "'Hostile act': Trump threatens EU with tariffs over Canada associate-membership proposal",
    "Israel weaponises AI for West Bank demolitions",
    "US interest rates raised for first time in three years",
    "Putin braces for election stress test as Russians 'feel the pain' of struggling economy",
    "OpenAI reports more incidents of models acting deceptively",
    "Snapchat open to putting time limits on teens, boss tells BBC",
    "A stronger dollar and rising yields: How the Fed’s rate hike could hit global markets",
)


def test_EL_CASO_la_subida_de_la_fed_entra_en_el_minimo():
    mercado = [t["headline"] for t in D.priorizar_titulares(MERCADO_1709)[:2]]
    medios = [t["headline"] for t in D.priorizar_titulares(MEDIOS_1709)[:2]]
    assert any("Fed hikes interest rates" in h for h in mercado), mercado
    assert any("interest rates raised" in h for h in medios), medios
    assert not any("Afghan" in h for h in mercado)


def test_a_igual_peso_se_respeta_el_orden_de_llegada():
    lista = _t("Oil rises on supply fears", "Oil falls on demand worries", "Celebrity news")
    assert [t["headline"] for t in D.priorizar_titulares(lista)] == [
        "Oil rises on supply fears", "Oil falls on demand worries", "Celebrity news"]


def test_fed_up_no_es_la_fed():
    """«Fed up with AI interviews» (15/09) es «harto de»."""
    lista = _t("Fed up with AI interviews, job seekers drop out", "Treasury yields rise")
    assert D.priorizar_titulares(lista)[0]["headline"] == "Treasury yields rise"


def test_el_prompt_recorta_DESPUES_de_priorizar():
    fuente = inspect.getsource(D.build_prompt)
    assert "news = priorizar_titulares(news)[:max_titulares]" in fuente
    assert "major_headlines = priorizar_titulares(major_headlines)[:max_titulares]" in fuente


def test_el_prompt_del_minimo_lleva_la_fed():
    md = {"date": "2026-09-17", "time": "07:00 UTC", "calendar": [],
          "sesion": {"fecha": "2026-09-16", "en_curso": False, "hora_et": "03:00"}}
    p = D.build_prompt(md, MERCADO_1709, MEDIOS_1709, [], {}, [], [], recorte=D.NIVELES_RECORTE[-1])
    assert "Fed hikes interest rates" in p and "interest rates raised" in p
    assert "Afghan migrants" not in p
