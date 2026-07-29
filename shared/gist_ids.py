"""
gist_ids.py -- fuente ÚNICA del Gist de medianas sectoriales, importada
tanto por quien escribe (scripts/sector_medians.py) como por quien lee
(backend/services/research_service.py).

Por qué existe (29/07/2026): el ID vivía duplicado en dos sitios sin
ninguna relación entre ellos -- hardcodeado en research_service.py y, en
el script, leído del secret SECTOR_MEDIANS_GIST_ID de GitHub. Divergieron
sin que nadie se enterara: el job semanal terminaba en ÉXITO (escribía en
el Gist del secret) mientras el backend leía otro Gist que seguía vacío,
así que Research llevaba desde el 20/07/2026 cayendo en silencio a los
benchmarks estáticos escritos a mano. Un fallo de configuración no puede
disfrazarse de éxito verde en Actions.

Con el ID aquí, el script y el backend no pueden apuntar a Gists
distintos: es literalmente la misma constante. El secret de GitHub deja de
usarse (el ID nunca fue secreto -- ya estaba en el repo público; lo único
que hay que proteger es GIST_TOKEN, el permiso de escritura).

Los otros 5 Gists del proyecto (Scanner, RS/RW, CANSLIM, Thematic,
Congress, Briefing) siguen resolviéndose por variable de entorno en sus
scripts. No se migran aquí porque hoy funcionan y no se toca lo que no
está roto -- pero dos de ellos (rsrw_scan.py, daily_briefing.py) ya
llevaban el ID real como valor por defecto del os.environ.get(), que es
justo la red de seguridad que a medianas sectoriales le faltaba. Si algún
otro vuelve a divergir, este es el sitio donde traerlo.

NO depende de nada de backend/ (fastapi, pydantic) -- scripts/ corre en el
runner de GitHub Actions sin ese entorno instalado.
"""

# Gist creado a mano el 23/07/2026. Ojo al crear uno nuevo: el nombre del
# fichero va en el campo "Filename including extension...", NO en el de
# descripción -- en este el nombre acabó en la descripción y el fichero se
# quedó como "gistfile1.txt", que es inofensivo (el PATCH añade el fichero
# bueno al lado) pero despista al mirarlo.
SECTOR_MEDIANS_GIST_ID = "9a8f96a19c239a0be18aaded30d56de1"
SECTOR_MEDIANS_GIST_FILE = "sector_medians.json"

# El job es SEMANAL (domingos 10:00 UTC). Pasados estos días sin
# regenerarse, el dato deja de considerarse vigente y el consumidor cae a
# los benchmarks estáticos -- 2 ejecuciones perdidas seguidas ya no es un
# tropiezo puntual, es que algo está roto. Sin este umbral, unas medianas
# congeladas hace meses se seguirían presentando como "reales" solo porque
# el fichero existe.
SECTOR_MEDIANS_MAX_EDAD_DIAS = 14
