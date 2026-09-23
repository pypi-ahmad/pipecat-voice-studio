---
type: reference
title: Isolated evaluation runs
description: Scenario allowlisting, temporary worker and database isolation, result handling, and the committed live-test gate.
tags:
  - evaluations
  - testing
  - runtime
verified:
  - by: openwiki/0.5.2
    at: 2026-09-23T15:44:25.460Z
sources:
  - id: openwiki-source-4ff611cd3b57c9a34b5746c5
    resource: repo://src/pipecat_voice_studio/evaluations.py
generated: { by: "codex", at: "2026-09-23T15:44:25.460Z" }
---

# Isolated evaluation runs

The evaluation runner executes a named scenario against an evaluation-mode pipeline in a disposable environment. It keeps evaluation-side writes out of the studio’s operational database, then records the result in the original store.

## Scenario selection

`evaluations.py` defines a fixed catalog: `happy-path`, `unavailable-slot`, `policy-denial`, `interruption`, and `synthetic-audio-smoke`. Each name maps to a checked-in scenario file and, for appointment scenarios, optional expectations about resulting bookings. Unknown names are rejected; callers can request one supported name or the catalog.

## Run lifecycle

1. The runner creates an evaluation-run record in the original `StudioStore`.
2. It creates a temporary directory and SQLite database, initializes that database, and copies the selected graph into it. The unavailable-slot scenario also seeds its collision fixture there.
3. It launches the bot worker as a child process, pointing `PVS_DATABASE_PATH` at the temporary database and passing the temporary graph identifier. The parent waits for the worker-ready signal before connecting the scenario.
4. It stops the worker after the scenario; termination escalates to a kill if the process does not exit within the timeout. The temporary directory is removed when its context ends.
5. The runner checks configured appointment-count expectations, bounds captured diagnostic/event lists, and saves the outcome to the original evaluation-run record. Exceptions are also recorded as an error result, and the `finally` path stops a still-running worker.

The isolation boundary applies to the worker’s database writes. A temporary database does not itself make external model calls free or prevent other external effects; configure credentials and paid-service usage accordingly.

## Live-test opt-in

The committed `tests/test_live_evaluations.py` test is marked `live_eval` and is skipped unless `PVS_RUN_LIVE_EVALS=1` and `OPENAI_API_KEY` are present. This describes the test’s execution gate, not a guard inside `run_evaluation`. That test file is absent from the current worktree; this reference is to its committed HEAD version, which was inspected without restoring it.

For the worker’s general session path, see [Voice session lifecycle](../runtime/session-lifecycle.md). Evaluation results are stored alongside the SQLite-backed records described in [SQLite state and semantic timeline](../state/sqlite-and-timeline.md).

## Source references

- [`evaluations.py`](../../src/pipecat_voice_studio/evaluations.py)
- [`voice/bot.py`](../../src/pipecat_voice_studio/voice/bot.py)
- `tests/test_live_evaluations.py` (committed HEAD; absent from the current worktree)
