---
type: reference
title: Test contracts and current checkout caveat
description: Coverage map for the committed test suite, with a clear distinction between HEAD references and tests present in this worktree.
tags:
  - testing
  - quality
  - safety
verified:
  - by: openwiki/0.5.2
    at: 2026-09-23T15:57:58.894Z
sources:
  - id: openwiki-source-925c392508361b6248d963a6
    resource: repo://.github/workflows/live-evaluations.yml
  - id: openwiki-source-846e7f6440c6b75d9f0bb306
    resource: repo://.github/workflows/quality.yml
  - id: openwiki-source-05ccef8d4cf1698187f20464
    resource: repo://pyproject.toml
  - id: openwiki-source-f249cd1df82e31cdeebfb2a1
    resource: repo://src/pipecat_voice_studio/storage.py
generated: { by: "codex", at: "2026-09-23T15:57:58.894Z" }
---

# Test contracts and current checkout caveat

## Current checkout status

The 11 test modules listed below, plus `tests/__init__.py` (12 deleted paths total), are absent from the current worktree. Their test names and assertions were inspected from committed HEAD `2e12bed` as read-only references, as requested. They were not restored or run, so this page describes committed test contracts, not passing results or coverage in the current checkout.

The current `pyproject.toml` configures pytest to discover `tests/`, enables coverage reporting with an 80% minimum, and registers the `live_eval` marker. The standard quality workflow runs `uv run pytest`. A separate workflow selects `live_eval` tests without coverage; it does not mean that live evaluations were run for this initialization.

## Committed test map

| Test file at HEAD | Contract areas covered |
|---|---|
| `tests/test_api.py` | Health endpoint response contract. |
| `tests/test_appointments.py` | Explicit booking confirmation, confirmation-flow requirements, collision recheck, and alternative slots. |
| `tests/test_config.py` | Environment-backed settings and derived settings properties. |
| `tests/test_diagnostics.py` | Runtime readiness reporting. |
| `tests/test_evaluations.py` | Scenario allowlist and parsing, temporary-store isolation, persisted pass/error outcomes, bounded logs, and worker cleanup. |
| `tests/test_extended_storage.py` | Integration bindings, calls and handoffs, calendar/CRM/healthcare records, and audit events. |
| `tests/test_graph.py` | Seeded graph validation/compilation, unknown-config rejection, cycle detection, and branch rejection. |
| `tests/test_live_evaluations.py` | Paid live scenarios; the pytest test is skipped unless `PVS_RUN_LIVE_EVALS=1` and `OPENAI_API_KEY` are set. |
| `tests/test_security.py` | E.164 validation, phone redaction/digest, session-bound healthcare encryption, media-token signature/expiry, and provider webhook signatures. |
| `tests/test_storage.py` | Seed graphs, ordered semantic events, raw-audio event rejection, timeline deletion, and evaluation-result persistence. |
| `tests/test_streamlit_app.py` | Streamlit command center, Agent Studio, and page-level behavior. |

## Source contracts behind the tests

The code behavior these tests target is documented in [Pipeline graph contract and compilation](../pipelines/graph-contract-and-compilation.md), [Appointments and calendar synchronization](../workflows/appointments-and-calendar.md), [Telephony gateway](../runtime/telephony-gateway.md), [SQLite state and semantic timeline](../state/sqlite-and-timeline.md), and [Isolated evaluation runs](../evaluations/isolated-runs.md). Source is present in the current checkout; the test files themselves are not.

## Current test configuration references

- [`pyproject.toml`](../../pyproject.toml)
- [Standard quality workflow](../../.github/workflows/quality.yml)
- [Live evaluation workflow](../../.github/workflows/live-evaluations.yml)
- Test implementations referenced from committed HEAD `2e12bed`; absent from the current worktree.
