---
type: workflow
title: Appointments and calendar synchronization
description: Local slot policy, explicit booking gate, Google Calendar event coordination, and incremental status synchronization.
tags:
  - appointments
  - calendar
  - workflows
verified:
  - by: openwiki/0.5.2
    at: 2026-09-23T15:44:25.460Z
sources:
  - id: openwiki-source-4279c878beec15531b6c3efc
    resource: repo://src/pipecat_voice_studio/appointments.py
  - id: openwiki-source-c4d52e224873433af77027a9
    resource: repo://src/pipecat_voice_studio/calendar_worker.py
  - id: openwiki-source-5a01e861aeb5d2e3ed4df7c1
    resource: repo://src/pipecat_voice_studio/integrations/google_calendar.py
  - id: openwiki-source-f249cd1df82e31cdeebfb2a1
    resource: repo://src/pipecat_voice_studio/storage.py
generated: { by: "codex", at: "2026-09-23T15:44:25.460Z" }
---

# Appointments and calendar synchronization

`AppointmentBook` owns local slot policy and is the only application component that writes appointment rows. It can run against the local appointment table alone or coordinate with a configured Google Calendar.

## Slot policy and confirmation gate

Appointment times must include a timezone and are normalized to the configured studio timezone. The local policy accepts 30-minute slots on the half-hour, Monday through Friday, within 09:00–17:00. A confirmed local booking blocks the same start time; `suggest` searches forward for the next three available slots by default.

Writing requires both `confirmed=True` and `flow_node="confirmation"`; the method rejects the write if either condition is missing. It checks local availability again immediately before inserting, and the database’s unique slot constraint handles a race where another booking takes the slot. The appointment flow is responsible for guiding the conversation to its confirmation node; see [Voice session lifecycle](../runtime/session-lifecycle.md) for how that flow is selected.

## Optional Google Calendar coordination

When a Google Calendar adapter is configured, availability requires both the local policy and the external calendar to be free for the interval. Confirmed event creation is ordered to avoid leaving a local booking behind when Google rejects the write: the external event is created first, then the local record. If the local insert fails, the code attempts to cancel the just-created external event. The resulting provider event ID and status are linked to the local appointment.

The calendar worker exits when service-account credentials or the calendar ID are missing. Otherwise, it polls at `PVS_CALENDAR_SYNC_SECONDS`, requests paginated changes using the saved sync token, applies changes to known appointments, and stores the next token. An HTTP 410 causes one full-sync retry without the expired token. Other HTTP errors are saved as sync errors and the polling loop continues on its next interval. External cancellations change the local appointment status to cancelled; other external status updates only change the external-status field.

The committed `tests/test_appointments.py` covers the confirmation-node/affirmation gate, collision recheck, and three-slot suggestions. The file is deleted in the current worktree; this note is based on its committed HEAD version and does not imply it was run.

See [Configuration and local launch](../operations/configuration-and-launch.md) for calendar settings and [SQLite state and semantic timeline](../state/sqlite-and-timeline.md) for appointment persistence.

## Source references

- [`appointments.py`](../../src/pipecat_voice_studio/appointments.py)
- [`integrations/google_calendar.py`](../../src/pipecat_voice_studio/integrations/google_calendar.py)
- [`calendar_worker.py`](../../src/pipecat_voice_studio/calendar_worker.py)
- [`storage.py`](../../src/pipecat_voice_studio/storage.py)
- `tests/test_appointments.py` (committed HEAD; absent from the current worktree)
