from pydantic import model_validator
from pydantic_settings import BaseSettings
from typing import List


# Valores que delatan que una clave no se ha llegado a definir de verdad: los
# defaults de este fichero y los textos de relleno de .env.example.
#
# Antes solo se comparaba contra los defaults literales, y eso dejaba abierto
# el caso más probable de todos (detectado el 28/07/2026): alguien copia
# .env.example, pone ENVIRONMENT=production y se olvida de cambiar las claves
# -- la app arrancaba tan tranquila con unas credenciales que están escritas
# en un fichero público del repositorio.
#
# Solo se buscan patrones inequívocos de relleno, NO una longitud mínima: un
# umbral de longitud podría dejar la app sin arrancar en el próximo despliegue
# si alguna clave real en producción resultara ser corta, y eso sería romper
# producción para prevenir algo hipotético.
_PREFIJOS_RELLENO = ("cambia_esto", "cambiar", "tu_", "your_", "xxx")
_VALORES_RELLENO  = {"dev_secret", "changeme_admin_key", "changeme", "secret", "admin", ""}


def _es_valor_de_relleno(valor: str) -> bool:
    v = (valor or "").strip().lower()
    return v in _VALORES_RELLENO or v.startswith(_PREFIJOS_RELLENO) or "changeme" in v

