# Architecture

## Architectural Style

- Primary style: local-first, layered application with event-driven Pipecat frame processing.
- Classification: Streamlit/FastAPI are presentation surfaces; validated graph and appointment modules hold policy; `StudioStore` is the persistence boundary; a separate worker builds asynchronous Pipecat pipelines.
- Constraints: graphs are an allowlist rather than executable code; credentials stay server-side; realtime media remains in WebRTC; SQLite is the shared local store.

## System Flow

```text
Streamlit/React -> Pipecat runner -> voice worker -> model services/Flow tools -> semantic observer -> SQLite/UI
```

1. Streamlit loads active pipeline metadata from `StudioStore`; the live page sends only worker URL and pipeline identity to the component.
2. The React client posts a SmallWebRTC session request to the worker and connects the browser media stream.
3. `voice.bot.bot()` reloads and validates the stored graph, compiles it, creates a frozen session snapshot, and selects realtime or cascaded construction.
4. Realtime mode uses the combined OpenAI realtime service. Cascade/eval mode wires STT, context/turn handling, Responses LLM, appointment Flow, and TTS.
5. Appointment tools enforce confirmation and scheduling policy before writing an appointment.
6. `SemanticTimelineObserver` stores selected lifecycle, turn, tool, flow, and metric events; the UI reads records and analytics from SQLite.

Evaluations follow a separate branch: copy one graph into a temporary database, launch a localhost worker subprocess with `EvalTransport`, execute an allowlisted scenario, persist the bounded result in the main store, and delete temporary resources.

## Layer and Module Responsibilities

| Module | Owns | Must not own | Evidence |
|---|---|---|---|
| Streamlit pages and React component | Operator UI and browser media controls | Provider secrets | `ui/`; `ui/frontend/src/StudioComponent.tsx` |
| `graph.py` and `seeds.py` | Pipeline contract, topology checks, starter graphs | Dynamic imports or arbitrary code | source files |
| `voice/bot.py` | Runtime service assembly and runner callbacks | Pipeline persistence schema | source file |
| `voice/appointment_flow.py` | Pipecat Flow nodes and function handlers | General database access | source file |
| `voice/timeline.py` | Frame-to-semantic-event adaptation | Raw audio retention | source file |
| `storage.py` / `appointments.py` | Transactions and booking invariants | HTTP/UI concerns | source files |
| `api/app.py` | Health and pipeline HTTP contracts | Independent business logic | source file |
| `evaluations.py` | Isolated scenario execution | Automatic production scheduling | source file |

## Reused Patterns

| Pattern | Where | Purpose |
|---|---|---|
| Repository | `StudioStore` | Centralize SQLite schema and transactions |
| Adapter/observer | `SemanticTimelineObserver` | Convert Pipecat frames into durable domain events |
| Schema allowlist | `PipelineGraph`, `GraphNode` | Reject executable or credential-bearing graph content |
| Compiler | `compile_graph()` | Convert a validated graph into a deterministic runtime recipe |
| Dependency injection | FastAPI `Depends`; constructor-injected stores | Replace boundaries in tests and centralize setup |
| Process isolation | `run_evaluation()` | Keep fixtures and worker failures outside the main database/process |

## Initialization Order

Settings are loaded first. Each surface initializes `StudioStore`, which creates/version-checks the schema and seeds graphs when empty. The worker then loads an active graph and creates the session before model services process frames. Frontend assets must already be built for the Streamlit custom component.

## Known Architectural Risks

- Streamlit, API, worker, and evaluation subprocesses share a local SQLite file; WAL and busy timeout help, but this is not a distributed persistence design.
- The management API has no authentication or authorization.
- Model-provider reliability is delegated to Pipecat/provider clients; this repository defines no circuit breaker or application retry policy.
- Runtime graph compilation supports one linear executable path, so arbitrary graph branching and multi-agent routing are not implemented.

## Evidence

- `src/pipecat_voice_studio/graph.py`
- `src/pipecat_voice_studio/voice/bot.py`
- `src/pipecat_voice_studio/voice/timeline.py`
- `src/pipecat_voice_studio/evaluations.py`
- `src/pipecat_voice_studio/storage.py`
- `src/pipecat_voice_studio/ui/frontend/src/StudioComponent.tsx`

