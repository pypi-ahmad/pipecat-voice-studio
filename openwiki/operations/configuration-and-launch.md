---
type: operations
title: Configuration and local launch
description: Configure the local settings and integrations, then start the application with its supervised Windows or Linux launcher.
tags:
  - operations
  - configuration
  - launch
verified:
  - by: openwiki/0.5.2
    at: 2026-09-23T15:44:25.460Z
sources:
  - id: openwiki-source-b568152f77a693d346781750
    resource: repo://launch.ps1
  - id: openwiki-source-0f221290ff1ceab94601309b
    resource: repo://launch.sh
  - id: openwiki-source-69c66a68c207eb84ffe43ffc
    resource: repo://src/pipecat_voice_studio/config.py
  - id: openwiki-source-456022411d266f690f48180d
    resource: repo://src/pipecat_voice_studio/integrations/readiness.py
  - id: openwiki-source-b2cd79ad4e2b52728a698ae1
    resource: repo://src/pipecat_voice_studio/voice/bot.py
generated: { by: "codex", at: "2026-09-23T15:44:25.460Z" }
---

# Configuration and local launch

## Configure the environment

`Settings` reads environment variables and a repository-root `.env` file. The checked-in `.env.example` lists the setting names and sample defaults; place local credentials in the untracked `.env` or the process environment, and do not commit secrets. OpenAI credentials are optional while configuring the application, but a voice worker requires `OPENAI_API_KEY` when it starts a pipeline.

Settings cover the database path, worker URL, timezone, model and voice defaults, public telephony URL, outbound-number allowlist, provider credentials, calendar sync interval, and healthcare controls. The default database is `data/pipecat_voice_studio.db`. The public telephony callback origin must use HTTPS; outbound destinations are matched against exact E.164 entries, without wildcard or prefix matching. Calendar polling accepts 15–3600 seconds.

The Integrations dashboard reports whether required settings are present and gives missing variable names. It checks for presence without reading or displaying secret values; a ready status is configuration readiness, not proof that a provider API call will succeed.

## Start with the launcher

On Windows, run `launch.ps1` (or `launch.cmd`). On supported Linux, run `./launch.sh`. The launchers synchronize locked Python dependencies, validate the local setup, start the worker, telephony gateway, calendar worker when configured, and Streamlit, then supervise child processes for shutdown. The management API is optional.

Common options:

- Windows: `-SetupOnly` validates setup without starting services; `-WithApi` also starts the management API.
- Linux: `--setup-only` validates setup without starting services; `--with-api` also starts the management API.
- Both launchers accept worker, Streamlit, gateway, and API port overrides. Defaults are 7860, 8501, 8080, and 8000 respectively.

For an individually managed process setup, the repository README lists direct `uv run` commands for the worker, gateway, optional calendar worker and API, and Streamlit. When using those commands, start the worker, gateway, and UI on endpoints consistent with `PVS_BOT_BASE_URL` and the public provider callbacks. See [Telephony gateway](../runtime/telephony-gateway.md) for callback requirements and [Appointments and calendar synchronization](../workflows/appointments-and-calendar.md) for the calendar flow.

## Readiness and troubleshooting

Use the command center’s runtime diagnostics to check Python and runtime dependencies. Use Integrations to see which provider settings are missing. For pipeline startup failures, first check `OPENAI_API_KEY` and the configured worker endpoint; for telephony callbacks, verify `PVS_PUBLIC_BASE_URL` is an HTTPS URL and that the provider’s callback reaches the gateway.

## Source references

- [`config.py`](../../src/pipecat_voice_studio/config.py) and [`integrations/readiness.py`](../../src/pipecat_voice_studio/integrations/readiness.py)
- [`launch.ps1`](../../launch.ps1) and [`launch.sh`](../../launch.sh)
- [`README.md`](../../README.md) for setup and manual process commands
