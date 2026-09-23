---
type: workflow
title: Business and healthcare workflows
description: Business routing, consent-gated CRM and phone handoff alongside the separately constrained healthcare-intake path.
tags:
  - workflows
  - consent
  - privacy
verified:
  - by: openwiki/0.5.2
    at: 2026-09-23T15:44:25.460Z
sources:
  - id: openwiki-source-7100843083727bbc177f5b29
    resource: repo://src/pipecat_voice_studio/graph.py
  - id: openwiki-source-d9b7d05d9da300920ad15edc
    resource: repo://src/pipecat_voice_studio/integrations/hubspot.py
  - id: openwiki-source-2976f97350cfeb28db7f0d38
    resource: repo://src/pipecat_voice_studio/security.py
  - id: openwiki-source-b2cd79ad4e2b52728a698ae1
    resource: repo://src/pipecat_voice_studio/voice/bot.py
  - id: openwiki-source-543e967798705c8b543ca4a7
    resource: repo://src/pipecat_voice_studio/voice/business_flow.py
  - id: openwiki-source-3c52e52240a27601da34f4f0
    resource: repo://src/pipecat_voice_studio/voice/healthcare_flow.py
generated: { by: "codex", at: "2026-09-23T15:44:25.460Z" }
---

# Business and healthcare workflows

The worker chooses an initial flow from the validated graph’s node kinds. Business routing and healthcare intake are separate flows with different integrations and data-handling constraints; graph validation prevents a healthcare graph from combining its intake node with CRM, calendar, appointments, or multi-agent routing.

## Business routing, CRM, and handoff

The receptionist routes to one of four allowlisted departments: billing, technical, sales, or appointments. HubSpot lead creation is available only in the sales specialist when configured. Both the business flow and the HubSpot adapter require explicit consent before transmitting customer information; absent HubSpot configuration is reported as unavailable. CRM outcomes are recorded locally with status and redacted phone information.

Human transfer is available only when the session is attached to a telephone call and a provider-specific handoff destination is configured. The flow saves a handoff record with a redacted destination and briefing, redirects the active Twilio or Vonage call, then marks the handoff transferred or failed.

## Healthcare intake

Healthcare graphs require the feature toggle, an operator-provided encryption key, and `openai` in the approved-service list before the flow is initialized. The flow begins with an explicit consent disclosure. A declined consent is recorded with the policy version and ends intake without advancing to the structured health questions.

After consent, the flow collects only chief concern, symptoms, medications, allergies, and an emergency-sign indicator. It does not diagnose. The structured payload is encrypted with AES-256-GCM using the session ID as authenticated data before storage; the stored intake includes ciphertext, nonce, review/escalation status, and an audit event. Emergency signs set `escalation-required` and direct the caller to emergency services; other intakes are marked for human review. Healthcare sessions also suppress conversation-turn persistence in the semantic timeline.

These controls describe application behavior; they do not establish medical-device status, regulatory compliance, or a clinical diagnosis capability. For persistence details, see [SQLite state and semantic timeline](../state/sqlite-and-timeline.md). Appointment and calendar behavior is documented in [Appointments and calendar synchronization](appointments-and-calendar.md).

## Source references

- [`voice/business_flow.py`](../../src/pipecat_voice_studio/voice/business_flow.py)
- [`integrations/hubspot.py`](../../src/pipecat_voice_studio/integrations/hubspot.py)
- [`voice/healthcare_flow.py`](../../src/pipecat_voice_studio/voice/healthcare_flow.py)
- [`security.py`](../../src/pipecat_voice_studio/security.py)
- [`graph.py`](../../src/pipecat_voice_studio/graph.py) and [`voice/bot.py`](../../src/pipecat_voice_studio/voice/bot.py)
