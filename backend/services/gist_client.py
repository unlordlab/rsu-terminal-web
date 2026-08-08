"""
gist_client.py -- cabeceras comunes para leer los Gists de los scans nocturnos.

Siete servicios del backend leen un Gist (briefing, RS/RW, Scanner, Thematic,
CANSLIM, medianas sectoriales y Congress) y ninguno mandaba token. La API de
Gists limita a 60 peticiones/hora sin autenticar, y el límite es POR IP: los
siete competían por el mismo cupo, así que un rato de mala suerte podía
encadenar 403 en varios módulos a la vez. Con token son 5.000/hora.

Solo se comparte la cabecera y no la lectura entera a propósito: cada servicio
procesa su Gist de forma distinta (qué considera un dato válido, cuánto lo
cachea, si cachea también el fallo), y unificar eso obligaría a reescribir esa
lógica en siete sitios sin necesidad.

Ver hallazgo #20 de la auditoría de Market.
"""
from config import settings

# Formato de respuesta que ya venían pidiendo los servicios. Se unifica en el
# actual: `v3+json` es el nombre antiguo del mismo formato, GitHub lo acepta
# igual, y tenerlos mezclados solo invitaba a preguntarse si había una razón.
_ACCEPT = "application/vnd.github+json"


def cabeceras_gist() -> dict:
    """Cabeceras para una lectura de Gist, con token si está configurado.

    Sin token devuelve exactamente lo que se mandaba antes, así que el
    comportamiento no cambia hasta que se rellene GITHUB_TOKEN en el .env.
    """
    cabeceras = {"Accept": _ACCEPT}
    token = getattr(settings, "github_token", "")
    if token:
        cabeceras["Authorization"] = f"Bearer {token}"
    return cabeceras
