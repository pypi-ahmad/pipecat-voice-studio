---
type: architecture
title: System architecture overview
description: How the operator UI, graph contract, Pipecat workers, telephony gateway, and SQLite store fit together.
tags:
  - architecture
  - runtime
  - components
verified:
  - by: openwiki/0.5.2
    at: 2026-09-23T15:44:25.460Z
sources:
  - id: openwiki-source-45b9e64d3be6eecf0ba84278
    resource: repo://src/pipecat_voice_studio/api/app.py
  - id: openwiki-source-f249cd1df82e31cdeebfb2a1
    resource: repo://src/pipecat_voice_studio/storage.py
  - id: openwiki-source-4fd6b7558f7b212a9a588367
    resource: repo://src/pipecat_voice_studio/telephony_gateway.py
  - id: openwiki-source-e754a11511799d75d16dbed4
    resource: repo://src/pipecat_voice_studio/ui/components.py
  - id: openwiki-source-58568c623141ad81c50bef91
    resource: repo://src/pipecat_voice_studio/ui/store.py
  - id: openwiki-source-5a29f3d3b9c1c2aaa256fd92
    resource: repo://src/pipecat_voice_studio/ui/streamlit_app.py
  - id: openwiki-source-b2cd79ad4e2b52728a698ae1
    resource: repo://src/pipecat_voice_studio/voice/bot.py
generated: { by: "codex", at: "2026-09-23T15:44:25.460Z" }
---

# System architecture overview

Pipecat Voice Studio is a local operator console around saved voice-pipeline graphs. The Streamlit application provides the dashboards and embeds a React component for graph editing and browser-side WebRTC; FastAPI exposes readiness and pipeline endpoints; Pipecat workers execute the saved graphs; and a shared SQLite store holds pipeline and runtime state.

## Main components

- **Operator UI:** `ui/streamlit_app.py` routes to the command center, Agent Studio, live session, integrations, records, evaluations, and analytics. `ui/components.py` connects Streamlit to the built React bundle for graph visualization and browser audio sessions.
- **Pipeline API and contract:** `api/app.py` reports local readiness and lists, retrieves, or creates pipeline definitions. A submitted definition is compiled before it is saved. The graph model in `graph.py` restricts node kinds and configuration and checks topology; compilation turns it into a runtime chain.
- **Voice worker:** `voice/bot.py` loads the selected saved graph and compiles it again before running. It builds either a combined realtime service or the cascaded STT/context/turn/LLM/TTS path, then attaches the session timeline observer. FlowManager is added for graphs that include supported conversational flows.
- **Telephony gateway:** `telephony_gateway.py` is a separate FastAPI application for Twilio and Vonage callbacks and media WebSockets. After provider verification, it resolves the provider’s bound pipeline and sends media through the same `run_pipeline` entry point used by other transports.
- **Shared state:** `StudioStore` in `storage.py` is the local SQLite repository used by the UI, gateway, and worker processes. Connections enable foreign keys and WAL mode for concurrent readers and serialized writes.

## Runtime paths

For browser sessions, the Streamlit page supplies a pipeline identifier to the React component, which owns the browser audio connection. The worker loads that identifier’s graph, validates and compiles it, records a session, assembles the processors, and observes semantic timeline events. Telephone calls enter through the provider gateway, which verifies the callback, binds the call to the configured pipeline, and creates the telephony transport before invoking the worker. Evaluation runs use the evaluation transport and are described separately in [Isolated evaluation runs](../evaluations/isolated-runs.md).

The graph format and its validation/compiler rules are covered in [Pipeline graph contract and compilation](../pipelines/graph-contract-and-compilation.md). See [Voice session lifecycle](../runtime/session-lifecycle.md) for worker setup and [SQLite state and semantic timeline](../state/sqlite-and-timeline.md) for persistence boundaries.

## Source references

- [`ui/streamlit_app.py`](../../src/pipecat_voice_studio/ui/streamlit_app.py) and [`ui/components.py`](../../src/pipecat_voice_studio/ui/components.py)
- [`api/app.py`](../../src/pipecat_voice_studio/api/app.py) and [`graph.py`](../../src/pipecat_voice_studio/graph.py)
- [`voice/bot.py`](../../src/pipecat_voice_studio/voice/bot.py)
- [`telephony_gateway.py`](../../src/pipecat_voice_studio/telephony_gateway.py)
- [`storage.py`](../../src/pipecat_voice_studio/storage.py)
