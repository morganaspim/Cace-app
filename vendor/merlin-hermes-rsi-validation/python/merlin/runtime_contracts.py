"""Durable, auditable execution contracts for Merlin.

This module is intentionally storage- and provider-neutral. A database adapter can
persist these records later; it must preserve event ordering, hash chaining,
idempotency, and approval binding rather than weakening these contracts.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
import json
from typing import Any, Mapping, Sequence

RUN_STATES = {"queued", "running", "waiting_approval", "succeeded", "failed", "cancelled"}
EVENT_TYPES = {
    "run.created", "run.started", "run.paused", "run.resumed",
    "run.completed", "run.failed", "run.cancelled",
    "step.started", "step.completed", "step.failed",
    "tool.requested", "tool.completed", "approval.required",
    "approval.granted", "approval.denied", "artifact.created",
}
TERMINAL_STATES = {"succeeded", "failed", "cancelled"}
GENESIS_HASH = "0" * 64


def _nonempty(value: str, field: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")


def _timestamp(value: str, field: str = "timestamp") -> None:
    _nonempty(value, field)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} must be ISO-8601") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field} must include a timezone")


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


@dataclass(frozen=True)
class RunRecord:
    run_id: str
    conversation_id: str
    request_id: str
    idempotency_key: str
    capability_id: str
    capability_version: str
    policy_hash: str
    state: str
    created_at: str
    max_steps: int
    max_runtime_seconds: int
    max_cost_units: int

    def __post_init__(self) -> None:
        for field in ("run_id", "conversation_id", "request_id", "idempotency_key",
                      "capability_id", "capability_version", "policy_hash"):
            _nonempty(getattr(self, field), field)
        _timestamp(self.created_at, "created_at")
        if self.state not in RUN_STATES:
            raise ValueError("invalid run state")
        if min(self.max_steps, self.max_runtime_seconds, self.max_cost_units) <= 0:
            raise ValueError("run budgets must be positive")


@dataclass(frozen=True)
class RunEvent:
    run_id: str
    sequence: int
    event_type: str
    occurred_at: str
    actor: str
    payload: Mapping[str, Any]
    previous_hash: str
    event_hash: str


def event_digest(run_id: str, sequence: int, event_type: str, occurred_at: str,
                 actor: str, payload: Mapping[str, Any], previous_hash: str) -> str:
    body = {
        "run_id": run_id, "sequence": sequence, "event_type": event_type,
        "occurred_at": occurred_at, "actor": actor, "payload": dict(payload),
        "previous_hash": previous_hash,
    }
    return sha256(_canonical(body).encode("utf-8")).hexdigest()


def append_event(events: Sequence[RunEvent], *, run_id: str, event_type: str,
                 occurred_at: str, actor: str, payload: Mapping[str, Any]) -> RunEvent:
    _nonempty(run_id, "run_id")
    _nonempty(actor, "actor")
    _timestamp(occurred_at, "occurred_at")
    if event_type not in EVENT_TYPES:
        raise ValueError("unsupported event type")
    if not isinstance(payload, Mapping):
        raise ValueError("payload must be a mapping")
    if events:
        verify_event_chain(events)
        if events[-1].run_id != run_id:
            raise ValueError("event chain belongs to another run")
        sequence = events[-1].sequence + 1
        previous_hash = events[-1].event_hash
    else:
        sequence, previous_hash = 1, GENESIS_HASH
    copied_payload = json.loads(_canonical(dict(payload)))
    digest = event_digest(run_id, sequence, event_type, occurred_at, actor,
                          copied_payload, previous_hash)
    return RunEvent(run_id, sequence, event_type, occurred_at, actor,
                    copied_payload, previous_hash, digest)


def verify_event_chain(events: Sequence[RunEvent]) -> bool:
    previous_hash = GENESIS_HASH
    expected_sequence = 1
    expected_run = events[0].run_id if events else None
    for event in events:
        if event.run_id != expected_run or event.sequence != expected_sequence:
            raise ValueError("event chain sequence or run identity is invalid")
        _timestamp(event.occurred_at, "occurred_at")
        expected = event_digest(event.run_id, event.sequence, event.event_type,
                                event.occurred_at, event.actor, event.payload,
                                previous_hash)
        if event.previous_hash != previous_hash or event.event_hash != expected:
            raise ValueError("event chain integrity check failed")
        previous_hash, expected_sequence = event.event_hash, expected_sequence + 1
    return True


@dataclass(frozen=True)
class ApprovalRecord:
    approval_id: str
    run_id: str
    step_id: str
    action_digest: str
    policy_hash: str
    status: str
    requested_at: str
    decided_at: str | None = None
    approver_id: str | None = None

    def __post_init__(self) -> None:
        for field in ("approval_id", "run_id", "step_id", "action_digest", "policy_hash"):
            _nonempty(getattr(self, field), field)
        _timestamp(self.requested_at, "requested_at")
        if self.status not in {"pending", "approved", "rejected", "expired", "revoked"}:
            raise ValueError("invalid approval status")
        if self.status == "approved":
            _nonempty(self.approver_id or "", "approver_id")
            _timestamp(self.decided_at or "", "decided_at")


def authorize_side_effect(approval: ApprovalRecord, *, run_id: str, step_id: str,
                          action_digest: str, policy_hash: str) -> bool:
    """Fail closed unless a human approved this exact action under this policy."""
    return (
        approval.status == "approved"
        and approval.run_id == run_id
        and approval.step_id == step_id
        and approval.action_digest == action_digest
        and approval.policy_hash == policy_hash
    )


def check_idempotency(existing: Mapping[str, str], *, idempotency_key: str,
                      request_digest: str) -> str:
    """Return replay/new; reject reuse of a key for a different request."""
    _nonempty(idempotency_key, "idempotency_key")
    _nonempty(request_digest, "request_digest")
    prior = existing.get(idempotency_key)
    if prior is None:
        return "new"
    if prior != request_digest:
        raise ValueError("idempotency key was reused for a different request")
    return "replay"
