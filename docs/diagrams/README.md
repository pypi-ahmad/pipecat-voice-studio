# Architecture diagrams

These diagrams reflect schema version 2 and the current browser, telephony, calendar, CRM,
healthcare, avatar, and evaluation implementation.

| Diagram | Mermaid source | Existing rendered artifact | Interactive Archify diagrams |
|---|---|---|---|
| System architecture | [system-architecture.mmd](system-architecture.mmd) | [SVG](system-architecture.svg) · [polished HTML](architecture-overview.html) | [System architecture](archify/system-architecture.html) |
| Browser/telephone voice sessions | [live-session-sequence.mmd](live-session-sequence.mmd) and session diagrams in [ARCHITECTURE.md](../ARCHITECTURE.md) | [SVG](live-session-sequence.svg) | [Browser setup](archify/browser-session.html) · [Browser events](archify/browser-session-events.html) · [Telephone setup](archify/telephone-session.html) · [Telephone runtime](archify/telephone-session-runtime.html) · [Live session](archify/live-session.html) · [Conversation lifecycle](archify/live-session-conversation.html) |
| Pipeline definition and runtime | Pipeline diagrams in [ARCHITECTURE.md](../ARCHITECTURE.md) | — | [Compile and persist](archify/pipeline-definition.html) · [Rejected definitions](archify/pipeline-definition-rejections.html) · [Instantiate persisted pipeline](archify/pipeline-runtime.html) |
| Evaluation run | Evaluation diagram in [ARCHITECTURE.md](../ARCHITECTURE.md) | — | [Evaluation run](archify/evaluation-run.html) |
| Calendar sync | Calendar diagram in [ARCHITECTURE.md](../ARCHITECTURE.md) | — | [Sync sequence](archify/calendar-sync.html) · [Calendar architecture](archify/calendar-sync-architecture.html) |
| Semantic data flow and healthcare intake | [semantic-data-flow.mmd](semantic-data-flow.mmd) and healthcare diagram in [ARCHITECTURE.md](../ARCHITECTURE.md) | [SVG](semantic-data-flow.svg) | [Semantic data flow](archify/semantic-data-flow.html) · [Healthcare intake](archify/healthcare-intake.html) |
| Module dependencies | [module-dependencies.mmd](module-dependencies.mmd) | [SVG](module-dependencies.svg) | [UI](archify/module-dependencies-ui.html) · [API](archify/module-dependencies-api.html) · [Telephony](archify/module-dependencies-telephony.html) · [Calendar](archify/module-dependencies-calendar.html) · [Evaluation harness](archify/module-dependencies-evaluations.html) · [Evaluation runtime](archify/module-dependencies-evaluation-runtime.html) · [Voice runtime](archify/module-dependencies-voice.html) · [Voice interactions](archify/module-dependencies-voice-interactions.html) · [Voice platform](archify/module-dependencies-voice-platform.html) · [Shared services](archify/module-dependencies-shared.html) |
| SQLite schema v2 relationships | [database-er.mmd](database-er.mmd) | [SVG](database-er.svg) | [Database relationships](archify/database-relationships.html) |

Regenerate an SVG with Mermaid CLI:

```powershell
npx --yes @mermaid-js/mermaid-cli -i docs/diagrams/system-architecture.mmd -o docs/diagrams/system-architecture.svg
```
