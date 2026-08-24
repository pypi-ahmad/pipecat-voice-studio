"""SQLite persistence for definitions, semantic events, appointments, and evaluations."""

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

SCHEMA_VERSION = 1


def _now() -> str:
    return datetime.now(UTC).isoformat()


class StudioStore:
    """Small transactional repository around the local studio database."""

    def __init__(self, path: Path) -> None:
        self.path = path

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        """Open a configured SQLite connection."""
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
                    UNIQUE(starts_at, duration_minutes),
                    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE SET NULL
                );
                CREATE TABLE IF NOT EXISTS eval_runs (
                    id TEXT PRIMARY KEY, pipeline_id TEXT NOT NULL, scenario TEXT NOT NULL,
                    status TEXT NOT NULL, result_json TEXT NOT NULL, created_at TEXT NOT NULL,
                    FOREIGN KEY (pipeline_id) REFERENCES pipeline_definitions(id)
                );
                """
            )
            row = connection.execute("SELECT version FROM schema_version LIMIT 1").fetchone()
            if row is None:
                connection.execute(
                    "INSERT INTO schema_version(version) VALUES (?)", (SCHEMA_VERSION,)
                )
            elif row["version"] != SCHEMA_VERSION:
                msg = f"Unsupported database schema version: {row['version']}"
                raise RuntimeError(msg)
            count = connection.execute(
                "SELECT COUNT(*) AS count FROM pipeline_definitions"
            ).fetchone()["count"]
            if count == 0:
                for graph in seed_graphs():
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

    def create_session(self, pipeline_id: str, graph: PipelineGraph, models: dict[str, str]) -> str:
        """Begin a session with a frozen graph/model snapshot."""
        session_id = uuid4().hex
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO sessions(id, pipeline_id, status, graph_json, models_json, "
                "started_at) VALUES (?, ?, 'running', ?, ?, ?)",
                (session_id, pipeline_id, graph.model_dump_json(), json.dumps(models), _now()),
            )
        self.append_event(session_id, "session.started", {"mode": graph.mode})
        return session_id

    def append_event(self, session_id: str, event_type: str, payload: dict[str, Any]) -> int:
        """Append an ordered semantic event; raw audio is deliberately unsupported."""
        if event_type == "audio.raw":
            raise ValueError("Raw audio may not be persisted")
        with self.connect() as connection:
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
