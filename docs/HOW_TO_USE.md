# How to use Pipecat Voice Studio

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
- [Connected providers](#connected-providers)
- [Provider runbook](PROVIDERS.md)
- [Unsupported capabilities](#unsupported-capabilities)

## What you can use

The current application provides:

- a Streamlit command center and agent studio;
- browser microphone sessions over Pipecat SmallWebRTC;
- OpenAI Realtime voice conversations;
- cascaded STT → LLM → TTS conversations;
- an appointment-booking Flow with availability and confirmation checks;
- Twilio and Vonage inbound/outbound telephone sessions with signed callbacks;
- Google Calendar availability, event creation, and incremental cancellation sync;
- consent-gated HubSpot contacts, deals, and notes;
- business routing across reception, billing, technical support, sales, and appointments;
- warm telephone handoff with a private human briefing;
- Simli avatar video for browser cascade sessions;
- consent-first healthcare intake with encrypted structured storage and no transcript retention;
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
.\launch.cmd
```

You can double-click `launch.cmd` in File Explorer. It invokes `launch.ps1` with the required execution-policy override and pauses if startup fails so the error remains visible.

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

Alternatively, native Windows users can define `OPENAI_API_KEY` and `OPENAI_BASE_URL` as user
environment variables. When either variable is absent from the launcher process, `launch.ps1`
imports it from the Windows user environment without printing its value. Linux uses the process
environment or `.env`.

Available settings:

| Variable | Default | Purpose |
|---|---|---|
| `OPENAI_API_KEY` | Empty | Required for live model calls and evaluations |
| `OPENAI_BASE_URL` | Empty | Optional OpenAI-compatible endpoint |
| `APP_NAME` | `Pipecat Voice Studio` | Application title used by the management API |
| `PVS_ENVIRONMENT` | `development` | Runtime environment label |
| `PVS_BOT_BASE_URL` | `http://127.0.0.1:7860` | Pipecat worker URL used by Streamlit and the browser |
| `PVS_DATABASE_PATH` | `data/pipecat_voice_studio.db` | Local SQLite database |
| `PVS_TIMEZONE` | `Asia/Calcutta` | IANA timezone used by appointment policy |
| `PVS_REALTIME_MODEL` | `gpt-realtime-2.1-mini` | Realtime model identifier |
| `PVS_CASCADE_STT_MODEL` | `gpt-realtime-whisper` | Cascaded speech-to-text model |
| `PVS_CASCADE_LLM_MODEL` | `gpt-5.6-luna` | Cascaded reasoning model |
| `PVS_CASCADE_TTS_MODEL` | `gpt-4o-mini-tts` | Cascaded text-to-speech model |
| `PVS_REALTIME_VOICE` | `marin` | Default realtime voice |
| `PVS_PUBLIC_BASE_URL` | Empty | Public HTTPS tunnel origin forwarding provider callbacks to the local gateway |
| `PVS_CALENDAR_SYNC_SECONDS` | `60` | Calendar polling interval; accepted range is 15 to 3600 seconds |
| `PVS_OUTBOUND_ALLOWLIST` | Empty | Comma-separated exact E.164 numbers authorized for outbound calls |
| `TWILIO_ACCOUNT_SID` | Empty | Twilio account identity |
| `TWILIO_AUTH_TOKEN` | Empty | Twilio REST credential, webhook secret, and media-token key |
| `TWILIO_FROM_NUMBER` | Empty | Twilio E.164 caller ID |
| `TWILIO_HANDOFF_DESTINATION` | Empty | Twilio E.164 warm-transfer destination |
| `VONAGE_APPLICATION_ID` | Empty | Vonage Voice application identity |
| `VONAGE_API_KEY` | Empty | Expected API key claim in signed Vonage webhooks |
| `VONAGE_PRIVATE_KEY` | Empty | PEM private key used to create Vonage application JWTs |
| `VONAGE_SIGNATURE_SECRET` | Empty | HS256 secret used to verify signed Vonage callbacks |
| `VONAGE_FROM_NUMBER` | Empty | Vonage E.164 caller ID |
| `VONAGE_HANDOFF_DESTINATION` | Empty | Vonage E.164 warm-transfer destination |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Empty | Complete Google service-account JSON document |
| `GOOGLE_CALENDAR_ID` | Empty | Calendar shared with the service account |
| `HUBSPOT_PRIVATE_APP_TOKEN` | Empty | HubSpot private-app bearer token |
| `SIMLI_API_KEY` | Empty | Simli service credential |
| `SIMLI_FACE_ID` | Empty | Simli avatar face identifier |
| `PVS_HEALTHCARE_ENABLED` | `false` | Explicit healthcare runtime enablement |
| `PVS_HEALTHCARE_DATA_KEY` | Empty | URL-safe base64 encoding of exactly 32 encryption-key bytes |
| `PVS_HEALTHCARE_APPROVED_SERVICES` | Empty in code; `openai` in `.env.example` | Comma-separated approved processors; seeded healthcare requires `openai` |

`PVS_TIMEZONE` must be a valid IANA timezone. `PVS_PUBLIC_BASE_URL`, when set, must begin with
`https://`. Telephone numbers use canonical E.164 form such as `+15551234567`. Model identifiers
must be supported by the configured provider endpoint. Keep multiline JSON and PEM values quoted
correctly for your shell or dotenv parser; never commit them.
When a launcher starts the application, it overrides `PVS_BOT_BASE_URL` for those processes to match the selected worker port. The table default applies to manual startup.

## Start the application

By default, the launcher supervises the voice worker, telephony callback gateway on port `8080`,
optional Google Calendar worker, and Streamlit. It waits for HTTP readiness and cleans up every
launcher-owned process when Streamlit exits.

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

Worker, gateway, calendar, and optional API logs are written under `artifacts/launcher/`. All
application processes bind to `127.0.0.1`; only the operator-supplied HTTPS tunnel is public.

The launchers support these equivalent controls:

| Purpose | Windows | Linux |
|---|---|---|
| Prepare dependencies without starting services | `-SetupOnly` | `--setup-only` |
| Start the optional management API | `-WithApi` | `--with-api` |
| Set the worker port | `-WorkerPort 7861` | `--worker-port 7861` |
| Set the Streamlit port | `-StreamlitPort 8502` | `--streamlit-port 8502` |
| Set the API port | `-ApiPort 8001` | `--api-port 8001` |
| Set the callback gateway port | `-GatewayPort 8081` | `--gateway-port 8081` |

Selected ports must be distinct and unused. The launcher stops when a port is unavailable or a
required service is not ready within 30 seconds. Use `-GatewayPort` on Windows or `--gateway-port`
on Linux to change the callback port. Dependency and frontend repair behavior remains automatic.

To manage processes yourself, start each one in a separate terminal.

### 1. Start the Pipecat worker

```powershell
uv run python -m pipecat_voice_studio.voice.bot `
  --host 127.0.0.1 `
  --port 7860 `
  --allowed-origins http://localhost:8501 http://127.0.0.1:8501
```

The worker should report that the bot is ready. Its `/status` endpoint must return a ready status before a live browser session can connect.

### 2. Start the callback gateway

The gateway is required for Twilio/Vonage only:

```powershell
uv run uvicorn pipecat_voice_studio.telephony_gateway:app --host 127.0.0.1 --port 8080 --proxy-headers --forwarded-allow-ips 127.0.0.1
```

Forward a public HTTPS tunnel to `127.0.0.1:8080` and set its origin in
`PVS_PUBLIC_BASE_URL`. The gateway exposes provider webhooks and media WebSockets, not an operator
UI. Keep the management API and Streamlit private.

### 3. Optionally start calendar synchronization

When Google credentials are configured:

```powershell
uv run python -m pipecat_voice_studio.calendar_worker
```

### 4. Start Streamlit

```powershell
uv run streamlit run src/pipecat_voice_studio/ui/streamlit_app.py
```

Open [http://localhost:8501](http://localhost:8501).

On Linux, use the same `uv run` commands without PowerShell backticks.

### 5. Optionally start the management API

The Streamlit UI does not require the management API. Start it only when you need its HTTP endpoints:

```powershell
uv run uvicorn pipecat_voice_studio.api.app:app --host 127.0.0.1 --port 8000
```

Open [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) for the generated OpenAPI interface.

## Use the Streamlit studio

Each page opens with a **How to use this page** panel. It summarizes what to select, what action to
take, and what result or side effect to expect.

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
3. Select a browser realtime or cascade pipeline. Evaluation and telephone pipelines are excluded.
4. Select the browser microphone if more than one input device is available.
5. Choose **Connect** and grant microphone permission.
6. Speak normally; use **Mic on / Mic off** to control microphone transmission and **Disconnect**
   to end the session.
7. Observe transcripts, speaking state, function calls, and available timing metrics.

The browser retains only bounded, ephemeral transcript state. The database stores selected semantic events but never raw audio or browser media tracks.

For **Simli avatar assistant**, configure Simli first and select that seeded pipeline. The bot video
appears above the conversation while audio continues through the normal browser transport.

### Book an appointment

Use a cascade pipeline and tell the assistant:

- the attendee name;
- the appointment purpose;
- the desired date and time.

The Flow checks local availability and may suggest alternatives. The Google-backed seeded pipeline
also checks the configured calendar. It creates an appointment only after explicit affirmative
confirmation. Google creation occurs first; a local failure triggers compensating event deletion.
Appointments last 30 minutes, start on the hour or half hour, and must fall on a weekday between
09:00 and 17:00 in `PVS_TIMEZONE`.

### Review records

Open **Records** to inspect:

- session status and timestamps;
- final user and assistant conversation turns;
- stored appointments;
- redacted telephone calls and warm-handoff state;
- healthcare consent, review, and escalation metadata without decrypted intake content.

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

The current code uses schema version 2 and automatically migrates version 1 after creating a `.v1.bak` backup. Preserve that backup. Other schema versions are rejected.

## Connected providers

The workflows below are a quick operator reference. See
[Provider setup and operations](PROVIDERS.md) for complete credentials, callback contracts,
privacy behavior, synchronization inspection, and troubleshooting.

### Twilio and Vonage calls

1. Configure one provider and `PVS_PUBLIC_BASE_URL`, then restart the launcher.
2. Configure the provider's answer/event webhooks to the corresponding URLs shown below for
   inbound calls. Outbound calls already supply these URLs in their API request.
3. Open **Integrations**, verify that the provider reports ready, select **Business phone agent**,
   choose the provider, and save the binding.
4. For outbound calls, add the exact destination to `PVS_OUTBOUND_ALLOWLIST`, enter it in E.164
   form, select the confirmation checkbox, and choose **Place call**.

| Provider | Answer URL | Event/status URL |
|---|---|---|
| Twilio | `{PVS_PUBLIC_BASE_URL}/telephony/twilio/answer` | `{PVS_PUBLIC_BASE_URL}/telephony/twilio/status` |
| Vonage | `{PVS_PUBLIC_BASE_URL}/telephony/vonage/answer` | `{PVS_PUBLIC_BASE_URL}/telephony/vonage/events` |

Twilio request signatures and Vonage signed-webhook JWTs are mandatory. Media uses short-lived,
call-bound tokens. SQLite retains only the final four telephone digits and a keyed digest. A human
handoff uses `*_HANDOFF_DESTINATION`: the provider calls the human, plays the locally stored summary
through a signed on-answer callback, and only then bridges the caller.

### Google Calendar

Google Calendar uses `GOOGLE_SERVICE_ACCOUNT_JSON` and `GOOGLE_CALENDAR_ID`. Share the calendar with the service-account email. Confirmed bookings are written to Google; the launcher starts incremental synchronization and applies external cancellations locally.

Use **Google Calendar appointment assistant** in Live session. The first synchronization performs a
full event listing; later polls use Google's incremental sync token. An expired token triggers a full
resynchronization. The local Records page shows provider IDs and external status. Inspect
`artifacts/launcher/calendar.err.log` and the persisted `calendar_sync_state.last_error` when polling
fails; the provider runbook includes a safe inspection command.

### HubSpot and business routing

The **Business phone agent** starts in reception and routes to billing, technical support, sales, or
appointments. Sales can write a HubSpot contact, optional deal, and note only after explicit CRM
consent. The database stores provider IDs, score, result, and redacted telephone suffix, not the full
lead payload.

### Simli avatar

Set `SIMLI_API_KEY` and `SIMLI_FACE_ID`, restart, and select **Simli avatar assistant** in Live
session. Simli receives TTS audio and emits synchronized bot video through SmallWebRTC. Avatar mode
is browser-cascade only; it is rejected for telephone, realtime-combined, and evaluation graphs.

### Healthcare intake

Generate the encryption value without printing or committing raw key material:

```powershell
uv run python -c "import base64,secrets; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())"
```

Set healthcare enablement, the generated key, and approved service list; restart; then select
**Healthcare intake assistant**. The assistant must record explicit consent before collection. It
stores only encrypted chief concern, symptoms, medications, and allergies. The Streamlit UI exposes
consent, review state, and escalation metadata only. Emergency signs produce an escalation-required
record and emergency-services wording. The assistant does not diagnose, and these controls do not
establish legal or regulatory compliance.

### Provider troubleshooting

- If callbacks return 403, verify the exact public URL and the provider signing secret. Twilio signs
  the complete public callback URL, so tunnel host or path mismatches invalidate it.
- If calls connect without audio, confirm the tunnel supports WebSockets and reaches port `8080`.
- If outbound calling is denied, use exact E.164 syntax and an exact allowlist match.
- If Google reports 403, share the selected calendar with the service-account email and grant write
  access.
- If a healthcare pipeline refuses to start, confirm enablement, a valid 32-byte decoded key, and
  `openai` in the approved-services list.

## Unsupported capabilities

- production authentication, RBAC, and internet-scale deployment;
- regulated healthcare certification or diagnostic use;
- multilingual translation workflows;
- meeting/classroom ingestion;
- avatar providers other than Simli;
- voice-controlled developer tools;
- live coaching, sentiment, keyword, or compliance alerts;
- arbitrary custom Pipecat service loading from saved graphs.

For implementation architecture, security boundaries, persistence details, and API contracts, see [Technical Documentation](TECHNICAL.md).
