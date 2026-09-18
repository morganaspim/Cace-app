from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import base64
import hashlib
import hmac
import json
from pathlib import Path
import secrets
import sqlite3
import time
from typing import Any


DAILY_FREE_SECONDS = 10 * 3600


class EntitlementExpired(RuntimeError):
    pass


class InvalidLease(RuntimeError):
    pass


def _utc_timestamp(now: datetime | None = None) -> float:
    value = now or datetime.now(timezone.utc)
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.timestamp()


def _utc_day(now: datetime | None = None) -> str:
    value = now or datetime.now(timezone.utc)
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).date().isoformat()


@dataclass(frozen=True)
class EntitlementStatus:
    subject: str
    day_utc: str
    free_daily_seconds: float
    free_consumed_seconds: float
    paid_remaining_seconds: float | None
    unlimited: bool
    allowed: bool

    @property
    def free_remaining_seconds(self) -> float:
        return max(0.0, self.free_daily_seconds - self.free_consumed_seconds)

    @property
    def remaining_seconds(self) -> float:
        if self.unlimited:
            return float("inf")
        return self.free_remaining_seconds + float(self.paid_remaining_seconds or 0.0)


@dataclass(frozen=True)
class ExecutionLease:
    schema: str
    lease_id: str
    subject: str
    issued_at: float
    expires_at: float
    max_execution_seconds: float
    nonce: str


class LeaseSigner:
    """Short-lived signed capability; server ledger remains authoritative."""

    def __init__(self, secret: bytes) -> None:
        if len(secret) < 32:
            raise ValueError("lease HMAC secret must be at least 32 bytes")
        self.secret = secret

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> "LeaseSigner":
        import os

        source = env if env is not None else os.environ
        value = source.get("CACE_ENTITLEMENT_HMAC_SECRET", "")
        if not value:
            raise RuntimeError("CACE_ENTITLEMENT_HMAC_SECRET is required")
        try:
            secret = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
        except Exception:
            secret = value.encode("utf-8")
        return cls(secret)

    def sign(self, lease: ExecutionLease) -> str:
        payload = json.dumps(asdict(lease), sort_keys=True, separators=(",", ":")).encode("utf-8")
        body = base64.urlsafe_b64encode(payload).rstrip(b"=")
        sig = hmac.new(self.secret, body, hashlib.sha256).digest()
        return body.decode("ascii") + "." + base64.urlsafe_b64encode(sig).rstrip(b"=").decode("ascii")

    def verify(self, token: str, *, now_monotonic_wall: float | None = None) -> ExecutionLease:
        try:
            body_text, sig_text = token.split(".", 1)
            body = body_text.encode("ascii")
            supplied = base64.urlsafe_b64decode(sig_text + "=" * (-len(sig_text) % 4))
        except Exception as exc:
            raise InvalidLease("malformed execution lease") from exc
        expected = hmac.new(self.secret, body, hashlib.sha256).digest()
        if not hmac.compare_digest(expected, supplied):
            raise InvalidLease("execution lease signature mismatch")
        try:
            payload = base64.urlsafe_b64decode(body + b"=" * (-len(body) % 4))
            raw = json.loads(payload)
            lease = ExecutionLease(**raw)
        except Exception as exc:
            raise InvalidLease("execution lease payload invalid") from exc
        now = time.time() if now_monotonic_wall is None else now_monotonic_wall
        if lease.schema != "cace-execution-lease-v1" or now >= lease.expires_at:
            raise InvalidLease("execution lease expired or unsupported")
        return lease


