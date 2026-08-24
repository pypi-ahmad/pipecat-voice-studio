"""Runtime diagnostics tests."""

from pipecat_voice_studio.diagnostics import runtime_readiness


def test_runtime_readiness_reports_available_hardware() -> None:
    readiness = runtime_readiness()

    assert readiness["status"] == "ok"
    assert readiness["python"].startswith(("3.13.", "3.14."))
    assert readiness["torch"].endswith("+cu132")
    assert isinstance(readiness["cuda_available"], bool)
    assert (readiness["gpu"] is not None) == readiness["cuda_available"]
