"""FastAPI application."""

from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel

from pipecat_voice_studio.config import Settings, get_settings
from pipecat_voice_studio.diagnostics import runtime_readiness
from pipecat_voice_studio.graph import PipelineGraph, compile_graph
from pipecat_voice_studio.storage import StudioStore


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


def get_store(settings: Annotated[Settings, Depends(get_settings)]) -> StudioStore:
    """Return an initialized local store."""
    store = StudioStore(settings.pvs_database_path)
    store.initialize()
    return store


@app.get("/health", response_model=HealthResponse)
def health(settings: Annotated[Settings, Depends(get_settings)]) -> HealthResponse:
    """Report application and local runtime readiness."""

    return HealthResponse(
        application=settings.app_name,
        environment=settings.environment,
        **runtime_readiness(),
    )


@app.get("/pipelines")
def list_pipelines(store: Annotated[StudioStore, Depends(get_store)]) -> list[dict]:
    """List stored pipeline metadata."""
    return store.list_graphs()


@app.get("/pipelines/{pipeline_id}", response_model=PipelineGraph)
def get_pipeline(
    pipeline_id: str, store: Annotated[StudioStore, Depends(get_store)]
) -> PipelineGraph:
    """Return one active validated pipeline."""
    try:
        return store.get_graph(pipeline_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail="Pipeline not found") from error


@app.post("/pipelines", status_code=201)
def create_pipeline(
    graph: PipelineGraph, store: Annotated[StudioStore, Depends(get_store)]
) -> dict[str, str]:
    """Compile before persisting a pipeline definition."""
    compile_graph(graph)
    return {"id": store.save_graph(graph, active=True)}
