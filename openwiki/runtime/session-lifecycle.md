---
type: workflow
title: Voice session lifecycle
description: How a stored pipeline becomes a transport-bound Pipecat worker, records session state, and finalizes after execution.
tags:
  - runtime
  - sessions
  - workers
verified:
  - by: openwiki/0.5.2
    at: 2026-09-23T15:44:25.460Z
sources:
  - id: openwiki-source-b2cd79ad4e2b52728a698ae1
    resource: repo://src/pipecat_voice_studio/voice/bot.py
  - id: openwiki-source-34422fd710e16da263822a2d
    resource: repo://src/pipecat_voice_studio/voice/timeline.py
generated: { by: "codex", at: "2026-09-23T15:44:25.460Z" }
---

# Voice session lifecycle

`voice/bot.py` is the common assembly point for a stored pipeline once a Pipecat transport is available. The standard runner reads `pipeline_id` from its runner body, reloads and recompiles the graph, and checks that an evaluation runner is paired with an evaluation-mode graph. Browser and evaluation transports are created through Pipecat’s runner; the telephony gateway creates its WebSocket transport separately and calls the same `run_pipeline` function.

## Session setup

`run_pipeline` loads the graph again and compiles it into an ordered recipe. Before processor construction it creates a session record with a graph snapshot and the configured model names, marks healthcare graphs as sensitive, and records `transport.connecting`. If invoked for a telephone call, it also links that call to the new session.

Processor assembly follows the graph mode:

- **Realtime:** one combined realtime service is placed between the transport input/output and the context aggregators.
- **Cascade and evaluation:** the worker builds the modular STT, context, turn detection, LLM, and TTS processors; optional graph nodes add their corresponding services.

The worker wraps the processor chain in `PipelineWorker`, enables pipeline and usage metrics, and attaches `SemanticTimelineObserver`. FlowManager is initialized only for graphs with supported appointment, business, handoff, multi-agent, or healthcare flow nodes. The flow selected depends on those node kinds; Google Calendar is attached to the appointment flow when its credentials and calendar ID are configured.

## Execution and finalization

After flow setup, the worker records `transport.connected` and runs through `WorkerRunner`. If that execution raises, the session is marked failed and the associated telephone call is marked failed; on normal return, the session and call are marked completed. The explicit success/failure finalizer surrounds the runner phase; graph loading, processor construction, and flow initialization happen before that `try` block.

The timeline observer persists selected semantic events rather than audio. When the graph contains the healthcare node, the worker disables conversation-turn persistence for that observer. See [SQLite state and semantic timeline](../state/sqlite-and-timeline.md) for which events are stored and [Telephony gateway](telephony-gateway.md) for provider call setup.

## Source references

- [`voice/bot.py`](../../src/pipecat_voice_studio/voice/bot.py)
- [`voice/timeline.py`](../../src/pipecat_voice_studio/voice/timeline.py)
- [`storage.py`](../../src/pipecat_voice_studio/storage.py)
