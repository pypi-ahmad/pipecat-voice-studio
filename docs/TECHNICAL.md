# Pipecat Voice Studio technical guide

## Purpose and audience

Pipecat Voice Studio is a local-first development environment for building, running, and
evaluating real-time voice agents. It combines a Streamlit control plane, a separate Pipecat
worker, a browser SmallWebRTC client, OpenAI speech and language services, and SQLite-backed
operational records.

This guide is for developers and operators working on the repository. It documents version
0.1.0 as implemented in the current codebase.

## System architecture

```mermaid
flowchart LR
    Browser[Browser microphone and speaker]
    UI[Streamlit studio]
    Component[React CCv2 component]
    API[FastAPI management API]
    Gateway[FastAPI telephony gateway]
    Phone[Twilio or Vonage]
    Worker[Pipecat worker]
    Models[OpenAI services]
    Providers[Google Calendar / HubSpot / Simli]
    Calendar[Calendar sync worker]
    DB[(SQLite)]
    Eval[Pipecat EvalSession]

    Browser <--> Component
    UI --> Component
    Component <-->|SmallWebRTC and RTVI| Worker
    Phone <-->|signed HTTP and media WebSocket| Gateway
    Gateway --> Worker
    Worker <--> Models
    Worker <--> Providers
    Calendar <--> Providers
    Calendar --> DB
    Worker --> DB
    UI <--> DB
    API <--> DB
    Eval <-->|EvalTransport and RTVI| Worker
```

The application has six runtime boundaries:

1. **Streamlit studio** — displays pipeline definitions, launches browser sessions, browses
   records, runs evaluations, and displays analytics.
2. **Pipecat worker** — validates the selected pipeline and owns audio transport, model calls,
   turn handling, function calls, metrics, and session persistence.
3. **Browser component** — owns microphone permission, WebRTC media, live transcript state,
   device selection, mute state, tool indicators, and latency display.
4. **Telephony gateway** — verifies callbacks, validates short-lived media tokens, creates provider
   serializers, and runs the bound cascade pipeline.
5. **Calendar synchronization worker** — polls Google incremental changes and updates known local
   appointments.
6. **External providers** — model, telephone, calendar, CRM, and avatar APIs behind explicit
   adapters and environment-backed credentials.

The worker is intentionally a separate process. The Streamlit application probes its `/status`
endpoint but does not create or supervise it; `launch.ps1` and `launch.sh` supervise both
processes during launcher-managed runs. On Windows, `launch.cmd` is a double-clickable wrapper
around `launch.ps1`, not a separate process supervisor.

## Repository structure

| Area | Responsibility |
| --- | --- |
| `src/pipecat_voice_studio/graph.py` | Closed graph schema, validation, and compilation |
| `src/pipecat_voice_studio/voice/` | Pipecat worker, pipeline construction, Flow, timeline observer |
| `src/pipecat_voice_studio/ui/` | Streamlit pages and Components v2 wrappers |
| `src/pipecat_voice_studio/ui/frontend/` | React graph and browser voice client |
| `src/pipecat_voice_studio/storage.py` | SQLite schema and transactional repository |
| `src/pipecat_voice_studio/integrations/` | Google, HubSpot, telephone, and readiness adapters |
| `src/pipecat_voice_studio/telephony_gateway.py` | Public provider callback and media boundary |
| `src/pipecat_voice_studio/calendar_worker.py` | Google incremental synchronization loop |
| `src/pipecat_voice_studio/security.py` | E.164, signatures, media tokens, and AES-GCM helpers |
| `src/pipecat_voice_studio/evaluations.py` | Isolated evaluation orchestration |
| `src/pipecat_voice_studio/eval_scenarios/` | Allowlisted Pipecat evaluation scenarios |
| `src/pipecat_voice_studio/api/` | FastAPI health and pipeline management API |
| `.github/workflows/` | Quality checks and manually dispatched live evaluations |

## Pipeline model

Saved pipelines use `PipelineGraph`, a Pydantic model that rejects unknown fields and node
configuration. Executable nodes must form one connected, acyclic chain. Timeline, metrics, and
persistence nodes are mandatory operational capabilities.

### Supported modes

