import os
from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    # Ambiente
    ENV: str = os.getenv("ENV", "local")

    # CORS
    ALLOWED_ORIGINS: str = os.getenv("ALLOWED_ORIGINS", "")

    # Postgres (metadados API)
    PG_HOST: str = os.getenv("PG_HOST", "localhost")
    PG_PORT: int = int(os.getenv("PG_PORT", "5432"))
    PG_DB: str = os.getenv("PG_DB", "agentgraph")
    PG_USER: str = os.getenv("PG_USER", "agent")
    PG_PASSWORD: str = os.getenv("PG_PASSWORD", "agent")

    SQLALCHEMY_DATABASE_URI: str | None = None

    # JWT
    JWT_SECRET: str = os.getenv("JWT_SECRET", "dev-secret")
    JWT_ALG: str = os.getenv("JWT_ALG", "HS256")
    JWT_EXPIRE_MINUTES: int = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))

    # Diretórios compartilhados
    DATA_DIR: Path = Path(os.getenv("DATA_DIR", "data"))

    # Celery/Redis
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

    class Config:
        env_file = ".env"

    def build_db_uri(self) -> str:
        return (
            self.SQLALCHEMY_DATABASE_URI
            or f"postgresql+psycopg2://{self.PG_USER}:{self.PG_PASSWORD}@{self.PG_HOST}:{self.PG_PORT}/{self.PG_DB}"
        )

    def ensure_dirs(self):
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)

settings = Settings()
DATABASE_URL = settings.build_db_uri()

