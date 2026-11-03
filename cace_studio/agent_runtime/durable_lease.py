from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import time
from typing import Any, Callable, Mapping
from uuid import uuid4

from .durability import (
    CrossProcessFileLock,
    atomic_write_json,
    hashed_envelope,
    validate_hashed_envelope,
)
from .recovery import LeaseUnavailableError, _safe_run_id


@dataclass(frozen=True)
class DurableAgentLease:
    lease_id: str
    run_id: str
    owner_id: str
    generation: int
    ttl_seconds: float
    acquired_unix: float
    expires_unix: float
    active: bool = True
    proof_effect: str = "none"
    promotion_authority: bool = False

    def __post_init__(self) -> None:
        _safe_run_id(self.run_id)
        if not self.lease_id or not self.owner_id:
            raise ValueError("durable lease identifiers must be non-empty")
        if self.generation <= 0:
            raise ValueError("durable lease generation must be positive")
        if self.ttl_seconds <= 0:
            raise ValueError("durable lease ttl_seconds must be positive")
        if self.expires_unix < self.acquired_unix:
            raise ValueError("durable lease expiry cannot precede acquisition")
        if self.proof_effect != "none" or self.promotion_authority:
            raise ValueError("durable lease cannot carry proof authority")

    def to_dict(self) -> dict[str, Any]:
        return {
            "durable_lease_schema": 1,
            "lease_id": self.lease_id,
            "run_id": self.run_id,
            "owner_id": self.owner_id,
            "generation": self.generation,
            "ttl_seconds": self.ttl_seconds,
            "acquired_unix": self.acquired_unix,
            "expires_unix": self.expires_unix,
            "active": self.active,
            "proof_effect": "none",
            "promotion_authority": False,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "DurableAgentLease":
        if payload.get("durable_lease_schema") != 1:
            raise ValueError("unsupported durable lease schema")
        return cls(
            lease_id=str(payload["lease_id"]),
            run_id=str(payload["run_id"]),
            owner_id=str(payload["owner_id"]),
            generation=int(payload["generation"]),
            ttl_seconds=float(payload["ttl_seconds"]),
            acquired_unix=float(payload["acquired_unix"]),
            expires_unix=float(payload["expires_unix"]),
            active=bool(payload.get("active", True)),
            proof_effect=str(payload.get("proof_effect", "none")),
            promotion_authority=bool(payload.get("promotion_authority", False)),
        )


class FileAgentLeaseManager:
    """Filesystem-backed cross-process lease manager with persistent fencing epochs."""

    def __init__(
        self,
        root: str | Path,
        *,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.root = Path(root).expanduser()
        self.root.mkdir(parents=True, exist_ok=True)
        self._clock = clock

    def _path(self, run_id: str) -> Path:
        return self.root / f"{_safe_run_id(run_id)}.lease.json"

    def _lock_path(self, run_id: str) -> Path:
        return self.root / f".{_safe_run_id(run_id)}.lease.lock"

    def _load_unlocked(self, run_id: str) -> DurableAgentLease | None:
        path = self._path(run_id)
        if not path.exists():
            return None
        raw = json.loads(path.read_text(encoding="utf-8"))
        payload = validate_hashed_envelope(
            raw,
            schema_key="durable_lease_envelope_schema",
            schema_value=1,
            digest_key="durable_lease_sha256",
            payload_key="lease",
        )
        lease = DurableAgentLease.from_dict(payload)
        if lease.run_id != run_id:
            raise ValueError("durable lease run_id does not match filename")
        return lease

    def _save_unlocked(self, lease: DurableAgentLease) -> None:
        envelope = hashed_envelope(
            schema_key="durable_lease_envelope_schema",
            schema_value=1,
            digest_key="durable_lease_sha256",
            payload_key="lease",
            payload=lease.to_dict(),
        )
        atomic_write_json(self._path(lease.run_id), envelope)

    def acquire(
        self,
        run_id: str,
        owner_id: str,
        *,
        ttl_seconds: float = 30.0,
    ) -> DurableAgentLease:
        run_id = _safe_run_id(run_id)
        if not isinstance(owner_id, str) or not owner_id:
            raise ValueError("lease owner_id must be non-empty")
        ttl = float(ttl_seconds)
        if ttl <= 0:
            raise ValueError("lease ttl_seconds must be positive")
        with CrossProcessFileLock(self._lock_path(run_id)):
            now = float(self._clock())
            existing = self._load_unlocked(run_id)
            if existing is not None and existing.active and existing.expires_unix > now:
                raise LeaseUnavailableError(
                    f"run {run_id!r} is already leased by {existing.owner_id!r}"
                )
            generation = 1 if existing is None else existing.generation + 1
            lease = DurableAgentLease(
                lease_id=str(uuid4()),
                run_id=run_id,
                owner_id=owner_id,
                generation=generation,
                ttl_seconds=ttl,
                acquired_unix=now,
                expires_unix=now + ttl,
                active=True,
            )
            self._save_unlocked(lease)
            return lease

    def renew(self, lease: DurableAgentLease) -> DurableAgentLease:
        if not isinstance(lease, DurableAgentLease):
            raise TypeError("FileAgentLeaseManager requires DurableAgentLease tokens")
        with CrossProcessFileLock(self._lock_path(lease.run_id)):
            now = float(self._clock())
            current = self._load_unlocked(lease.run_id)
            if current is None or not current.active:
                raise LeaseUnavailableError("durable lease is no longer active")
            if (
                current.lease_id != lease.lease_id
                or current.owner_id != lease.owner_id
                or current.generation != lease.generation
            ):
                raise LeaseUnavailableError("durable lease fencing token is stale")
            if current.expires_unix <= now:
                expired = DurableAgentLease(
                    lease_id=current.lease_id,
                    run_id=current.run_id,
                    owner_id=current.owner_id,
                    generation=current.generation,
                    ttl_seconds=current.ttl_seconds,
                    acquired_unix=current.acquired_unix,
                    expires_unix=current.expires_unix,
                    active=False,
                )
                self._save_unlocked(expired)
                raise LeaseUnavailableError("durable lease expired before renewal")
            renewed = DurableAgentLease(
                lease_id=current.lease_id,
                run_id=current.run_id,
                owner_id=current.owner_id,
                generation=current.generation,
                ttl_seconds=current.ttl_seconds,
                acquired_unix=current.acquired_unix,
                expires_unix=now + current.ttl_seconds,
                active=True,
            )
            self._save_unlocked(renewed)
            return renewed

    def release(self, lease: DurableAgentLease) -> bool:
        if not isinstance(lease, DurableAgentLease):
            return False
        with CrossProcessFileLock(self._lock_path(lease.run_id)):
            current = self._load_unlocked(lease.run_id)
            if current is None or not current.active:
                return False
            if (
                current.lease_id != lease.lease_id
                or current.owner_id != lease.owner_id
                or current.generation != lease.generation
            ):
                return False
            now = float(self._clock())
            released = DurableAgentLease(
                lease_id=current.lease_id,
                run_id=current.run_id,
                owner_id=current.owner_id,
                generation=current.generation,
                ttl_seconds=current.ttl_seconds,
                acquired_unix=current.acquired_unix,
                expires_unix=min(current.expires_unix, now),
                active=False,
            )
            self._save_unlocked(released)
            return True

    def assert_current(
        self,
        run_id: str,
        lease_id: str,
        generation: int,
    ) -> DurableAgentLease:
        current = self.current(run_id)
        if current is None:
            raise LeaseUnavailableError("no active durable lease for run")
        if (
            current.lease_id != lease_id
            or current.generation != generation
        ):
            raise LeaseUnavailableError("durable lease fencing token is stale")
        return current

    def current(self, run_id: str) -> DurableAgentLease | None:
        run_id = _safe_run_id(run_id)
        with CrossProcessFileLock(self._lock_path(run_id)):
            current = self._load_unlocked(run_id)
            if current is None or not current.active:
                return None
            now = float(self._clock())
            if current.expires_unix <= now:
                expired = DurableAgentLease(
                    lease_id=current.lease_id,
                    run_id=current.run_id,
                    owner_id=current.owner_id,
                    generation=current.generation,
                    ttl_seconds=current.ttl_seconds,
                    acquired_unix=current.acquired_unix,
                    expires_unix=current.expires_unix,
                    active=False,
                )
                self._save_unlocked(expired)
                return None
            return current
