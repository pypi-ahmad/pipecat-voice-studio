---
type: guide
title: OpenWiki quickstart
description: A starting point for running Pipecat Voice Studio and navigating its architecture, workflows, operations, and test references.
tags:
  - quickstart
  - navigation
  - onboarding
verified:
  - by: openwiki/0.5.2
    at: 2026-09-23T15:57:58.894Z
sources:
  - id: openwiki-source-6d4b4e707b8d60b6ccfa3425
    resource: repo://.github/workflows/openwiki-update.yml
  - id: openwiki-source-23775c3de52f3ab95a13cb8b
    resource: repo://README.md
generated: { by: "codex", at: "2026-09-23T15:57:58.894Z" }
---

# OpenWiki quickstart

## Run the application

For local setup, use `launch.ps1` on Windows or `launch.sh` on supported Linux. Add `-WithApi` or `--with-api` to start the optional management API. Configure local credentials and settings through the environment or repository-root `.env`; live voice pipelines require `OPENAI_API_KEY`. The detailed setup, ports, and provider configuration are in [Configuration and local launch](operations/configuration-and-launch.md), with user-facing steps in [`docs/HOW_TO_USE.md`](../docs/HOW_TO_USE.md).

## Find the relevant guide

| If you need to understand… | Start here |
|---|---|
| How the UI, graph API, workers, gateway, and database fit together | [System architecture overview](architecture/system-overview.md) |
| Which pipeline definitions are accepted and how they compile | [Pipeline graph contract and compilation](pipelines/graph-contract-and-compilation.md) |
| How a stored graph becomes a running session | [Voice session lifecycle](runtime/session-lifecycle.md) |
| Provider webhooks, telephone media, and handoff | [Telephony gateway](runtime/telephony-gateway.md) |
| SQLite entities, event ordering, and data-retention boundaries | [SQLite state and semantic timeline](state/sqlite-and-timeline.md) |
| Booking rules and Google Calendar synchronization | [Appointments and calendar synchronization](workflows/appointments-and-calendar.md) |
| Business routing, consent-gated CRM, and healthcare intake | [Business and healthcare workflows](workflows/business-and-healthcare.md) |
| Scenario-based evaluation isolation and result storage | [Isolated evaluation runs](evaluations/isolated-runs.md) |
| Settings, launch modes, readiness, and local operations | [Configuration and local launch](operations/configuration-and-launch.md) |
| What tests cover and which checkout they came from | [Test contracts and current checkout caveat](testing/test-contracts.md) |

## Test-reference caveat

The 11 test modules and `tests/__init__.py` (12 deleted paths total) are absent from the current worktree. Test-specific notes in this wiki use their committed `HEAD` versions as read-only references; no test files were restored and no test results are claimed. The test page distinguishes those references from source code that is present in this checkout.

## Keeping OpenWiki current

The repository’s OpenWiki update workflow supports manual dispatch and a daily scheduled run. It generates an update and opens a pull request; see [`.github/workflows/openwiki-update.yml`](../.github/workflows/openwiki-update.yml). The local README and [`docs/HOW_TO_USE.md`](../docs/HOW_TO_USE.md) remain the entry points for complete installation and operation instructions.

## Source references

- [`README.md`](../README.md)
- [`docs/HOW_TO_USE.md`](../docs/HOW_TO_USE.md)
- [OpenWiki update workflow](../.github/workflows/openwiki-update.yml)
