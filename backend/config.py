from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "RSU Terminal"
    secret_key: str = "dev_secret"
    algorithm: str = "HS256"
    token_expire_minutes: int = 480
    community_password: str = "rsu2024"
    cors_origins: list[str] = ["http://localhost:8000", "http://localhost:5500"]
    environment: str = "development"
    fred_api_key: str = ""
    url_cartera: str = ""
    xai_api_key: str = ""
    fmp_api_key: str = ""
    finnhub_api_key: str = ""
    alpha_vantage_api_key: str = ""
    groq_api_key: str = ""

    class Config:
        env_file = ".env"

settings = Settings()