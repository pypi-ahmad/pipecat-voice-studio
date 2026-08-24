"""Runtime diagnostics tests."""

from pipecat_voice_studio.diagnostics import runtime_readiness


def test_runtime_readiness_reports_cuda() -> None:
    readiness = runtime_readiness()

    assert readiness["status"] == "ok"
    assert readiness["python"].startswith("3.14.")
    assert readiness["torch"].endswith("+cu132")
    assert readiness["cuda_available"] is True
    assert readiness["gpu"] == "NVIDIA GeForce RTX 4060 Laptop GPU"
