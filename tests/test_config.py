"""Configuration tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pipecat_voice_studio.config import Settings

if TYPE_CHECKING:
    import pytest


def test_settings_use_prefixed_environment_variables(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PVS_ENVIRONMENT", "test")

    settings = Settings()

    assert settings.environment == "test"
    assert settings.app_name == "Pipecat Voice Studio"
    assert settings.bot_websocket_base_url == "ws://127.0.0.1:7860/realtime"
