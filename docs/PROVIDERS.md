# Provider setup and operations

The application is local-first: server processes bind to `127.0.0.1`, and an operator-managed HTTPS
tunnel exposes only the telephony callback gateway when telephone calls are enabled.

> [!WARNING]
> Never commit `.env`, service-account JSON, private keys, API tokens, signature secrets, or the
> healthcare encryption key. Do not expose Streamlit or the unauthenticated management API publicly.

## Common setup

1. Run `launch.cmd` on Windows or `./launch.sh` on Linux once to create `.env` and `.venv`.
2. Add the required provider variables from `.env.example`.
3. Restart the launcher after changing configuration.
4. Open **Integrations** and confirm the service reports ready.

The launcher starts the browser worker, callback gateway on port `8080`, Streamlit, and, when Google
is configured, the Calendar synchronization worker. Use `-GatewayPort` or `--gateway-port` to change
the local gateway port.

## Twilio Voice

Configure:

```dotenv
PVS_PUBLIC_BASE_URL=https://your-tunnel.example
PVS_OUTBOUND_ALLOWLIST=+15551234567
TWILIO_ACCOUNT_SID=...
TWILIO_AUTH_TOKEN=...
TWILIO_FROM_NUMBER=+15550000000
TWILIO_HANDOFF_DESTINATION=+15559999999
```

Forward the public HTTPS/WSS origin to local port `8080`. For inbound calls, configure Twilio with:

| Purpose | URL |
|---|---|
| Answer webhook | `{PVS_PUBLIC_BASE_URL}/telephony/twilio/answer` |
| Status webhook | `{PVS_PUBLIC_BASE_URL}/telephony/twilio/status` |

Enable the **Business phone agent** binding for Twilio on the Integrations page. Outbound calls also
require an exact allowlist match and per-call confirmation. Twilio signs every HTTP callback with
`TWILIO_AUTH_TOKEN`; tunnel host/path mismatches therefore produce HTTP 403.

## Vonage Voice

Configure:

```dotenv
PVS_PUBLIC_BASE_URL=https://your-tunnel.example
PVS_OUTBOUND_ALLOWLIST=+15551234567
VONAGE_APPLICATION_ID=...
VONAGE_API_KEY=...
VONAGE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----"
VONAGE_SIGNATURE_SECRET=...
VONAGE_FROM_NUMBER=+15550000000
VONAGE_HANDOFF_DESTINATION=+15559999999
```

Enable signed Voice webhooks in Vonage and configure:

| Purpose | URL |
|---|---|
| Answer webhook | `{PVS_PUBLIC_BASE_URL}/telephony/vonage/answer` |
| Event webhook | `{PVS_PUBLIC_BASE_URL}/telephony/vonage/events` |

Bind Vonage to **Business phone agent**. The application verifies signed-webhook JWTs with the
signature secret and expected API-key claim. Application JWTs for REST calls use the private key.

## Telephone privacy and handoff

- Provider media uses call-bound HMAC tokens that expire after five minutes.
- SQLite retains the final four remote digits and a keyed digest, never the full number.
- Telephone pipelines are cascade-only.
- A warm handoff calls the configured human, plays the stored summary through a signed on-answer
  callback, and then joins the original caller.
- Provider callback and worker logs are under `artifacts/launcher/`.

## Google Calendar

1. Create a Google Cloud service account with Calendar API access.
2. Share the target calendar with the service-account email and grant event-write permission.
3. Set the complete JSON document and calendar ID:

```dotenv
GOOGLE_SERVICE_ACCOUNT_JSON='{"type":"service_account",...}'
GOOGLE_CALENDAR_ID=calendar-id@example.com
PVS_CALENDAR_SYNC_SECONDS=60
```

Use **Google Calendar appointment assistant** in Live session. Availability checks local booking
policy and Google events. After explicit confirmation, Google creation occurs before the local
insert; a failed local insert triggers compensating deletion. The worker stores an incremental sync
token and applies external cancellations. HTTP 410 resets synchronization to a full listing.

Inspect synchronization state without exposing credentials:

```powershell
uv run python -c "from pipecat_voice_studio.config import get_settings; from pipecat_voice_studio.storage import StudioStore; s=get_settings(); d=StudioStore(s.pvs_database_path); d.initialize(); print(d.get_calendar_sync())"
```

Also inspect `artifacts/launcher/calendar.err.log`. A non-empty `last_error` contains only an error
class, not provider response content or credentials.

## HubSpot

Set `HUBSPOT_PRIVATE_APP_TOKEN`, restart, and use the sales specialist in **Business phone agent**.
The assistant must receive explicit CRM consent before writing. The adapter upserts a contact by
email and may create an associated deal and note. Local records retain provider IDs, lead score,
status, failure class, and a redacted phone suffix.

## Simli

Set `SIMLI_API_KEY` and `SIMLI_FACE_ID`, restart, and select **Simli avatar assistant** in Live
session. Simli receives synthesized audio and returns the bot video track through SmallWebRTC.
Avatar nodes are valid only in browser cascade graphs.

## Healthcare intake

The `Settings` code default for `PVS_HEALTHCARE_APPROVED_SERVICES` is empty. The committed
`.env.example` deliberately sets it to `openai` so a copied template can run the seeded healthcare
pipeline after the operator explicitly enables healthcare and supplies an encryption key.

Generate a URL-safe base64 key containing exactly 32 random bytes, store the output securely, and
do not commit or share it:

```powershell
uv run python -c "import base64,secrets; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())"
```

Configure:

```dotenv
PVS_HEALTHCARE_ENABLED=true
PVS_HEALTHCARE_DATA_KEY=generated-value
PVS_HEALTHCARE_APPROVED_SERVICES=openai
```

Healthcare sessions require explicit consent, suppress conversation-turn persistence, and encrypt
the structured intake with AES-256-GCM using the session ID as associated data. The database stores only
consent, review, and escalation metadata. This implementation is not diagnostic software and does
not establish legal or regulatory compliance.

## Troubleshooting checklist

- Provider reports not ready: compare `.env` with the missing-variable list on Integrations and
  restart all launcher-managed processes.
- Telephone HTTP 403: verify the exact HTTPS origin, callback path, and signing secret.
- Call connects without media: confirm the tunnel supports WebSockets and forwards to the
  gateway port rather than the worker port.
- Outbound call denied: use canonical E.164 and an exact `PVS_OUTBOUND_ALLOWLIST` match.
- Google HTTP 403: confirm Calendar API access and calendar sharing for the service account.
- Avatar fails immediately: verify both Simli variables and use a browser cascade graph.
- Healthcare refuses startup: verify enablement, decoded key length, and `openai` approval.
