from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://tokenflow:tokenflow@localhost:5432/tokenflow_db"
    environment: str = "development"
    log_level: str = "info"
    synthetic_data_dir: str = str(Path(__file__).parent.parent.parent / "synthetic-data")
    allowed_origins: str = "http://localhost:3000,https://tokenflow-ai-two.vercel.app"

    # Redis / async queue
    redis_url: str = "redis://localhost:6379/0"

    # JWT / auth
    jwt_secret: str = "change-me-in-production-use-a-32-char-secret"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60
    default_admin_email: str = "admin@tokenflow.local"
    default_admin_password: str = "tokenflow2024"

    @property
    def origins(self) -> list[str]:
        base = [o.strip() for o in self.allowed_origins.split(",") if o.strip()]
        # Always allow the deployed Vercel frontend regardless of env var value
        always_allow = [
            "http://localhost:3000",
            "https://tokenflow-ai-two.vercel.app",
        ]
        return list(dict.fromkeys(base + always_allow))


settings = Settings()