| Mode | Transport | Processing path | Intended use |
| --- | --- | --- | --- |
| `realtime` | SmallWebRTC | Browser → context → OpenAI Realtime → browser | Low-latency general voice assistant |
| `cascade` | SmallWebRTC or telephony WebSocket | Audio → STT → turn detection → context → LLM → optional Flow/avatar → TTS → output | Appointment, business, healthcare, or avatar assistant |
| `eval` | EvalTransport | Scripted input through the cascaded pipeline | Behavioral regression testing |

Runtime graphs select only audited implementations. A stored graph cannot inject Python code,
credentials, import paths, or arbitrary provider classes.

### Realtime path

The realtime pipeline uses `OpenAIRealtimeLLMService` with:

- input transcription;
- near-field noise reduction;
- semantic turn detection;
- interruption of active responses;
- streamed model audio output;
- a server-owned system prompt, language, voice, and VAD eagerness.

### Cascaded path

The cascaded pipeline uses:

1. `OpenAIRealtimeSTTService` for streaming transcription.
2. `SileroVADAnalyzer` through the user context aggregator.
3. `OpenAIResponsesLLMService` for reasoning and function calls.
4. Pipecat Flows for appointments, specialist routing/CRM/handoff, or healthcare intake.
5. `OpenAITTSService` for streamed speech output.
6. Optional `SimliVideoService` after TTS for synchronized browser avatar frames.

Appointment creation is permitted only from the confirmation node with an affirmative
`confirmed` value. The appointment store independently validates timezone awareness, business
hours, half-hour boundaries, required fields, and slot uniqueness.

Business routing uses deterministic Flow transitions among reception, billing, technical support,
sales, and appointments. HubSpot and provider transfer functions remain server-side. Healthcare
uses a separate isolated graph: it cannot contain appointment, calendar, CRM, or multi-agent nodes.

## Telephone runtime

The callback gateway binds to localhost and is intended to sit behind an operator-managed HTTPS
tunnel. Twilio callbacks use protocol-required HMAC-SHA1 verification. Vonage callbacks use signed
HS256 webhook JWTs and verify the expected API-key claim. Both providers receive a short-lived HMAC
media token bound to one local call record.

Twilio media uses `TwilioFrameSerializer`; Vonage uses 16 kHz linear PCM through
`VonageFrameSerializer`. Telephone graphs must use cascade mode. Outbound calls require canonical
E.164, an exact allowlist match, and explicit Streamlit confirmation. The store retains only the
last four digits and a keyed digest.

Warm transfer creates a handoff record, redirects the active provider leg, and supplies a signed
on-answer callback. The callback speaks the local summary to the human before the provider joins
the original caller.

### Telephony gateway endpoints

| Method | Path | Authentication | Purpose |
|---|---|---|---|
| `GET` | `/health` | None; localhost/tunnel health probe | Gateway liveness |
| `POST` | `/telephony/twilio/answer` | Twilio request signature | Create/redact call state and return TwiML media connection |
| `POST` | `/telephony/twilio/status` | Twilio request signature | Persist terminal and intermediate call status |
| `WS` | `/telephony/twilio/media/{token}` | Five-minute call-bound media token | Run Twilio audio through the bound cascade pipeline |
| `POST` | `/telephony/twilio/handoff/{handoff_id}` | Twilio request signature | Speak the briefing to the answered human leg |
| `GET` | `/telephony/vonage/answer` | Signed Vonage webhook JWT | Create/redact call state and return WebSocket NCCO |
| `POST` | `/telephony/vonage/events` | Signed Vonage webhook JWT | Persist Vonage call status |
| `WS` | `/telephony/vonage/media/{token}` | Five-minute call-bound media token | Run 16 kHz linear audio through the bound cascade pipeline |
| `GET` | `/telephony/vonage/handoff/{handoff_id}` | Signed Vonage webhook JWT | Return the human-leg briefing NCCO |

These routes are provider contracts, not an operator API. Only `/health` is unsigned; keep the
gateway behind TLS and expose no other application process through the tunnel. See
[Provider setup and operations](PROVIDERS.md) for configuration steps.

## Calendar, CRM, avatar, and healthcare boundaries

`GoogleCalendar` obtains service-account OAuth credentials for the Calendar scope and calls the REST
API through `httpx`. Appointment availability checks both local business policy and Google events.
Confirmed creation is compensating: if the local insert fails after Google creation, the adapter
deletes the new external event. `calendar_worker` stores the next sync token, applies cancellation
status to known external appointments, and resets to full sync after HTTP 410.

