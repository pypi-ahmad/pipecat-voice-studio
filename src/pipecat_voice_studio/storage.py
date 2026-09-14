"""SQLite persistence for definitions, semantic events, appointments, and evaluations.

Owns the single local SQLite database file, handling table creation, schema
migrations, WAL journal mode, and foreign keys. This module is the only place
where database tables are defined and schema operations are executed. It must
never persist unredacted phone numbers, plaintext healthcare intake data, or
raw audio frames. See `appointments.py` for slot booking validation that sits
atop the appointments table, and `voice/timeline.py` for how Pipecat audio frames
become `session_events` rows.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from pipecat_voice_studio.graph import PipelineGraph
from pipecat_voice_studio.seeds import seed_graphs

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

# Schema migration version. v1 -> v2 added healthcare sensitivity and external
# calendar provider tracking on appointments.
SCHEMA_VERSION = 2


def _now() -> str:
    return datetime.now(UTC).isoformat()


class StudioStore:
    """Small transactional repository around the local studio database."""

    def __init__(self, path: Path) -> None:
        self.path = path

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        """Open a configured SQLite connection.

        Configured for concurrent access across the Streamlit UI, telephony gateway,
        and audio bot worker processes: WAL journal mode allows concurrent readers
        alongside a single writer, and busy_timeout=5000ms avoids immediate locks.
        """
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path, timeout=5)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA busy_timeout = 5000")
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def initialize(self) -> None:
        """Create the versioned schema and starter graphs idempotently."""
        with self.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS pipeline_definitions (
                    id TEXT PRIMARY KEY, name TEXT NOT NULL, mode TEXT NOT NULL,
                    graph_json TEXT NOT NULL, revision INTEGER NOT NULL,
                    active INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY, pipeline_id TEXT NOT NULL,
                    status TEXT NOT NULL, graph_json TEXT NOT NULL,
                    models_json TEXT NOT NULL, summary TEXT, action_items_json TEXT,
                    failure TEXT, started_at TEXT NOT NULL, ended_at TEXT,
                    sensitive INTEGER NOT NULL DEFAULT 0,
                    FOREIGN KEY (pipeline_id) REFERENCES pipeline_definitions(id)
                );
                CREATE TABLE IF NOT EXISTS session_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL,
                    sequence INTEGER NOT NULL, event_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL, created_at TEXT NOT NULL,
                    UNIQUE(session_id, sequence),
                    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS appointments (
                    id TEXT PRIMARY KEY, session_id TEXT, attendee_name TEXT NOT NULL,
                    purpose TEXT NOT NULL, starts_at TEXT NOT NULL,
                    duration_minutes INTEGER NOT NULL CHECK(duration_minutes = 30),
                    status TEXT NOT NULL, created_at TEXT NOT NULL,
                    provider TEXT, external_id TEXT, external_status TEXT,
                    UNIQUE(starts_at, duration_minutes),
                    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE SET NULL
                );
                CREATE TABLE IF NOT EXISTS eval_runs (
                    id TEXT PRIMARY KEY, pipeline_id TEXT NOT NULL, scenario TEXT NOT NULL,
                    status TEXT NOT NULL, result_json TEXT NOT NULL, created_at TEXT NOT NULL,
                    FOREIGN KEY (pipeline_id) REFERENCES pipeline_definitions(id)
                );
                CREATE TABLE IF NOT EXISTS integration_bindings (
                    provider TEXT PRIMARY KEY, pipeline_id TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (pipeline_id) REFERENCES pipeline_definitions(id)
                );
                CREATE TABLE IF NOT EXISTS calls (
                    id TEXT PRIMARY KEY, session_id TEXT, provider TEXT NOT NULL,
                    provider_call_id TEXT, direction TEXT NOT NULL,
                    remote_last_four TEXT NOT NULL, remote_digest TEXT NOT NULL,
                    status TEXT NOT NULL, failure TEXT, created_at TEXT NOT NULL,
                    ended_at TEXT,
                    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE SET NULL
                );
                CREATE TABLE IF NOT EXISTS handoffs (
                    id TEXT PRIMARY KEY, call_id TEXT NOT NULL, session_id TEXT,
                    provider TEXT NOT NULL, destination_last_four TEXT NOT NULL,
                    status TEXT NOT NULL, summary TEXT, failure TEXT,
                    created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                    FOREIGN KEY (call_id) REFERENCES calls(id),
                    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE SET NULL
                );
                CREATE TABLE IF NOT EXISTS calendar_sync_state (
                    provider TEXT PRIMARY KEY, sync_token TEXT,
                    last_synced_at TEXT, last_error TEXT
                );
                CREATE TABLE IF NOT EXISTS crm_records (
                    id TEXT PRIMARY KEY, session_id TEXT, provider TEXT NOT NULL,
                    contact_id TEXT, deal_id TEXT, contact_last_four TEXT,
                    score INTEGER, status TEXT NOT NULL, failure TEXT,
                    created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE SET NULL
                );
                CREATE TABLE IF NOT EXISTS healthcare_consents (
                    id TEXT PRIMARY KEY, session_id TEXT NOT NULL UNIQUE,
                    policy_version TEXT NOT NULL, accepted INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS healthcare_intakes (
                    id TEXT PRIMARY KEY, session_id TEXT NOT NULL UNIQUE,
                    ciphertext BLOB NOT NULL, nonce BLOB NOT NULL,
                    status TEXT NOT NULL, escalated INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS audit_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, actor TEXT NOT NULL,
                    action TEXT NOT NULL, resource_type TEXT NOT NULL,
                    resource_id TEXT, outcome TEXT NOT NULL,
                    metadata_json TEXT NOT NULL, created_at TEXT NOT NULL
                );
                """
            )
            row = connection.execute("SELECT version FROM schema_version LIMIT 1").fetchone()
            if row is None:
                connection.execute(
                    "INSERT INTO schema_version(version) VALUES (?)", (SCHEMA_VERSION,)
                )
            elif row["version"] == 1:
                # Upgrading from v1 -> v2 creates an offline copy before altering columns
                # to guard against data corruption on crashes during migration.
                backup_path = self.path.with_suffix(self.path.suffix + ".v1.bak")
                if not backup_path.exists():
                    with sqlite3.connect(backup_path) as backup:
                        connection.backup(backup)
                connection.executescript(
                    """
                    ALTER TABLE sessions ADD COLUMN sensitive INTEGER NOT NULL DEFAULT 0;
                    ALTER TABLE appointments ADD COLUMN provider TEXT;
                    ALTER TABLE appointments ADD COLUMN external_id TEXT;
                    ALTER TABLE appointments ADD COLUMN external_status TEXT;
                    UPDATE schema_version SET version = 2;
                    """
                )
            elif row["version"] != SCHEMA_VERSION:
                # Unsupported schema versions fail fast rather than risking partial writes.
                msg = f"Unsupported database schema version: {row['version']}"
                raise RuntimeError(msg)
            names = {
                str(row["name"])
                for row in connection.execute("SELECT name FROM pipeline_definitions").fetchall()
            }
            for graph in seed_graphs():
                if graph.name not in names:
                    self._insert_graph(connection, graph, active=True)

    def _insert_graph(
        self, connection: sqlite3.Connection, graph: PipelineGraph, *, active: bool
    ) -> str:
        pipeline_id = uuid4().hex
        timestamp = _now()
        connection.execute(
            "INSERT INTO pipeline_definitions VALUES (?, ?, ?, ?, 1, ?, ?, ?)",
            (
                pipeline_id,
                graph.name,
                graph.mode,
                graph.model_dump_json(),
                active,
                timestamp,
                timestamp,
            ),
        )
        return pipeline_id

    def save_graph(self, graph: PipelineGraph, *, active: bool = False) -> str:
        """Store a validated graph as revision one."""
        with self.connect() as connection:
            return self._insert_graph(connection, graph, active=active)

    def list_graphs(self) -> list[dict[str, Any]]:
        """List graph metadata without exposing credentials (graphs cannot contain any)."""
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT id, name, mode, revision, active, updated_at "
                "FROM pipeline_definitions ORDER BY name"
            ).fetchall()
        return [dict(row) for row in rows]

    def get_graph(self, pipeline_id: str) -> PipelineGraph:
        """Load and revalidate a graph at the runtime trust boundary."""
        with self.connect() as connection:
            row = connection.execute(
                "SELECT graph_json FROM pipeline_definitions WHERE id = ? AND active = 1",
                (pipeline_id,),
            ).fetchone()
        if row is None:
            raise KeyError(pipeline_id)
        return PipelineGraph.model_validate_json(row["graph_json"])

    def create_session(
        self,
        pipeline_id: str,
        graph: PipelineGraph,
        models: dict[str, str],
        *,
        sensitive: bool = False,
    ) -> str:
        """Begin a session with a frozen graph/model snapshot."""
        session_id = uuid4().hex
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO sessions(id, pipeline_id, status, graph_json, models_json, "
                "started_at, sensitive) VALUES (?, ?, 'running', ?, ?, ?, ?)",
                (
                    session_id,
                    pipeline_id,
                    graph.model_dump_json(),
                    json.dumps(models),
                    _now(),
                    sensitive,
                ),
            )
        self.append_event(session_id, "session.started", {"mode": graph.mode})
        return session_id

    def append_event(self, session_id: str, event_type: str, payload: dict[str, Any]) -> int:
        """Append an ordered semantic event; raw audio is deliberately unsupported."""
        # Core privacy invariant: raw binary audio must never touch local storage.
        if event_type == "audio.raw":
            raise ValueError("Raw audio may not be persisted")
        with self.connect() as connection:
            # Monotonic sequence counter per session guarantees deterministic timeline
            # ordering even when events are logged in the same millisecond.
            row = connection.execute(
                "SELECT COALESCE(MAX(sequence), 0) + 1 AS sequence "
                "FROM session_events WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            sequence = int(row["sequence"])
            connection.execute(
                "INSERT INTO session_events(session_id, sequence, event_type, payload_json, "
                "created_at) VALUES (?, ?, ?, ?, ?)",
                (session_id, sequence, event_type, json.dumps(payload), _now()),
            )
        return sequence

    def list_events(self, session_id: str) -> list[dict[str, Any]]:
        """Return a session's semantic timeline in sequence order."""
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT sequence, event_type, payload_json, created_at FROM session_events "
                "WHERE session_id = ? ORDER BY sequence",
                (session_id,),
            ).fetchall()
        return [{**dict(row), "payload": json.loads(row["payload_json"])} for row in rows]

    def delete_session(self, session_id: str) -> None:
        """Delete one session and its cascading timeline."""
        with self.connect() as connection:
            connection.execute("DELETE FROM sessions WHERE id = ?", (session_id,))

    def finish_session(self, session_id: str, *, failure: str | None = None) -> None:
        """Close a session and record its terminal lifecycle event."""
        status = "failed" if failure else "completed"
        self.append_event(session_id, f"session.{status}", {})
        with self.connect() as connection:
            connection.execute(
                "UPDATE sessions SET status = ?, failure = ?, ended_at = ? WHERE id = ?",
                (status, failure, _now(), session_id),
            )

    def create_eval_run(self, pipeline_id: str, scenario: str) -> str:
        """Create a pending evaluation record for an allowlisted scenario."""
        run_id = uuid4().hex
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO eval_runs VALUES (?, ?, ?, 'running', '{}', ?)",
                (run_id, pipeline_id, scenario, _now()),
            )
        return run_id

    def finish_eval_run(
        self,
        run_id: str,
        *,
        status: str,
        result: dict[str, Any],
    ) -> None:
        """Persist the terminal status and serializable result for one evaluation."""
        with self.connect() as connection:
            cursor = connection.execute(
                "UPDATE eval_runs SET status = ?, result_json = ? WHERE id = ?",
                (status, json.dumps(result, default=str), run_id),
            )
            if cursor.rowcount != 1:
                raise KeyError(run_id)

    def list_eval_runs(self, *, limit: int = 25) -> list[dict[str, Any]]:
        """Return recent evaluation runs with decoded result payloads."""
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT id, pipeline_id, scenario, status, result_json, created_at "
                "FROM eval_runs ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [{**dict(row), "result": json.loads(row["result_json"])} for row in rows]

    def set_integration_binding(self, provider: str, pipeline_id: str) -> None:
        """Bind one external channel to an active stored pipeline."""
        self.get_graph(pipeline_id)
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO integration_bindings VALUES (?, ?, ?) "
                "ON CONFLICT(provider) DO UPDATE SET pipeline_id=excluded.pipeline_id, "
                "updated_at=excluded.updated_at",
                (provider, pipeline_id, _now()),
            )

    def get_integration_binding(self, provider: str) -> str:
        """Return the pipeline bound to a provider."""
        with self.connect() as connection:
            row = connection.execute(
                "SELECT pipeline_id FROM integration_bindings WHERE provider = ?", (provider,)
            ).fetchone()
        if row is None:
            raise KeyError(provider)
        return str(row["pipeline_id"])

    def create_call(
        self,
        *,
        provider: str,
        direction: str,
        remote_last_four: str,
        remote_digest: str,
        provider_call_id: str | None = None,
    ) -> str:
        """Create a redacted telephone-call record."""
        call_id = uuid4().hex
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO calls(id, provider, provider_call_id, direction, remote_last_four, "
                "remote_digest, status, created_at) VALUES (?, ?, ?, ?, ?, ?, 'queued', ?)",
                (
                    call_id,
                    provider,
                    provider_call_id,
                    direction,
                    remote_last_four,
                    remote_digest,
                    _now(),
                ),
            )
        return call_id

    def update_call(
        self,
        call_id: str,
        *,
        status: str,
        provider_call_id: str | None = None,
        session_id: str | None = None,
        failure: str | None = None,
        ended: bool = False,
    ) -> None:
        """Update a call lifecycle without retaining a full telephone number."""
        with self.connect() as connection:
            cursor = connection.execute(
                "UPDATE calls SET status = ?, provider_call_id = COALESCE(?, provider_call_id), "
                "session_id = COALESCE(?, session_id), failure = ?, "
                "ended_at = CASE WHEN ? THEN ? ELSE ended_at END WHERE id = ?",
                (status, provider_call_id, session_id, failure, ended, _now(), call_id),
            )
            if cursor.rowcount != 1:
                raise KeyError(call_id)

    def list_calls(self, *, limit: int = 100) -> list[dict[str, Any]]:
        """Return recent redacted calls."""
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT id, session_id, provider, provider_call_id, direction, "
                "remote_last_four, status, failure, created_at, ended_at "
                "FROM calls ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_call_by_provider_id(self, provider: str, provider_call_id: str) -> dict[str, Any]:
        """Resolve a provider callback to its redacted local call record."""
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM calls WHERE provider = ? AND provider_call_id = ?",
                (provider, provider_call_id),
            ).fetchone()
        if row is None:
            raise KeyError(provider_call_id)
        return dict(row)

    def get_call(self, call_id: str) -> dict[str, Any]:
        """Return one redacted call record by local identifier."""
        with self.connect() as connection:
            row = connection.execute("SELECT * FROM calls WHERE id = ?", (call_id,)).fetchone()
        if row is None:
            raise KeyError(call_id)
        return dict(row)

    def create_handoff(
        self,
        *,
        call_id: str,
        session_id: str | None,
        provider: str,
        destination_last_four: str,
        summary: str,
    ) -> str:
        """Create a redacted operator-visible human handoff record."""
        handoff_id = uuid4().hex
        timestamp = _now()
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO handoffs VALUES (?, ?, ?, ?, ?, 'requested', ?, NULL, ?, ?)",
                (
                    handoff_id,
                    call_id,
                    session_id,
                    provider,
                    destination_last_four,
                    summary,
                    timestamp,
                    timestamp,
                ),
            )
        return handoff_id

    def update_handoff(self, handoff_id: str, *, status: str, failure: str | None = None) -> None:
        """Move one human handoff through its provider lifecycle."""
        with self.connect() as connection:
            cursor = connection.execute(
                "UPDATE handoffs SET status = ?, failure = ?, updated_at = ? WHERE id = ?",
                (status, failure, _now(), handoff_id),
            )
            if cursor.rowcount != 1:
                raise KeyError(handoff_id)

    def get_handoff(self, handoff_id: str) -> dict[str, Any]:
        """Return one handoff briefing for its authenticated provider callback."""
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM handoffs WHERE id = ?", (handoff_id,)
            ).fetchone()
        if row is None:
            raise KeyError(handoff_id)
        return dict(row)

    def list_handoffs(self, *, limit: int = 100) -> list[dict[str, Any]]:
        """Return recent handoff state for local operators."""
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM handoffs ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(row) for row in rows]

    def save_calendar_sync(self, *, sync_token: str | None, error: str | None = None) -> None:
        """Persist Google Calendar incremental-sync state."""
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO calendar_sync_state VALUES ('google', ?, ?, ?) "
                "ON CONFLICT(provider) DO UPDATE SET sync_token=excluded.sync_token, "
                "last_synced_at=excluded.last_synced_at, last_error=excluded.last_error",
                (sync_token, _now(), error),
            )

    def link_appointment_provider(
        self, appointment_id: str, *, provider: str, external_id: str, external_status: str
    ) -> None:
        """Attach an external calendar identity to a confirmed local appointment."""
        with self.connect() as connection:
            cursor = connection.execute(
                "UPDATE appointments SET provider = ?, external_id = ?, external_status = ? "
                "WHERE id = ?",
                (provider, external_id, external_status, appointment_id),
            )
            if cursor.rowcount != 1:
                raise KeyError(appointment_id)

    def apply_calendar_changes(self, changes: list[dict[str, Any]]) -> int:
        """Apply Google status changes to known external appointments.

        When an external event is marked 'cancelled' in Google Calendar, the local
        status flips to 'cancelled' as well. Other external updates modify external_status
        without overwriting the local appointment status.
        """
        updated = 0
        with self.connect() as connection:
            for event in changes:
                external_id = event.get("id")
                if not external_id:
                    continue
                cursor = connection.execute(
                    "UPDATE appointments SET external_status = ?, status = CASE "
                    "WHEN ? = 'cancelled' THEN 'cancelled' ELSE status END "
                    "WHERE provider = 'google' AND external_id = ?",
                    (event.get("status", "confirmed"), event.get("status"), external_id),
                )
                updated += cursor.rowcount
        return updated

    def get_calendar_sync(self) -> dict[str, Any] | None:
        """Return current Google Calendar synchronization state."""
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM calendar_sync_state WHERE provider = 'google'"
            ).fetchone()
        return dict(row) if row else None

    def record_crm_result(
        self,
        *,
        session_id: str | None,
        contact_id: str | None,
        deal_id: str | None,
        contact_last_four: str | None,
        score: int | None,
        status: str,
        failure: str | None = None,
    ) -> str:
        """Persist a redacted HubSpot write result."""
        record_id = uuid4().hex
        timestamp = _now()
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO crm_records VALUES (?, ?, 'hubspot', ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    record_id,
                    session_id,
                    contact_id,
                    deal_id,
                    contact_last_four,
                    score,
                    status,
                    failure,
                    timestamp,
                    timestamp,
                ),
            )
        return record_id

    def save_healthcare_consent(
        self, session_id: str, *, accepted: bool, policy_version: str
    ) -> str:
        """Persist healthcare consent independently from intake content."""
        consent_id = uuid4().hex
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO healthcare_consents VALUES (?, ?, ?, ?, ?)",
                (consent_id, session_id, policy_version, accepted, _now()),
            )
        return consent_id

    def save_healthcare_intake(
        self,
        session_id: str,
        *,
        ciphertext: bytes,
        nonce: bytes,
        status: str,
        escalated: bool,
    ) -> str:
        """Persist only encrypted structured healthcare intake content.

        Raw patient intake fields never touch the database. The caller must encrypt
        with HealthcareCipher using session_id as authenticated data (AAD) before
        storing the ciphertext and nonce bytes here.
        """
        intake_id = uuid4().hex
        timestamp = _now()
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO healthcare_intakes VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    intake_id,
                    session_id,
                    ciphertext,
                    nonce,
                    status,
                    escalated,
                    timestamp,
                    timestamp,
                ),
            )
        return intake_id

    def list_healthcare_metadata(self) -> list[dict[str, Any]]:
        """Return intake state without decrypting or selecting protected fields.

        The UI only displays policy version, consent acceptance, triage status,
        and escalation flags; ciphertext and nonce are omitted from the projection.
        """
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT i.id, i.session_id, c.policy_version, c.accepted, i.status, "
                "i.escalated, i.created_at, i.updated_at FROM healthcare_intakes i "
                "JOIN healthcare_consents c ON c.session_id = i.session_id "
                "ORDER BY i.created_at DESC"
            ).fetchall()
        return [dict(row) for row in rows]

    def append_audit(
        self,
        *,
        action: str,
        resource_type: str,
        resource_id: str | None,
        outcome: str,
        metadata: dict[str, Any] | None = None,
        actor: str = "local-operator",
    ) -> None:
        """Append a redacted local audit event."""
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO audit_events(actor, action, resource_type, resource_id, outcome, "
                "metadata_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    actor,
                    action,
                    resource_type,
                    resource_id,
                    outcome,
                    json.dumps(metadata or {}),
                    _now(),
                ),
            )