class EntitlementStore:
    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=30, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS daily_usage (
                    subject TEXT NOT NULL,
                    day_utc TEXT NOT NULL,
                    consumed_seconds REAL NOT NULL DEFAULT 0 CHECK(consumed_seconds >= 0),
                    PRIMARY KEY(subject, day_utc)
                );
                CREATE TABLE IF NOT EXISTS grants (
                    grant_id TEXT PRIMARY KEY,
                    subject TEXT NOT NULL,
                    valid_from REAL NOT NULL,
                    valid_until REAL,
                    compute_seconds REAL,
                    consumed_seconds REAL NOT NULL DEFAULT 0 CHECK(consumed_seconds >= 0),
                    source TEXT NOT NULL,
                    receipt_id TEXT NOT NULL UNIQUE,
                    CHECK(compute_seconds IS NULL OR compute_seconds >= 0)
                );
                CREATE INDEX IF NOT EXISTS grants_subject_idx ON grants(subject, valid_from, valid_until);
                """
            )

    def add_grant(
        self,
        *,
        grant_id: str,
        subject: str,
        valid_from: float,
        valid_until: float | None,
        compute_seconds: float | None,
        source: str,
        receipt_id: str,
    ) -> bool:
        with self._connect() as conn:
            try:
                conn.execute(
                    "INSERT INTO grants(grant_id,subject,valid_from,valid_until,compute_seconds,source,receipt_id) "
                    "VALUES(?,?,?,?,?,?,?)",
                    (grant_id, subject, valid_from, valid_until, compute_seconds, source, receipt_id),
                )
            except sqlite3.IntegrityError:
                # Idempotency: same payment receipt can never mint a second grant.
                existing = conn.execute(
                    "SELECT subject, source FROM grants WHERE receipt_id=?", (receipt_id,)
                ).fetchone()
                if existing and existing["subject"] == subject and existing["source"] == source:
                    return False
                raise
        return True

    def status(
        self,
        subject: str,
        *,
        now: datetime | None = None,
        daily_free_seconds: float = DAILY_FREE_SECONDS,
    ) -> EntitlementStatus:
        timestamp = _utc_timestamp(now)
        day = _utc_day(now)
        with self._connect() as conn:
            usage = conn.execute(
                "SELECT consumed_seconds FROM daily_usage WHERE subject=? AND day_utc=?",
                (subject, day),
            ).fetchone()
            free_consumed = float(usage[0]) if usage else 0.0
            grants = conn.execute(
                "SELECT compute_seconds, consumed_seconds, valid_until FROM grants "
                "WHERE subject=? AND valid_from<=? AND (valid_until IS NULL OR valid_until>?)",
                (subject, timestamp, timestamp),
            ).fetchall()

        unlimited = any(row["compute_seconds"] is None for row in grants)
        paid_remaining: float | None
        if unlimited:
            paid_remaining = None
        else:
            paid_remaining = sum(
                max(0.0, float(row["compute_seconds"]) - float(row["consumed_seconds"]))
                for row in grants
            )
        allowed = unlimited or max(0.0, daily_free_seconds - free_consumed) + float(paid_remaining or 0) > 0
        return EntitlementStatus(
            subject=subject,
            day_utc=day,
            free_daily_seconds=float(daily_free_seconds),
            free_consumed_seconds=free_consumed,
            paid_remaining_seconds=paid_remaining,
            unlimited=unlimited,
            allowed=allowed,
        )

    def charge(
        self,
        subject: str,
        seconds: float,
        *,
        now: datetime | None = None,
        daily_free_seconds: float = DAILY_FREE_SECONDS,
    ) -> None:
        if not isinstance(seconds, (int, float)) or seconds <= 0:
            raise ValueError("charge seconds must be positive")
        timestamp = _utc_timestamp(now)
        day = _utc_day(now)
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            usage = conn.execute(
                "SELECT consumed_seconds FROM daily_usage WHERE subject=? AND day_utc=?",
                (subject, day),
            ).fetchone()
            free_consumed = float(usage[0]) if usage else 0.0
            free_remaining = max(0.0, daily_free_seconds - free_consumed)
            grants = conn.execute(
                "SELECT grant_id, compute_seconds, consumed_seconds, valid_until FROM grants "
                "WHERE subject=? AND valid_from<=? AND (valid_until IS NULL OR valid_until>?) "
                "ORDER BY CASE WHEN valid_until IS NULL THEN 1 ELSE 0 END, valid_until, valid_from, grant_id",
                (subject, timestamp, timestamp),
            ).fetchall()
            if any(row["compute_seconds"] is None for row in grants):
                # Active unlimited grant: no metered deduction required.
                conn.execute("COMMIT")
                return
            paid_remaining = sum(
                max(0.0, float(row["compute_seconds"]) - float(row["consumed_seconds"]))
                for row in grants
            )
            if free_remaining + paid_remaining + 1e-9 < seconds:
                conn.execute("ROLLBACK")
                raise EntitlementExpired("execution time exhausted")

            remaining = float(seconds)
            from_free = min(free_remaining, remaining)
            if from_free > 0:
                conn.execute(
                    "INSERT INTO daily_usage(subject,day_utc,consumed_seconds) VALUES(?,?,?) "
                    "ON CONFLICT(subject,day_utc) DO UPDATE SET consumed_seconds=consumed_seconds+excluded.consumed_seconds",
                    (subject, day, from_free),
                )
                remaining -= from_free

            for row in grants:
                if remaining <= 1e-9:
                    break
                available = max(0.0, float(row["compute_seconds"]) - float(row["consumed_seconds"]))
                take = min(available, remaining)
                if take > 0:
                    conn.execute(
                        "UPDATE grants SET consumed_seconds=consumed_seconds+? WHERE grant_id=?",
                        (take, row["grant_id"]),
                    )
                    remaining -= take
            conn.execute("COMMIT")


class EntitlementService:
    def __init__(
        self,
        store: EntitlementStore,
        signer: LeaseSigner,
        *,
        daily_free_seconds: float = DAILY_FREE_SECONDS,
        max_lease_seconds: float = 60.0,
    ) -> None:
        self.store = store
        self.signer = signer
        self.daily_free_seconds = daily_free_seconds
        self.max_lease_seconds = max_lease_seconds

    def status(self, subject: str, *, now: datetime | None = None) -> EntitlementStatus:
        return self.store.status(subject, now=now, daily_free_seconds=self.daily_free_seconds)

    def issue_lease(self, subject: str, *, requested_seconds: float = 30.0) -> str:
        status = self.status(subject)
        if not status.allowed:
            raise EntitlementExpired("execution time exhausted")
        seconds = min(float(requested_seconds), self.max_lease_seconds)
        if not status.unlimited:
            seconds = min(seconds, status.remaining_seconds)
        if seconds <= 0:
            raise EntitlementExpired("execution time exhausted")
        now = time.time()
        lease = ExecutionLease(
            schema="cace-execution-lease-v1",
            lease_id=secrets.token_urlsafe(18),
            subject=subject,
            issued_at=now,
            expires_at=now + min(seconds + 5.0, self.max_lease_seconds + 5.0),
            max_execution_seconds=seconds,
            nonce=secrets.token_urlsafe(18),
        )
        return self.signer.sign(lease)

    def consume(self, token: str, elapsed_seconds: float) -> EntitlementStatus:
        lease = self.signer.verify(token)
        if elapsed_seconds < 0 or elapsed_seconds > lease.max_execution_seconds + 1e-6:
            raise InvalidLease("elapsed execution exceeds lease capability")
        if elapsed_seconds > 0:
            self.store.charge(
                lease.subject,
                elapsed_seconds,
                daily_free_seconds=self.daily_free_seconds,
            )
        return self.status(lease.subject)
