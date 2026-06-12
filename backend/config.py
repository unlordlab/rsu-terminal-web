from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "RSU Terminal"
    secret_key: str
    algorithm: str = "HS256"
    token_expire_minutes: int = 480
    cors_origins: list[str] = ["http://localhost:5500", "http://localhost:8000"]
    environment: str = "development"

    class Config:
        env_file = ".env"

settings = Settings()
