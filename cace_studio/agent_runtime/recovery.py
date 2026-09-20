from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import json
import os
from pathlib import Path
import time
from typing import Any, Callable, Mapping
from uuid import uuid4

from cace_studio.core.reproducibility import sha256_identity


class AgentPhase(str, Enum):
    STARTING = "starting"
    PLANNING = "planning"
    ACTING = "acting"
    CHECKPOINTED = "checkpointed"
    RECOVERY_BLOCKED = "recovery-blocked"
    FINISHED = "finished"
    ABORTED = "aborted"
    BUDGET_EXHAUSTED = "budget-exhausted"


@dataclass(frozen=True)
class AgentHeartbeat:
    run_id: str
    monotonic_seq: int
    phase: AgentPhase
    step: int
    tool_calls: int
    failures: int
    lease_id: str
    lease_generation: int = 0
    checkpoint_sha256: str | None = None
    detail: str = ""
    evidence_authority: bool = False

    def __post_init__(self) -> None:
        if not self.run_id:
            raise ValueError("heartbeat run_id must be non-empty")
        if self.monotonic_seq < 0:
            raise ValueError("heartbeat monotonic_seq must be non-negative")
        if self.step < 0 or self.tool_calls < 0 or self.failures < 0:
            raise ValueError("heartbeat counters must be non-negative")
        if self.lease_generation < 0:
            raise ValueError("heartbeat lease_generation must be non-negative")
        if self.evidence_authority:
            raise ValueError("agent heartbeat cannot have evidence authority")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "cace-agent-runtime-heartbeat-v1",
            "run_id": self.run_id,
            "monotonic_seq": self.monotonic_seq,
            "phase": self.phase.value,
            "step": self.step,
            "tool_calls": self.tool_calls,
            "failures": self.failures,
            "lease_id": self.lease_id,
            "lease_generation": self.lease_generation,
            "checkpoint_sha256": self.checkpoint_sha256,
            "detail": self.detail,
            "evidence_authority": False,
            "proof_effect": "none",
            "promotion_authority": False,
        }


@dataclass(frozen=True)
class AgentLease:
    lease_id: str
    run_id: str
    owner_id: str
    generation: int
    ttl_seconds: float
    acquired_monotonic: float
    expires_monotonic: float

    def __post_init__(self) -> None:
        if not self.lease_id or not self.run_id or not self.owner_id:
            raise ValueError("lease identifiers must be non-empty")
        if self.generation <= 0:
            raise ValueError("lease generation must be positive")
        if self.ttl_seconds <= 0:
            raise ValueError("lease ttl_seconds must be positive")
        if self.expires_monotonic <= self.acquired_monotonic:
            raise ValueError("lease expiry must follow acquisition")

    def to_dict(self) -> dict[str, Any]:
        return {
            "lease_schema": 1,
            "lease_id": self.lease_id,
            "run_id": self.run_id,
            "owner_id": self.owner_id,
            "generation": self.generation,
            "ttl_seconds": self.ttl_seconds,
            "proof_effect": "none",
            "promotion_authority": False,
            "durability_note": "process-local lease; restart clears stale ownership and durable checkpoint governs recovery",
        }


class LeaseUnavailableError(RuntimeError):
    pass