class Settings(BaseSettings):
    app_name: str = "RSU Terminal"
    secret_key: str = "dev_secret"
    algorithm: str = "HS256"
    token_expire_minutes: int = 480
    # Clave para los endpoints de administración de usuarios (/api/v1/auth/admin/*),
    # usada por Marc para subir el tier de un usuario tras un pago manual,
    # mientras no haya una pasarela de pago automatizada. Se envía en el
    # header X-Admin-Key. No confundir con el login normal de usuarios.
    admin_key: str = "changeme_admin_key"
    cors_origins: List[str] = [
        "http://localhost:8000",
        "http://localhost:5500",
        "http://127.0.0.1:8000",
    ]
    environment: str = "development"
    # Production domain — set via .env: CORS_ORIGINS=["https://tudominio.com"]
    # Capital total de referencia para el sizing por niveles Core/High/Lottery
    # (columna "Nivel" en la hoja de Cartera). Ej: CAPITAL_TOTAL=50000
    capital_total: float = 100000
    # API Keys
    fred_api_key: str = ""
    url_cartera: str = ""
    xai_api_key: str = ""
    fmp_api_key: str = ""
    finnhub_api_key: str = ""
    # Precios de Cartera en vivo por el WebSocket de trades de Finnhub, en vez
    # de las cotizaciones diferidas de yfinance. Ver
    # services/finnhub_stream_service.py.
    #
    # DESACTIVADO POR DEFECTO, y no por prudencia técnica: los términos de
    # Finnhub dicen que todos sus planes son «strictly for personal use unless
    # explicitly stated otherwise» y prohíben redistribuir los datos «or
    # derived results» a terceros sin aprobación escrita. Servir estos precios
    # a los usuarios de la terminal ES redistribución, así que encenderlo es
    # una decisión de licencia, no solo de configuración.
    #
    # Apagarlo devuelve Cartera a yfinance sin tocar nada más: el camino
    # anterior sigue intacto y en uso (es quien aporta el cierre anterior).
    finnhub_realtime: bool = False
    # YA NO SE USA EN NINGÚN SITIO desde el 29/07/2026: la única función que
    # la usaba (sorpresas de resultados en Research) pasó a yfinance, porque
    # el plan gratuito de Alpha Vantage son 25 peticiones AL DÍA y con ~100
    # usuarios el gráfico desaparecía a media mañana sin avisar.
    #
    # PERO EL CAMPO SE QUEDA, y no es por si acaso: la clave sigue en el .env
    # real del VPS, y Settings valida el fichero .env de forma estricta --
    # cualquier variable sin campo correspondiente tumba el arranque entero.
    # Quitar este campo sin quitar antes la línea del .env de producción
    # provocaría un 502, exactamente como ya pasó el 20/07/2026 con
    # openrouter_api_key. Para retirarla de verdad: primero el .env del VPS,
    # después este campo.
    alpha_vantage_api_key: str = ""
    groq_api_key: str = ""
    # openrouter_api_key: SÍ está configurada en el .env real (con clave
    # válida) aunque el código no la lea todavía en ningún sitio -- se
    # había quitado por error el 20/07/2026 (Fase 2.5) asumiendo que "sin
    # uso en código" significaba "segura de borrar", sin contar con que
    # Settings usa validación estricta (extra_forbidden): cualquier
    # variable en .env sin campo correspondiente tira abajo el arranque
    # entero. Restaurada tras causar un 502 en producción. Lección: antes
    # de quitar un campo de Settings, comprobar el .env real, no solo el
    # código.
    openrouter_api_key: str = ""
    anthropic_api_key: str = ""  # agente Bull (tesis) — ver conversacion 17/07/2026
    gemini_api_key: str = ""     # agente Bull, modo de prueba gratuito (Google AI Studio)
    # Proxy para TODAS las llamadas a yfinance (Algoritmo, Cartera, Scanner,
    # Options Flow, Research, Market — cada sitio que use yfinance en toda
    # la terminal) — ver conversación 16/07/2026 sobre bloqueos de Yahoo a
    # IPs de datacenter (Hetzner). Formato: http://usuario:contraseña@host:puerto
    # Vacío = sin proxy, yfinance funciona igual que siempre (comportamiento
    # actual sin cambios hasta que se configure uno de verdad).
    yfinance_proxy_url: str = ""
    # Notificaciones de Telegram — usado por el algoritmo RSU para avisar de
    # cambios de semáforo (ROJO/ÁMBAR/VERDE). Bot creado gratis con @BotFather;
    # chat_id puede ser el de un chat personal o el de un canal/grupo donde se
    # quiera publicar (para un canal, empieza por "-100...").
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    # @handle público del bot (sin @) -- para construir el enlace
    # t.me/<user>?start=<code> de vinculación por usuario (Watchlist, ver
    # 25/07/2026). Dato no sensible, distinto del token.
    telegram_bot_username: str = ""
    # chat_id PERSONAL del admin (mensaje directo, no el canal/grupo de
    # telegram_chat_id) -- ese canal es comunitario (Algoritmo, Cartera,
    # tesis, lo ve cualquier usuario suscrito), así que no es sitio para
    # avisos privados como el feedback de Community (puede incluir quejas,
    # contacto personal de usuarios, bugs delicados). Mismo bot de
    # telegram_bot_token, chat_id distinto. Ver sesión 26/07/2026.
    telegram_admin_chat_id: str = ""
    terminal_base_url: str = "http://178.104.148.117"  # ver conversacion 17/07/2026, sin dominio propio todavia
    # Reddit OAuth (grant_type=client_credentials, solo lectura de listados
    # públicos) -- necesario porque reddit.com/*.json bloquea con 403 desde la
    # IP del VPS (Hetzner), verificado 23/07/2026, independiente del
    # User-Agent. Se registra una app tipo "script" gratis en
    # reddit.com/prefs/apps -- puede tardar en aprobarse. Vacío = Reddit Pulse
    # sigue funcionando solo con StockTwits (o "sin datos" si ese también
    # falla), igual que hoy -- sin romper nada mientras no haya credenciales.
    reddit_client_id: str = ""
    reddit_client_secret: str = ""
    # Reddit exige un User-Agent único y descriptivo (con el usuario/app real)
    # para no ser limitado agresivamente -- actualizar con el nombre de la app
    # creada en reddit.com/prefs/apps.
    reddit_user_agent: str = "RSUTerminal/1.0"

    class Config:
        env_file = ".env"
        # CORS_ORIGINS solo admite formato JSON en el .env:
        #     CORS_ORIGINS=["https://x.com","https://y.com"]
        # El comentario anterior decía que valía separarlo por comas, y era
        # FALSO -- comprobado el 28/07/2026: con comas lanza SettingsError y
        # la app no arranca. Justo la trampa que alguien se encontraría al
        # configurar el dominio propio para HTTPS.
        env_file_encoding = "utf-8"

    @model_validator(mode="after")
    def _block_default_secrets_in_production(self):
        """Corta el arranque si en producción se han quedado SECRET_KEY o
        ADMIN_KEY con su valor por defecto (p. ej. porque el .env no se ha
        cargado, tiene un typo en el nombre de variable, o el volumen/env
        del contenedor no está bien montado). Es mejor que la app no arranque
        a que arranque en producción con credenciales públicas y conocidas.
        """
        if self.environment == "production":
            for nombre, valor in (("SECRET_KEY", self.secret_key), ("ADMIN_KEY", self.admin_key)):
                if _es_valor_de_relleno(valor):
                    raise ValueError(
                        f"{nombre} sigue con un valor de relleno ('{valor}') y "
                        "ENVIRONMENT=production. Define una clave propia, larga y "
                        "aleatoria, en el .env antes de desplegar."
                    )
        return self

settings = Settings()