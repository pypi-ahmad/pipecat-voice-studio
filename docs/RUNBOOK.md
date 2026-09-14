# Runbook

This runbook covers day-to-day operations, service startup and shutdown procedures, log locations, health verification, and troubleshooting guides for Pipecat Voice Studio.

## Service overview and port allocation

Pipecat Voice Studio consists of multiple processes coordinating on localhost. By default, processes bind to the following loopback ports:

| Service | Default port | Protocol | Entry point |
|---|---|---|---|
| Pipecat voice worker | `7860` | HTTP / WebRTC / RTVI | [voice/bot.py](file:///D:/AI/Github/pipecat-voice-studio/src/pipecat_voice_studio/voice/bot.py) |
| Streamlit control plane | `8501` | HTTP / WebSocket | [ui/streamlit_app.py](file:///D:/AI/Github/pipecat-voice-studio/src/pipecat_voice_studio/ui/streamlit_app.py) |
| Telephony gateway | `8080` | HTTP / WebSocket | [telephony_gateway.py](file:///D:/AI/Github/pipecat-voice-studio/src/pipecat_voice_studio/telephony_gateway.py) |
| Management API (optional) | `8000` | HTTP | [api/app.py](file:///D:/AI/Github/pipecat-voice-studio/src/pipecat_voice_studio/api/app.py) |
| Calendar worker (optional) | None | Periodic polling loop | [calendar_worker.py](file:///D:/AI/Github/pipecat-voice-studio/src/pipecat_voice_studio/calendar_worker.py) |

## Starting and stopping services

### Using launcher scripts

The recommended method to run Pipecat Voice Studio is via the root launcher scripts, which validate prerequisites, manage dependencies, supervise child processes, and perform teardown on exit.

#### Windows

From Command Prompt:
```cmd
launch.cmd
```

From PowerShell:
```powershell
.\launch.ps1
```

PowerShell options:
- Run with the optional management API enabled:
  ```powershell
  .\launch.ps1 -WithApi
  ```
- Validate dependencies and setup without starting services:
  ```powershell
  .\launch.ps1 -SetupOnly
  ```
- Specify custom ports:
  ```powershell
  .\launch.ps1 -WorkerPort 7861 -StreamlitPort 8502 -GatewayPort 8081 -ApiPort 8001
  ```

#### Linux

On Linux x86_64:
```bash
chmod +x launch.sh
./launch.sh
```

Linux options:
- Run with the optional management API enabled:
  ```bash
  ./launch.sh --with-api
  ```
- Validate dependencies and setup without starting services:
  ```bash
  ./launch.sh --setup-only
  ```
- Specify custom ports:
  ```bash
  ./launch.sh --worker-port 7861 --streamlit-port 8502 --gateway-port 8081 --api-port 8001
  ```

### Manual startup sequence

If running without the launcher scripts, execute each process in a separate terminal window:

1. **Verify dependencies and lockfile**:
   ```bash
   uv sync --frozen
   ```

2. **Start the Pipecat audio worker**:
   ```bash
   uv run python -m pipecat_voice_studio.voice.bot --host 127.0.0.1 --port 7860 --allowed-origins http://localhost:8501 http://127.0.0.1:8501
   ```

3. **Start the telephony gateway**:
   ```bash
   uv run uvicorn pipecat_voice_studio.telephony_gateway:app --host 127.0.0.1 --port 8080 --proxy-headers --forwarded-allow-ips 127.0.0.1
   ```

4. **Start the calendar worker (optional)**:
   ```bash
   uv run python -m pipecat_voice_studio.calendar_worker
   ```

5. **Start the management API (optional)**:
   ```bash
   uv run uvicorn pipecat_voice_studio.api.app:app --host 127.0.0.1 --port 8000
   ```

6. **Start Streamlit**:
   ```bash
   uv run streamlit run src/pipecat_voice_studio/ui/streamlit_app.py --server.address 127.0.0.1 --server.port 8501
   ```

### Stopping services

#### Clean shutdown

When using `launch.ps1` or `launch.sh`, press `Ctrl+C` in the terminal hosting the script.
- On Windows, `launch.ps1` executes its `finally` block, running `Stop-OwnedProcess` (`taskkill /PID <pid> /T /F`) to terminate the entire process tree of each background service.
- On Linux, `launch.sh` executes its `cleanup` trap (`trap cleanup EXIT INT TERM`) to kill background process group IDs.

#### Terminating orphaned processes

If a launcher is terminated unexpectedly and ports remain bound:

On Windows (PowerShell):
```powershell
# Identify processes bound to default ports
Get-NetTCPConnection -LocalPort 7860, 8501, 8080, 8000 -State Listen -ErrorAction SilentlyContinue |
  Select-Object LocalPort, OwningProcess |
  ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }
```

On Linux (Bash):
```bash
# Terminate processes listening on default ports
fuser -k 7860/tcp 8501/tcp 8080/tcp 8000/tcp
```

## Logs locations and inspection

### Launcher logs

When running via `launch.ps1` or `launch.sh`, background process output is redirected to disk under [artifacts/launcher/](file:///D:/AI/Github/pipecat-voice-studio/artifacts/launcher):

| File | Source | Description |
|---|---|---|
| `artifacts/launcher/worker.out.log` | Pipecat worker | Standard output, WebRTC connection logs, session startup |
| `artifacts/launcher/worker.err.log` | Pipecat worker | Uncaught Python exceptions, pipeline error traces |
| `artifacts/launcher/gateway.out.log` | Telephony gateway | Uvicorn access logs for Twilio and Vonage requests |
| `artifacts/launcher/gateway.err.log` | Telephony gateway | Signature verification failures, webhook errors |
| `artifacts/launcher/api.out.log` | Management API | Uvicorn access logs for API endpoints |
| `artifacts/launcher/api.err.log` | Management API | API validation exceptions and error traces |
| `artifacts/launcher/calendar.out.log` | Calendar worker | Google Calendar polling cycles and sync tokens |
| `artifacts/launcher/calendar.err.log` | Calendar worker | Google API HTTP errors and tracebacks |

### Foreground logs

- **Streamlit**: Streamlit logs output directly to the foreground terminal running the launcher or `streamlit run`.
- **Browser console**: Open browser Developer Tools (`F12`) to inspect client-side WebRTC ICE negotiation, audio permissions, and SmallWebRTC transport state.

### Audit logs

Administrative actions, healthcare intake submissions, and session security events are recorded in the SQLite database table `audit_events`. Query recent audit records using SQLite CLI:

```bash
sqlite3 data/pipecat_voice_studio.db "SELECT id, action, resource_type, outcome, created_at FROM audit_events ORDER BY id DESC LIMIT 20;"
```

## Health check procedures

### Pipecat worker liveness

Verify the audio worker is running and accepting connections:

```bash
curl -s http://127.0.0.1:7860/status
```
Expected response:
```json
{"status": "ready"}
```

### Telephony gateway liveness

Verify the callback gateway is responsive:

```bash
curl -s http://127.0.0.1:8080/health
```
Expected response:
```json
{"status": "ok"}
```

### Management API liveness

When running with `-WithApi`, check application diagnostic status:

```bash
curl -s http://127.0.0.1:8000/health
```
Expected response includes application name, environment, Python, Pipecat, Torch, and CUDA readiness.

## Common failures and troubleshooting

### 1. Port conflict during startup

**Error message**:
```text
Port 7860 is already in use. Stop the existing service or select another port.
```
**Cause**: Another process or a previous orphaned instance of the worker, Streamlit, gateway, or API is already listening on the requested port.  
**Resolution**:
1. Check listening processes using the port lookup commands in the "Terminating orphaned processes" section.
2. Stop the conflicting process or launch with non-conflicting port parameters (e.g. `.\launch.ps1 -WorkerPort 7861 -StreamlitPort 8502`).

### 2. Missing frontend build assets

**Error message**:
```text
Frontend assets are missing. Install Node.js/npm, then run this launcher again.
```
**Cause**: Directory `src/pipecat_voice_studio/ui/frontend/build` is missing or does not contain `index-*.js`.  
**Resolution**:
1. Install Node.js 24 and npm.
2. Run the frontend build:
   ```bash
   cd src/pipecat_voice_studio/ui/frontend
   npm ci
   npm run build
   cd ../../../..
   ```
3. Re-run the launcher script.

### 3. Missing OpenAI API key

**Error message**:
```text
RuntimeError: OPENAI_API_KEY is required to start a voice pipeline
```
**Cause**: The Pipecat worker attempted to construct a pipeline processor without an active OpenAI API key.  
**Resolution**:
1. Provide `OPENAI_API_KEY` in `.env` or set it in the host environment.
2. Restart the launcher. On Windows, `launch.ps1` will automatically check the Windows user environment if the key is not present in the current terminal session.

### 4. Telephony public base URL validation failure

**Error message**:
```text
ValueError: PVS_PUBLIC_BASE_URL must use https://
```
**Cause**: `PVS_PUBLIC_BASE_URL` was configured with an insecure `http://` prefix.  
**Resolution**: Configure a secure HTTPS reverse proxy or tunnel URL (e.g. `https://example.ngrok-free.app`) in `.env`.

### 5. Incompatible Linux platform or glibc version

**Error message**:
```text
Pipecat Voice Studio supports native x86-64 Linux only.
glibc 2.34 or newer is required; found 2.31
```
**Cause**: Running on an unsupported CPU architecture (e.g. ARM64) or an older Linux distribution with glibc older than 2.34.  
**Resolution**: Deploy to Ubuntu 22.04 LTS or newer (or equivalent x86_64 distribution with glibc >= 2.34). ARM64 and musl Linux are not supported.

### 6. Provider webhook signature rejection

**Error message**:
```text
HTTPException: 403: Invalid provider signature
```
**Cause**:
- Twilio: `TWILIO_AUTH_TOKEN` does not match the account sending the webhook, or `PVS_PUBLIC_BASE_URL` does not exactly match the external URL called by Twilio.
- Vonage: `VONAGE_SIGNATURE_SECRET` or `VONAGE_API_KEY` does not match the webhook JWT.  
**Resolution**: Verify that the external webhook URL registered in the carrier console exactly matches `PVS_PUBLIC_BASE_URL` and provider credentials in `.env`.

### 7. Telephony media token expired or invalid

**Error message**:
```text
WebSocket closed with code 1008
```
**Cause**: A media connection was initiated more than 300 seconds after the call webhook was signed, or the token's HMAC signature could not be verified using the carrier secret.  
**Resolution**: Ensure call connections complete within 5 minutes of carrier answer webhooks. Verify system clock synchronization.

### 8. Unbound telephone provider pipeline

**Error message**:
```text
HTTPException: 503: No pipeline is bound to provider
```
**Cause**: An incoming call arrived for `twilio` or `vonage`, but no pipeline binding exists in SQLite.  
**Resolution**: Open the Streamlit UI, navigate to the **Integrations** page, and select a pipeline (such as "Business phone agent") to bind to the provider.

### 9. Healthcare configuration validation failure

**Error message**:
```text
RuntimeError: Healthcare requires enablement, an encryption key, and openai approval
```
**Cause**: A healthcare pipeline was started, but one or more healthcare invariants were unmet: `PVS_HEALTHCARE_ENABLED` is `false`, `PVS_HEALTHCARE_DATA_KEY` is missing or not a 32-byte base64 key, or `openai` is missing from `PVS_HEALTHCARE_APPROVED_SERVICES`.  
**Resolution**: Update `.env` with:
```dotenv
PVS_HEALTHCARE_ENABLED=true
PVS_HEALTHCARE_DATA_KEY=<url-safe-base64-encoded-32-byte-key>
PVS_HEALTHCARE_APPROVED_SERVICES=openai
```

### 10. Appointment booking rejected without confirmation

**Error message**:
```text
PermissionError: Appointment creation requires explicit confirmation
```
**Cause**: A tool call attempted to invoke appointment creation without passing `confirmed=True` or without being in the `confirmation` Flow node.  
**Resolution**: This is an intended behavioral invariant. The conversational model must prompt the user for explicit confirmation and receive an affirmative response before transitioning to appointment creation.

### 11. Appointment slot unavailable or collision

**Error message**:
```text
ValueError: The requested slot is unavailable
ValueError: The requested slot was just taken
```
**Cause**: The requested time falls outside business hours (09:00–17:00 weekdays), is not on a 30-minute boundary, or another confirmed appointment already exists at that timestamp.  
**Resolution**: Use the appointment flow's `suggest` function to identify next available half-hour slots.

### 12. Outbound telephone destination not allowlisted

**Error message**:
```text
PermissionError: DestinationNotAllowedError
```
**Cause**: An outbound call was attempted to a phone number that is not explicitly listed in `PVS_OUTBOUND_ALLOWLIST`.  
**Resolution**: Add the exact canonical E.164 phone number (e.g. `+12025550143`) to `PVS_OUTBOUND_ALLOWLIST` in `.env` and restart the application.

### 13. CRM lead creation refused without consent

**Error message**:
```text
PermissionError: CrmConsentRequiredError
```
**Cause**: `HubSpot.upsert_lead()` was called with `consent=False`.  
**Resolution**: The conversational Flow must obtain explicit user consent before storing lead data in HubSpot CRM.
