# Coding Conventions

## Naming Rules

| Item | Rule | Example | Evidence |
|---|---|---|---|
| Python files | `snake_case.py` | `appointment_flow.py` | `src/pipecat_voice_studio/voice/` |
| Python functions | `snake_case`; leading `_` for module-private helpers | `compile_graph`, `_start_worker` | `graph.py`; `evaluations.py` |
| Python types | `PascalCase` | `PipelineGraph`, `StudioStore` | `graph.py`; `storage.py` |
| Constants/env vars | `UPPER_SNAKE_CASE`; settings fields are lower-case env names | `SCHEMA_VERSION`, `PVS_DATABASE_PATH` | `storage.py`; `.env.example` |
| React components | `PascalCase` files/functions | `StudioComponent` | frontend source |

## Formatting and Linting

- Ruff is configured for Python 3.14, 100-character lines, and all rules except explicit repository ignores.
- ty checks Python 3.14 and treats warnings as errors.
- TypeScript uses `tsc --noEmit`; Vite performs production builds.
- Commands: `uv run ruff check .`, `uv run ty check`, and frontend `npm run build`.
- Several complex runtime modules have narrow Ruff exceptions recorded in `pyproject.toml`; do not generalize those exceptions to new files.

## Import and Module Conventions

- Standard-library imports precede third-party and project imports, as enforced by Ruff.
- Cross-module Python imports are absolute (`pipecat_voice_studio.*`). Relative imports are not the established pattern.
- Type-only imports are guarded with `TYPE_CHECKING` where useful.
- Public behavior is imported from defining modules; no broad re-export layer exists.

## Error and Logging Conventions

- Contract violations use boundary-specific `ValueError`/`PermissionError` subclasses, `KeyError`,
  HTTP status errors, or Pydantic validation errors at the responsible layer.
- FastAPI maps a missing active pipeline to HTTP 404; request validation remains FastAPI/Pydantic's standard 422 behavior.
- The worker catches terminal exceptions, records a failed session, then re-raises. Evaluations convert failures into persisted structured results.
- Operational output uses Pipecat/loguru logging in the worker and bounded subprocess logs in evaluations. There is no repository-wide structured logging schema.
- Secrets use Pydantic `SecretStr`; graphs cannot contain credentials; browser component data excludes API keys. Raw audio persistence is explicitly rejected.

## Testing Conventions

- Tests live in `tests/` and use `test_*.py` plus plain `assert`.
- pytest fixtures and `monkeypatch` isolate files, environment, subprocesses, and model-backed execution.
- Live paid tests require both an explicit flag and `OPENAI_API_KEY`.
- Coverage must be at least 80%. Interactive UI/voice code and credential-dependent provider,
  gateway, and polling boundaries are omitted; security, storage, graph, API, and policy code remain
  measured.

## Evidence

- `pyproject.toml`
- `src/pipecat_voice_studio/graph.py`
- `src/pipecat_voice_studio/evaluations.py`
- `src/pipecat_voice_studio/voice/bot.py`
- `tests/test_evaluations.py`
- `tests/test_security.py`
- `tests/test_extended_storage.py`
