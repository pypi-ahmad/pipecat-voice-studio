"""Runtime readiness diagnostics shared by the API and UI."""

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
        "gpu": torch.cuda.get_device_name(0) if cuda_available else None,
    }
