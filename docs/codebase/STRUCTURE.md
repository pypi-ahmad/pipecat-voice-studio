# Codebase Structure

## Top-Level Map

| Path | Purpose | Evidence |
|---|---|---|
| `src/pipecat_voice_studio/` | Installable Python application | `pyproject.toml` |
| `src/pipecat_voice_studio/api/` | FastAPI management endpoints | `api/app.py` |
| `src/pipecat_voice_studio/integrations/` | External provider and readiness adapters | integration modules |
| `src/pipecat_voice_studio/ui/` | Streamlit pages, shared store, and component bridge | `ui/streamlit_app.py` |
| `src/pipecat_voice_studio/ui/frontend/` | React/TypeScript graph and live-voice component | frontend `package.json` |
| `src/pipecat_voice_studio/voice/` | Pipecat worker, Flow tools, and timeline observer | `voice/bot.py` |
| `src/pipecat_voice_studio/eval_scenarios/` | Allowlisted YAML behavior scenarios | `evaluations.py` |
| `tests/` | Python unit, API, UI smoke, and opt-in live tests | `pyproject.toml` |
| `.github/workflows/` | Automated quality and manual live evaluations | workflow files |
| `data/` | Default local SQLite runtime data | `.env.example` |
| `docs/` | Technical and codebase documentation | `docs/TECHNICAL.md` |
| `launch.cmd`, `launch.ps1`, `launch.sh` | Windows wrapper plus native Windows/Linux setup and process supervision | launcher files |

Generated directories include `.venv/`, `dist/`, caches, and frontend `build/`; they are not source architecture.

## Entry Points

- Streamlit UI: `src/pipecat_voice_studio/ui/streamlit_app.py`.
- Voice worker: module `pipecat_voice_studio.voice.bot`, whose `bot()` callback is run by Pipecat's CLI runner.
- Management API: ASGI object `pipecat_voice_studio.api.app:app`.
- Telephony gateway: ASGI object `pipecat_voice_studio.telephony_gateway:app`.
- Calendar synchronization: module `pipecat_voice_studio.calendar_worker`.
- Evaluations: `run_evaluation()` in `evaluations.py`, invoked by the Streamlit page or pytest live suite.
- Frontend component: `ui/frontend/src/index.tsx`, built by Vite and registered through `ui/components.py`.
- User launch entry points: root `launch.cmd`, `launch.ps1`, and `launch.sh`. The CMD file wraps the
  PowerShell launcher for File Explorer; native launchers prepare `.venv` and supervise the browser
  worker, callback gateway, optional calendar/API workers, and Streamlit.

## Module Boundaries

| Boundary | Owns | Must not own |
|---|---|---|
| `graph.py` | Closed graph schema and deterministic compiler | Provider credentials or runtime I/O |
| `storage.py` | SQLite schema, transactions, and records | Voice pipeline construction |
| `appointments.py` | Booking policy and availability | UI rendering |
| `integrations/` | Provider authentication and REST contracts | Streamlit rendering or graph policy |
| `security.py` | Signatures, redaction, media tokens, healthcare encryption | Provider orchestration |
| `telephony_gateway.py` | Public callback verification and media transport construction | Management API behavior |
| `calendar_worker.py` | Google incremental polling lifecycle | Voice pipeline construction |
| `voice/` | Pipecat services, frame processing, tools | Browser state or direct Streamlit rendering |
| `ui/` | Navigation and operator interactions | Secret delivery to browser component |
| `api/` | HTTP contracts and dependency wiring | Duplicate persistence rules |
| `evaluations.py` | Scenario catalog and isolated runner lifecycle | Normal unit-test model calls |

## Naming and Organization Rules

- Python files, functions, and variables use `snake_case`; classes use `PascalCase`.
- React component files use `PascalCase`; TypeScript variables/functions use `camelCase`.
- Modules are organized mostly by runtime layer, with UI pages separated by feature.
- Python imports use the absolute `pipecat_voice_studio.*` package path across modules.
- There is no Python barrel-export pattern; package `__init__.py` files are minimal.

## Evidence

- `docs/codebase/.codebase-scan.txt`
- `pyproject.toml`
- `src/pipecat_voice_studio/ui/streamlit_app.py`
- `src/pipecat_voice_studio/voice/bot.py`
- `src/pipecat_voice_studio/api/app.py`
- `launch.cmd`
- `launch.ps1`
- `launch.sh`
