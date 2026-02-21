from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="allow")

    # App
    APP_NAME: str = "LuminaLib"
    APP_ENV: str = Field(default="local", description="Environment name")
    API_PREFIX: str = "/api"
    LOG_LEVEL: str = "INFO"

    # Security
    JWT_SECRET_KEY: str = Field(default="change-me", description="JWT signing key")
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_EXPIRES_MIN: int = 30
    JWT_REFRESH_EXPIRES_DAYS: int = 7

    # Database
    DATABASE_URL: str = "postgresql+psycopg2://postgres:postgres@db:5432/luminalib"

    # Storage
    STORAGE_PROVIDER: str = "minio"
    MINIO_ENDPOINT: str = "minio:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    STORAGE_BUCKET: str = "luminalib"
    LOCAL_STORAGE_PATH: str = "./data"
    MAX_UPLOAD_MB: int = 25

    # LLM
    LLM_PROVIDER: str = "ollama"
    OLLAMA_BASE_URL: str = "http://ollama:11434"
    OLLAMA_MODEL: str = "mistral"

    # Recommendations
    RECS_PROVIDER: str = "ml_als"  # ml_als | content

    # Celery/Redis
    REDIS_URL: str = "redis://redis:6379/0"
    CELERY_BROKER_URL: str = "redis://redis:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/2"


settings = Settings()