`HubSpot.upsert_lead()` refuses processing without explicit consent. It batch-upserts the contact by
email, optionally creates and associates a deal, and writes an optional note. Local CRM records keep
only provider IDs, score, state, failure class, and a redacted phone suffix.

Simli consumes `TTSAudioRawFrame` after speech synthesis and emits `OutputImageRawFrame` through the
video-enabled SmallWebRTC output. The React component renders the bot video track. Graph validation
restricts avatars to browser cascade pipelines.

Healthcare starts at a consent Flow node. Accepted sessions collect a deliberately small schema:
chief concern, symptoms, medications, allergies, and an emergency-sign flag. Content is encrypted
before SQLite insertion; the UI selects metadata only. Emergency signs change state and wording but
do not trigger an external emergency call. This is intake support, not diagnosis or certification.

## Live browser session

The Streamlit Live session page passes only the worker URL and selected pipeline metadata to
the React component. It never sends an API key to the browser.

The component starts a session with:

```http
POST {PVS_BOT_BASE_URL}/start
Content-Type: application/json

{
  "transport": "webrtc",
  "enableDefaultIceServers": true,
  "body": {
    "pipeline_id": "<stored pipeline ID>"
  }
}
```

The Pipecat client then connects through the session-specific SmallWebRTC endpoint returned by
the runner. Live state remains inside React to avoid Streamlit reruns interrupting WebRTC.

The browser UI provides:

- connect and disconnect controls;
- microphone permission and input-device selection;
- accessible `Mic on / Mic off` control with visible and pressed state;
- user and assistant speaking indicators;
- interim and final user transcripts;
- streamed assistant output;
- function-call lifecycle status;
- TTFB and processing metrics;
- mixed-content, device, and transport errors.

The transcript view retains at most 200 entries in browser memory. Browser transcript state is
ephemeral; durable semantic events are written by the worker.

## Semantic timeline and data retention

`SemanticTimelineObserver` maps selected Pipecat frames into ordered session events.

| Event | Stored data |
| --- | --- |
| `session.started` | Pipeline mode |
| `transport.connecting`, `transport.connected` | Transport name |
| `turn.final` | Final user or completed assistant text |
| `turn.interrupted` | Interruption marker |
| `flow.node`, `agent.routed` | Flow node/outcome or selected business specialist |
| `tool.requested` | Function names and tool-call IDs |
| `tool.started` | Function name and tool-call ID |
| `tool.completed` | Function name, tool-call ID, and normalized status |
| `tool.cancelled` | Function name and tool-call ID |
| `metrics.observed` | Pipecat metric type and serialized metric fields |
| `session.completed`, `session.failed` | Terminal status |

The application deliberately does not persist raw audio, interim transcripts, unrestricted
tool arguments, API keys, or browser media tracks. Interrupted assistant text is discarded from
the final-turn buffer.

Healthcare sessions set `sensitive=1` and construct the observer with conversation persistence
disabled, so user/assistant `turn.final` content is not written. Structured intake is encrypted
separately with AES-256-GCM, a random 96-bit nonce, and the session ID as associated data.

## Persistence

SQLite is configured with foreign keys, WAL journaling, a five-second busy timeout, and explicit
transactions. The default location is `data/pipecat_voice_studio.db`.

| Table | Purpose |
| --- | --- |
| `schema_version` | Rejects incompatible database layouts |
| `pipeline_definitions` | Validated graph JSON, revision, active status, timestamps |
| `sessions` | Frozen graph and model snapshot for each worker session |
| `session_events` | Ordered semantic timeline with per-session sequence numbers |
| `appointments` | Confirmation-gated records and optional Google identity/status |
| `eval_runs` | Evaluation status and structured result JSON |
| `integration_bindings` | Telephone provider to active pipeline binding |
| `calls` | Redacted call lifecycle and provider identity |
| `handoffs` | Human-transfer state and briefing summary |
| `calendar_sync_state` | Google incremental token and last result |
| `crm_records` | Redacted HubSpot write outcome and provider IDs |
| `healthcare_consents` | Policy version and acceptance state |
| `healthcare_intakes` | AES-GCM ciphertext, nonce, review state, and escalation flag |
| `audit_events` | Redacted governance action log |

