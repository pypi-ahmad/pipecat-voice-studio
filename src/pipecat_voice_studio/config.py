"""Application configuration."""

from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Non-secret application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="",
        extra="ignore",
    )

    app_name: str = "Pipecat Voice Studio"
    pvs_environment: str = "development"
    openai_api_key: SecretStr | None = None
    openai_base_url: str | None = None
    pvs_bot_base_url: str = "http://127.0.0.1:7860"
    pvs_database_path: Path = Path("data/pipecat_voice_studio.db")
    pvs_timezone: str = "Asia/Calcutta"
    pvs_realtime_model: str = "gpt-realtime-2.1-mini"
    pvs_cascade_stt_model: str = "gpt-realtime-whisper"
    pvs_cascade_llm_model: str = "gpt-5.6-luna"
    pvs_cascade_tts_model: str = "gpt-4o-mini-tts"
    pvs_realtime_voice: str = "marin"

    @property
    def environment(self) -> str:
        """Expose the conventional short name used by the UI."""
        return self.pvs_environment

    @property
    def bot_websocket_base_url(self) -> str:
        """Derive the browser WebSocket endpoint from the configured HTTP endpoint."""
        scheme, separator, remainder = self.pvs_bot_base_url.partition("://")
        if separator == "" or scheme not in {"http", "https"}:
            msg = "PVS_BOT_BASE_URL must be an absolute HTTP(S) URL"
            raise ValueError(msg)
        websocket_scheme = "wss" if scheme == "https" else "ws"
        return f"{websocket_scheme}://{remainder.rstrip('/')}/realtime"

    @field_validator("pvs_timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        """Reject invalid IANA timezone names during startup."""
        ZoneInfo(value)
        return value


@lru_cache
def get_settings() -> Settings:
    """Return process-wide application settings."""

    return Settings()
