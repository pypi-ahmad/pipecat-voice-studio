# Pipecat Voice Studio

Pipecat Voice Studio is a local application for building, running, inspecting, and evaluating real-time voice and multimodal pipelines using the Pipecat framework. It provides a Streamlit control interface, a React browser audio client using SmallWebRTC, a standalone Pipecat audio worker, a FastAPI telephony callback gateway for Twilio and Vonage, an optional management API, and a local SQLite database for session and operational records.

## Requirements

The required runtime versions and environment constraints are defined in [pyproject.toml](file:///D:/AI/Github/pipecat-voice-studio/pyproject.toml) and [package.json](file:///D:/AI/Github/pipecat-voice-studio/src/pipecat_voice_studio/ui/frontend/package.json):

- Python: `>=3.13,<3.15`. The launchers target Python `3.14.7` by default and fall back to `3.13.13` if installation is required.
- Operating system:
  - Native 64-bit Windows AMD64 (`sys_platform == 'win32' and platform_machine == 'AMD64'`).
  - Native 64-bit Linux x86_64 (`sys_platform == 'linux' and platform_machine == 'x86_64'`) with GNU glibc 2.34 or newer.
  - macOS, Apple Silicon, ARM64 architectures, and musl-based Linux distributions are not supported due to platform-specific wheel builds (`torch==2.13.0+cu132`).
- Package and environment manager: [uv](https://docs.astral.sh/uv/) (installed automatically by launchers if absent on PATH).
- Node.js and npm: Node.js 24 (or modern LTS) and npm are required only when rebuilding the React frontend component. Pre-built frontend bundles are committed under [build/](file:///D:/AI/Github/pipecat-voice-studio/src/pipecat_voice_studio/ui/frontend/build).
- Hardware acceleration: CUDA 13.2 GPU acceleration is optional. CPU mode is supported when no compatible GPU is detected.
- External credentials: An OpenAI API key (`OPENAI_API_KEY`) is required for live voice sessions, speech transcription, language model generation, text-to-speech, and automated evaluations.

## Setup and run commands

### Launchers

The repository includes startup scripts that check system prerequisites, configure Python via `uv`, synchronize locked dependencies, build missing frontend assets, verify port availability, start background processes, and open Streamlit.

On Windows (Command Prompt or PowerShell):

```cmd
launch.cmd
```

Or directly via PowerShell:

```powershell
.\launch.ps1
```

PowerShell options:
- `.\launch.ps1 -WithApi`: Also start the FastAPI management API on port 8000.
- `.\launch.ps1 -SetupOnly`: Install and validate dependencies and exit without starting services.
- `.\launch.ps1 -WorkerPort 7860 -StreamlitPort 8501 -GatewayPort 8080 -ApiPort 8000`: Override default service ports.

On Linux:

```bash
chmod +x launch.sh
./launch.sh
```

Linux options:
- `./launch.sh --with-api`: Also start the FastAPI management API on port 8000.
- `./launch.sh --setup-only`: Install and validate dependencies and exit without starting services.
- `./launch.sh --worker-port 7860 --streamlit-port 8501 --gateway-port 8080 --api-port 8000`: Override default service ports.

### Manual process execution

If running services individually without launcher supervision:

1. Synchronize Python dependencies:
   ```bash
   uv sync --frozen
   ```

2. Build frontend assets (only required if modifying the React component):
   ```bash
   cd src/pipecat_voice_studio/ui/frontend
   npm ci
   npm run build
   cd ../../../..
   ```

3. Start the Pipecat audio worker:
   ```bash
   uv run python -m pipecat_voice_studio.voice.bot --host 127.0.0.1 --port 7860 --allowed-origins http://localhost:8501 http://127.0.0.1:8501
   ```

4. Start the telephony gateway (required for Twilio or Vonage webhooks):
   ```bash
   uv run uvicorn pipecat_voice_studio.telephony_gateway:app --host 127.0.0.1 --port 8080 --proxy-headers --forwarded-allow-ips 127.0.0.1
   ```

5. Start the Google Calendar sync worker (optional, when Google credentials are configured):
   ```bash
   uv run python -m pipecat_voice_studio.calendar_worker
   ```

6. Start the management API (optional):
   ```bash
   uv run uvicorn pipecat_voice_studio.api.app:app --host 127.0.0.1 --port 8000
   ```

7. Start the Streamlit user interface:
   ```bash
   uv run streamlit run src/pipecat_voice_studio/ui/streamlit_app.py --server.address 127.0.0.1 --server.port 8501
   ```

## Configuration

Settings are parsed via [Settings](file:///D:/AI/Github/pipecat-voice-studio/src/pipecat_voice_studio/config.py#L21-L130) from environment variables or a [.env](file:///D:/AI/Github/pipecat-voice-studio/.env.example) file in the repository root.

| Variable | Default | Description |
|---|---|---|
| `OPENAI_API_KEY` | None | Secret key for OpenAI models and evaluations. |
| `OPENAI_BASE_URL` | None | Custom base URL for OpenAI API endpoints. |
| `APP_NAME` | `Pipecat Voice Studio` | Application name displayed across API and UI. |
| `PVS_ENVIRONMENT` | `development` | Deployment environment identifier. |
| `PVS_BOT_BASE_URL` | `http://127.0.0.1:7860` | HTTP endpoint of the Pipecat worker process. |
| `PVS_DATABASE_PATH` | `data/pipecat_voice_studio.db` | Filesystem path to the SQLite database. |
| `PVS_TIMEZONE` | `Asia/Calcutta` | IANA timezone name used for business hours and appointments. |
| `PVS_REALTIME_MODEL` | `gpt-realtime-2.1-mini` | Model name for OpenAI Realtime pipelines. |
| `PVS_CASCADE_STT_MODEL` | `gpt-realtime-whisper` | Speech-to-text model name for cascaded pipelines. |
| `PVS_CASCADE_LLM_MODEL` | `gpt-5.6-luna` | Large language model name for cascaded pipelines. |
| `PVS_CASCADE_TTS_MODEL` | `gpt-4o-mini-tts` | Text-to-speech voice model for cascaded pipelines. |
| `PVS_REALTIME_VOICE` | `marin` | Default voice identifier. |
| `PVS_PUBLIC_BASE_URL` | None | Public HTTPS URL (e.g. reverse proxy tunnel) forwarding to port 8080 for telephony callbacks. Must use `https://`. |
| `PVS_OUTBOUND_ALLOWLIST` | `""` | Comma-separated list of exact E.164 phone numbers allowed for outbound calls. Wildcards are not supported. |
| `TWILIO_ACCOUNT_SID` | None | Twilio account identifier. |
| `TWILIO_AUTH_TOKEN` | None | Secret auth token for Twilio signature verification and API calls. |
| `TWILIO_FROM_NUMBER` | None | Canonical E.164 sender phone number for Twilio outbound calls. |
| `TWILIO_HANDOFF_DESTINATION` | None | E.164 phone number to bridge calls during human handoff. |
| `VONAGE_APPLICATION_ID` | None | Vonage application UUID. |
| `VONAGE_API_KEY` | None | Vonage API key used for webhook signature verification. |
| `VONAGE_PRIVATE_KEY` | None | Secret private key for Vonage JWT authentication. |
| `VONAGE_SIGNATURE_SECRET` | None | Secret key for verifying signed incoming Vonage webhooks. |
| `VONAGE_FROM_NUMBER` | None | Canonical E.164 sender phone number for Vonage outbound calls. |
| `VONAGE_HANDOFF_DESTINATION` | None | E.164 phone number to bridge calls during human handoff. |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | None | JSON credential string for Google Calendar service account. |
| `GOOGLE_CALENDAR_ID` | None | Google Calendar ID for appointment synchronization. |
| `PVS_CALENDAR_SYNC_SECONDS` | `60` | Polling interval in seconds (minimum 15, maximum 3600). |
| `HUBSPOT_PRIVATE_APP_TOKEN` | None | Secret token for HubSpot CRM contact and deal insertion. |
| `SIMLI_API_KEY` | None | Secret API key for Simli video avatar service. |
| `SIMLI_FACE_ID` | None | Face identifier for Simli video avatar generation. |
| `PVS_HEALTHCARE_ENABLED` | `false` | Boolean toggle to enable the healthcare intake flow. |
| `PVS_HEALTHCARE_DATA_KEY` | None | URL-safe base64-encoded 32-byte secret key for AES-256-GCM intake encryption. |
| `PVS_HEALTHCARE_APPROVED_SERVICES` | `""` | Comma-separated allowlist of approved model providers (must include `openai`). |

## Repository map

```text
pipecat-voice-studio/
├── .github/workflows/                 # GitHub Actions workflows
│   ├── quality.yml                    # CI workflow for linting, typing, tests, and builds
│   └── live-evaluations.yml           # Manual workflow for live model evaluations
├── artifacts/                         # Generated process logs and evaluation reports
│   └── launcher/                      # Background process log files
├── data/                              # SQLite database storage directory
├── docs/                              # Technical, architectural, and operational documentation
│   ├── ARCHITECTURE.md                # System diagrams, data flows, and external boundaries
│   ├── TECHNICAL.md                   # Technical stack rationale, invariants, and persistence
│   ├── RUNBOOK.md                     # Startup, shutdown, process management, and troubleshooting
│   ├── CONTRIBUTING.md                # Development standards, CI gates, and test requirements
│   ├── HOW_TO_USE.md                  # Page-by-page UI operational guide
│   └── PROVIDERS.md                   # External service setup instructions
├── src/pipecat_voice_studio/          # Core Python application package
│   ├── api/                           # FastAPI management surface
│   │   └── app.py                     # Health and pipeline management endpoints
│   ├── eval_scenarios/                # YAML test scenarios for behavioral evaluations
│   ├── integrations/                  # Provider adapters
│   │   ├── google_calendar.py         # Google Calendar OAuth and REST adapter
│   │   ├── hubspot.py                 # Consent-gated HubSpot CRM adapter
│   │   ├── readiness.py               # Provider readiness checks without secret leakage
│   │   └── telephony.py               # Twilio and Vonage REST and handoff clients
│   ├── ui/                            # Streamlit user interface
│   │   ├── app_pages/                 # Streamlit page modules (Command center, Studio, Live, etc.)
│   │   ├── components.py              # Streamlit Components v2 bridge
│   │   ├── frontend/                  # React 19 / Vite / TypeScript voice client component
│   │   └── streamlit_app.py           # Streamlit entrypoint and page navigation
│   ├── voice/                         # Real-time voice pipeline implementation
│   │   ├── appointment_flow.py        # Pipecat Flow for appointment booking
│   │   ├── bot.py                     # Standalone Pipecat runner and pipeline builder
│   │   ├── business_flow.py           # Specialist routing, CRM, and handoff Flow
│   │   ├── healthcare_flow.py         # Consent-gated encrypted healthcare intake Flow
│   │   └── timeline.py                # Semantic frame observer (excluding raw audio)
│   ├── appointments.py                # Booking policy, business hours, and collision logic
│   ├── calendar_worker.py             # Background Google Calendar sync process
│   ├── config.py                      # Pydantic Settings configuration definitions
│   ├── diagnostics.py                 # Runtime readiness and CUDA/GPU detection
│   ├── evaluations.py                 # Isolated subprocess evaluation runner
│   ├── graph.py                       # Pipeline schema validation and compilation
│   ├── security.py                    # E.164 parsing, webhook verification, AES-256-GCM cipher
│   ├── seeds.py                       # Pre-configured starter pipeline definitions
│   ├── storage.py                     # SQLite persistence layer and repository operations
│   └── telephony_gateway.py           # FastAPI ASGI app for Twilio/Vonage webhooks and media
├── launch.cmd                         # Double-clickable Windows launch wrapper
├── launch.ps1                         # PowerShell launch and process supervisor script
├── launch.sh                          # Bash launch script for Linux
├── pyproject.toml                     # Python package metadata, dependencies, and tool settings
└── uv.lock                            # Deterministic dependency lockfile
```

## How to run tests

Python tests and linters are defined in [pyproject.toml](file:///D:/AI/Github/pipecat-voice-studio/pyproject.toml) and executed in CI via [.github/workflows/quality.yml](file:///D:/AI/Github/pipecat-voice-studio/.github/workflows/quality.yml).

### Quality checks

Verify the dependency lockfile:
```bash
uv lock --check
```

Run static linting with Ruff:
```bash
uv run ruff check .
```

Run static type checking with ty:
```bash
uv run ty check
```

Run automated tests with coverage enforcement:
```bash
uv run pytest
```
The test suite requires a minimum coverage of 80% on non-omitted modules (configured in `[tool.pytest.ini_options]`).

Run frontend type checking and compilation:
```bash
cd src/pipecat_voice_studio/ui/frontend
npm ci
npm run build
cd ../../../..
```

Validate launcher scripts in dry-run mode:
- On Windows (PowerShell):
  ```powershell
  .\launch.ps1 -SetupOnly
  ```
- On Linux (Bash):
  ```bash
  bash -n launch.sh
  ./launch.sh --setup-only
  ```

Build the Python distribution package:
```bash
uv build
```

### Live model evaluations

Live evaluations execute end-to-end conversations against real model APIs using [evaluations.py](file:///D:/AI/Github/pipecat-voice-studio/src/pipecat_voice_studio/evaluations.py) and YAML scenarios under [eval_scenarios/](file:///D:/AI/Github/pipecat-voice-studio/src/pipecat_voice_studio/eval_scenarios):

```bash
uv run pytest -m live_eval tests/test_live_evaluations.py --no-cov -q
```
*Note: Live evaluations incur model API usage costs and require `OPENAI_API_KEY` to be set.*

## Known limitations

1. Localhost single-tenant architecture: The FastAPI management API (`api/app.py`) includes no authentication or role-based access control. The application is intended for local execution or trusted private networks.
2. Platform limitations: Only 64-bit Windows AMD64 and Linux x86_64 (glibc >= 2.34) are supported. macOS, Apple Silicon, and ARM64 architectures are unsupported due to PyTorch CUDA wheel requirements.
3. Linear pipeline compilation: The graph compiler ([compile_graph](file:///D:/AI/Github/pipecat-voice-studio/src/pipecat_voice_studio/graph.py#L247-L290)) only permits a single, unbranching, connected acyclic chain. Graph nodes cannot fork or merge frame streams. Multi-specialist routing is implemented through state transitions in Pipecat Flow rather than topology branches.
4. Appointment scheduling rules: Appointments are strictly restricted to 30-minute intervals, aligned to half-hour marks (`:00`, `:30`), between 09:00 and 17:00, Monday through Friday, evaluated in the studio's configured timezone.
5. Outbound telephone destination restrictions: Outbound calls require exact string matching in `PVS_OUTBOUND_ALLOWLIST`. Prefix or wildcard matching is not supported.
6. Public webhook ingress: Telephony webhooks from Twilio and Vonage require an external HTTPS tunnel (such as ngrok or Cloudflare Tunnel) forwarding to local port 8080. Plain HTTP URLs are rejected by `pvs_public_base_url` validation.
7. Single-file SQLite concurrency: All concurrent processes (worker, gateway, calendar worker, API, Streamlit) read and write to a single SQLite file. Concurrency is managed via WAL mode and a 5-second busy timeout; high-throughput distributed database clustering is not supported.
8. Healthcare privacy constraints: When healthcare intake is active, raw user and assistant turns are suppressed from SQLite event logs (`persist_conversation=False`). Intake data is encrypted with AES-256-GCM. Automated encryption key rotation is not implemented.