Deleting a session cascades to its timeline. Appointment references become null when their
session is deleted. Pipeline and appointment uniqueness are enforced by SQLite constraints. Schema
version 2 migrates version 1 after creating a `.v1.bak` backup; other versions are rejected.

## Behavioral evaluations

The Evaluations page runs only scenarios present in the packaged allowlist:

| Scenario | Assertion |
| --- | --- |
| `happy-path` | Availability and confirmation functions create one appointment |
| `unavailable-slot` | A preoccupied slot does not produce another appointment |
| `policy-denial` | Explicit denial leaves the appointment book empty |
| `interruption` | A user turn is accepted while assistant generation is active |
| `synthetic-audio-smoke` | Kokoro-generated speech traverses the real STT path |

Each run performs the following lifecycle:

1. Create an `eval_runs` record in the studio database.
2. Create a temporary SQLite database.
3. Copy the selected validated graph into the temporary database.
4. Add any scenario fixture, such as an occupied appointment slot.
5. Start a hidden localhost-only worker using `EvalTransport`.
6. Run `EvalSession` over RTVI.
7. Stop the worker and discard the temporary database.
8. Persist pass/fail status, failures, duration, observed events, and bounded diagnostics.

Model-backed evaluations are never triggered by normal tests or pull requests.

## Configuration reference

Configuration is loaded from environment variables or a project-root `.env` file.

| Variable | Default | Purpose |
| --- | --- | --- |
| `OPENAI_API_KEY` | None | Required for voice pipelines and live evaluations |
| `OPENAI_BASE_URL` | None | Optional compatible OpenAI endpoint |
| `APP_NAME` | `Pipecat Voice Studio` | Application/API title |
| `PVS_ENVIRONMENT` | `development` | Environment label shown by diagnostics |
| `PVS_BOT_BASE_URL` | `http://127.0.0.1:7860` | Browser and Streamlit worker endpoint |
| `PVS_DATABASE_PATH` | `data/pipecat_voice_studio.db` | SQLite database path |
| `PVS_TIMEZONE` | `Asia/Calcutta` | IANA timezone for appointment policy |
| `PVS_REALTIME_MODEL` | `gpt-realtime-2.1-mini` | Realtime service model |
| `PVS_CASCADE_STT_MODEL` | `gpt-realtime-whisper` | Cascaded speech recognition model |
| `PVS_CASCADE_LLM_MODEL` | `gpt-5.6-luna` | Cascaded reasoning model |
| `PVS_CASCADE_TTS_MODEL` | `gpt-4o-mini-tts` | Cascaded speech synthesis model |
| `PVS_REALTIME_VOICE` | `marin` | Default voice |
| `PVS_PUBLIC_BASE_URL` | None | Public HTTPS tunnel origin for telephone callbacks |
| `PVS_CALENDAR_SYNC_SECONDS` | `60` | Google polling interval, constrained to 15–3600 seconds |
| `PVS_OUTBOUND_ALLOWLIST` | Empty | Exact comma-separated E.164 outbound destinations |
| `TWILIO_ACCOUNT_SID` | None | Twilio account identity |
| `TWILIO_AUTH_TOKEN` | None | Twilio REST and signature secret |
| `TWILIO_FROM_NUMBER` | None | Twilio caller ID |
| `TWILIO_HANDOFF_DESTINATION` | None | Twilio warm-transfer destination |
| `VONAGE_APPLICATION_ID` | None | Vonage Voice application identity |
| `VONAGE_API_KEY` | None | Expected signed-webhook claim |
| `VONAGE_PRIVATE_KEY` | None | Vonage application JWT private key |
| `VONAGE_SIGNATURE_SECRET` | None | Vonage webhook verification secret |
| `VONAGE_FROM_NUMBER` | None | Vonage caller ID |
| `VONAGE_HANDOFF_DESTINATION` | None | Vonage warm-transfer destination |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | None | Google service-account JSON |
| `GOOGLE_CALENDAR_ID` | None | Shared organization calendar |
| `HUBSPOT_PRIVATE_APP_TOKEN` | None | HubSpot private-app bearer token |
| `SIMLI_API_KEY` | None | Simli credential |
| `SIMLI_FACE_ID` | None | Simli face identifier |
| `PVS_HEALTHCARE_ENABLED` | `false` | Explicit healthcare mode gate |
| `PVS_HEALTHCARE_DATA_KEY` | None | URL-safe base64 32-byte AES key |
| `PVS_HEALTHCARE_APPROVED_SERVICES` | Empty | Approved processors; seeded flow requires `openai` |

