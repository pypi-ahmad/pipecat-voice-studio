"""Evaluation catalog and isolated runner tests."""

import subprocess
import threading
from pathlib import Path
from typing import Never, cast

import pytest
from pipecat.evals.harness import EvalResult
from pipecat.evals.scenario import EvalScenario

from pipecat_voice_studio import evaluations
from pipecat_voice_studio.storage import StudioStore


def _store_with_eval_graph(tmp_path: Path) -> tuple[StudioStore, str]:
    store = StudioStore(tmp_path / "studio.db")
    store.initialize()
    pipeline_id = next(graph["id"] for graph in store.list_graphs() if graph["mode"] == "eval")
    return store, pipeline_id


def test_scenario_catalog_is_allowlisted_and_parseable() -> None:
    assert evaluations.scenario_names() == tuple(evaluations.SCENARIOS)
    assert evaluations.scenario_names("happy-path") == ("happy-path",)
    for spec in evaluations.SCENARIOS.values():
        scenario = EvalScenario.load(evaluations._SCENARIO_DIR / spec.filename)
        assert scenario.turns

    with pytest.raises(ValueError, match="Unknown evaluation scenario"):
        evaluations.scenario_names("not-shipped")


def test_prepare_store_copies_graph_and_isolates_collision(tmp_path: Path) -> None:
    source, pipeline_id = _store_with_eval_graph(tmp_path)
    spec = evaluations.SCENARIOS["unavailable-slot"]

    temporary, copied_id = evaluations._prepare_store(
        source,
        pipeline_id,
        tmp_path / "temporary.db",
        spec,
    )

    assert temporary.get_graph(copied_id).mode.value == "eval"
    assert evaluations._appointment_count(temporary) == 1
    assert evaluations._appointment_count(source) == 0


def test_run_evaluation_persists_passing_result(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    store, pipeline_id = _store_with_eval_graph(tmp_path)
    ready = threading.Event()
    ready.set()

    class FinishedProcess:
        def poll(self) -> int:
            return 0

    monkeypatch.setattr(
        evaluations,
        "_start_worker",
        lambda **_kwargs: (FinishedProcess(), ["Bot ready!"], ready),
    )

    async def passed(_scenario: EvalScenario, _port: int) -> EvalResult:
        return EvalResult(
            scenario_name="policy-denial",
            passed=True,
            duration_ms=12,
            events_seen=[{"type": "function_call"}],
            debug_log=["matched"],
        )

    monkeypatch.setattr(evaluations, "_run_session", passed)

    result = evaluations.run_evaluation(store, pipeline_id, "policy-denial")

    assert result["passed"] is True
    persisted = store.list_eval_runs()
    assert persisted[0]["status"] == "passed"
    assert persisted[0]["result"]["duration_ms"] == 12


def test_run_evaluation_records_worker_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    store, pipeline_id = _store_with_eval_graph(tmp_path)

    def fail_to_start(**_kwargs: object) -> Never:
        message = "worker failed"
        raise RuntimeError(message)

    monkeypatch.setattr(evaluations, "_start_worker", fail_to_start)

    result = evaluations.run_evaluation(store, pipeline_id, "interruption")

    assert result["passed"] is False
    assert "worker failed" in result["failures"][0]
    assert store.list_eval_runs()[0]["status"] == "error"


def test_worker_helpers_bound_logs_and_force_cleanup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ready = threading.Event()

    class OutputProcess:
        def __init__(self) -> None:
            self.stdout = ["starting\n", "Bot ready!\n"]

    logs: list[str] = []
    evaluations._drain_output(cast("subprocess.Popen[str]", OutputProcess()), logs, ready)
    assert ready.is_set()
    assert logs == ["starting", "Bot ready!"]

    class StuckProcess:
        def __init__(self) -> None:
            self.terminated = False
            self.killed = False
            self.waits = 0

        def poll(self) -> None:
            return None

        def terminate(self) -> None:
            self.terminated = True

        def wait(self, *, timeout: float) -> int:
            self.waits += 1
            if self.waits == 1:
                command = "worker"
                raise evaluations.subprocess.TimeoutExpired(command, timeout)
            return 0

        def kill(self) -> None:
            self.killed = True

    process = StuckProcess()
    evaluations._stop_worker(cast("subprocess.Popen[str]", process))
    assert process.terminated and process.killed

    monkeypatch.setattr(evaluations, "_READY_TIMEOUT_SECONDS", 0)

    class ExitedProcess:
        def poll(self) -> int:
            return 9

    with pytest.raises(RuntimeError, match="worker exited with 9"):
        evaluations._wait_for_worker(
            cast("subprocess.Popen[str]", ExitedProcess()), threading.Event()
        )


def test_free_port_and_serialization() -> None:
    assert evaluations._free_port() > 0
    serialized = evaluations._serializable({"value": object()})
    assert isinstance(serialized, dict)
    assert cast("dict[str, str]", serialized)["value"].startswith("<object")
