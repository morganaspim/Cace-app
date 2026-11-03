from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Literal, Mapping
import time

from cace_studio.core.reproducibility import sha256_identity

from .contracts import ToolResult, ToolStatus
from .durability import (
    CrossProcessFileLock,
    atomic_write_json,
    hashed_envelope,
    validate_hashed_envelope,
)


class OperationConflictError(ValueError):
    pass


class OperationInProgressError(RuntimeError):
    pass


@dataclass(frozen=True)
class OperationClaim:
    operation_id: str
    action: Literal["execute", "replay"]
    result: ToolResult | None = None

    def __post_init__(self) -> None:
        if self.action == "replay" and self.result is None:
            raise ValueError("replay claim requires a stored result")
        if self.action == "execute" and self.result is not None:
            raise ValueError("execute claim cannot carry a stored result")


@dataclass(frozen=True)
class OperationRecord:
    operation_id: str
    state: Literal["in_progress", "committed"]
    call_id: str
    tool_name: str
    input_sha256: str
    lease_id: str
    lease_generation: int
    created_unix: float
    updated_unix: float
    approved: bool = False
    result: Mapping[str, Any] | None = None
    proof_effect: str = "none"
    promotion_authority: bool = False

    def __post_init__(self) -> None:
        _safe_operation_id(self.operation_id)
        if not self.call_id or not self.tool_name:
            raise ValueError("operation call/tool identity must be non-empty")
        if len(self.input_sha256) != 64 or any(
            ch not in "0123456789abcdef" for ch in self.input_sha256
        ):
            raise ValueError("operation input_sha256 must be lowercase SHA-256")
        if self.lease_generation < 0:
            raise ValueError("lease_generation must be non-negative")
        if self.updated_unix < self.created_unix:
            raise ValueError("operation update time cannot precede creation")
        if self.state not in {"in_progress", "committed"}:
            raise ValueError("unsupported operation state")
        if self.state == "committed" and self.result is None:
            raise ValueError("committed operation requires a result")
        if self.state == "in_progress" and self.result is not None:
            raise ValueError("in-progress operation cannot carry a result")
        if self.proof_effect != "none" or self.promotion_authority:
            raise ValueError("operation ledger cannot carry proof authority")

    def to_dict(self) -> dict[str, Any]:
        return {
            "operation_record_schema": 1,
            "operation_id": self.operation_id,
            "state": self.state,
            "call_id": self.call_id,
            "tool_name": self.tool_name,
            "input_sha256": self.input_sha256,
            "lease_id": self.lease_id,
            "lease_generation": self.lease_generation,
            "created_unix": self.created_unix,
            "updated_unix": self.updated_unix,
            "approved": self.approved,
            "result": dict(self.result) if self.result is not None else None,
            "proof_effect": "none",
            "promotion_authority": False,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "OperationRecord":
        if payload.get("operation_record_schema") != 1:
            raise ValueError("unsupported operation record schema")
        result = payload.get("result")
        if result is not None and not isinstance(result, Mapping):
            raise ValueError("operation result must be an object or null")
        return cls(
            operation_id=str(payload["operation_id"]),
            state=str(payload["state"]),
            call_id=str(payload["call_id"]),
            tool_name=str(payload["tool_name"]),
            input_sha256=str(payload["input_sha256"]),
            lease_id=str(payload.get("lease_id", "")),
            lease_generation=int(payload.get("lease_generation", 0)),
            created_unix=float(payload["created_unix"]),
            updated_unix=float(payload["updated_unix"]),
            approved=bool(payload.get("approved", False)),
            result=dict(result) if result is not None else None,
            proof_effect=str(payload.get("proof_effect", "none")),
            promotion_authority=bool(payload.get("promotion_authority", False)),
        )


def _safe_operation_id(operation_id: str) -> str:
    if not isinstance(operation_id, str) or not operation_id:
        raise ValueError("operation_id must be non-empty")
    if len(operation_id) > 128 or any(
        ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-"
        for ch in operation_id
    ):
        raise ValueError("operation_id contains unsafe characters")
    return operation_id


def _result_from_dict(payload: Mapping[str, Any]) -> ToolResult:
    if payload.get("tool_result_schema") != 1:
        raise ValueError("unsupported stored ToolResult schema")
    output = payload.get("output")
    if output is not None and not isinstance(output, Mapping):
        raise ValueError("stored ToolResult output must be an object or null")
    result = ToolResult(
        call_id=str(payload["call_id"]),
        tool_name=str(payload["tool_name"]),
        status=ToolStatus(str(payload["status"])),
        output=dict(output) if output is not None else None,
        error=str(payload.get("error", "")),
        proof_effect=str(payload.get("proof_effect", "none")),
        promotion_authority=bool(payload.get("promotion_authority", False)),
    )
    if result.proof_effect != "none" or result.promotion_authority:
        raise ValueError("stored ToolResult cannot carry proof authority")
    return result


class FileOperationStore:
    """Cross-process durable idempotency ledger for Tool Bus operations.

    Claim and commit transitions are serialized by an OS file lock. Once an
    operation is committed, the stored typed result can be replayed without
    re-running the handler. An in-progress operation is intentionally uncertain
    and blocks duplicate execution.
    """

    def __init__(self, root: str | Path, *, clock=time.time) -> None:
        self.root = Path(root).expanduser()
        self.root.mkdir(parents=True, exist_ok=True)
        self._clock = clock

    def _record_path(self, operation_id: str) -> Path:
        return self.root / f"{_safe_operation_id(operation_id)}.json"

    def _lock_path(self, operation_id: str) -> Path:
        return self.root / f".{_safe_operation_id(operation_id)}.lock"

    def _load_unlocked(self, operation_id: str) -> OperationRecord | None:
        path = self._record_path(operation_id)
        if not path.exists():
            return None
        raw = json.loads(path.read_text(encoding="utf-8"))
        payload = validate_hashed_envelope(
            raw,
            schema_key="operation_envelope_schema",
            schema_value=1,
            digest_key="operation_sha256",
            payload_key="operation",
        )
        return OperationRecord.from_dict(payload)

    def _save_unlocked(self, record: OperationRecord) -> None:
        envelope = hashed_envelope(
            schema_key="operation_envelope_schema",
            schema_value=1,
            digest_key="operation_sha256",
            payload_key="operation",
            payload=record.to_dict(),
        )
        atomic_write_json(self._record_path(record.operation_id), envelope)

    def load(self, operation_id: str) -> OperationRecord | None:
        with CrossProcessFileLock(self._lock_path(operation_id)):
            return self._load_unlocked(operation_id)

    def claim(
        self,
        *,
        operation_id: str,
        call_id: str,
        tool_name: str,
        input_sha256: str,
        lease_id: str = "",
        lease_generation: int = 0,
        approved: bool = False,
    ) -> OperationClaim:
        operation_id = _safe_operation_id(operation_id)
        with CrossProcessFileLock(self._lock_path(operation_id)):
            existing = self._load_unlocked(operation_id)
            if existing is not None:
                if (
                    existing.tool_name != tool_name
                    or existing.input_sha256 != input_sha256
                ):
                    raise OperationConflictError(
                        "operation_id is already bound to a different tool/input"
                    )
                if existing.state == "committed":
                    assert existing.result is not None
                    return OperationClaim(
                        operation_id,
                        "replay",
                        _result_from_dict(existing.result),
                    )
                raise OperationInProgressError(
                    "operation is already in progress or unresolved"
                )

            now = float(self._clock())
            record = OperationRecord(
                operation_id=operation_id,
                state="in_progress",
                call_id=call_id,
                tool_name=tool_name,
                input_sha256=input_sha256,
                lease_id=lease_id,
                lease_generation=int(lease_generation),
                created_unix=now,
                updated_unix=now,
                approved=bool(approved),
            )
            self._save_unlocked(record)
            return OperationClaim(operation_id, "execute")

    def commit(
        self,
        *,
        operation_id: str,
        tool_name: str,
        input_sha256: str,
        result: ToolResult,
    ) -> None:
        if not isinstance(result, ToolResult):
            raise TypeError("operation commit result must be a ToolResult")
        with CrossProcessFileLock(self._lock_path(operation_id)):
            existing = self._load_unlocked(operation_id)
            if existing is None:
                raise OperationConflictError("operation was not claimed")
            if (
                existing.tool_name != tool_name
                or existing.input_sha256 != input_sha256
            ):
                raise OperationConflictError(
                    "operation commit does not match claimed tool/input"
                )
            if result.call_id != existing.call_id or result.tool_name != existing.tool_name:
                raise OperationConflictError(
                    "operation result identity does not match the claimed call"
                )
            if existing.state == "committed":
                stored = _result_from_dict(existing.result or {})
                if stored.to_dict() != result.to_dict():
                    raise OperationConflictError(
                        "operation is already committed with a different result"
                    )
                return
            now = float(self._clock())
            committed = OperationRecord(
                operation_id=existing.operation_id,
                state="committed",
                call_id=existing.call_id,
                tool_name=existing.tool_name,
                input_sha256=existing.input_sha256,
                lease_id=existing.lease_id,
                lease_generation=existing.lease_generation,
                created_unix=existing.created_unix,
                updated_unix=now,
                approved=existing.approved,
                result=result.to_dict(),
            )
            self._save_unlocked(committed)

    def lookup_result(self, operation_id: str) -> ToolResult | None:
        record = self.load(operation_id)
        if record is None or record.state != "committed" or record.result is None:
            return None
        return _result_from_dict(record.result)


def operation_id_for(
    *,
    run_id: str,
    ordinal: int,
    tool_name: str,
    arguments: Mapping[str, Any],
) -> str:
    if not isinstance(ordinal, int) or isinstance(ordinal, bool) or ordinal <= 0:
        raise ValueError("operation ordinal must be positive")
    return sha256_identity(
        {
            "agent_operation_schema": 1,
            "run_id": run_id,
            "ordinal": ordinal,
            "tool_name": tool_name,
            "arguments": dict(arguments),
        }
    )