`PVS_TIMEZONE` is validated as an IANA timezone; `PVS_PUBLIC_BASE_URL` must use HTTPS.
The settings default for `PVS_HEALTHCARE_APPROVED_SERVICES` is empty; `.env.example` sets `openai`
as a template value, but healthcare remains disabled until the operator explicitly enables it and
supplies an encryption key.
Launcher-managed runs override `PVS_BOT_BASE_URL` in child processes to match the selected
worker port; the documented default applies to manual process startup.

## Local development on Windows and Linux

### Prerequisites

- Native 64-bit Windows 11, or native x86-64 Linux with glibc 2.34+
- PowerShell on Windows; Bash and either `curl` or `wget` on Linux
- Node.js and npm for frontend changes
- An OpenAI API key for live model calls
- A CUDA 13.2-compatible environment for GPU acceleration; CPU mode is supported

### One-command setup and launch

Windows:

```powershell
.\launch.cmd
```

`launch.cmd` forwards command-line arguments to `launch.ps1`, starts PowerShell without loading
a user profile, applies the required execution-policy override, and pauses after a nonzero exit
so File Explorer users can read the error. Run `launch.ps1` directly when invoking advanced
PowerShell parameters interactively.

Linux:

```bash
./launch.sh
```

The PowerShell and Bash launchers bootstrap `uv`, install the pinned Python with fallback, create
root `.venv` and `.env`, synchronize `uv.lock`, repair pandas/dateutil when needed, and validate
frontend assets. They supervise the Pipecat browser worker, localhost telephony gateway, optional
Google Calendar synchronization worker, optional management API, and Streamlit. Worker, gateway,
Streamlit, and API ports are configurable and must be distinct. Readiness has a 30-second timeout;
logs are stored in `artifacts/launcher/`, and all launcher-owned processes stop on exit.

When `OPENAI_API_KEY` or `OPENAI_BASE_URL` is absent from the Windows launcher process,
`launch.ps1` imports the missing value from the Windows user environment. Existing process values
and `.env` configuration retain their normal precedence, and values are never printed.

Linux support requires glibc 2.34+ because the Pipecat evaluation dependency ships its x86-64 wheel at that baseline. ARM64 and musl Linux are not supported.

### Manual install

```powershell
uv sync --frozen
Copy-Item .env.example .env
```

Populate `OPENAI_API_KEY` in `.env` or the process environment. Do not commit `.env` or Streamlit
secrets files. Manual startup does not perform the Windows user-environment fallback implemented by
`launch.ps1`.

Build the Streamlit component after changing frontend source:

```powershell
Set-Location src\pipecat_voice_studio\ui\frontend
npm ci
npm run build
Set-Location ..\..\..\..
```

### Start the worker

```powershell
uv run python -m pipecat_voice_studio.voice.bot `
  --host 127.0.0.1 `
  --port 7860 `
  --allowed-origins http://localhost:8501 http://127.0.0.1:8501
```

### Start Streamlit

In another terminal:

```powershell
uv run streamlit run src\pipecat_voice_studio\ui\streamlit_app.py
```

Open `http://localhost:8501`, select Live session, choose a browser pipeline, and connect. Telephone
pipelines are operated through provider bindings on the Integrations page.

### Start telephone and calendar services

Telephone callbacks require the gateway plus a public HTTPS tunnel forwarding to port 8080:

```powershell
uv run uvicorn pipecat_voice_studio.telephony_gateway:app --host 127.0.0.1 --port 8080 --proxy-headers --forwarded-allow-ips 127.0.0.1
```

Google synchronization is a separate optional process:

```powershell
uv run python -m pipecat_voice_studio.calendar_worker
```

### Start the management API

```powershell
uv run uvicorn pipecat_voice_studio.api.app:app --host 127.0.0.1 --port 8000
```

OpenAPI documentation is available at `http://127.0.0.1:8000/docs` while the API is running.

## Management API reference

### `GET /health`

