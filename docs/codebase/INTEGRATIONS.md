# External integrations

Operator setup and recovery procedures are documented in
[Provider setup and operations](../PROVIDERS.md).

## Integration inventory

| System | Type | Purpose | Auth model | Criticality | Evidence |
|---|---|---|---|---|---|
| OpenAI-compatible endpoint | Model API | Realtime speech, STT, reasoning, and TTS | `OPENAI_API_KEY`; optional base URL | High | `config.py`; `voice/bot.py` |
| Pipecat SmallWebRTC | Realtime transport | Browser audio and RTVI events | No app-level user auth | High | `voice/bot.py`; frontend component |
| Pipecat Flows | In-process orchestration | Appointments, specialist routing, CRM/handoff, healthcare intake | N/A | High for cascade mode | `voice/*_flow.py` |
| Pipecat Evals | Evaluation transport/harness | Behavioral scenario execution | Model credentials inherited by worker | Medium | `evaluations.py` |
| GitHub Actions | CI service | Quality checks and manual paid evaluations | GitHub environment secrets | Medium | `.github/workflows/` |
| PyTorch CUDA index | Package registry | CUDA wheel resolution | Public | Build-time | `pyproject.toml` |
| Twilio Voice | Telephone media and call control | Inbound/outbound calls and transfer | Account SID/token; signed webhooks | High | `telephony_gateway.py`; `integrations/telephony.py` |
| Vonage Voice | Telephone media and call control | Inbound/outbound calls and transfer | Application JWT; signed webhook secret | High | `telephony_gateway.py`; `integrations/telephony.py` |
| Google Calendar | Calendar REST API | Availability, booking, incremental cancellation sync | Service account OAuth | High | `integrations/google_calendar.py`; `calendar_worker.py` |
| HubSpot | CRM REST API | Consent-gated contact/deal/note writes | Private app token | Medium | `integrations/hubspot.py`; `voice/business_flow.py` |
| Simli | Avatar service | Convert TTS audio into synchronized bot video | API key and face ID | Medium | `voice/bot.py`; React video component |

Healthcare intake is an internal governance boundary: explicit consent, transcript suppression,
AES-256-GCM structured storage, metadata-only UI, audit events, and mandatory service approval.

## Data stores

| Store | Role | Access layer | Key risk | Evidence |
|---|---|---|---|---|
| SQLite | Pipelines, events, appointments, evaluations, integrations, calls, encrypted intake, audit | `StudioStore`, `AppointmentBook` | Local-file concurrency, local key availability, and no replication | `storage.py`; `appointments.py` |
| Browser memory | Live transcript and component state | React component | Ephemeral; bounded transcript is lost on disconnect/reload | `StudioComponent.tsx` |
| Temporary SQLite | Evaluation fixture isolation | `evaluations.py` | Subprocess cleanup after abnormal termination | `evaluations.py` |

Raw audio is not a supported persistent data type.
Full telephone numbers are not persisted. Healthcare ciphertext is durable, but its decryption key
is environment-owned and has no built-in rotation workflow.

## Secrets and credentials handling

- Credentials come from environment variables or an uncommitted `.env` file.
- API keys, tokens, private keys, and healthcare encryption material use `SecretStr` and remain server-side.
- The live component receives worker/pipeline metadata, not provider credentials.
- GitHub live evaluations use protected environment secrets.
- No hardcoded credential was found by the repository scan.
- Credential rotation and revocation policies are not documented in repository configuration.

## Reliability and failure behavior

- The live page probes worker `/status` with a one-second timeout and reports unavailability.
- Evaluation worker startup has a readiness timeout, bounded logs, terminate-then-kill cleanup, and a disposable database.
- SQLite uses WAL, foreign keys, five-second connection/busy timeouts, and explicit commits.
- Calendar polling recovers expired sync tokens. Other provider calls fail closed and expose redacted status;
  generalized retries, circuit breakers, and alternate-provider fallback are not implemented.
- SmallWebRTC default ICE servers are enabled; production TURN/failover topology is not configured here.

## Observability for integrations

- Pipecat metrics and selected frame events are persisted through `SemanticTimelineObserver`.
- Evaluation results retain duration, failures, observed events, and bounded diagnostics.
- Runtime health reports package versions, CUDA availability, and GPU identity.
- There is no APM, distributed tracing backend, Prometheus exporter, or centralized log sink.

## Evidence

- `.env.example`
- `src/pipecat_voice_studio/config.py`
- `src/pipecat_voice_studio/voice/bot.py`
- `src/pipecat_voice_studio/voice/timeline.py`
- `src/pipecat_voice_studio/telephony_gateway.py`
- `src/pipecat_voice_studio/calendar_worker.py`
- `src/pipecat_voice_studio/integrations/`
- `src/pipecat_voice_studio/security.py`
- `src/pipecat_voice_studio/evaluations.py`
- `.github/workflows/live-evaluations.yml`
