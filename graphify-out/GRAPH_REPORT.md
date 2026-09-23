# Graph report: pipecat-voice-studio (2026-09-23)

## Corpus Check
- 75 files · ~59,083 words
- The corpus is large enough for graph structure to add value.
- Unclassified: 13 file(s) not represented in the graph (top: .mmd 5, (none) 4, .example 1)

## Summary
- 583 nodes · 1092 edges · 40 communities (29 shown, 11 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 60 edges (avg confidence: 0.93)
- Token cost: 0 input · 0 output

## Community hubs
- Code Architecture
- Code Architecture
- Code Architecture
- Code Architecture
- Code Architecture
- Code Architecture
- Code Architecture
- Code Architecture
- Code Architecture
- Code Architecture
- Code Architecture
- Code Architecture
- Code Architecture
- Code Architecture
- Code Architecture
- Code Architecture
- Code Architecture
- Code Architecture
- Code Architecture
- Code Architecture
- Code Architecture
- Code Architecture
- Code Architecture
- Code Architecture
- Code Architecture
- Code Architecture
- Code Architecture
- Code Architecture
- Code Architecture
- Code Architecture
- Code Architecture
- Code Architecture
- Code Architecture
- Code Architecture
- Code Architecture
- Code Architecture
- Code Architecture
- Code Architecture

## Most connected nodes
1. `StudioStore` - 69 edges
2. `Settings` - 41 edges
3. `get_settings()` - 25 edges
4. `run_pipeline()` - 22 edges
5. `_now()` - 18 edges
6. `AppointmentBook` - 17 edges
7. `PipelineGraph` - 17 edges
8. `GoogleCalendar` - 17 edges
9. `compilerOptions` - 17 edges
10. `build_business_flow()` - 17 edges

## Inferred connections
- `get_store()` --uses--> `Settings`  [INFERRED]
  src/pipecat_voice_studio/api/app.py → src/pipecat_voice_studio/config.py
- `health()` --uses--> `Settings`  [INFERRED]
  src/pipecat_voice_studio/api/app.py → src/pipecat_voice_studio/config.py
- `list_pipelines()` --uses--> `StudioStore`  [INFERRED]
  src/pipecat_voice_studio/api/app.py → src/pipecat_voice_studio/storage.py
- `get_pipeline()` --uses--> `StudioStore`  [INFERRED]
  src/pipecat_voice_studio/api/app.py → src/pipecat_voice_studio/storage.py
- `create_pipeline()` --uses--> `StudioStore`  [INFERRED]
  src/pipecat_voice_studio/api/app.py → src/pipecat_voice_studio/storage.py

## Import Cycles
- None detected.

## Communities (40 total, 11 thin omitted)

### Community 0 - "Code Architecture"
Cohesion: 0.06
Nodes (60): BaseSettings, field_validator, html, pipecat_serializers_twilio, pipecat_serializers_vonage, pipecat_transports_websocket_fastapi, Request, Response (+52 more)

### Community 1 - "Code Architecture"
Cohesion: 0.05
Nodes (52): LLMContextAggregatorPair, OpenAIResponsesLLMService, pipecat_audio_vad_silero, pipecat_pipeline_pipeline, pipecat_pipeline_worker, pipecat_processors_aggregators_llm_context, pipecat_processors_aggregators_llm_response_universal, pipecat_runner_run (+44 more)

### Community 2 - "Code Architecture"
Cohesion: 0.07
Nodes (43): enum, fastapi, itertools, model_validator, pydantic, create_pipeline(), get_pipeline(), get_store() (+35 more)

### Community 3 - "Code Architecture"
Cohesion: 0.07
Nodes (29): HubSpot, Any, Create or update contacts and optional lead deals in HubSpot., Upsert a contact, then create a deal and note when supplied., Any, Create a short-lived application JWT for one Voice API request., Start an outbound call through the configured answer webhook., Transfer an active Vonage call to a human telephone endpoint. (+21 more)

### Community 4 - "Code Architecture"
Cohesion: 0.09
Nodes (25): functools, pathlib, pydantic_settings, Application configuration. Single source of runtime settings, loaded from…, integration_readiness(), Operator-facing integration readiness without exposing credentials. Evaluates…, Return configuration readiness and a concise missing-setting hint. Only checks…, Validated visual pipeline studio page. Renders the interactive React Flow graph… (+17 more)

### Community 5 - "Code Architecture"
Cohesion: 0.10
Nodes (21): AppointmentBook, datetime, Check local policy and Google Calendar when configured., Create a confirmation-gated local record and synchronized Google event., Local mock calendar with explicit confirmation enforcement., Require aware datetimes and normalize into the studio timezone. Truncating…, Check business hours and collision state., Return the next available half-hour slots. (+13 more)

### Community 6 - "Code Architecture"
Cohesion: 0.10
Nodes (31): dataclasses, EvalResult, EvalScenario, Event, pipecat_evals_harness, pipecat_evals_scenario, Popen, socket (+23 more)

### Community 7 - "Code Architecture"
Cohesion: 0.10
Nodes (16): Any, Path, List graph metadata without exposing credentials (graphs cannot contain any)., Return a session's semantic timeline in sequence order., Persist the terminal status and serializable result for one evaluation., Return recent evaluation runs with decoded result payloads., Small transactional repository around the local studio database., Return recent redacted calls. (+8 more)

### Community 8 - "Code Architecture"
Cohesion: 0.11
Nodes (18): compilerOptions, allowJs, allowSyntheticDefaultImports, esModuleInterop, forceConsistentCasingInFileNames, isolatedModules, jsx, lib (+10 more)

### Community 9 - "Code Architecture"
Cohesion: 0.12
Nodes (9): _now(), Create a pending evaluation record for an allowlisted scenario., Create a redacted telephone-call record., Update a call lifecycle without retaining a full telephone number., Create a redacted operator-visible human handoff record., Persist Google Calendar incremental-sync state., Persist a redacted HubSpot write result., Persist healthcare consent independently from intake content. (+1 more)

### Community 10 - "Code Architecture"
Cohesion: 0.17
Nodes (14): importlib_metadata, platform, _package_version(), Runtime readiness diagnostics shared by the API and UI. Read-only introspection…, Installed framework and CUDA readiness details., Collect installed framework and CUDA readiness information., runtime_readiness(), RuntimeReadiness (+6 more)

### Community 11 - "Code Architecture"
Cohesion: 0.15
Nodes (14): base64, cryptography_hazmat_primitives_ciphers_aead, hashlib, hmac, os, re, InvalidHealthcareKeyError, InvalidMediaTokenError (+6 more)

### Community 12 - "Code Architecture"
Cohesion: 0.14
Nodes (13): cross-env, ref_node_process, rimraf, @types/node, @types/react, @types/react-dom, typescript, vite (+5 more)

### Community 13 - "Code Architecture"
Cohesion: 0.18
Nodes (10): @pipecat-ai/client-js, @pipecat-ai/client-react, @pipecat-ai/small-webrtc-transport, react, @xyflow/react, errorMessage(), GraphData, TranscriptItem (+2 more)

### Community 14 - "Code Architecture"
Cohesion: 0.17
Nodes (6): Delete one session and its cascading timeline., Return the pipeline bound to a provider., Open a configured SQLite connection. Configured for concurrent access across…, Move one human handoff through its provider lifecycle., Attach an external calendar identity to a confirmed local appointment., Append a redacted local audit event.

### Community 15 - "Code Architecture"
Cohesion: 0.24
Nodes (8): collections_abc, contextlib, json, sqlite3, Deterministic appointment availability and mutation policy. Owns local slot…, SQLite persistence for definitions, semantic events, appointments, and…, uuid, zoneinfo

### Community 16 - "Code Architecture"
Cohesion: 0.20
Nodes (9): jwt, RuntimeError, DestinationNotAllowedError, PermissionError, Twilio and Vonage Voice REST operations for calls and handoffs. Implements…, Raised when a selected provider is missing required configuration., Raised when an outbound destination is not explicitly allowlisted., TelephonyNotConfiguredError (+1 more)

### Community 17 - "Code Architecture"
Cohesion: 0.29
Nodes (8): port_available(), PVS_BOT_BASE_URL, PYTHONIOENCODING, PYTHONUTF8, launch.sh script, usage(), valid_port(), wait_for_endpoint()

### Community 18 - "Code Architecture"
Cohesion: 0.28
Nodes (6): datetime, pipecat_flows, Pipecat Flow nodes for the conversational appointment booking pipeline.…, Pipecat Flow routing for business specialists, CRM, and human handoff.…, Consent-first encrypted healthcare intake Flow. Implements a non-diagnostic…, typing

### Community 19 - "Code Architecture"
Cohesion: 0.22
Nodes (9): devDependencies, cross-env, rimraf, @types/node, @types/react, @types/react-dom, typescript, vite (+1 more)

### Community 20 - "Code Architecture"
Cohesion: 0.32
Nodes (6): asyncio, google_auth_transport_requests, google_oauth2, httpx, Incremental Google Calendar synchronization worker. Runs as a background…, Google Calendar adapter using service-account OAuth and the REST API. Provides…

### Community 21 - "Code Architecture"
Cohesion: 0.29
Nodes (5): BaseObserver, FramePushed, Persist bounded semantic conversation events without retaining audio., Map selected Pipecat frames into bounded semantic events., SemanticTimelineObserver

### Community 22 - "Code Architecture"
Cohesion: 0.25
Nodes (6): react-dom, @streamlit/component-v2-lib, roots, StudioComponent(), StudioData, src_pipecat_voice_studio_ui_frontend_src_style

### Community 23 - "Code Architecture"
Cohesion: 0.25
Nodes (8): dependencies, @pipecat-ai/client-js, @pipecat-ai/client-react, @pipecat-ai/small-webrtc-transport, react, react-dom, @streamlit/component-v2-lib, @xyflow/react

### Community 25 - "Code Architecture"
Cohesion: 0.33
Nodes (3): Connection, Store a validated graph as revision one., Create the versioned schema and starter graphs idempotently.

### Community 26 - "Code Architecture"
Cohesion: 0.33
Nodes (3): Begin a session with a frozen graph/model snapshot., Append an ordered semantic event; raw audio is deliberately unsupported., Close a session and record its terminal lifecycle event.

### Community 27 - "Code Architecture"
Cohesion: 0.40
Nodes (4): collections, pipecat_frames_frames, pipecat_observers_base_observer, Semantic Pipecat frame observer; deliberately excludes raw audio. Intercepts…

### Community 28 - "Code Architecture"
Cohesion: 0.40
Nodes (4): CrmConsentRequiredError, PermissionError, Consent-gated HubSpot CRM adapter. Creates or updates HubSpot contacts, sales…, Raised when CRM processing was not explicitly accepted.

### Community 29 - "Code Architecture"
Cohesion: 0.40
Nodes (5): scripts, build, build:frontend:production, clean, typecheck

## Knowledge Gaps
- **55 isolated node(s):** `PVS_BOT_BASE_URL`, `PYTHONUTF8`, `PYTHONIOENCODING`, `pipecat-voice-studio`, `pipecat-voice-studio` (+50 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 304 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **11 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Questions for further review
_Questions to explore with this graph:_

- **Why does `StudioStore` connect `Code Architecture` to `Code Architecture`, `Code Architecture`, `Code Architecture`, `Code Architecture`, `Code Architecture`, `Code Architecture`, `Code Architecture`, `Code Architecture`, `Code Architecture`, `Code Architecture`, `Code Architecture`, `Code Architecture`, `Code Architecture`, `Code Architecture`, `Code Architecture`, `Code Architecture`, `Code Architecture`?**
  _High betweenness centrality (0.236) - this node is a cross-community bridge._
- **Why does `Settings` connect `Code Architecture` to `Code Architecture`, `Code Architecture`, `Code Architecture`, `Code Architecture`, `Code Architecture`, `Code Architecture`?**
  _High betweenness centrality (0.092) - this node is a cross-community bridge._
- **Why does `run_pipeline()` connect `Code Architecture` to `Code Architecture`, `Code Architecture`, `Code Architecture`, `Code Architecture`, `Code Architecture`, `Code Architecture`?**
  _High betweenness centrality (0.044) - this node is a cross-community bridge._
- **Are the 14 inferred relationships involving `StudioStore` (e.g. with `create_pipeline()` and `get_pipeline()`) actually correct?**
  _`StudioStore` has 14 INFERRED edges - model-reasoned connections that need verification._
- **Are the 22 inferred relationships involving `Settings` (e.g. with `get_store()` and `health()`) actually correct?**
  _`Settings` has 22 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `run_pipeline()` (e.g. with `Settings` and `NodeKind`) actually correct?**
  _`run_pipeline()` has 3 INFERRED edges - model-reasoned connections that need verification._
- **What connects `PVS_BOT_BASE_URL`, `PYTHONUTF8`, `PYTHONIOENCODING` to the rest of the system?**
  _55 weakly-connected nodes found - possible documentation gaps or missing edges._
