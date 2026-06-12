from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "RSU Terminal"
    secret_key: str = "dev_secret"
    algorithm: str = "HS256"
    token_expire_minutes: int = 480
    community_password: str = "RSU2026"
    cors_origins: list[str] = ["http://localhost:8000", "http://localhost:5500"]
    environment: str = "development"
    fred_api_key: str = ""
    url_cartera: str = ""

    class Config:
        env_file = ".env"

settings = Settings()