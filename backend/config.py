from pydantic import model_validator
from pydantic_settings import BaseSettings
from typing import List

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
    alpha_vantage_api_key: str = ""
    groq_api_key: str = ""
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
    terminal_base_url: str = "http://178.104.148.117"  # ver conversacion 17/07/2026, sin dominio propio todavia

    class Config:
        env_file = ".env"
        # Allows CORS_ORIGINS=https://x.com,https://y.com in .env
        env_file_encoding = "utf-8"

    @model_validator(mode="after")
    def _block_default_secrets_in_production(self):
        """Corta el arranque si en producción se ha quedado el SECRET_KEY o
        la COMMUNITY_PASSWORD por defecto (p. ej. porque el .env no se ha
        cargado, tiene un typo en el nombre de variable, o el volumen/env
        del contenedor no está bien montado). Es mejor que la app no arranque
        a que arranque en producción con credenciales públicas y conocidas.
        """
        if self.environment == "production":
            if self.secret_key == "dev_secret":
                raise ValueError(
                    "SECRET_KEY sigue en su valor por defecto ('dev_secret') "
                    "con ENVIRONMENT=production. Define un SECRET_KEY propio "
                    "en el .env antes de desplegar."
                )
            if self.admin_key == "changeme_admin_key":
                raise ValueError(
                    "ADMIN_KEY sigue en su valor por defecto "
                    "('changeme_admin_key') con ENVIRONMENT=production. Define una "
                    "clave de administrador propia en el .env antes de desplegar."
                )
        return self

settings = Settings()