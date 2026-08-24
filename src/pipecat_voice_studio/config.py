"""Application configuration."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Non-secret application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="PVS_",
        extra="ignore",
    )

    app_name: str = "Pipecat Voice Studio"
    environment: str = "development"


@lru_cache
def get_settings() -> Settings:
    """Return process-wide application settings."""

    return Settings()
