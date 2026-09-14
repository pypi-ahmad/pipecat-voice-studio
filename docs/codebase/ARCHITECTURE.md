# Architecture

## Architectural style

- Primary style: local-first, layered application with event-driven Pipecat frame processing.
- Classification: Streamlit/FastAPI are presentation surfaces; validated graph and appointment modules hold policy; `StudioStore` is the persistence boundary; a separate worker builds asynchronous Pipecat pipelines.
- Constraints: graphs are an allowlist rather than executable code; credentials stay server-side;
  media remains in WebRTC/provider WebSockets; SQLite is the shared local store.

## System flow

```text
Browser/telephone -> Pipecat runtime -> model services/Flow tools -> observer/provider adapters -> SQLite/UI
```

1. Streamlit loads active pipeline metadata from `StudioStore`; the live page sends only worker URL and pipeline identity to the component.
2. The React client posts a SmallWebRTC session request to the worker and connects the browser media stream.
3. `voice.bot.bot()` reloads and validates the stored graph, compiles it, creates a frozen session snapshot, and selects realtime or cascaded construction.
4. Realtime uses the combined OpenAI service. Cascade/eval wires STT, context/turn handling,
   Responses LLM, optional appointment/business/healthcare Flow, TTS, and optional Simli video.
5. The telephony gateway authenticates provider callbacks, resolves the bound graph, and supplies a
   serializer-backed FastAPI WebSocket transport to the same pipeline runner.
6. Appointment, CRM, handoff, and healthcare tools enforce confirmation/consent/governance before
   crossing provider or persistence boundaries.
7. `SemanticTimelineObserver` stores selected lifecycle, turn, tool, flow, and metric events;
   healthcare disables turn persistence. The UI reads records and metadata from SQLite.

Evaluations follow a separate branch: copy one graph into a temporary database, launch a localhost worker subprocess with `EvalTransport`, execute an allowlisted scenario, persist the bounded result in the main store, and delete temporary resources.

## Layer and module responsibilities

| Module | Owns | Must not own | Evidence |
|---|---|---|---|
| Streamlit pages and React component | Operator UI and browser media controls | Provider secrets | `ui/`; `ui/frontend/src/StudioComponent.tsx` |
| `graph.py` and `seeds.py` | Pipeline contract, topology checks, starter graphs | Dynamic imports or arbitrary code | source files |
| `voice/bot.py` | Runtime service assembly and runner callbacks | Pipeline persistence schema | source file |
| `voice/appointment_flow.py` | Pipecat Flow nodes and function handlers | General database access | source file |
| `voice/business_flow.py` | Specialist routing, CRM consent, and warm handoff | Healthcare intake | source file |
| `voice/healthcare_flow.py` | Consent-first structured intake and escalation state | Diagnosis or business tools | source file |
| `voice/timeline.py` | Frame-to-semantic-event adaptation | Raw audio retention | source file |
| `storage.py` / `appointments.py` | Transactions and booking invariants | HTTP/UI concerns | source files |
| `api/app.py` | Health and pipeline HTTP contracts | Independent business logic | source file |
| `telephony_gateway.py` | Signed provider callbacks and media transports | Operator management API | source file |
| `integrations/` | External REST/JWT/OAuth adapters | UI state | source directory |
| `calendar_worker.py` | Incremental Google synchronization | Interactive voice lifecycle | source file |
| `security.py` | Cryptographic and redaction primitives | Provider workflow policy | source file |
| `evaluations.py` | Isolated scenario execution | Automatic production scheduling | source file |

## Reused patterns

| Pattern | Where | Purpose |
|---|---|---|
| Repository | `StudioStore` | Centralize SQLite schema and transactions |
| Adapter/observer | `SemanticTimelineObserver` | Convert Pipecat frames into durable domain events |
| Schema allowlist | `PipelineGraph`, `GraphNode` | Reject executable or credential-bearing graph content |
| Compiler | `compile_graph()` | Convert a validated graph into a deterministic runtime recipe |
| Dependency injection | FastAPI `Depends`; constructor-injected stores | Replace boundaries in tests and centralize setup |
| Process isolation | `run_evaluation()` | Keep fixtures and worker failures outside the main database/process |
| Compensating transaction | Google-backed appointment creation | Delete external event if local insertion fails |
| Consent/policy gate | CRM and healthcare Flow functions | Prevent external or sensitive writes before explicit approval |

## Initialization order

Settings are loaded first. Each surface initializes `StudioStore`, which creates/version-checks
schema v2, migrates v1 with a backup, and inserts any missing built-in graphs by name. The launcher
starts the browser worker and callback gateway, conditionally starts Calendar sync, then starts the
optional API and foreground Streamlit. A voice runtime loads an active graph and creates the session
before model services process frames. Frontend assets must already be built.

## Known architectural risks

- Streamlit, API, worker, and evaluation subprocesses share a local SQLite file; WAL and busy timeout help, but this is not a distributed persistence design.
- The management API has no authentication or authorization.
- Model-provider reliability is delegated to Pipecat/provider clients; this repository defines no circuit breaker or application retry policy.
- Callback gateway exposure depends on external tunnel/TLS configuration and has no app-level rate limiter.
- Healthcare encryption has no built-in key rotation or regulated retention workflow.
- Runtime graph compilation supports one linear frame path. Business specialist routing is implemented
  as deterministic Pipecat Flow node transitions rather than arbitrary executable graph branches.

## Evidence

- `src/pipecat_voice_studio/graph.py`
- `src/pipecat_voice_studio/voice/bot.py`
- `src/pipecat_voice_studio/voice/timeline.py`
- `src/pipecat_voice_studio/evaluations.py`
- `src/pipecat_voice_studio/storage.py`
- `src/pipecat_voice_studio/ui/frontend/src/StudioComponent.tsx`
