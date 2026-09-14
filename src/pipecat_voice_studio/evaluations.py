"""Isolated Pipecat behavioral evaluation runner.

Executes automated dialog and audio test scenarios using Pipecat's evaluation
harness (`pipecat.evals`). Spawns ephemeral background worker processes against
isolated temporary SQLite databases to prevent pollution of production records.
Must never retain raw audio or execute unvalidated scenarios outside the
allowlist. Next module to read: `voice/bot.py` for evaluation WebSocket handling
and `storage.py` for evaluation run persistence.
"""

from __future__ import annotations

import asyncio
import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from pipecat.evals.harness import EvalResult, EvalSession
from pipecat.evals.scenario import EvalScenario

from pipecat_voice_studio.appointments import AppointmentBook
from pipecat_voice_studio.config import get_settings
from pipecat_voice_studio.storage import StudioStore

if TYPE_CHECKING:
    from collections.abc import Sequence


@dataclass(frozen=True)
class ScenarioSpec:
    """Static metadata for an evaluation scenario shipped with the studio."""

    filename: str
    description: str
    expected_appointments: int | None = None
    blocked_slot: str | None = None


SCENARIOS: dict[str, ScenarioSpec] = {
    "happy-path": ScenarioSpec(
        "happy_path.yaml",
        "Collect details, confirm once, then create exactly one appointment.",
        expected_appointments=1,
    ),
    "unavailable-slot": ScenarioSpec(
        "unavailable_slot.yaml",
        "Reject a collision and keep the appointment book unchanged.",
        expected_appointments=1,
        blocked_slot="2030-01-02T10:00:00+05:30",
    ),
    "policy-denial": ScenarioSpec(
        "policy_denial.yaml",
        "Do not create an appointment after an explicit denial.",
        expected_appointments=0,
    ),
    "interruption": ScenarioSpec(
        "interruption.yaml",
        "Accept a new user turn while the assistant is responding.",
    ),
    "synthetic-audio-smoke": ScenarioSpec(
        "synthetic_audio_smoke.yaml",
        "Exercise generated user speech through the real STT path without retaining audio.",
    ),
}

_SCENARIO_DIR = Path(__file__).with_name("eval_scenarios")
_READY_TIMEOUT_SECONDS = 20


def _creation_flags() -> int:
    return subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0


def _drain_output(process: subprocess.Popen[str], logs: list[str], ready: threading.Event) -> None:
    # Continuously drains worker stdout to prevent OS pipe buffers from deadlocking
    # the subprocess. Keeps only the latest 200 lines to bound memory.
    if process.stdout is None:
        return
    for line in process.stdout:
        clean = line.rstrip()
        logs.append(clean)
        del logs[:-200]
        if "Bot ready!" in clean:
            ready.set()


def _start_worker(
    *, port: int, body_path: Path, database_path: Path
) -> tuple[subprocess.Popen[str], list[str], threading.Event]:
    # Worker runs with an isolated PVS_DATABASE_PATH pointing to the tempdir,
    # ensuring that evaluation side effects cannot alter the production database.
    env = os.environ.copy()
    env["PVS_DATABASE_PATH"] = str(database_path)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUNBUFFERED"] = "1"
    command = [
        sys.executable,
        "-m",
        "pipecat_voice_studio.voice.bot",
        "--transport",
        "eval",
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
        "--runner-body",
        str(body_path),
    ]
    process = subprocess.Popen(  # noqa: S603
        command,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=_creation_flags(),
    )
    logs: list[str] = []
    ready = threading.Event()
    threading.Thread(
        target=_drain_output,
        args=(process, logs, ready),
        daemon=True,
        name="pvs-eval-log-reader",
    ).start()
    return process, logs, ready


