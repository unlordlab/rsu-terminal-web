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

settings = Settings()