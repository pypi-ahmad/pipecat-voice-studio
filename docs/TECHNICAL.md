# Technical guide

This guide documents the technical design, architectural invariants, dependency choices, persistence models, and failure recovery mechanisms implemented in Pipecat Voice Studio.

## Purpose and scope

Pipecat Voice Studio is a local application for developing, testing, and evaluating real-time conversational agents. It integrates a Streamlit control interface, a standalone Pipecat audio worker, a browser-based SmallWebRTC client, external telephony gateways (Twilio and Vonage), Google Calendar, HubSpot CRM, Simli avatar streaming, and an ACID SQLite storage engine.

## Technology stack and rationale

The choice of each dependency is grounded directly in repository implementation requirements:

- **Python (`>=3.13,<3.15`) and [uv](https://docs.astral.sh/uv/)**: `uv` manages package resolution, virtual environments, and reproducible execution via [uv.lock](file:///D:/AI/Github/pipecat-voice-studio/uv.lock). Launcher scripts and GitHub Actions workflows run pinned Python versions (`3.14.7` with fallback to `3.13.13`).
- **Pipecat (`pipecat-ai[cli,evals,runner,simli,webrtc,websocket]==1.7.0`)**: Core runtime framework providing pipeline frame streaming, transport adapters (`SmallWebRTCTransport`, `FastAPIWebsocketTransport`, `EvalTransport`), audio/video serializers (`TwilioFrameSerializer`, `VonageFrameSerializer`), Silero VAD turn detection, OpenAI service integration, Flow state management, and the behavioral evaluation harness.
- **Streamlit (`streamlit==1.62.0`)**: Multi-page operator UI control plane ([streamlit_app.py](file:///D:/AI/Github/pipecat-voice-studio/src/pipecat_voice_studio/ui/streamlit_app.py)) hosting navigation, parameter configuration, session history, and evaluation reporting.
- **React 19, TypeScript, Vite, and `@xyflow/react`**: Implements the browser client component ([StudioComponent.tsx](file:///D:/AI/Github/pipecat-voice-studio/src/pipecat_voice_studio/ui/frontend/src/StudioComponent.tsx)). Direct WebRTC audio/video streaming is handled in browser React state to avoid Streamlit reruns breaking active WebRTC peer connections.
- **FastAPI (`fastapi>=0.141.1`) and Uvicorn (`uvicorn>=0.52.4`)**: ASGI server powering the telephony callback gateway ([telephony_gateway.py](file:///D:/AI/Github/pipecat-voice-studio/src/pipecat_voice_studio/telephony_gateway.py)) and the optional management API ([api/app.py](file:///D:/AI/Github/pipecat-voice-studio/src/pipecat_voice_studio/api/app.py)).
- **PyTorch (`torch==2.13.0+cu132`) and torchvision (`torchvision==0.28.0+cu132`)**: Direct dependency of Pipecat's `SileroVADAnalyzer` for streaming voice activity detection. The explicit CUDA 13.2 wheel requirement constrains host platforms to 64-bit Windows AMD64 and Linux x86_64 glibc 2.34+.
- **SQLite 3**: Embedded relational database configured with Write-Ahead Logging (`PRAGMA journal_mode=WAL`), foreign keys enabled (`PRAGMA foreign_keys=ON`), and a 5000ms busy timeout (`PRAGMA busy_timeout=5000`) in [storage.py](file:///D:/AI/Github/pipecat-voice-studio/src/pipecat_voice_studio/storage.py).
- **Pydantic (`pydantic>=2.15.0`) and Pydantic Settings (`pydantic-settings>=2.13.1`)**: Strict runtime schema validation with `extra="forbid"` for pipeline models ([graph.py](file:///D:/AI/Github/pipecat-voice-studio/src/pipecat_voice_studio/graph.py)) and typed environment configuration ([config.py](file:///D:/AI/Github/pipecat-voice-studio/src/pipecat_voice_studio/config.py)).
- **Cryptography (`cryptography>=44.0.0`)**: Provides `AESGCM` authenticated symmetric encryption for healthcare intake payloads in [security.py](file:///D:/AI/Github/pipecat-voice-studio/src/pipecat_voice_studio/security.py).
- **PyJWT (`pyjwt>=2.13.0`) and google-auth (`google-auth>=2.56.0`)**: JWT verification for Vonage signed webhooks and OAuth2 service-account token exchange for Google Calendar REST APIs.
- **HTTPX (`httpx>=0.28.1`)**: Asynchronous HTTP client for telephony REST operations, Google Calendar synchronization, and HubSpot CRM requests.

## Pipeline model and execution modes

Pipelines are represented by the [`PipelineGraph`](file:///D:/AI/Github/pipecat-voice-studio/src/pipecat_voice_studio/graph.py#L107-L236) schema in [graph.py](file:///D:/AI/Github/pipecat-voice-studio/src/pipecat_voice_studio/graph.py).

### Execution modes

1. **`realtime`**:
   - Audio path: Browser WebRTC -> Context -> `OpenAIRealtimeLLMService` -> Browser WebRTC.
   - Built via `_realtime_processors` in [voice/bot.py](file:///D:/AI/Github/pipecat-voice-studio/src/pipecat_voice_studio/voice/bot.py#L72-L117).
   - Features input transcription, near-field noise reduction, semantic turn detection, client interruption handling, and streaming audio synthesis.
2. **`cascade`**:
   - Audio path: Audio transport -> `OpenAIRealtimeSTTService` -> `SileroVADAnalyzer` -> Context -> `LLMUserAggregator` -> `OpenAIResponsesLLMService` -> Optional Flow / Avatar -> `OpenAITTSService` -> Audio output.
   - Built via `_cascade_processors` in [voice/bot.py](file:///D:/AI/Github/pipecat-voice-studio/src/pipecat_voice_studio/voice/bot.py#L119-L195).
   - Supports browser WebRTC or telephony WebSocket transports, Flow managers ([appointment_flow.py](file:///D:/AI/Github/pipecat-voice-studio/src/pipecat_voice_studio/voice/appointment_flow.py), [business_flow.py](file:///D:/AI/Github/pipecat-voice-studio/src/pipecat_voice_studio/voice/business_flow.py), [healthcare_flow.py](file:///D:/AI/Github/pipecat-voice-studio/src/pipecat_voice_studio/voice/healthcare_flow.py)), and Simli video avatar generation.
3. **`eval`**:
   - Audio path: `EvalTransport` -> Cascaded pipeline stack -> `EvalTransport`.
   - Used exclusively for headless, automated behavioral evaluation runs against scripted scenarios.

## Core system invariants

### Closed graph schema and single-chain compilation

- **Allowlisted node kinds**: Nodes must strictly belong to [`NodeKind`](file:///D:/AI/Github/pipecat-voice-studio/src/pipecat_voice_studio/graph.py#L29-L52). Arbitrary classes or dynamic module paths cannot be injected.
- **Configuration allowlist**: Node configuration is validated against [`ALLOWED_CONFIG`](file:///D:/AI/Github/pipecat-voice-studio/src/pipecat_voice_studio/graph.py#L76) (`prompt`, `voice`, `speed`, `language`, `vad_eagerness`). Unknown keys are rejected with `ValueError`.
- **Mandatory operational triad**: Every graph must contain [`NodeKind.TIMELINE`](file:///D:/AI/Github/pipecat-voice-studio/src/pipecat_voice_studio/graph.py#L49), [`NodeKind.METRICS`](file:///D:/AI/Github/pipecat-voice-studio/src/pipecat_voice_studio/graph.py#L50), and [`NodeKind.PERSISTENCE`](file:///D:/AI/Github/pipecat-voice-studio/src/pipecat_voice_studio/graph.py#L51).
- **Single unbranched chain**: [`compile_graph()`](file:///D:/AI/Github/pipecat-voice-studio/src/pipecat_voice_studio/graph.py#L247-L290) traverses the frame path and raises `ValueError("The executable frame path cannot branch")` if any node contains more than one outgoing path edge. Frame splitting and merging are forbidden.

### Appointment booking confirmation gate

In [appointments.py](file:///D:/AI/Github/pipecat-voice-studio/src/pipecat_voice_studio/appointments.py#L83-L125), creating an appointment row requires:
1. `confirmed is True` and `flow_node == "confirmation"`. Either failing raises `PermissionError("Appointment creation requires explicit confirmation")`.
2. Start timestamp must be timezone-aware and is normalized to the configured studio timezone (`PVS_TIMEZONE`) with seconds and microseconds truncated to zero.
3. Slots are restricted to half-hour marks (`:00` or `:30`), Monday through Friday, between 09:00 and 17:00.
4. Slot collision check queries SQLite for existing confirmed appointments at `starts_at`.
5. Compensating transaction: When integrated with Google Calendar ([appointments.py](file:///D:/AI/Github/pipecat-voice-studio/src/pipecat_voice_studio/appointments.py#L133-L174)), the external Google event is created first. If the local database insert subsequently fails (e.g. SQLite unique constraint violation), the newly created Google Calendar event is deleted immediately to prevent state divergence.

### Healthcare privacy and encryption

- **Transcript suppression**: When running a healthcare pipeline, [bot.py](file:///D:/AI/Github/pipecat-voice-studio/src/pipecat_voice_studio/voice/bot.py#L245-L253) initializes [`SemanticTimelineObserver`](file:///D:/AI/Github/pipecat-voice-studio/src/pipecat_voice_studio/voice/timeline.py#L24-L129) with `persist_conversation=False` and marks the session with `sensitive=1`. No user transcription or assistant speech turns (`turn.final`) are saved to the database.
- **Intake encryption**: Structured intake fields (chief concern, symptoms, medications, allergies) are encrypted using [`HealthcareCipher`](file:///D:/AI/Github/pipecat-voice-studio/src/pipecat_voice_studio/security.py#L58-L87) with AES-256-GCM. A unique 12-byte random nonce is generated per intake, and `session_id` is passed as authenticated associated data (AAD). Ciphertext cannot be decrypted under a different session ID.
- **Isolation requirement**: Graph validation rejects any graph combining [`NodeKind.HEALTHCARE`](file:///D:/AI/Github/pipecat-voice-studio/src/pipecat_voice_studio/graph.py#L46) with CRM, Calendar, Appointment, or Multi-agent nodes.

### Telephony security and phone number redaction

- **Webhook verification**: Twilio webhooks are validated via [`verify_twilio_signature()`](file:///D:/AI/Github/pipecat-voice-studio/src/pipecat_voice_studio/security.py#L123-L134) using HMAC-SHA1 over sorted parameters and the configured public callback URL. Vonage webhooks are validated via [`verify_vonage_webhook()`](file:///D:/AI/Github/pipecat-voice-studio/src/pipecat_voice_studio/security.py#L136-L151) using HS256 JWT decoding and API key claim comparison.
- **Media tokens**: WebSocket media endpoints authenticate connections via signed tokens created by [`sign_media_token()`](file:///D:/AI/Github/pipecat-voice-studio/src/pipecat_voice_studio/security.py#L89-L99) (`{call_id}.{timestamp}.{hmac_sha256}`). Tokens expire after 300 seconds with a 30-second clock skew tolerance.
- **Phone number privacy**: Full phone numbers are never stored in SQLite. Only the last four digits ([`redact_phone()`](file:///D:/AI/Github/pipecat-voice-studio/src/pipecat_voice_studio/security.py#L48-L50)) and an HMAC-SHA256 digest ([`digest_phone()`](file:///D:/AI/Github/pipecat-voice-studio/src/pipecat_voice_studio/security.py#L53-L55)) keyed by the provider secret are persisted.
- **Outbound call restrictions**: Outbound calls must strictly match canonical E.164 entries in `PVS_OUTBOUND_ALLOWLIST` via [`require_allowed_destination()`](file:///D:/AI/Github/pipecat-voice-studio/src/pipecat_voice_studio/integrations/telephony.py#L26-L31).

### CRM consent gate

In [integrations/hubspot.py](file:///D:/AI/Github/pipecat-voice-studio/src/pipecat_voice_studio/integrations/hubspot.py#L32-L84), [`HubSpot.upsert_lead()`](file:///D:/AI/Github/pipecat-voice-studio/src/pipecat_voice_studio/integrations/hubspot.py#L32-L84) checks `consent: bool`. If `consent` is `False`, it immediately raises [`CrmConsentRequiredError`](file:///D:/AI/Github/pipecat-voice-studio/src/pipecat_voice_studio/integrations/hubspot.py#L12-L13) without issuing network requests.

## Error handling and failure modes

### Exception hierarchy

| Exception class | Location | Cause / Trigger condition |
|---|---|---|
| [`InvalidTelephoneNumberError`](file:///D:/AI/Github/pipecat-voice-studio/src/pipecat_voice_studio/security.py#L29-L30) | [security.py](file:///D:/AI/Github/pipecat-voice-studio/src/pipecat_voice_studio/security.py) | Phone number string fails canonical E.164 regex pattern (`^\+[1-9]\d{7,14}$`). |
| [`InvalidHealthcareKeyError`](file:///D:/AI/Github/pipecat-voice-studio/src/pipecat_voice_studio/security.py#L33-L34) | [security.py](file:///D:/AI/Github/pipecat-voice-studio/src/pipecat_voice_studio/security.py) | Configured healthcare key is not valid base64 or length is not exactly 32 bytes. |
| [`InvalidMediaTokenError`](file:///D:/AI/Github/pipecat-voice-studio/src/pipecat_voice_studio/security.py#L37-L38) | [security.py](file:///D:/AI/Github/pipecat-voice-studio/src/pipecat_voice_studio/security.py) | Telephony media token is malformed, HMAC signature fails, or timestamp is expired (> 300s). |
| [`TelephonyNotConfiguredError`](file:///D:/AI/Github/pipecat-voice-studio/src/pipecat_voice_studio/integrations/telephony.py#L18-L19) | [integrations/telephony.py](file:///D:/AI/Github/pipecat-voice-studio/src/pipecat_voice_studio/integrations/telephony.py) | Required provider settings (account SID, auth token, from number, public base URL) are missing. |
| [`DestinationNotAllowedError`](file:///D:/AI/Github/pipecat-voice-studio/src/pipecat_voice_studio/integrations/telephony.py#L22-L23) | [integrations/telephony.py](file:///D:/AI/Github/pipecat-voice-studio/src/pipecat_voice_studio/integrations/telephony.py) | Outbound destination number is not present in `PVS_OUTBOUND_ALLOWLIST`. |
| [`CrmConsentRequiredError`](file:///D:/AI/Github/pipecat-voice-studio/src/pipecat_voice_studio/integrations/hubspot.py#L12-L13) | [integrations/hubspot.py](file:///D:/AI/Github/pipecat-voice-studio/src/pipecat_voice_studio/integrations/hubspot.py) | CRM lead creation called without user consent flag set to `True`. |

### Pipeline execution failures

In [voice/bot.py](file:///D:/AI/Github/pipecat-voice-studio/src/pipecat_voice_studio/voice/bot.py#L302-L311), any uncaught exception raised during pipeline execution is caught:
1. The exception type name is retrieved (`failure = type(error).__name__`).
2. The session record is updated with `status="failed"`, `failure_class=failure`, and marked ended.
3. If an associated telephone call exists, `store.update_call(call_id, status="failed", ended=True)` is called.
4. The error is re-raised.

### Google Calendar synchronization recovery

In [calendar_worker.py](file:///D:/AI/Github/pipecat-voice-studio/src/pipecat_voice_studio/calendar_worker.py#L17-L32), when Google Calendar returns HTTP 410 Gone (`SYNC_TOKEN_GONE = 410`), the worker catches `httpx.HTTPStatusError`, resets `sync_token=None`, and executes a full event resynchronization without raising.

## Persistence paths and schema

The SQLite database path is resolved from `PVS_DATABASE_PATH` (defaults to `data/pipecat_voice_studio.db`).

### Schema migrations

[StudioStore.initialize()](file:///D:/AI/Github/pipecat-voice-studio/src/pipecat_voice_studio/storage.py#L47-L140) checks `schema_version`.
- If the database contains version 1 (`current == 1`):
  1. Creates a file backup at `<database_path>.v1.bak`.
  2. Runs migration statements adding `sensitive` and `failure_class` to `sessions`, and creates tables `healthcare_consents`, `healthcare_intakes`, and `audit_events`.
  3. Updates `schema_version` to 2.
- If the database has an unsupported version, it raises `RuntimeError(f"Unsupported schema version: {current}")`.

### Schema tables

```text
schema_version (version INTEGER PRIMARY KEY)

pipeline_definitions (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  revision INTEGER NOT NULL DEFAULT 1,
  graph_json TEXT NOT NULL,
  active INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
)

sessions (
  id TEXT PRIMARY KEY,
  pipeline_id TEXT NOT NULL REFERENCES pipeline_definitions(id),
  pipeline_name TEXT NOT NULL,
  mode TEXT NOT NULL,
  transport TEXT NOT NULL,
  call_id TEXT REFERENCES calls(id),
  started_at TEXT NOT NULL,
  ended_at TEXT,
  duration_seconds REAL,
  status TEXT NOT NULL,
  sensitive INTEGER NOT NULL DEFAULT 0,
  failure_class TEXT
)

session_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
  sequence INTEGER NOT NULL,
  event_type TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  UNIQUE(session_id, sequence)
)

appointments (
  id TEXT PRIMARY KEY,
  session_id TEXT REFERENCES sessions(id) ON DELETE SET NULL,
  attendee_name TEXT NOT NULL,
  purpose TEXT NOT NULL,
  starts_at TEXT NOT NULL,
  duration_minutes INTEGER NOT NULL,
  status TEXT NOT NULL,
  external_provider TEXT,
  external_id TEXT,
  external_status TEXT,
  created_at TEXT NOT NULL,
  UNIQUE(starts_at, status)
)

eval_runs (
  id TEXT PRIMARY KEY,
  scenario_name TEXT NOT NULL,
  pipeline_id TEXT NOT NULL,
  passed INTEGER NOT NULL,
  started_at TEXT NOT NULL,
  duration_seconds REAL NOT NULL,
  result_json TEXT NOT NULL
)

integration_bindings (
  provider TEXT PRIMARY KEY,
  pipeline_id TEXT NOT NULL REFERENCES pipeline_definitions(id),
  updated_at TEXT NOT NULL
)

calls (
  id TEXT PRIMARY KEY,
  provider TEXT NOT NULL,
  provider_call_id TEXT NOT NULL,
  direction TEXT NOT NULL,
  remote_last_four TEXT NOT NULL,
  remote_digest TEXT NOT NULL,
  status TEXT NOT NULL,
  started_at TEXT NOT NULL,
  ended_at TEXT,
  UNIQUE(provider, provider_call_id)
)

handoffs (
  id TEXT PRIMARY KEY,
  call_id TEXT NOT NULL REFERENCES calls(id) ON DELETE CASCADE,
  provider TEXT NOT NULL,
  destination_last_four TEXT NOT NULL,
  summary TEXT NOT NULL,
  status TEXT NOT NULL,
  created_at TEXT NOT NULL
)

calendar_sync_state (
  provider TEXT PRIMARY KEY,
  sync_token TEXT,
  last_synced_at TEXT NOT NULL,
  last_error TEXT
)

crm_records (
  id TEXT PRIMARY KEY,
  provider TEXT NOT NULL,
  session_id TEXT REFERENCES sessions(id) ON DELETE SET NULL,
  remote_contact_id TEXT NOT NULL,
  remote_deal_id TEXT,
  status TEXT NOT NULL,
  created_at TEXT NOT NULL
)

healthcare_consents (
  session_id TEXT PRIMARY KEY REFERENCES sessions(id) ON DELETE CASCADE,
  accepted INTEGER NOT NULL,
  policy_version TEXT NOT NULL,
  created_at TEXT NOT NULL
)

healthcare_intakes (
  id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
  ciphertext BLOB NOT NULL,
  nonce BLOB NOT NULL,
  status TEXT NOT NULL,
  escalated INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL
)

audit_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  action TEXT NOT NULL,
  resource_type TEXT NOT NULL,
  resource_id TEXT NOT NULL,
  outcome TEXT NOT NULL,
  created_at TEXT NOT NULL
)
```
