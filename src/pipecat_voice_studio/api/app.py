"""FastAPI application."""

from typing import Annotated

from fastapi import Depends, FastAPI
from pydantic import BaseModel

from pipecat_voice_studio.config import Settings, get_settings
from pipecat_voice_studio.diagnostics import runtime_readiness


class HealthResponse(BaseModel):
    """Runtime health response."""

    status: str
    application: str
    environment: str
    python: str
    pipecat: str
    streamlit: str
    torch: str
    cuda_available: bool
    gpu: str | None


app = FastAPI(title=get_settings().app_name)


@app.get("/health", response_model=HealthResponse)
def health(settings: Annotated[Settings, Depends(get_settings)]) -> HealthResponse:
    """Report application and local runtime readiness."""

    return HealthResponse(
        application=settings.app_name,
        environment=settings.environment,
        **runtime_readiness(),
    )
