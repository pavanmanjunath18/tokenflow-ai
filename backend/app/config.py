from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://tokenflow:tokenflow@localhost:5432/tokenflow_db"
    environment: str = "development"
    log_level: str = "info"
    synthetic_data_dir: str = str(Path(__file__).parent.parent.parent / "synthetic-data")
    allowed_origins: str = "http://localhost:3000"

    @property
    def origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]


settings = Settings()
