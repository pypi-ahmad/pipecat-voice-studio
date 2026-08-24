# Codebase Concerns

## Top Risks

| Severity | Concern | Evidence | Impact | Suggested action |
|---|---|---|---|---|
| High | Management API has no authentication or authorization | `api/app.py` | Any reachable client can read/create pipelines | Keep local-only or add identity and per-action authorization before exposure |
| High | Local-first WebRTC and SQLite are not a production topology | `voice/bot.py`; `storage.py` | Internet/N-instance deployments may fail or contend | Define deployment, TURN, and managed-store architecture first |
| High | Public telephony depends on an operator-managed tunnel and correct provider signing configuration | `telephony_gateway.py`; `config.py` | Misconfiguration can break calls or weaken callback trust | Keep gateway-only exposure, require TLS, and monitor repeated signature failures |
| High | Healthcare safeguards are technical controls, not regulatory certification | `voice/healthcare_flow.py`; `security.py` | Operators could overstate suitability for clinical use | Complete legal, privacy, threat-model, and domain review before real patient data |
| Medium | Voice/UI runtime modules are excluded from coverage | `pyproject.toml` | Core realtime regressions may pass the 80% gate | Add targeted worker/component tests and narrow omissions |
| Medium | No app-level model retry/fallback policy | `voice/bot.py` | Transient provider failures terminate sessions | Define timeout/retry policy around idempotent operations and surface failures |
| Medium | Broad exception handling at runtime/evaluation boundaries | `voice/bot.py`; `evaluations.py` | Failure categories can be obscured | Preserve cleanup but classify expected provider/transport errors |

## Technical Debt

| Debt item | Why it exists | Where | Risk if ignored | Suggested fix |
|---|---|---|---|---|
| Complex graph and timeline functions have Ruff complexity exemptions | Centralized validation/frame classification | `graph.py`; `voice/timeline.py` | Harder safe extension | Add characterization tests before extracting cohesive helpers |
| Frontend validates by type-check/build only | No test runner is configured | frontend `package.json` | Interaction regressions require manual discovery | Add focused component tests when UI behavior stabilizes |
| Schema migration supports only v1 → v2 | First provider expansion | `storage.py` | Later schema changes need another explicit path | Introduce ordered migrations before schema v3 |
| Provider clients create a fresh HTTP client per request | Simple local adapter design | `integrations/` | Extra connection setup under sustained load | Reuse lifecycle-managed clients if profiling shows material cost |
| No generalized provider retry/idempotency layer | Fail-closed local scope | `integrations/`; `calendar_worker.py` | Transient failures require operator retry; CRM duplicates depend on provider semantics | Add operation-specific retry and idempotency keys before production use |

The production-code scan found no TODO/FIXME/HACK markers; the items above are evidence-based limitations, not comments copied from tests.

## Security Concerns

| Risk | OWASP | Evidence | Current mitigation | Gap |
|---|---|---|---|---|
| Unauthenticated API | A01 | `api/app.py` | Documented local/trusted use | No identity, roles, or authorization |
| Public worker/CORS deployment mistakes | A05 | worker CLI/origin handling; live page | Explicit allowed origins and HTTPS guidance | No production ingress policy in repo |
| Sensitive conversational data retention | A02 | `storage.py`; `timeline.py`; `security.py` | No raw audio; healthcare transcript suppression and AES-GCM intake encryption | Retention, key rotation, backup encryption, and deletion policy remain undefined |
| Telephone callback exposure | A07/A08 | `telephony_gateway.py` | Twilio/Vonage signatures, TLS requirement, short-lived media tokens | No rate limiter or centralized abuse alerting |
| Diagnostic details exposed to operators | A09 | evaluations and records UI | Local operator surface; bounded logs | No role-based redaction policy |

No credential is embedded in the inspected source. This is not a substitute for secret scanning in CI.

## Performance and Scaling Concerns

| Concern | Evidence | Current symptom | Scaling risk | Suggested improvement |
|---|---|---|---|---|
| One local SQLite file shared by processes | `storage.py` | None documented; WAL/busy timeout configured | Write contention and single-host coupling | Move to a service database for multi-instance operation |
| Event sequence uses `MAX(sequence)+1` per append | `storage.py` | Correct for current transaction pattern | Contention for high-frequency concurrent writers | Use database-generated sequencing or atomic counters at scale |
| Streamlit probes worker synchronously on rerun | `live_session.py` | Up to one-second page delay when unavailable | Repeated latency under reruns | Cache briefly or make health status asynchronous if observed |
| Evaluation starts a worker process per run | `evaluations.py` | Deliberate startup overhead | Slow suites at large scenario counts | Retain isolation until profiling justifies pooling |

## Fragile and High-Churn Areas

The repository has a short history: the top 90-day churn count is only two changes per file. Current signals therefore show active surfaces, not statistically strong fragility.

| Area | Why fragile | Churn signal | Safe change strategy |
|---|---|---|---|
| UI pages and Streamlit entry | Navigation and state behavior span Streamlit reruns | Several files changed twice | Run AppTest and manually verify live component lifecycle |
| Configuration/API | Shared startup contract | `config.py` and `api/app.py` changed twice | Update `.env.example`, tests, and docs together |
| Frontend build artifacts | Source and generated bundle must agree | Active frontend changes in worktree/history | Use `npm run build`; do not hand-edit build output |
| Voice worker | Async lifecycle and provider integrations | Active current work | Exercise graph tests plus an opt-in live scenario |

## `[ASK USER]` Questions

1. [ASK USER] Is the management API intended to remain localhost-only, or should authentication be a near-term requirement?
2. [ASK USER] What retention period and deletion/audit requirements apply to transcripts, encrypted
   intake, call/handoff records, appointments, and evaluation diagnostics?
3. [ASK USER] Beyond supported native Windows/Linux local hosts, is the eventual deployment target a trusted LAN or public multi-instance service?

## Evidence

- `docs/codebase/.codebase-scan.txt` (metrics, churn, TODO scan, CI/container detection)
- `pyproject.toml`
- `src/pipecat_voice_studio/api/app.py`
- `src/pipecat_voice_studio/storage.py`
- `src/pipecat_voice_studio/voice/bot.py`
- `src/pipecat_voice_studio/evaluations.py`
