# Testing patterns

## Test stack and commands

- Framework: pytest >=9.1.1 with pytest-asyncio and pytest-cov.
- Assertions: native pytest/plain `assert`; mocking through fixtures, `monkeypatch`, and small test doubles.

```powershell
uv run pytest
uv run pytest tests/test_graph.py
uv run pytest -m live_eval tests/test_live_evaluations.py --no-cov -q
uv run pytest --cov=pipecat_voice_studio --cov-report=term-missing
```

The live command also requires `PVS_RUN_LIVE_EVALS=1` and `OPENAI_API_KEY`.

## Test layout

- All Python tests are under `tests/`, named `test_*.py`.
- There is no global `conftest.py`; fixtures are local to relevant test modules.
- Async API tests use `httpx.ASGITransport`, avoiding a network server.
- Streamlit smoke tests use `streamlit.testing.v1.AppTest` against page files.
- Frontend has type-check/build validation but no JavaScript unit-test runner configured.

## Test scope matrix

| Scope | Covered? | Typical target | Notes |
|---|---|---|---|
| Unit | Yes | Graph validation, booking policy, settings, security primitives, extended storage, evaluation helpers | Uses temporary SQLite files and mocks |
| Integration | Yes | FastAPI ASGI contracts, Streamlit page loading, schema v2/provider records | Local and deterministic |
| End-to-end | Opt-in | Real Pipecat worker, models, RTVI scenarios | Paid, credential-gated, manual CI workflow |
| Browser media E2E | No | Microphone/WebRTC UI | No automated browser/device suite exists |
| Live provider contracts | No | Twilio, Vonage, Google, HubSpot, Simli | Requires external accounts and callback infrastructure |

## Mocking and isolation strategy

- `tmp_path` gives each storage/evaluation test an isolated database.
- `monkeypatch` replaces subprocess startup/session execution and environment settings.
- Evaluation scenarios copy the selected graph into a temporary store, so fixtures cannot mutate the studio database.
- App-level settings and Streamlit resource caches are process-global; tests currently avoid broad mutation of those caches.
- Live tests skip unless explicitly enabled, preventing accidental paid calls during normal pytest and pull requests.

## Coverage and quality signals

- pytest-cov enforces 80% minimum Python coverage.
- UI, voice runtime, callback gateway, calendar loop, and external provider adapters are omitted from
  measured coverage; graph, storage, configuration, encryption, signatures, API, and policy remain
  measured.
- The Quality workflow runs lockfile validation, Ruff, ty, pytest, frontend type-check/build, launcher setup checks, and `uv build` on Windows and Ubuntu.
- The separate Live evaluations workflow is manually dispatched and uploads a JSON report.
- The repository does not record a flaky-test history or test-duration budget.

## Evidence

- `pyproject.toml`
- `tests/test_graph.py`
- `tests/test_evaluations.py`
- `tests/test_streamlit_app.py`
- `tests/test_live_evaluations.py`
- `tests/test_security.py`
- `tests/test_extended_storage.py`
- `.github/workflows/quality.yml`
