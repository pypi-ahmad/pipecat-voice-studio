"""Runtime readiness diagnostics shared by the API and UI.

Read-only introspection of installed package versions and CUDA/GPU state,
used by the FastAPI `/health` endpoint (`api/app.py`) and the Streamlit
Command center page. Must not import or touch application settings; this
module only reports on the environment torch/pipecat/streamlit are already
running in.
"""

import platform
from importlib.metadata import PackageNotFoundError, version
from typing import TypedDict

import torch


class RuntimeReadiness(TypedDict):
    """Installed framework and CUDA readiness details."""

    status: str
    python: str
    pipecat: str
    streamlit: str
    torch: str
    cuda_available: bool
    gpu: str | None


def _package_version(package: str) -> str:
    try:
        return version(package)
    except PackageNotFoundError:
        return "not installed"


def runtime_readiness() -> RuntimeReadiness:
    """Collect installed framework and CUDA readiness information."""

    cuda_available = torch.cuda.is_available()
    return {
        "status": "ok",
        "python": platform.python_version(),
        "pipecat": _package_version("pipecat-ai"),
        "streamlit": _package_version("streamlit"),
        "torch": torch.__version__,
        "cuda_available": cuda_available,
        # Reports only the first visible device; multi-GPU selection is not modeled here.
        "gpu": torch.cuda.get_device_name(0) if cuda_available else None,
    }
