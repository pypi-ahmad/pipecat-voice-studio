---
type: architecture
title: Pipeline graph contract and compilation
description: The graph schema, mode and topology constraints, compiler linearity check, and validation boundaries before execution.
tags:
  - pipelines
  - validation
  - compiler
verified:
  - by: openwiki/0.5.2
    at: 2026-09-23T15:44:25.460Z
sources:
  - id: openwiki-source-45b9e64d3be6eecf0ba84278
    resource: repo://src/pipecat_voice_studio/api/app.py
  - id: openwiki-source-7100843083727bbc177f5b29
    resource: repo://src/pipecat_voice_studio/graph.py
  - id: openwiki-source-4a2d8638cd3e258250970f5c
    resource: repo://src/pipecat_voice_studio/ui/app_pages/agent_studio.py
  - id: openwiki-source-b2cd79ad4e2b52728a698ae1
    resource: repo://src/pipecat_voice_studio/voice/bot.py
generated: { by: "codex", at: "2026-09-23T15:44:25.460Z" }
---

# Pipeline graph contract and compilation

Pipeline definitions are operator-editable data, but only the node implementations and settings explicitly recognized by the application can pass the graph contract. `PipelineGraph` validates the serialized graph; `compile_graph` then produces the deterministic recipe consumed by the voice worker.

## Schema and mode rules

The graph consists of a name, one of three modes (`realtime`, `cascade`, or `eval`), nodes, and directed edges. Node kinds are a closed `NodeKind` enum. Node configuration accepts only `prompt`, `voice`, `speed`, `language`, and `vad_eagerness`; extra model fields are forbidden. Node IDs have a bounded lowercase pattern and labels must be non-empty.

Every graph must include the operational nodes for timeline, metrics, and persistence, plus exactly one transport appropriate to its mode. Realtime graphs use the combined realtime service. Cascade and evaluation graphs require the STT, context, turn-detection, LLM, and TTS stack; evaluation mode requires the evaluation transport. Telephony is cascade-only, and an avatar is limited to browser cascade graphs. Healthcare graphs cannot combine healthcare intake with CRM, calendar, appointment, or multi-agent nodes.

## Topology and compilation

Edges must refer to existing nodes, node IDs must be unique, and self-edges are rejected. The executable path is formed from `PATH_KINDS`; the operational triad is deliberately outside that frame path. Validation checks that this executable path is acyclic and connected.

Connectivity and acyclicity do not guarantee a linear chain. `compile_graph` walks the path and rejects any node with more than one outgoing path edge, and also rejects an ordering that does not visit every path node. A successful compilation returns the mode, ordered node kinds, collected safe settings, and transport label (`webrtc`, `telephony`, or `eval`).

## Where the contract is applied

The management API compiles a submitted graph before saving it. Agent Studio validates and compiles a clone before persistence. The worker reloads the stored graph and compiles it again when starting a session, so persisted data is not treated as a substitute for runtime validation.

The committed `tests/test_graph.py` exercises seeded-graph compilation, unknown-config and cycle rejection, and branch rejection. This file is absent from the current worktree; those cases were read from its committed HEAD version and were not run here.

For how the compiled recipe becomes Pipecat processors, see [Voice session lifecycle](../runtime/session-lifecycle.md). The broader component map is in [System architecture overview](../architecture/system-overview.md).

## Source references

- [`graph.py`](../../src/pipecat_voice_studio/graph.py) and [`seeds.py`](../../src/pipecat_voice_studio/seeds.py)
- [`api/app.py`](../../src/pipecat_voice_studio/api/app.py)
- [`ui/app_pages/agent_studio.py`](../../src/pipecat_voice_studio/ui/app_pages/agent_studio.py)
- [`voice/bot.py`](../../src/pipecat_voice_studio/voice/bot.py)
- `tests/test_graph.py` (committed HEAD; absent from the current worktree)
