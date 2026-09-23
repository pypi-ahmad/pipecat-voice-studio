---
type: architecture
title: Telephony gateway
description: Twilio and Vonage webhook verification, call routing to saved pipelines, token-bound media sockets, and redacted call state.
tags:
  - telephony
  - security
  - runtime
verified:
  - by: openwiki/0.5.2
    at: 2026-09-23T15:44:25.460Z
sources:
  - id: openwiki-source-5eab55ff7727edbb0ab9a9ad
    resource: repo://src/pipecat_voice_studio/integrations/telephony.py
  - id: openwiki-source-2976f97350cfeb28db7f0d38
    resource: repo://src/pipecat_voice_studio/security.py
  - id: openwiki-source-f249cd1df82e31cdeebfb2a1
    resource: repo://src/pipecat_voice_studio/storage.py
  - id: openwiki-source-4fd6b7558f7b212a9a588367
    resource: repo://src/pipecat_voice_studio/telephony_gateway.py
generated: { by: "codex", at: "2026-09-23T15:44:25.460Z" }
---

# Telephony gateway

`telephony_gateway.py` is a separate FastAPI application for provider callbacks and media WebSockets. It does not choose a pipeline from callback input: each provider must already be bound to a saved pipeline in `StudioStore`. Verified media is then run through the shared `run_pipeline` worker entry point.

## Provider routes

| Purpose | Twilio | Vonage |
|---|---|---|
| Answer callback | `POST /telephony/twilio/answer` | `GET /telephony/vonage/answer` |
| Call status | `POST /telephony/twilio/status` | `POST /telephony/vonage/events` |
| Audio media | `WS /telephony/twilio/media/{token}` | `WS /telephony/vonage/media/{token}` |
| Human briefing | `POST /telephony/twilio/handoff/{handoff_id}` | `GET /telephony/vonage/handoff/{handoff_id}` |

Twilio form callbacks are checked against `X-Twilio-Signature`, using the configured public callback URL and form parameters. Vonage callbacks require a signed Bearer JWT with the configured API key. Missing provider configuration returns a service-unavailable response; invalid signatures are rejected. Answer handlers also require a provider-to-pipeline binding before they establish media.

## Call and media lifecycle

The answer route records a call if the provider call ID is new, selects the already-bound pipeline, and returns provider connection instructions: TwiML for Twilio or an NCCO for Vonage. It mints a media token that binds the internal call ID to an HMAC signature and timestamp. The media WebSocket validates that token before accepting the connection; tokens expire after 300 seconds by default. Provider-specific audio serializers adapt the incoming stream, and the gateway passes the transport, pipeline ID, store, and call ID to `run_pipeline`.

Status/event callbacks update the local call status and end timestamp for known provider call IDs. Call records retain the provider identifier, direction, status, and only the remote number’s final four digits plus a keyed digest; the full remote phone number is not written to the call table.

## Outbound calls and human handoff

Outbound call creation is implemented by `integrations/telephony.py`, not by the callback routes. Both provider clients require a valid E.164 destination that exactly matches `PVS_OUTBOUND_ALLOWLIST`. A successful provider call then returns through the answer and status routes above.

For a handoff, the integration redirects the provider call to a human leg. The gateway’s handoff route verifies the provider callback, loads the stored handoff briefing, then returns TwiML or an NCCO message for that human leg. The configured public callback origin and provider credentials are described in [Configuration and local launch](../operations/configuration-and-launch.md).

The committed `tests/test_security.py` covers phone redaction/digests, media-token authentication and expiry, and provider signature verification. This file is absent from the current worktree; the test cases were read from committed HEAD and were not run here.

See [Voice session lifecycle](session-lifecycle.md) for worker session setup and [SQLite state and semantic timeline](../state/sqlite-and-timeline.md) for persisted call records.

## Source references

- [`telephony_gateway.py`](../../src/pipecat_voice_studio/telephony_gateway.py)
- [`security.py`](../../src/pipecat_voice_studio/security.py)
- [`integrations/telephony.py`](../../src/pipecat_voice_studio/integrations/telephony.py)
- [`storage.py`](../../src/pipecat_voice_studio/storage.py)
- `tests/test_security.py` (committed HEAD; absent from the current worktree)
