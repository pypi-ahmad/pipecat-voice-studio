"""FastAPI contract tests."""

from http import HTTPStatus

import httpx
import pytest

from pipecat_voice_studio.api.app import app


@pytest.mark.asyncio
async def test_health_reports_runtime_readiness() -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == HTTPStatus.OK
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["application"] == "Pipecat Voice Studio"
    assert payload["python"].startswith("3.14.")
    assert payload["pipecat"] == "1.7.0"
    assert payload["streamlit"] == "1.62.0"
    assert payload["cuda_available"] is True
    assert payload["gpu"]
