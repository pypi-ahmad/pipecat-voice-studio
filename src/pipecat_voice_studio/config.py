"""Application configuration.

Single source of runtime settings, loaded from process environment variables
(and `.env` in the repository root) via Pydantic Settings. Every other module
that needs a credential, path, or tunable reads it from here rather than
`os.environ` directly. Unknown environment variables are ignored rather than
rejected (`extra="ignore"`), so a shared `.env` can carry keys this project
does not use without failing startup. See `pipecat_voice_studio.storage` for
how `pvs_database_path` is used, and `integrations/readiness.py` for how the
optional provider settings are turned into an operator-facing status.
"""

from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo

from pydantic import Field, SecretStr, field_validator
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
    pvs_public_base_url: str | None = None
    pvs_calendar_sync_seconds: int = Field(default=60, ge=15, le=3600)
    pvs_outbound_allowlist: str = ""
    twilio_account_sid: str | None = None
    twilio_auth_token: SecretStr | None = None
    twilio_from_number: str | None = None
    twilio_handoff_destination: str | None = None
    vonage_application_id: str | None = None
    vonage_api_key: str | None = None
    vonage_private_key: SecretStr | None = None
    vonage_signature_secret: SecretStr | None = None
    vonage_from_number: str | None = None
    vonage_handoff_destination: str | None = None
    google_service_account_json: SecretStr | None = None
    google_calendar_id: str | None = None
    hubspot_private_app_token: SecretStr | None = None
    simli_api_key: SecretStr | None = None
    simli_face_id: str | None = None
    pvs_healthcare_enabled: bool = False
    pvs_healthcare_data_key: SecretStr | None = None
    pvs_healthcare_approved_services: str = ""

    @property
    def environment(self) -> str:
        """Expose the conventional short name used by the UI."""
        return self.pvs_environment

    @property
    def bot_websocket_base_url(self) -> str:
        """Derive the browser WebSocket endpoint from the configured HTTP endpoint.

        Converts the configured http(s) worker URL into the matching ws(s) URL and
        appends the fixed `/realtime` path; there is no separate websocket setting.
        """
        scheme, separator, remainder = self.pvs_bot_base_url.partition("://")
        if separator == "" or scheme not in {"http", "https"}:
            msg = "PVS_BOT_BASE_URL must be an absolute HTTP(S) URL"
            raise ValueError(msg)
        websocket_scheme = "wss" if scheme == "https" else "ws"
        return f"{websocket_scheme}://{remainder.rstrip('/')}/realtime"

    @property
    def public_websocket_base_url(self) -> str | None:
        """Return the public WSS origin used by provider media callbacks."""
        if self.pvs_public_base_url is None:
            return None
        return "wss://" + self.pvs_public_base_url.removeprefix("https://").rstrip("/")

    @property
    def outbound_allowlist(self) -> frozenset[str]:
        """Return exact E.164 destinations approved for local outbound calls.

        `PVS_OUTBOUND_ALLOWLIST` is a comma-separated list of exact numbers; there is
        no wildcard or prefix matching, so every callable destination must be listed
        verbatim (see `integrations/telephony.require_allowed_destination`).
        """
        return frozenset(value.strip() for value in self.pvs_outbound_allowlist.split(",") if value)

    @property
    def healthcare_approved_services(self) -> frozenset[str]:
        """Return services explicitly approved by the operator for health data."""
        return frozenset(
            value.strip().lower()
            for value in self.pvs_healthcare_approved_services.split(",")
            if value
        )

    @field_validator("pvs_timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        """Reject invalid IANA timezone names during startup."""
        ZoneInfo(value)
        return value

    @field_validator("pvs_public_base_url")
    @classmethod
    def validate_public_url(cls, value: str | None) -> str | None:
        """Require TLS for public telephony callbacks.

        This URL is handed to Twilio/Vonage as the callback origin for untrusted
        public webhooks, so plain http is rejected outright rather than allowed
        and merely discouraged.
        """
        if value is not None and not value.startswith("https://"):
            msg = "PVS_PUBLIC_BASE_URL must use https://"
            raise ValueError(msg)
        return value.rstrip("/") if value else None


@lru_cache
def get_settings() -> Settings:
    """Return process-wide application settings."""

    return Settings()
