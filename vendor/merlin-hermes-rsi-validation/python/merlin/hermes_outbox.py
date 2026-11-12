"""Durable Hermes task outbox and result inbox on Merlin's SQLite registry.

Delivery is at-least-once. Consumers must be idempotent. An inbox receipt is
only a transport acknowledgement, never CACE verification or human approval.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
import secrets
from typing import Any, Mapping

from merlin.runtime_contracts import RunEvent, append_event
from merlin.sqlite_registry import SQLiteRunStore


class HermesOutbox:
    def __init__(self, registry: SQLiteRunStore):
        self.registry = registry
        with registry._transaction() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS hermes_outbox (
                task_id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(run_id),
                step_id TEXT NOT NULL, capability_id TEXT NOT NULL,
                capability_version TEXT NOT NULL, idempotency_key TEXT NOT NULL UNIQUE,
                payload_json TEXT NOT NULL, payload_digest TEXT NOT NULL,
                status TEXT NOT NULL CHECK (status IN
                  ('pending','leased','acknowledged','retry','dead_letter','cancelled')),
                attempts INTEGER NOT NULL DEFAULT 0, max_attempts INTEGER NOT NULL,
                next_attempt_at TEXT NOT NULL, created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL, lease_owner TEXT, lease_token TEXT,
                lease_expires_at TEXT, result_digest TEXT, last_error TEXT)""")
            db.execute("""CREATE TABLE IF NOT EXISTS hermes_inbox (
                inbox_id TEXT PRIMARY KEY, task_id TEXT NOT NULL REFERENCES hermes_outbox(task_id),
                worker_id TEXT NOT NULL, idempotency_key TEXT NOT NULL,
                message_digest TEXT NOT NULL, result_digest TEXT NOT NULL,
                received_at TEXT NOT NULL, UNIQUE(task_id, idempotency_key))""")
            db.execute("CREATE INDEX IF NOT EXISTS idx_hermes_ready ON hermes_outbox(status, next_attempt_at, created_at)")

    @staticmethod
    def _time(value: str, field: str) -> datetime:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field} is required")
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError(f"{field} must be ISO-8601") from exc
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError(f"{field} must include a timezone")
        return parsed.astimezone(timezone.utc)

    @staticmethod
    def _json(value: Mapping[str, Any]) -> str:
        return json.dumps(dict(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False)

    @staticmethod
    def _events(db, run_id: str) -> list[RunEvent]:
        rows = db.execute("SELECT * FROM run_events WHERE run_id=? ORDER BY sequence",
                          (run_id,)).fetchall()
        return [RunEvent(run_id=r["run_id"], sequence=r["sequence"],
            event_type=r["event_type"], occurred_at=r["occurred_at"], actor=r["actor"],
            payload=json.loads(r["payload_json"]), previous_hash=r["previous_hash"],
            event_hash=r["event_hash"]) for r in rows]

    def _append_event(self, db, run_id: str, event_type: str, occurred_at: str,
                      actor: str, payload: Mapping[str, Any]) -> None:
        event = append_event(self._events(db, run_id), run_id=run_id,
            event_type=event_type, occurred_at=occurred_at, actor=actor, payload=payload)
        db.execute("""INSERT INTO run_events
            (run_id, sequence, event_type, occurred_at, actor, payload_json,
             previous_hash, event_hash) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (event.run_id, event.sequence, event.event_type, event.occurred_at,
             event.actor, self._json(event.payload), event.previous_hash, event.event_hash))

    def publish_task(self, *, task_id: str, run_id: str, step_id: str,
                     idempotency_key: str, payload: Mapping[str, Any],
                     created_at: str, max_attempts: int = 5) -> dict[str, Any]:
        for field, value in (("task_id", task_id), ("run_id", run_id),
                             ("step_id", step_id), ("idempotency_key", idempotency_key)):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field} is required")
        created_at = self._time(created_at, "created_at").isoformat()
        if not isinstance(payload, Mapping) or max_attempts < 1:
            raise ValueError("payload must be a mapping and max_attempts positive")
        payload_json = self._json(payload)
        digest = sha256(payload_json.encode("utf-8")).hexdigest()
        with self.registry._transaction() as db:
            prior = db.execute("SELECT * FROM hermes_outbox WHERE idempotency_key=?",
                               (idempotency_key,)).fetchone()
            if prior:
                if prior["payload_digest"] != digest or prior["run_id"] != run_id:
                    raise ValueError("task idempotency key conflicts with prior payload")
                replay = dict(prior)
                replay["payload"] = json.loads(replay.pop("payload_json"))
                return replay
            run = db.execute("SELECT * FROM runs WHERE run_id=?", (run_id,)).fetchone()
            if run is None:
                raise ValueError("unknown run_id")
            self._append_event(db, run_id, "tool.requested", created_at, "hermes", {
                "task_id": task_id, "step_id": step_id,
                "capability_id": run["capability_id"],
                "capability_version": run["capability_version"],
                "payload_digest": digest,
            })
            db.execute("""INSERT INTO hermes_outbox
                (task_id, run_id, step_id, capability_id, capability_version,
                 idempotency_key, payload_json, payload_digest, status, attempts,
                 max_attempts, next_attempt_at, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', 0, ?, ?, ?, ?)""",
                (task_id, run_id, step_id, run["capability_id"], run["capability_version"],
                 idempotency_key, payload_json, digest, max_attempts,
                 created_at, created_at, created_at))
            row = db.execute("SELECT * FROM hermes_outbox WHERE task_id=?", (task_id,)).fetchone()
            item = dict(row)
            item["payload"] = json.loads(item.pop("payload_json"))
            return item

    def claim(self, *, worker_id: str, now: str, lease_seconds: int = 60,
              limit: int = 1) -> tuple[dict[str, Any], ...]:
        now_dt = self._time(now, "now")
        if not worker_id.strip() or lease_seconds < 1 or not 1 <= limit <= 100:
            raise ValueError("worker_id, positive lease_seconds, and limit 1..100 required")
        now_s = now_dt.isoformat()
        expiry = (now_dt + timedelta(seconds=lease_seconds)).isoformat()
        claimed = []
        with self.registry._transaction() as db:
            db.execute("""UPDATE hermes_outbox SET status='dead_letter', updated_at=?,
                lease_owner=NULL, lease_token=NULL, lease_expires_at=NULL,
                last_error=COALESCE(last_error, 'lease expired after final attempt')
                WHERE status='leased' AND lease_expires_at <= ?
                  AND attempts >= max_attempts""", (now_s, now_s))
            rows = db.execute("""SELECT * FROM hermes_outbox
                WHERE attempts < max_attempts AND next_attempt_at <= ?
                  AND (status IN ('pending','retry') OR
                       (status='leased' AND lease_expires_at <= ?))
                ORDER BY created_at, task_id LIMIT ?""", (now_s, now_s, limit)).fetchall()
            for row in rows:
                token = secrets.token_hex(24)
                changed = db.execute("""UPDATE hermes_outbox SET status='leased',
                    attempts=attempts+1, lease_owner=?, lease_token=?, lease_expires_at=?,
                    updated_at=? WHERE task_id=? AND
                    (status IN ('pending','retry') OR
                     (status='leased' AND lease_expires_at <= ?))""",
                    (worker_id, token, expiry, now_s, row["task_id"], now_s))
                if changed.rowcount:
                    item = dict(db.execute("SELECT * FROM hermes_outbox WHERE task_id=?",
                                           (row["task_id"],)).fetchone())
                    item["payload"] = json.loads(item.pop("payload_json"))
                    claimed.append(item)
        return tuple(claimed)

    def acknowledge(self, *, task_id: str, worker_id: str, lease_token: str,
                    idempotency_key: str, message_digest: str, result_digest: str,
                    received_at: str) -> str:
        self._time(received_at, "received_at")
        for name, value in (("task_id", task_id), ("worker_id", worker_id),
            ("lease_token", lease_token), ("idempotency_key", idempotency_key),
            ("message_digest", message_digest), ("result_digest", result_digest)):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} is required")
        with self.registry._transaction() as db:
            prior = db.execute("""SELECT message_digest FROM hermes_inbox
                WHERE task_id=? AND idempotency_key=?""", (task_id, idempotency_key)).fetchone()
            if prior:
                if prior["message_digest"] != message_digest:
                    raise ValueError("inbox idempotency key conflicts with prior message")
                return "duplicate"
            task = db.execute("SELECT * FROM hermes_outbox WHERE task_id=?", (task_id,)).fetchone()
            if task is None:
                raise ValueError("unknown task_id")
            if task["status"] != "leased" or task["lease_owner"] != worker_id or task["lease_token"] != lease_token:
                raise ValueError("worker lease is stale or not owned by worker")
            db.execute("""INSERT INTO hermes_inbox
                (inbox_id, task_id, worker_id, idempotency_key, message_digest,
                 result_digest, received_at) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (secrets.token_hex(16), task_id, worker_id, idempotency_key,
                 message_digest, result_digest, received_at))
            db.execute("""UPDATE hermes_outbox SET status='acknowledged', result_digest=?,
                updated_at=?, lease_owner=NULL, lease_token=NULL, lease_expires_at=NULL
                WHERE task_id=?""", (result_digest, received_at, task_id))
            self._append_event(db, task["run_id"], "tool.completed", received_at, worker_id, {
                "task_id": task_id, "message_digest": message_digest,
                "result_digest": result_digest, "delivery_acknowledged": True,
            })
            return "acknowledged"

    def retry(self, *, task_id: str, lease_token: str, now: str,
              error: str, backoff_seconds: int = 30) -> str:
        now_dt = self._time(now, "now")
        if backoff_seconds < 0:
            raise ValueError("backoff_seconds cannot be negative")
        with self.registry._transaction() as db:
            row = db.execute("SELECT * FROM hermes_outbox WHERE task_id=?", (task_id,)).fetchone()
            if row is None:
                raise ValueError("unknown task_id")
            if row["status"] != "leased" or row["lease_token"] != lease_token:
                raise ValueError("worker lease is stale")
            status = "dead_letter" if row["attempts"] >= row["max_attempts"] else "retry"
            due = (now_dt + timedelta(seconds=backoff_seconds)).isoformat()
            db.execute("""UPDATE hermes_outbox SET status=?, next_attempt_at=?, updated_at=?,
                last_error=?, lease_owner=NULL, lease_token=NULL, lease_expires_at=NULL
                WHERE task_id=?""", (status, due, now_dt.isoformat(), str(error)[:2000], task_id))
            return status

    def cancel(self, *, task_id: str, now: str) -> bool:
        now_s = self._time(now, "now").isoformat()
        with self.registry._transaction() as db:
            row = db.execute("SELECT status FROM hermes_outbox WHERE task_id=?", (task_id,)).fetchone()
            if row is None:
                raise ValueError("unknown task_id")
            if row["status"] in {"acknowledged", "dead_letter", "cancelled"}:
                return False
            db.execute("""UPDATE hermes_outbox SET status='cancelled', updated_at=?,
                lease_owner=NULL, lease_token=NULL, lease_expires_at=NULL WHERE task_id=?""",
                (now_s, task_id))
            return True

    def get(self, task_id: str) -> dict[str, Any] | None:
        with self.registry._transaction() as db:
            row = db.execute("SELECT * FROM hermes_outbox WHERE task_id=?", (task_id,)).fetchone()
        if row is None:
            return None
        item = dict(row)
        item["payload"] = json.loads(item.pop("payload_json"))
        return item
