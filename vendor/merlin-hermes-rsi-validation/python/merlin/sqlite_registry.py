"""Transactional SQLite persistence for Merlin runtime contracts.

SQLite is the first durable adapter, not the final distributed scheduler. The
interface is intentionally small so a later Postgres adapter can preserve the
same run/event/idempotency/approval semantics.
"""
from __future__ import annotations

from contextlib import contextmanager
import json
import sqlite3
from typing import Iterator, Mapping, Any

from merlin.runtime_contracts import (
    ApprovalRecord, RunEvent, RunRecord, append_event, verify_event_chain,
)


SCHEMA_VERSION = 1


class SQLiteRunStore:
    def __init__(self, database_path: str):
        if not database_path:
            raise ValueError("database_path is required")
        self.database_path = database_path
        self._initialize()

    @contextmanager
    def _transaction(self) -> Iterator[sqlite3.Connection]:
        db = sqlite3.connect(self.database_path, timeout=10, isolation_level=None)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        db.execute("PRAGMA busy_timeout = 10000")
        try:
            db.execute("BEGIN IMMEDIATE")
            yield db
            db.execute("COMMIT")
        except Exception:
            db.execute("ROLLBACK")
            raise
        finally:
            db.close()

    def _initialize(self) -> None:
        with self._transaction() as db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS schema_meta (
                    singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
                    version INTEGER NOT NULL
                )
            """)
            row = db.execute("SELECT version FROM schema_meta WHERE singleton = 1").fetchone()
            if row is None:
                db.execute("INSERT INTO schema_meta(singleton, version) VALUES (1, ?)",
                           (SCHEMA_VERSION,))
            elif row["version"] != SCHEMA_VERSION:
                raise RuntimeError("unsupported Merlin registry schema version")
            statements = (
                """CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY, conversation_id TEXT NOT NULL,
                    request_id TEXT NOT NULL, idempotency_key TEXT NOT NULL UNIQUE,
                    request_digest TEXT NOT NULL, capability_id TEXT NOT NULL,
                    capability_version TEXT NOT NULL, policy_hash TEXT NOT NULL,
                    state TEXT NOT NULL, created_at TEXT NOT NULL,
                    max_steps INTEGER NOT NULL, max_runtime_seconds INTEGER NOT NULL,
                    max_cost_units INTEGER NOT NULL)""",
                """CREATE TABLE IF NOT EXISTS run_events (
                    run_id TEXT NOT NULL REFERENCES runs(run_id),
                    sequence INTEGER NOT NULL, event_type TEXT NOT NULL,
                    occurred_at TEXT NOT NULL, actor TEXT NOT NULL,
                    payload_json TEXT NOT NULL, previous_hash TEXT NOT NULL,
                    event_hash TEXT NOT NULL, PRIMARY KEY (run_id, sequence),
                    UNIQUE (run_id, event_hash))""",
                """CREATE TABLE IF NOT EXISTS approvals (
                    approval_id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(run_id),
                    step_id TEXT NOT NULL, action_digest TEXT NOT NULL,
                    policy_hash TEXT NOT NULL, status TEXT NOT NULL,
                    requested_at TEXT NOT NULL, decided_at TEXT, approver_id TEXT)""",
                "CREATE INDEX IF NOT EXISTS idx_run_events_run_type ON run_events(run_id, event_type)",
                "CREATE INDEX IF NOT EXISTS idx_approvals_run_status ON approvals(run_id, status)",
            )
            for statement in statements:
                db.execute(statement)

    @staticmethod
    def _run_from_row(row: sqlite3.Row) -> RunRecord:
        return RunRecord(**{key: row[key] for key in (
            "run_id", "conversation_id", "request_id", "idempotency_key",
            "capability_id", "capability_version", "policy_hash", "state",
            "created_at", "max_steps", "max_runtime_seconds", "max_cost_units",
        )})

    def create_run(self, run: RunRecord, *, request_digest: str) -> tuple[str, bool]:
        if not isinstance(request_digest, str) or not request_digest.strip():
            raise ValueError("request_digest is required")
        with self._transaction() as db:
            existing = db.execute(
                "SELECT run_id, request_digest FROM runs WHERE idempotency_key = ?",
                (run.idempotency_key,),
            ).fetchone()
            if existing:
                if existing["request_digest"] != request_digest:
                    raise ValueError("idempotency key was reused for a different request")
                return existing["run_id"], False
            db.execute("""
                INSERT INTO runs (
                    run_id, conversation_id, request_id, idempotency_key,
                    request_digest, capability_id, capability_version, policy_hash,
                    state, created_at, max_steps, max_runtime_seconds, max_cost_units
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                run.run_id, run.conversation_id, run.request_id, run.idempotency_key,
                request_digest, run.capability_id, run.capability_version, run.policy_hash,
                run.state, run.created_at, run.max_steps, run.max_runtime_seconds,
                run.max_cost_units,
            ))
            return run.run_id, True

    def get_run(self, run_id: str) -> RunRecord | None:
        with self._transaction() as db:
            row = db.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()
            return self._run_from_row(row) if row else None

    def append_run_event(self, *, run_id: str, event_type: str, occurred_at: str,
                         actor: str, payload: Mapping[str, Any]) -> RunEvent:
        with self._transaction() as db:
            if not db.execute("SELECT 1 FROM runs WHERE run_id = ?", (run_id,)).fetchone():
                raise ValueError("unknown run_id")
            rows = db.execute(
                "SELECT * FROM run_events WHERE run_id = ? ORDER BY sequence", (run_id,)
            ).fetchall()
            prior = [RunEvent(
                run_id=row["run_id"], sequence=row["sequence"],
                event_type=row["event_type"], occurred_at=row["occurred_at"],
                actor=row["actor"], payload=json.loads(row["payload_json"]),
                previous_hash=row["previous_hash"], event_hash=row["event_hash"],
            ) for row in rows]
            event = append_event(prior, run_id=run_id, event_type=event_type,
                                 occurred_at=occurred_at, actor=actor, payload=payload)
            db.execute("""
                INSERT INTO run_events (
                    run_id, sequence, event_type, occurred_at, actor, payload_json,
                    previous_hash, event_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (event.run_id, event.sequence, event.event_type, event.occurred_at,
                  event.actor, json.dumps(event.payload, sort_keys=True, separators=(",", ":")),
                  event.previous_hash, event.event_hash))
            return event

    def list_run_events(self, run_id: str) -> tuple[RunEvent, ...]:
        with self._transaction() as db:
            rows = db.execute(
                "SELECT * FROM run_events WHERE run_id = ? ORDER BY sequence", (run_id,)
            ).fetchall()
        events = tuple(RunEvent(
            run_id=row["run_id"], sequence=row["sequence"], event_type=row["event_type"],
            occurred_at=row["occurred_at"], actor=row["actor"],
            payload=json.loads(row["payload_json"]), previous_hash=row["previous_hash"],
            event_hash=row["event_hash"],
        ) for row in rows)
        verify_event_chain(events)
        return events

    def create_approval(self, approval: ApprovalRecord) -> None:
        with self._transaction() as db:
            db.execute("""
                INSERT INTO approvals (
                    approval_id, run_id, step_id, action_digest, policy_hash,
                    status, requested_at, decided_at, approver_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (approval.approval_id, approval.run_id, approval.step_id,
                  approval.action_digest, approval.policy_hash, approval.status,
                  approval.requested_at, approval.decided_at, approval.approver_id))

    def decide_approval(self, approval_id: str, *, decision: str,
                        decided_at: str, approver_id: str) -> ApprovalRecord:
        if decision not in {"approved", "rejected"}:
            raise ValueError("decision must be approved or rejected")
        if not approver_id or not approver_id.strip():
            raise ValueError("approver_id is required")
        with self._transaction() as db:
            row = db.execute(
                "SELECT * FROM approvals WHERE approval_id = ?", (approval_id,)
            ).fetchone()
            if row is None:
                raise ValueError("unknown approval_id")
            if row["status"] != "pending":
                raise ValueError("approval is already decided")
            db.execute("""
                UPDATE approvals SET status = ?, decided_at = ?, approver_id = ?
                WHERE approval_id = ? AND status = 'pending'
            """, (decision, decided_at, approver_id, approval_id))
            updated = db.execute(
                "SELECT * FROM approvals WHERE approval_id = ?", (approval_id,)
            ).fetchone()
        return ApprovalRecord(
            approval_id=updated["approval_id"], run_id=updated["run_id"],
            step_id=updated["step_id"], action_digest=updated["action_digest"],
            policy_hash=updated["policy_hash"], status=updated["status"],
            requested_at=updated["requested_at"], decided_at=updated["decided_at"],
            approver_id=updated["approver_id"],
        )
