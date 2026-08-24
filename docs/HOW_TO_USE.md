# How to Use Pipecat Voice Studio

This guide is for developers and local operators running Pipecat Voice Studio on native Windows or native x86-64 Linux.

> [!IMPORTANT]
> Pipecat Voice Studio is currently designed for local development and trusted networks. Its management API has no authentication, and its SQLite and SmallWebRTC configuration is not intended for a public production deployment.

## Contents

- [What you can use](#what-you-can-use)
- [Prerequisites](#prerequisites)
- [Install the project](#install-the-project)
- [Configure the application](#configure-the-application)
- [Start the application](#start-the-application)
- [Use the Streamlit studio](#use-the-streamlit-studio)
- [Use the management API](#use-the-management-api)
- [Run evaluations](#run-evaluations)
- [Rebuild the browser component](#rebuild-the-browser-component)
- [Run development checks](#run-development-checks)
- [Troubleshooting](#troubleshooting)
- [Unsupported capabilities](#unsupported-capabilities)

## What you can use

The current application provides:

- a Streamlit command center and agent studio;
- browser microphone sessions over Pipecat SmallWebRTC;
- OpenAI Realtime voice conversations;
- cascaded STT → LLM → TTS conversations;
- an appointment-booking Flow with availability and confirmation checks;
- validated and persisted pipeline definitions;
- session timelines, records, appointments, and analytics;
- isolated behavioral evaluations;
- a FastAPI health and pipeline-management API.

## Prerequisites

Install or provide:

- 64-bit Windows 11, or x86-64 Linux with glibc 2.34+ such as Ubuntu 22.04+;
- [Git](https://git-scm.com/);
- PowerShell on Windows, or Bash plus `curl` or `wget` on Linux;
- an OpenAI API key for live voice calls and model-backed evaluations;
- a browser with microphone permission;
- Node.js and npm only if you modify the React component;
- a CUDA 13.2-compatible NVIDIA environment for GPU acceleration; CPU mode also works.

The launchers install `uv` when needed, reuse an installed Python 3.14.7 or install it through `uv`, and fall back to Python 3.13.13 if required. They also install project dependencies. Docker, WSL, and manual virtual-environment activation are not used.

## Install the project

Clone the repository:

```powershell
git clone https://github.com/pypi-ahmad/pipecat-voice-studio.git
Set-Location pipecat-voice-studio
```

Run first-time setup and launch on Windows:

```powershell
powershell -ExecutionPolicy Bypass -File .\launch.ps1
```

On Linux:

```bash
git clone https://github.com/pypi-ahmad/pipecat-voice-studio.git
cd pipecat-voice-studio
./launch.sh
```

The launcher creates root `.venv` and `.env` files without overwriting an existing `.env`. Use `-SetupOnly` or `--setup-only` to install without starting services. Do not commit `.env` or place credentials in pipeline graphs, frontend code, or Streamlit component data.

## Configure the application

After the first setup, edit `.env` and set at least:

```dotenv
OPENAI_API_KEY=your-key-here
```

Available settings:

| Variable | Default | Purpose |
|---|---|---|
| `OPENAI_API_KEY` | Empty | Required for live model calls and evaluations |
| `OPENAI_BASE_URL` | Empty | Optional OpenAI-compatible endpoint |
| `PVS_ENVIRONMENT` | `development` | Runtime environment label |
| `PVS_BOT_BASE_URL` | `http://127.0.0.1:7860` | Pipecat worker URL used by Streamlit and the browser |
| `PVS_DATABASE_PATH` | `data/pipecat_voice_studio.db` | Local SQLite database |
| `PVS_TIMEZONE` | `Asia/Calcutta` | IANA timezone used by appointment policy |
| `PVS_REALTIME_MODEL` | `gpt-realtime-2.1-mini` | Realtime model identifier |
| `PVS_CASCADE_STT_MODEL` | `gpt-realtime-whisper` | Cascaded speech-to-text model |
| `PVS_CASCADE_LLM_MODEL` | `gpt-5.6-luna` | Cascaded reasoning model |
| `PVS_CASCADE_TTS_MODEL` | `gpt-4o-mini-tts` | Cascaded text-to-speech model |
| `PVS_REALTIME_VOICE` | `marin` | Default realtime voice |

`PVS_TIMEZONE` must be a valid IANA timezone. Model identifiers must be supported by the configured provider endpoint.
When a launcher starts the application, it overrides `PVS_BOT_BASE_URL` for those processes to match the selected worker port. The table default applies to manual startup.

## Start the application

By default, the launcher supervises the separate voice worker and Streamlit processes, waits for worker readiness, and cleans up the worker when Streamlit exits.

```powershell
.\launch.ps1
.\launch.ps1 -WithApi
.\launch.ps1 -WorkerPort 7861 -StreamlitPort 8502 -ApiPort 8001 -WithApi
```

```bash
./launch.sh
./launch.sh --with-api
./launch.sh --worker-port 7861 --streamlit-port 8502 --api-port 8001 --with-api
```

Worker and optional API logs are written under `artifacts/launcher/`. All services bind to `127.0.0.1`.

The launchers support these equivalent controls:

| Purpose | Windows | Linux |
|---|---|---|
| Prepare dependencies without starting services | `-SetupOnly` | `--setup-only` |
| Start the optional management API | `-WithApi` | `--with-api` |
| Set the worker port | `-WorkerPort 7861` | `--worker-port 7861` |
| Set the Streamlit port | `-StreamlitPort 8502` | `--streamlit-port 8502` |
| Set the API port | `-ApiPort 8001` | `--api-port 8001` |

Selected ports must be distinct and unused. The launcher stops with an error when a port is unavailable or when the worker or optional API does not become ready within 30 seconds. If a single built JavaScript or CSS asset is missing, the launcher rebuilds the frontend with npm; Node.js and npm are required only for that fallback or for frontend development.

The following commands are the manual alternative when you want to manage each process yourself.

### 1. Start the Pipecat worker

```powershell
uv run python -m pipecat_voice_studio.voice.bot `
  --host 127.0.0.1 `
  --port 7860 `
  --allowed-origins http://localhost:8501 http://127.0.0.1:8501
```

The worker should report that the bot is ready. Its `/status` endpoint must return a ready status before a live browser session can connect.

### 2. Start Streamlit

```powershell
uv run streamlit run src/pipecat_voice_studio/ui/streamlit_app.py
```

Open [http://localhost:8501](http://localhost:8501).

On Linux, use the same `uv run` commands without PowerShell backticks.

### 3. Optionally start the management API

The Streamlit UI does not require the management API. Start it only when you need its HTTP endpoints:

```powershell
uv run uvicorn pipecat_voice_studio.api.app:app --host 127.0.0.1 --port 8000
```

Open [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) for the generated OpenAPI interface.

## Use the Streamlit studio

### Check runtime readiness

Open **Command center** to inspect the environment, installed runtime, CUDA status, and GPU readiness.

### Inspect or create a pipeline

Open **Agent studio**:

1. Select one of the seeded realtime, cascade, or evaluation pipelines.
2. Inspect its visual graph and node configuration.
3. To create a variant, provide a unique name and optionally change the system prompt and select the `marin` or `cedar` voice.
4. Save the clone.

The application validates the complete graph and compiles its executable path before persistence. Graphs cannot inject Python code, credentials, provider classes, or arbitrary configuration fields.

### Run a browser voice session

1. Confirm the Pipecat worker is running.
2. Open **Live session**.
3. Select a realtime or cascade pipeline. Evaluation pipelines are intentionally excluded.
4. Select the browser microphone if more than one input device is available.
5. Choose **Connect** and grant microphone permission.
6. Speak normally; use mute or disconnect controls when needed.
7. Observe transcripts, speaking state, function calls, and available timing metrics.

The browser retains only bounded, ephemeral transcript state. The database stores selected semantic events but never raw audio or browser media tracks.

### Book an appointment

Use a cascade pipeline and tell the assistant:

- the attendee name;
- the appointment purpose;
- the desired date and time.

The Flow checks local availability and may suggest alternatives. It creates an appointment only after reaching the confirmation node and receiving explicit affirmative confirmation. Appointments last 30 minutes, start on the hour or half hour, and must fall on a weekday between 09:00 and 17:00 in `PVS_TIMEZONE`.

### Review records

Open **Records** to inspect:

- session status and timestamps;
- final user and assistant conversation turns;
- stored appointments;

Deleting a session also deletes its timeline. An appointment linked to that session remains but its session reference becomes null.

### Review analytics

Open **Analytics** to view local counts for sessions, completed sessions, appointments, and tool events.

## Use the management API

The API currently exposes:

| Method | Endpoint | Use |
|---|---|---|
| `GET` | `/health` | Inspect application, Python, dependency, CUDA, and GPU readiness |
| `GET` | `/pipelines` | List pipeline metadata |
| `GET` | `/pipelines/{pipeline_id}` | Retrieve one active validated pipeline graph |
| `POST` | `/pipelines` | Validate, compile, and save a complete graph |

Example health request:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

> [!WARNING]
> Do not expose the API publicly in its current form. It has no authentication, authorization, or rate limiting.

## Run evaluations

### From Streamlit

1. Set `OPENAI_API_KEY` and restart Streamlit if configuration changed.
2. Open **Evaluations**.
3. Select the evaluation pipeline.
4. Select an allowlisted scenario.
5. Choose **Run evaluation**.
6. Review the pass/fail result and diagnostics.

Each run copies the selected graph into a temporary SQLite database, launches a hidden localhost worker, runs the scenario, terminates the worker, deletes temporary storage, and saves the result in the main database.

Available scenarios cover:

- successful booking;
- unavailable slots;
- policy denial;
- interruption handling;
- a synthetic-audio STT smoke path.

Evaluations can make paid model calls.

### From pytest

Normal tests skip live evaluations. To run them deliberately:

```powershell
$env:PVS_RUN_LIVE_EVALS = "1"
$env:PVS_LIVE_EVAL_SCENARIOS = "all"
uv run pytest -m live_eval tests/test_live_evaluations.py --no-cov -q
```

`OPENAI_API_KEY` must also exist in the environment or `.env` configuration available to the worker.

## Rebuild the browser component

Rebuild after changing files under `src/pipecat_voice_studio/ui/frontend/src`:

```powershell
Set-Location src\pipecat_voice_studio\ui\frontend
npm ci
npm run build
Set-Location ..\..\..\..
```

The Streamlit application uses the generated assets in the frontend `build` directory.

## Run development checks

From the repository root:

```powershell
uv lock --check
uv run ruff check .
uv run ty check
uv run pytest
uv build
```

Python tests enforce at least 80% measured coverage. The GitHub Quality workflow also installs frontend dependencies, type-checks the React component, and builds its production assets.

## Troubleshooting

### The worker is unavailable

1. Confirm the worker terminal is still running.
2. Open `http://127.0.0.1:7860/status` and check for `status: ready`.
3. Ensure `PVS_BOT_BASE_URL` uses the same host and port.
4. Ensure `--allowed-origins` contains the exact Streamlit URL.
5. If using a launcher, inspect `artifacts/launcher/worker.err.log`.

### Linux setup rejects the distribution

- Confirm `uname -m` reports `x86_64`.
- Confirm `getconf GNU_LIBC_VERSION` reports glibc 2.34 or newer.
- Use a supported native distribution such as Ubuntu 22.04 or newer; musl and ARM64 are outside the current dependency contract.

### Microphone access fails

- Use `localhost`, `127.0.0.1`, or HTTPS; browser microphone APIs require a secure context.
- Allow microphone access for the active Streamlit origin.
- Disconnect before changing operating-system input devices.
- Do not connect from an HTTPS page to an HTTP worker; browsers block mixed content.

### A voice pipeline fails immediately

- Confirm `OPENAI_API_KEY` is configured in the worker process.
- Confirm the configured model identifiers exist at the selected endpoint.
- Confirm a live session uses a realtime or cascade graph, not an evaluation graph.
- Inspect the failed session and semantic events on **Records**.

### An evaluation does not start

- Select an evaluation-mode graph.
- Confirm `OPENAI_API_KEY` is configured.
- Review the latest evaluation diagnostics and bounded worker log.
- Ensure local security software permits the hidden Python subprocess and localhost sockets.

### The browser component is blank

Rebuild its assets:

```powershell
Set-Location src\pipecat_voice_studio\ui\frontend
npm ci
npm run clean
npm run build
```

Then restart Streamlit.

### SQLite reports an incompatible schema

The current code accepts schema version 1 and does not provide migrations. Preserve the database if its records matter. For disposable local data, stop all application processes, move the database to a backup location, and restart the studio to create a fresh schema.

## Unsupported capabilities

The following ideas are not implemented in the current code:

- Twilio or Vonage telephony;
- external calendar providers and confirmation messaging;
- CRM storage and production human handoff;
- healthcare privacy/compliance controls;
- multilingual translation workflows;
- meeting/classroom ingestion;
- avatar providers such as HeyGen, Tavus, or Simli;
- multi-agent routing and shared buses;
- voice-controlled developer tools;
- live coaching, sentiment, keyword, or compliance alerts;
- arbitrary custom Pipecat service loading from saved graphs.

For implementation architecture, security boundaries, persistence details, and API contracts, see [Technical Documentation](TECHNICAL.md).
