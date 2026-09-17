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


# ── #78 Números en castellano ────────────────────────────────────────────────

PRINCIPAL_1709 = ("El S&P 500 cerró el miércoles en 7,551.81, una caída del 0.45%, pero solo el 32.1% "
                  "de los componentes subieron mientras el oscilador McClellan se hundía hasta -111.6. "
                  "El VIX subió un 2.97% hasta 17.71, y la curva sigue en contango (ratio 0.898). "
                  "El nivel que invalida esta lectura es la SMA20, en 7,661.94. Datos del cierre del "
                  "2026-09-16, futuros de las 03:02 ET y nóminas de +162k.")


def test_EL_CASO_el_principal_del_17_09_sale_en_castellano():
    t = D.numeros_a_formato_espanol(PRINCIPAL_1709)
    for esperado in ("7.551,81", "0,45%", "32,1%", "-111,6", "2,97%", "17,71", "0,898", "7.661,94"):
        assert esperado in t, esperado
    assert "2026-09-16" in t and "03:02 ET" in t and "+162k" in t, "fechas, horas y otras cifras intactas"


def test_con_los_dos_formatos_mezclados_no_se_toca_nada():
    """«7,675» es 7.675 en inglés y 7,675 en castellano: sin saber en qué está
    escrito el texto, adivinarlo es publicar un número que no es."""
    mezcla = "El S&P cerró en 7.551,81 y el VIX subió un 2.97% hasta 17,71."
    assert D.numeros_a_formato_espanol(mezcla) == mezcla


def test_lo_que_ya_esta_en_castellano_no_cambia():
    """La segunda lectura (`compound`) y los briefings del 15 y 16/09."""
    for t in ("El S&P 500 cerró 7 551,81, 0,45 % bajo.", "cayó un 0,45% hasta 7.585,73",
              "El McClellan está en -94,7 y el 31,2% subió."):
        assert D.numeros_a_formato_espanol(t) == t


def test_un_cero_con_tres_decimales_no_es_un_millar_espanol():
    """«ratio 0.898» hacía creer que el texto venía mezclado y no se convertía."""
    assert D.numeros_a_formato_espanol("ratio 0.898 y caída del 0.45%") == "ratio 0,898 y caída del 0,45%"


def test_sin_cifras_americanas_no_se_toca():
    t = "El 2026-09-17 a las 07:00 UTC, con 3 sesiones y 10 días."
    assert D.numeros_a_formato_espanol(t) == t


def test_se_aplica_al_principal_y_a_la_segunda_lectura():
    main = inspect.getsource(D.main)
    i = main.index("en_castellano = numeros_a_formato_espanol(briefing)")
    assert i < main.index("save_to_gist(briefing, market_data, bias")
    assert main.index("revision = revisar_briefing(briefing") < i, "después de revisar"
    assert '"text": numeros_a_formato_espanol(cuerpo)' in inspect.getsource(D.generar_segunda_lectura)


def test_sin_ninguna_cifra_claramente_americana_no_se_adivina():
    """«ratio 0.898» solo, sin un «%» ni un millar con coma, no dice en qué
    formato está el texto."""
    t = "La curva sigue en contango, con el ratio en 0.898."
    assert D.numeros_a_formato_espanol(t) == t


def test_un_porcentaje_en_castellano_basta_para_no_tocar():
    t = "El S&P cayó un 0,45% y el VIX subió un 2.97%."
    assert D.numeros_a_formato_espanol(t) == t
