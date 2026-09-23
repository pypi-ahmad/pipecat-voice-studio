---
type: architecture
title: SQLite state and semantic timeline
description: The local SQLite schema, session snapshots, ordered semantic events, and retention boundaries across application records.
tags:
  - persistence
  - sqlite
  - privacy
verified:
  - by: openwiki/0.5.2
    at: 2026-09-23T15:44:25.460Z
sources:
  - id: openwiki-source-f249cd1df82e31cdeebfb2a1
    resource: repo://src/pipecat_voice_studio/storage.py
  - id: openwiki-source-34422fd710e16da263822a2d
    resource: repo://src/pipecat_voice_studio/voice/timeline.py
generated: { by: "codex", at: "2026-09-23T15:44:25.460Z" }
---

# SQLite state and semantic timeline

`StudioStore` is the shared local repository for the Streamlit UI, API, gateway, and voice workers. It initializes a versioned SQLite schema and built-in pipeline graphs. Connections enable foreign keys and WAL mode, allowing concurrent readers with SQLite’s single-writer behavior.

## Stored state

The schema groups state by lifecycle:

- **Pipelines:** serialized graph definitions, revision, active state, and timestamps.
- **Sessions and timeline:** session status plus a frozen graph/model snapshot; associated events have per-session sequence numbers and JSON payloads.
- **Appointments and integrations:** appointments and external calendar state, CRM outcomes, provider-to-pipeline bindings, telephone calls, and handoffs.
- **Evaluation and audit:** evaluation scenario/result records and append-only operator audit events.
- **Healthcare:** consent metadata is stored separately from intake ciphertext and nonce; the metadata listing does not select the protected ciphertext fields.

Schema initialization seeds missing built-in graphs. The current schema migration from version 1 to version 2 first makes a `.v1.bak` database copy; unsupported versions fail initialization instead of proceeding with writes.

## Session timeline

`create_session` stores the graph and model names used for that run, records `session.started`, and marks whether the session is sensitive. `append_event` assigns an increasing sequence within the session, serializes the payload, and explicitly rejects the `audio.raw` event type. Events are read back in sequence order. Deleting a session cascades its timeline; appointments, calls, handoffs, and CRM rows retain their own records with nullable session references, while healthcare consent and intake rows cascade with the session.

`SemanticTimelineObserver` maps selected Pipecat frames into semantic events: finalized user/assistant turns, interruptions, tool request/start/complete/cancel states, and metrics. It does not persist audio frames. The worker disables conversation-turn persistence for healthcare sessions, while keeping the session marked sensitive.

## Related records and privacy boundaries

Evaluation runs keep their status and JSON result in the main store. Call records keep the remote number’s final four digits and a keyed digest rather than the full phone number. Healthcare intake is supplied to `StudioStore` as ciphertext and nonce after encryption by the caller; the UI-facing healthcare metadata query returns consent, status, and escalation fields without selecting the ciphertext or nonce.

The committed storage tests cover seeded graphs, ordered events and raw-audio rejection, event deletion, evaluation results, and extended integration/audit records. Their files are deleted in the current worktree; these references use the committed HEAD versions and do not indicate that those tests were run here.

For how the worker writes these records, see [Voice session lifecycle](../runtime/session-lifecycle.md). Telephony-specific call handling is in [Telephony gateway](../runtime/telephony-gateway.md).

## Source references

- [`storage.py`](../../src/pipecat_voice_studio/storage.py)
- [`voice/timeline.py`](../../src/pipecat_voice_studio/voice/timeline.py)
- `tests/test_storage.py` and `tests/test_extended_storage.py` (committed HEAD; absent from the current worktree)