class AgentLeaseManager:
    """Single-process lease manager using monotonic time.

    Leases deliberately are not persisted. A process restart clears stale ownership,
    while durable checkpoints decide whether a run can be resumed.
    """

    def __init__(self, *, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._leases_by_run: dict[str, AgentLease] = {}
        self._generation_by_run: dict[str, int] = {}

    def acquire(self, run_id: str, owner_id: str, *, ttl_seconds: float = 30.0) -> AgentLease:
        now = float(self._clock())
        existing = self._leases_by_run.get(run_id)
        if existing is not None and existing.expires_monotonic > now:
            raise LeaseUnavailableError(
                f"run {run_id!r} is already leased by {existing.owner_id!r}"
            )
        generation = self._generation_by_run.get(run_id, 0) + 1
        lease = AgentLease(
            lease_id=str(uuid4()),
            run_id=run_id,
            owner_id=owner_id,
            generation=generation,
            ttl_seconds=float(ttl_seconds),
            acquired_monotonic=now,
            expires_monotonic=now + float(ttl_seconds),
        )
        self._leases_by_run[run_id] = lease
        self._generation_by_run[run_id] = generation
        return lease

    def renew(self, lease: AgentLease) -> AgentLease:
        now = float(self._clock())
        current = self._leases_by_run.get(lease.run_id)
        if current is None or current.lease_id != lease.lease_id:
            raise LeaseUnavailableError("lease is no longer current")
        if current.expires_monotonic <= now:
            self._leases_by_run.pop(lease.run_id, None)
            raise LeaseUnavailableError("lease expired before renewal")
        renewed = AgentLease(
            lease_id=current.lease_id,
            run_id=current.run_id,
            owner_id=current.owner_id,
            generation=current.generation,
            ttl_seconds=current.ttl_seconds,
            acquired_monotonic=current.acquired_monotonic,
            expires_monotonic=now + current.ttl_seconds,
        )
        self._leases_by_run[lease.run_id] = renewed
        return renewed

    def release(self, lease: AgentLease) -> bool:
        current = self._leases_by_run.get(lease.run_id)
        if current is None or current.lease_id != lease.lease_id:
            return False
        self._leases_by_run.pop(lease.run_id, None)
        return True

    def current(self, run_id: str) -> AgentLease | None:
        current = self._leases_by_run.get(run_id)
        if current is None:
            return None
        if current.expires_monotonic <= float(self._clock()):
            self._leases_by_run.pop(run_id, None)
            return None
        return current


def _safe_run_id(run_id: str) -> str:
    if not isinstance(run_id, str) or not run_id:
        raise ValueError("run_id must be non-empty")
    if any(
        ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-"
        for ch in run_id
    ):
        raise ValueError("run_id contains unsafe characters")
    return run_id


@dataclass(frozen=True)
class AgentCheckpoint:
    run_id: str
    task: str
    next_step: int
    tool_calls: int
    failures: int
    heartbeat_seq: int
    budget: Mapping[str, int] | None = None
    tool_contract_sha256: str | None = None
    observations: tuple[Mapping[str, Any], ...] = ()
    trace: tuple[Mapping[str, Any], ...] = ()
    pending_call: Mapping[str, Any] | None = None
    status: str = "running"
    proof_effect: str = "none"
    promotion_authority: bool = False

    def __post_init__(self) -> None:
        _safe_run_id(self.run_id)
        if not isinstance(self.task, str) or not self.task.strip():
            raise ValueError("checkpoint task must be non-empty")
        if self.next_step <= 0:
            raise ValueError("checkpoint next_step must be positive")
        if min(self.tool_calls, self.failures, self.heartbeat_seq) < 0:
            raise ValueError("checkpoint counters must be non-negative")
        if self.budget is not None:
            if not isinstance(self.budget, Mapping):
                raise ValueError("checkpoint budget must be an object or null")
            for key, value in self.budget.items():
                if not isinstance(key, str) or not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                    raise ValueError("checkpoint budget entries must be positive integers")
        if self.tool_contract_sha256 is not None:
            value = self.tool_contract_sha256
            if len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value):
                raise ValueError("checkpoint tool_contract_sha256 must be lowercase SHA-256")
        if self.proof_effect != "none" or self.promotion_authority:
            raise ValueError("agent checkpoint cannot carry proof authority")
        if self.status not in {
            "running",
            "finished",
            "aborted",
            "budget_exhausted",
            "recovery_blocked",
        }:
            raise ValueError("unsupported checkpoint status")

    def to_dict(self) -> dict[str, Any]:
        return {
            "checkpoint_schema": 1,
            "run_id": self.run_id,
            "task": self.task,
            "next_step": self.next_step,
            "tool_calls": self.tool_calls,
            "failures": self.failures,
            "heartbeat_seq": self.heartbeat_seq,
            "budget": dict(self.budget) if self.budget is not None else None,
            "tool_contract_sha256": self.tool_contract_sha256,
            "observations": [dict(item) for item in self.observations],
            "trace": [dict(item) for item in self.trace],
            "pending_call": dict(self.pending_call) if self.pending_call is not None else None,
            "status": self.status,
            "proof_effect": "none",
            "promotion_authority": False,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "AgentCheckpoint":
        if not isinstance(payload, Mapping):
            raise ValueError("checkpoint must be an object")
        allowed = {
            "checkpoint_schema",
            "run_id",
            "task",
            "next_step",
            "tool_calls",
            "failures",
            "heartbeat_seq",
            "budget",
            "tool_contract_sha256",
            "observations",
            "trace",
            "pending_call",
            "status",
            "proof_effect",
            "promotion_authority",
        }
        unknown = sorted(set(payload) - allowed)
        if unknown:
            raise ValueError(f"checkpoint contains unknown fields: {unknown}")
        if payload.get("checkpoint_schema") != 1:
            raise ValueError("unsupported checkpoint schema")
        observations = payload.get("observations", [])
        trace = payload.get("trace", [])
        pending = payload.get("pending_call")
        budget = payload.get("budget")
        tool_contract_sha256 = payload.get("tool_contract_sha256")
        if budget is not None and not isinstance(budget, Mapping):
            raise ValueError("checkpoint budget must be an object or null")
        if tool_contract_sha256 is not None and not isinstance(tool_contract_sha256, str):
            raise ValueError("checkpoint tool_contract_sha256 must be a string or null")
        if not isinstance(observations, list) or not all(
            isinstance(x, Mapping) for x in observations
        ):
            raise ValueError("checkpoint observations must be an array of objects")
        if not isinstance(trace, list) or not all(isinstance(x, Mapping) for x in trace):
            raise ValueError("checkpoint trace must be an array of objects")
        if pending is not None and not isinstance(pending, Mapping):
            raise ValueError("checkpoint pending_call must be an object or null")
        if payload.get("proof_effect", "none") != "none":
            raise ValueError("checkpoint proof_effect must be none")
        if bool(payload.get("promotion_authority", False)):
            raise ValueError("checkpoint promotion_authority must be false")
        return cls(
            run_id=str(payload["run_id"]),
            task=str(payload["task"]),
            next_step=int(payload["next_step"]),
            tool_calls=int(payload["tool_calls"]),
            failures=int(payload["failures"]),
            heartbeat_seq=int(payload.get("heartbeat_seq", 0)),
            budget=(
                {str(key): int(value) for key, value in budget.items()}
                if budget is not None
                else None
            ),
            tool_contract_sha256=tool_contract_sha256,
            observations=tuple(dict(x) for x in observations),
            trace=tuple(dict(x) for x in trace),
            pending_call=dict(pending) if pending is not None else None,
            status=str(payload.get("status", "running")),
        )


class FileCheckpointStore:
    """Atomic content-hashed checkpoint store.

    The configured root is supplied by trusted host configuration, never by a model
    tool argument. Writes use same-directory temp files followed by os.replace.
    """

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).expanduser()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, run_id: str) -> Path:
        return self.root / f"{_safe_run_id(run_id)}.json"

    def save(self, checkpoint: AgentCheckpoint) -> str:
        payload = checkpoint.to_dict()
        digest = sha256_identity(payload)
        envelope = {
            "checkpoint_envelope_schema": 1,
            "checkpoint_sha256": digest,
            "checkpoint": payload,
        }
        target = self._path(checkpoint.run_id)
        temp = target.with_name(f".{target.name}.{uuid4().hex}.tmp")
        text = (
            json.dumps(
                envelope,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            )
            + "\n"
        )
        with temp.open("x", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            temp.chmod(0o600)
        except OSError:
            pass
        os.replace(temp, target)
        return digest

    def load(self, run_id: str) -> AgentCheckpoint | None:
        target = self._path(run_id)
        if not target.exists():
            return None
        raw = json.loads(target.read_text(encoding="utf-8"))
        if not isinstance(raw, dict) or raw.get("checkpoint_envelope_schema") != 1:
            raise ValueError("invalid checkpoint envelope")
        payload = raw.get("checkpoint")
        if not isinstance(payload, dict):
            raise ValueError("checkpoint envelope missing checkpoint object")
        expected = raw.get("checkpoint_sha256")
        actual = sha256_identity(payload)
        if expected != actual:
            raise ValueError("checkpoint content hash mismatch")
        return AgentCheckpoint.from_dict(payload)

    def digest(self, run_id: str) -> str | None:
        checkpoint = self.load(run_id)
        return (
            sha256_identity(checkpoint.to_dict())
            if checkpoint is not None
            else None
        )

    def clear(self, run_id: str) -> None:
        target = self._path(run_id)
        try:
            target.unlink()
        except FileNotFoundError:
            pass