def _stop_worker(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def _wait_for_worker(process: subprocess.Popen[str], ready: threading.Event) -> None:
    if ready.wait(_READY_TIMEOUT_SECONDS):
        return
    return_code = process.poll()
    detail = f"worker exited with {return_code}" if return_code is not None else "timeout"
    message = f"Evaluation worker did not become ready: {detail}"
    raise RuntimeError(message)


def _free_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def _prepare_store(
    source: StudioStore,
    pipeline_id: str,
    database_path: Path,
    spec: ScenarioSpec,
) -> tuple[StudioStore, str]:
    graph = source.get_graph(pipeline_id)
    temporary = StudioStore(database_path)
    temporary.initialize()
    temporary_pipeline_id = temporary.save_graph(graph, active=True)
    if spec.blocked_slot is not None:
        AppointmentBook(temporary, get_settings().pvs_timezone).create(
            session_id=None,
            attendee_name="Existing booking",
            purpose="Collision fixture",
            starts_at=datetime.fromisoformat(spec.blocked_slot),
            confirmed=True,
            flow_node="confirmation",
        )
    return temporary, temporary_pipeline_id


def _appointment_count(store: StudioStore) -> int:
    with store.connect() as connection:
        return int(connection.execute("SELECT COUNT(*) FROM appointments").fetchone()[0])


def _serializable(value: object) -> object:
    return cast("object", json.loads(json.dumps(value, default=str)))


async def _run_session(scenario: EvalScenario, port: int) -> EvalResult:
    session = EvalSession.from_scenario(
        scenario,
        f"ws://127.0.0.1:{port}",
        connect_timeout_s=10,
        default_timeout_ms=60_000,
        stop_bot=True,
    )
    return await session.run()


def run_evaluation(store: StudioStore, pipeline_id: str, scenario_name: str) -> dict[str, Any]:
    """Run one allowlisted scenario in a disposable worker and database."""
    try:
        spec = SCENARIOS[scenario_name]
    except KeyError as error:
        message = f"Unknown evaluation scenario: {scenario_name}"
        raise ValueError(message) from error

    run_id = store.create_eval_run(pipeline_id, scenario_name)
    process: subprocess.Popen[str] | None = None
    logs: list[str] = []
    try:
        with tempfile.TemporaryDirectory(prefix="pvs-eval-") as directory:
            workdir = Path(directory)
            temporary_store, temporary_pipeline_id = _prepare_store(
                store,
                pipeline_id,
                workdir / "evaluation.db",
                spec,
            )
            body_path = workdir / "runner-body.json"
            body_path.write_text(
                json.dumps({"pipeline_id": temporary_pipeline_id}),
                encoding="utf-8",
            )
            scenario = EvalScenario.load(_SCENARIO_DIR / spec.filename)
            port = _free_port()
            process, logs, ready = _start_worker(
                port=port,
                body_path=body_path,
                database_path=temporary_store.path,
            )
            try:
                _wait_for_worker(process, ready)
                eval_result = asyncio.run(_run_session(scenario, port))
            finally:
                _stop_worker(process)
                process = None
            failures = [str(failure) for failure in eval_result.failures]
            if (
                spec.expected_appointments is not None
                and _appointment_count(temporary_store) != spec.expected_appointments
            ):
                failures.append(
                    f"expected {spec.expected_appointments} appointments after the scenario"
                )
            passed = eval_result.passed and not failures and eval_result.skipped is None
            result = {
                "run_id": run_id,
                "scenario": eval_result.scenario_name,
                "passed": passed,
                "skipped": eval_result.skipped,
                "failures": failures,
                "duration_ms": eval_result.duration_ms,
                "events_seen": _serializable(eval_result.events_seen[-200:]),
                "debug_log": eval_result.debug_log[-200:],
                "worker_log": logs[-200:],
            }
            status = "passed" if passed else ("skipped" if eval_result.skipped else "failed")
            store.finish_eval_run(run_id, status=status, result=result)
            return result
    except Exception as error:
        result = {
            "run_id": run_id,
            "scenario": scenario_name,
            "passed": False,
            "failures": [f"{type(error).__name__}: {error}"],
            "worker_log": logs[-200:],
        }
        store.finish_eval_run(run_id, status="error", result=result)
        return result
    finally:
        if process is not None:
            _stop_worker(process)


def scenario_names(value: str | None = None) -> Sequence[str]:
    """Return one validated scenario name or the complete allowlist."""
    if value is None or value == "all":
        return tuple(SCENARIOS)
    if value not in SCENARIOS:
        message = f"Unknown evaluation scenario: {value}"
        raise ValueError(message)
    return (value,)