Returns application metadata, installed Python/Pipecat/Streamlit/PyTorch versions, CUDA
availability, and the detected GPU name.

### `GET /pipelines`

Returns pipeline metadata without graph bodies or credentials.

### `GET /pipelines/{pipeline_id}`

Returns one active `PipelineGraph`. A missing or inactive ID returns HTTP 404.

### `POST /pipelines`

Validates and compiles a complete `PipelineGraph`, stores it as active revision one, and returns:

```json
{"id": "<pipeline ID>"}
```

Validation failures return FastAPI's standard HTTP 422 response. Compilation failures reject
non-executable graph topology before persistence.

## Quality and CI

Run the complete local verification set with:

```powershell
uv lock --check
uv run ruff check .
uv run ty check
uv run pytest

Set-Location src\pipecat_voice_studio\ui\frontend
npm run typecheck
npm run build
Set-Location ..\..\..\..

uv build
```

The `Quality` workflow performs these checks on native Windows and Ubuntu for pushes, pull
requests, and manual dispatches. It also validates each launcher in setup-only mode. Python
coverage must remain at or above 80 percent.

The `Live evaluations` workflow is manual. Configure a protected GitHub environment named
`live-evals` with `OPENAI_API_KEY` and, when needed, `OPENAI_BASE_URL`. The workflow accepts one
scenario or `all` and uploads `live-evaluations.json` as an artifact.

## Security and deployment boundaries

- Provider credentials remain in server-process environments and are never included in component
  data, logs, or pipeline graph JSON.
- The graph schema is an allowlist, not a general code execution format.
- Browser microphone access requires localhost or HTTPS.
- An HTTPS Streamlit deployment cannot connect to an HTTP worker because browsers block mixed
  content.
- CORS origins must match the Streamlit origin passed to the worker.
- Evaluation subprocesses receive arguments as a list with no shell interpolation.
- Evaluation fixtures and generated audio are isolated in temporary storage.

The current system is designed for local development and trusted LAN use. Public deployment
requires authentication, HTTPS termination, production ICE/TURN configuration, authorization,
rate limiting, data-retention policy, monitoring, and threat review.

## Troubleshooting

### The Live session page reports that the worker is unavailable

1. Start the worker with the command shown on the page.
2. Confirm `PVS_BOT_BASE_URL` points to the same host and port.
3. Open `{PVS_BOT_BASE_URL}/status`; it should report `status: ready`.
4. Verify the worker's allowed origins include the exact Streamlit origin.

### Microphone permission fails

- Use `localhost`, `127.0.0.1`, or HTTPS.
- Confirm the browser has permission for the active Streamlit origin.
- Disconnect before changing operating-system audio devices.
- Avoid an HTTPS page with an HTTP worker URL.

### A pipeline fails immediately

- Confirm `OPENAI_API_KEY` exists in the worker environment.
- Confirm the selected graph matches its transport: `eval` requires EvalTransport, realtime uses
  browser WebRTC, cascade supports browser WebRTC or a bound telephone WebSocket, and avatar is
  browser-cascade only.
- Review the session failure type and semantic events in Records.
- Verify configured model identifiers are supported by the selected endpoint.

### An evaluation does not start

- Confirm an evaluation-mode graph is selected.
- Confirm `OPENAI_API_KEY` is configured.
- Review the stored worker log in the evaluation result.
- On Windows, ensure security software permits the hidden child Python process and localhost
  WebSocket listener.

### The Streamlit component is blank

Rebuild from a clean frontend output directory:

```powershell
Set-Location src\pipecat_voice_studio\ui\frontend
npm ci
npm run clean
npm run build
```

The component manifest and Python registration must retain the fully qualified key
`pipecat-voice-studio.studio_graph`, and each `index-*.js` and `index-*.css` glob must match
exactly one built file.

## Current limitations

- SmallWebRTC is configured for local-first operation, not internet-scale deployment.
- The management API has no authentication.
- Graphs execute realtime, cascade, and evaluation modes. Cascade feature nodes select appointment,
  business-routing, healthcare, and Simli runtime behavior.
- Twilio and Vonage callbacks terminate at a dedicated localhost gateway intended for an operator-
  supplied HTTPS tunnel. Google Calendar synchronization is a launcher-managed polling worker.
- The application has no production authentication, RBAC, high-availability topology, or regulated
  healthcare certification.
