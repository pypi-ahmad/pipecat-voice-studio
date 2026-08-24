# Architecture diagrams

These diagrams reflect schema version 2 and the current browser, telephony, calendar, CRM,
healthcare, avatar, and evaluation implementation.

| Diagram | Mermaid source | Rendered artifact |
|---|---|---|
| System architecture | [system-architecture.mmd](system-architecture.mmd) | [SVG](system-architecture.svg) · [polished HTML](architecture-overview.html) |
| Browser/telephone voice session | [live-session-sequence.mmd](live-session-sequence.mmd) | [SVG](live-session-sequence.svg) |
| Semantic data flow | [semantic-data-flow.mmd](semantic-data-flow.mmd) | [SVG](semantic-data-flow.svg) |
| Module dependencies | [module-dependencies.mmd](module-dependencies.mmd) | [SVG](module-dependencies.svg) |
| SQLite schema v2 relationships | [database-er.mmd](database-er.mmd) | [SVG](database-er.svg) |

Regenerate an SVG with Mermaid CLI:

```powershell
npx --yes @mermaid-js/mermaid-cli -i docs/diagrams/system-architecture.mmd -o docs/diagrams/system-architecture.svg
```
