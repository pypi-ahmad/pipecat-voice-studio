# Technology Stack

## Runtime Summary

| Area | Value | Evidence |
|---|---|---|
| Primary language | Python, with a TypeScript/React browser component | `pyproject.toml`; `src/pipecat_voice_studio/ui/frontend/package.json` |
| Runtime + version | Python `>=3.13,<3.15`; CI uses 3.14.7 | `pyproject.toml`; `.github/workflows/quality.yml` |
| Package manager | uv for Python; npm for the frontend | `uv.lock`; frontend `package-lock.json` |
| Build system | `uv_build` for Python; Vite for the component | `pyproject.toml`; frontend `vite.config.ts` |

## Production Frameworks and Dependencies

| Dependency | Version | Role | Evidence |
|---|---:|---|---|
| Pipecat | 1.7.0 | Voice pipelines, CLI runner, WebRTC/WebSocket, Simli, Flows, and evaluations | `pyproject.toml` |
| Streamlit | 1.62.0 | Studio UI and component host | `pyproject.toml` |
| FastAPI | >=0.141.1 | Pipeline-management and health API | `pyproject.toml` |
| Pydantic Settings | >=2.15.0 | Environment-backed configuration | `pyproject.toml` |
| HTTPX | >=0.28.1 | Async Google, HubSpot, Twilio, and Vonage REST calls | `pyproject.toml` |
| google-auth | >=2.56.3 | Calendar service-account OAuth | `pyproject.toml` |
| PyJWT + cryptography | >=2.13.0 | Vonage application/webhook JWTs and AES-GCM support | `pyproject.toml` |
| python-multipart | >=0.0.22 | Twilio form webhook parsing | `pyproject.toml` |
| Uvicorn | >=0.52.4 | ASGI server | `pyproject.toml` |
| PyTorch / torchvision | 2.13.0+cu132 / 0.28.0+cu132 | CUDA-enabled ML runtime used by Pipecat services | `pyproject.toml` |
| React | ^19.1.1 | Browser component UI | frontend `package.json` |
| Pipecat client packages | client-js 1.13.0; client-react 1.8.1; SmallWebRTC 1.10.6 | Browser-to-worker voice connection | frontend `package.json` |

SQLite is supplied by Python's standard library; it is not a separately managed dependency.

## Development Toolchain

| Tool | Purpose | Evidence |
|---|---|---|
| Ruff 0.16+ | Python linting and formatting rules | `pyproject.toml` |
| ty 0.0.74+ | Python type checking | `pyproject.toml` |
| pytest 9.1+ / pytest-asyncio / pytest-cov | Tests and coverage | `pyproject.toml` |
| TypeScript 5.9+ | Frontend type checking | frontend `package.json` |
| Vite 8+ | Frontend production build | frontend `package.json` |
| GitHub Actions | Windows/Linux quality jobs and a Windows-only manual live-evaluation job | `.github/workflows/` |

## Key Commands

```powershell
.\launch.cmd
.\launch.ps1 -WithApi
uv sync --frozen
uv run streamlit run src/pipecat_voice_studio/ui/streamlit_app.py
uv run python -m pipecat_voice_studio.voice.bot --host 127.0.0.1 --port 7860
uv run uvicorn pipecat_voice_studio.telephony_gateway:app --host 127.0.0.1 --port 8080
uv run python -m pipecat_voice_studio.calendar_worker
uv run uvicorn pipecat_voice_studio.api.app:app --host 127.0.0.1 --port 8000
uv run ruff check .
uv run ty check
uv run pytest
uv build
```

On Windows, `launch.cmd` is the double-clickable entry point and forwards arguments to
`launch.ps1`. On Linux, `./launch.sh` performs the equivalent setup and launch. The PowerShell
and Bash scripts support setup-only, custom ports, and optional management-API modes.

Frontend changes additionally require `npm ci` and `npm run build` in
`src/pipecat_voice_studio/ui/frontend`.

## Environment and Config

- Sources: process environment and project-root `.env`; `.env.example` is the committed template.
- `OPENAI_API_KEY` is required for voice pipelines and paid evaluations. `OPENAI_BASE_URL` is optional.
- The Windows launcher imports missing OpenAI values from the user environment; both native launchers verify pandas and `dateutil` and repair an incomplete `python-dateutil` installation.
- `PVS_*` variables configure environment, worker/public URLs, database, timezone, models, voice,
  outbound allowlisting, calendar polling, and healthcare governance.
- Provider groups are `TWILIO_*`, `VONAGE_*`, `GOOGLE_*`, `HUBSPOT_*`, and `SIMLI_*`; secrets use
  `SecretStr` and remain in server processes.
- The default database is `data/pipecat_voice_studio.db`.
- Local GPU dependencies use the PyTorch CUDA 13.2 index.
- Supported hosts are native Windows x86-64 and Linux x86-64 with glibc 2.34+. Launchers prefer Python 3.14.7 and fall back to 3.13.13.
- There is no container or orchestration configuration in the repository.

## Evidence

- `pyproject.toml`
- `.python-version`
- `.env.example`
- `src/pipecat_voice_studio/ui/frontend/package.json`
- `.github/workflows/quality.yml`
- `launch.cmd`
- `launch.ps1`
- `launch.sh`
