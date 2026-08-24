# External Integrations

## Integration Inventory

| System | Type | Purpose | Auth model | Criticality | Evidence |
|---|---|---|---|---|---|
| OpenAI-compatible endpoint | Model API | Realtime speech, STT, reasoning, and TTS | `OPENAI_API_KEY`; optional base URL | High | `config.py`; `voice/bot.py` |
| Pipecat SmallWebRTC | Realtime transport | Browser audio and RTVI events | No app-level user auth | High | `voice/bot.py`; frontend component |
| Pipecat Flows | In-process orchestration | Appointment state and tools | N/A | High for cascade mode | `voice/appointment_flow.py` |
| Pipecat Evals | Evaluation transport/harness | Behavioral scenario execution | Model credentials inherited by worker | Medium | `evaluations.py` |
| GitHub Actions | CI service | Quality checks and manual paid evaluations | GitHub environment secrets | Medium | `.github/workflows/` |
| PyTorch CUDA index | Package registry | CUDA wheel resolution | Public | Build-time | `pyproject.toml` |

Twilio, Vonage, CRM, external calendar, healthcare, avatar, and multi-agent services are not integrated in the current code.

## Data Stores

| Store | Role | Access layer | Key risk | Evidence |
|---|---|---|---|---|
| SQLite | Pipelines, sessions/events, appointments, eval results | `StudioStore`, `AppointmentBook` | Local-file concurrency and no distributed replication | `storage.py`; `appointments.py` |
| Browser memory | Live transcript and component state | React component | Ephemeral; bounded transcript is lost on disconnect/reload | `StudioComponent.tsx` |
| Temporary SQLite | Evaluation fixture isolation | `evaluations.py` | Subprocess cleanup after abnormal termination | `evaluations.py` |

Raw audio is not a supported persistent data type.

## Secrets and Credentials Handling

- Credentials come from environment variables or an uncommitted `.env` file.
- `OPENAI_API_KEY` is represented as `SecretStr` and passed only to server-side services.
- The live component receives worker/pipeline metadata, not provider credentials.
- GitHub live evaluations use protected environment secrets.
- No hardcoded credential was found by the repository scan.
- [TODO] Credential rotation and revocation policy is not documented in code or repository policy.

## Reliability and Failure Behavior

- The live page probes worker `/status` with a one-second timeout and reports unavailability.
- Evaluation worker startup has a readiness timeout, bounded logs, terminate-then-kill cleanup, and a disposable database.
- SQLite uses WAL, foreign keys, five-second connection/busy timeouts, and explicit commits.
- No application-level provider retry, backoff, circuit breaker, or alternate-provider fallback is implemented.
- SmallWebRTC default ICE servers are enabled; production TURN/failover topology is not configured here.

## Observability for Integrations

- Pipecat metrics and selected frame events are persisted through `SemanticTimelineObserver`.
- Evaluation results retain duration, failures, observed events, and bounded diagnostics.
- Runtime health reports package versions, CUDA availability, and GPU identity.
- There is no APM, distributed tracing backend, Prometheus exporter, or centralized log sink.

## Evidence

- `.env.example`
- `src/pipecat_voice_studio/config.py`
- `src/pipecat_voice_studio/voice/bot.py`
- `src/pipecat_voice_studio/voice/timeline.py`
- `src/pipecat_voice_studio/evaluations.py`
- `.github/workflows/live-evaluations.yml`

