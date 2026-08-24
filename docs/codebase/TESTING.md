# Testing Patterns

## Test Stack and Commands

- Framework: pytest >=9.1.1 with pytest-asyncio and pytest-cov.
- Assertions: native pytest/plain `assert`; mocking through fixtures, `monkeypatch`, and small test doubles.

```powershell
uv run pytest
uv run pytest tests/test_graph.py
uv run pytest -m live_eval tests/test_live_evaluations.py --no-cov -q
uv run pytest --cov=pipecat_voice_studio --cov-report=term-missing
```

The live command additionally requires `PVS_RUN_LIVE_EVALS=1` and `OPENAI_API_KEY`.

## Test Layout

- All Python tests are under `tests/`, named `test_*.py`.
- There is no global `conftest.py`; fixtures are local to relevant test modules.
- Async API tests use `httpx.ASGITransport`, avoiding a network server.
- Streamlit smoke tests use `streamlit.testing.v1.AppTest` against page files.
- Frontend has type-check/build validation but no JavaScript unit-test runner configured.

## Test Scope Matrix

| Scope | Covered? | Typical target | Notes |
|---|---|---|---|
| Unit | Yes | Graph validation, booking policy, settings, storage, evaluation helpers | Uses temporary SQLite files and mocks |
| Integration | Yes | FastAPI ASGI contracts, Streamlit page loading, store/schema behavior | Local and deterministic |
| End-to-end | Opt-in | Real Pipecat worker, models, RTVI scenarios | Paid, credential-gated, manual CI workflow |
| Browser media E2E | No | Microphone/WebRTC UI | [TODO] No automated browser/device suite exists |

## Mocking and Isolation Strategy

- `tmp_path` gives each storage/evaluation test an isolated database.
- `monkeypatch` replaces subprocess startup/session execution and environment settings.
- Evaluation scenarios copy the selected graph into a temporary store, so fixtures cannot mutate the studio database.
- App-level settings and Streamlit resource caches are process-global; tests currently avoid broad mutation of those caches.
- Live tests skip unless explicitly enabled, preventing accidental paid calls during normal pytest and pull requests.

## Coverage and Quality Signals

- pytest-cov enforces 80% minimum Python coverage.
- `src/pipecat_voice_studio/ui/*` and `src/pipecat_voice_studio/voice/*` are omitted from measured coverage.
- The Quality workflow runs lockfile validation, Ruff, ty, pytest, frontend type-check/build, launcher setup checks, and `uv build` on Windows and Ubuntu.
- The separate Live evaluations workflow is manually dispatched and uploads a JSON report.
- [TODO] No flaky-test history or test-duration budget is recorded.

## Evidence

- `pyproject.toml`
- `tests/test_graph.py`
- `tests/test_evaluations.py`
- `tests/test_streamlit_app.py`
- `tests/test_live_evaluations.py`
- `.github/workflows/quality.yml`
