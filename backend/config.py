from pydantic import model_validator
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    app_name: str = "RSU Terminal"
    secret_key: str = "dev_secret"
    algorithm: str = "HS256"
    token_expire_minutes: int = 480
    community_password: str = "rsu2024"
    cors_origins: List[str] = [
        "http://localhost:8000",
        "http://localhost:5500",
        "http://127.0.0.1:8000",
    ]
    environment: str = "development"
    # Production domain — set via .env: CORS_ORIGINS=["https://tudominio.com"]
    # API Keys
    fred_api_key: str = ""
    url_cartera: str = ""
    xai_api_key: str = ""
    fmp_api_key: str = ""
    finnhub_api_key: str = ""
    alpha_vantage_api_key: str = ""
    groq_api_key: str = ""
    openrouter_api_key: str = ""

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
            if self.community_password == "rsu2024":
                raise ValueError(
                    "COMMUNITY_PASSWORD sigue en su valor por defecto "
                    "('rsu2024') con ENVIRONMENT=production. Define una "
                    "contraseña propia en el .env antes de desplegar."
                )
        return self

settings = Settings()