"""Durable idempotent outbox for Merlin service boundaries (at-least-once delivery)."""
from __future__ import annotations
import hashlib
import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Mapping
from uuid import uuid4


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False)


class OutboxConflict(ValueError):
    """An idempotency key was reused for different event content."""


class LeaseConflict(RuntimeError):
    """The caller does not hold the active event lease."""


class MerlinEventOutbox:
    """SQLite outbox with leases, retry, crash recovery and explicit acknowledgements."""
    def __init__(self, database: str | Path):
        self.path = Path(database)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.executescript("""
            CREATE TABLE IF NOT EXISTS event_outbox (
              event_id TEXT PRIMARY KEY, idempotency_key TEXT NOT NULL UNIQUE,
              topic TEXT NOT NULL, payload_json TEXT NOT NULL,
              state TEXT NOT NULL CHECK(state IN ('pending','leased','acknowledged','quarantined')),
              attempts INTEGER NOT NULL DEFAULT 0, available_at REAL NOT NULL,
              lease_owner TEXT, lease_token TEXT, lease_expires_at REAL,
              last_error TEXT, created_at REAL NOT NULL, updated_at REAL NOT NULL,
              acknowledged_at REAL, result_json TEXT);
            CREATE INDEX IF NOT EXISTS outbox_ready
              ON event_outbox(state, available_at, created_at);
            CREATE INDEX IF NOT EXISTS outbox_expiry
              ON event_outbox(state, lease_expires_at);
            """)
            columns = {row[1] for row in self._connect().execute(
                "PRAGMA table_info(event_outbox)"
            )}
            if "result_json" not in columns:
                with self._connect() as db:
                    db.execute("ALTER TABLE event_outbox ADD COLUMN result_json TEXT")

    def _connect(self):
        db = sqlite3.connect(self.path, timeout=30)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA busy_timeout=30000")
        return db

    @staticmethod
    def _text(value: str, label: str, limit: int) -> str:
        if not isinstance(value, str) or not value.strip() or len(value) > limit:
            raise ValueError(f"{label} must be a non-empty string of at most {limit} characters")
        return value.strip()

    @staticmethod
    def _row(row: sqlite3.Row) -> dict[str, Any]:
        result = dict(row)
        result["payload"] = json.loads(result.pop("payload_json"))
        encoded_result = result.pop("result_json", None)
        result["result"] = json.loads(encoded_result) if encoded_result else None
        return result

    def enqueue(self, idempotency_key: str, topic: str, payload: Mapping[str, Any],
                *, now: float | None = None) -> dict[str, Any]:
        key = self._text(idempotency_key, "idempotency_key", 256)
        topic = self._text(topic, "topic", 200)
        if not isinstance(payload, Mapping):
            raise ValueError("payload must be an object")
        encoded = _canonical(dict(payload))
        timestamp = time.time() if now is None else float(now)
        event_id = "evt_" + hashlib.sha256(key.encode()).hexdigest()
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            old = db.execute("SELECT * FROM event_outbox WHERE idempotency_key=?", (key,)).fetchone()
            if old:
                if old["topic"] != topic or old["payload_json"] != encoded:
                    raise OutboxConflict("idempotency key was reused with different event content")
                return self._row(old)
            db.execute("""INSERT INTO event_outbox(
                event_id,idempotency_key,topic,payload_json,state,attempts,
                available_at,created_at,updated_at)
                VALUES(?,?,?,?,'pending',0,?,?,?)""",
                (event_id,key,topic,encoded,timestamp,timestamp,timestamp))
            return self._row(db.execute(
                "SELECT * FROM event_outbox WHERE event_id=?", (event_id,)).fetchone())

    def claim_next(self, worker_id: str, *, lease_seconds: float = 60,
                   topics: tuple[str, ...] | list[str] | None = None,
                   now: float | None = None) -> dict[str, Any] | None:
        worker = self._text(worker_id, "worker_id", 128)
        if isinstance(lease_seconds, bool) or not isinstance(lease_seconds, (int,float)) or lease_seconds <= 0:
            raise ValueError("lease_seconds must be positive")
        timestamp = time.time() if now is None else float(now)
        if topics is not None:
            if not isinstance(topics, (tuple, list)) or any(
                not isinstance(topic, str) or not topic.strip() for topic in topics
            ):
                raise ValueError("topics must be a list of non-empty topic strings")
            topics = tuple(dict.fromkeys(topic.strip() for topic in topics))
            if not topics:
                return None
        token = str(uuid4())
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("""UPDATE event_outbox SET state='pending',lease_owner=NULL,
                lease_token=NULL,lease_expires_at=NULL,updated_at=?
                WHERE state='leased' AND lease_expires_at<=?""", (timestamp,timestamp))
            if topics is None:
                row = db.execute("""SELECT event_id FROM event_outbox
                    WHERE state='pending' AND available_at<=?
                    ORDER BY created_at,event_id LIMIT 1""", (timestamp,)).fetchone()
            else:
                placeholders = ",".join("?" for _ in topics)
                row = db.execute(
                    "SELECT event_id FROM event_outbox WHERE state='pending' AND available_at<=? "
                    f"AND topic IN ({placeholders}) ORDER BY created_at,event_id LIMIT 1",
                    (timestamp, *topics),
                ).fetchone()
            if row is None:
                return None
            event_id = row["event_id"]
            db.execute("""UPDATE event_outbox SET state='leased',attempts=attempts+1,
                lease_owner=?,lease_token=?,lease_expires_at=?,updated_at=?
                WHERE event_id=? AND state='pending'""",
                (worker,token,timestamp+lease_seconds,timestamp,event_id))
            result = self._row(db.execute(
                "SELECT * FROM event_outbox WHERE event_id=?", (event_id,)).fetchone())
            result["lease_token"] = token
            return result

    def _require_lease(self, row: sqlite3.Row, worker_id: str,
                       lease_token: str, now: float) -> None:
        if row["state"] != "leased" or row["lease_owner"] != worker_id or row["lease_token"] != lease_token or row["lease_expires_at"] is None or row["lease_expires_at"] <= now:
            raise LeaseConflict("operation requires the current unexpired lease")

    def acknowledge(self, event_id: str, worker_id: str, lease_token: str,
                    *, result: Mapping[str, Any] | None = None,
                    now: float | None = None) -> dict[str, Any]:
        timestamp = time.time() if now is None else float(now)
        result_json = None if result is None else _canonical(dict(result))
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM event_outbox WHERE event_id=?", (event_id,)).fetchone()
            if row is None:
                raise KeyError(event_id)
            if row["state"] == "acknowledged":
                return self._row(row)
            self._require_lease(row,worker_id,lease_token,timestamp)
            db.execute("""UPDATE event_outbox SET state='acknowledged',acknowledged_at=?,
                lease_owner=NULL,lease_token=NULL,lease_expires_at=NULL,updated_at=?,result_json=?
                WHERE event_id=?""", (timestamp,timestamp,result_json,event_id))
            return self._row(db.execute(
                "SELECT * FROM event_outbox WHERE event_id=?", (event_id,)).fetchone())

    def retry(self, event_id: str, worker_id: str, lease_token: str, error: str,
              *, delay_seconds: float = 0, max_attempts: int = 5,
              now: float | None = None) -> dict[str, Any]:
        timestamp = time.time() if now is None else float(now)
        if isinstance(max_attempts,bool) or not isinstance(max_attempts,int) or max_attempts < 1:
            raise ValueError("max_attempts must be a positive integer")
        if isinstance(delay_seconds,bool) or not isinstance(delay_seconds,(int,float)) or delay_seconds < 0:
            raise ValueError("delay_seconds must be non-negative")
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM event_outbox WHERE event_id=?", (event_id,)).fetchone()
            if row is None:
                raise KeyError(event_id)
            self._require_lease(row,worker_id,lease_token,timestamp)
            state = "quarantined" if row["attempts"] >= max_attempts else "pending"
            db.execute("""UPDATE event_outbox SET state=?,available_at=?,last_error=?,
                lease_owner=NULL,lease_token=NULL,lease_expires_at=NULL,updated_at=?
                WHERE event_id=?""",
                (state,timestamp+delay_seconds,str(error)[:2000],timestamp,event_id))
            return self._row(db.execute(
                "SELECT * FROM event_outbox WHERE event_id=?", (event_id,)).fetchone())

    def recover_expired(self, *, now: float | None = None) -> int:
        timestamp = time.time() if now is None else float(now)
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            cur = db.execute("""UPDATE event_outbox SET state='pending',lease_owner=NULL,
                lease_token=NULL,lease_expires_at=NULL,updated_at=?
                WHERE state='leased' AND lease_expires_at<=?""", (timestamp,timestamp))
            return cur.rowcount

    def get(self, event_id: str) -> dict[str, Any] | None:
        with self._connect() as db:
            row = db.execute("SELECT * FROM event_outbox WHERE event_id=?", (event_id,)).fetchone()
        return self._row(row) if row else None

    def counts(self) -> dict[str, int]:
        states = ("pending","leased","acknowledged","quarantined")
        with self._connect() as db:
            rows = db.execute("SELECT state,COUNT(*) AS n FROM event_outbox GROUP BY state").fetchall()
        result = {state:0 for state in states}
        result.update({row["state"]:row["n"] for row in rows})
        return result
