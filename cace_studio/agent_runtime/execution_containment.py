from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
from pathlib import Path
import time
from typing import Any, Mapping

from cace_studio.core.executor import RunResult
from cace_studio.core.report import run_report
from cace_studio.core.reproducibility import sha256_identity

from .durability import (
    CrossProcessFileLock,
    atomic_write_json,
    hashed_envelope,
    validate_hashed_envelope,
)


class RunControlState(str, Enum):
    RUNNING = "running"
    PAUSED = "paused"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class RunControlRecord:
    control_id: str
    state: RunControlState
    updated_unix: float
    proof_effect: str = "none"
    promotion_authority: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_control_schema": 1,
            "control_id": self.control_id,
            "state": self.state.value,
            "updated_unix": self.updated_unix,
            "proof_effect": "none",
            "promotion_authority": False,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "RunControlRecord":
        if payload.get("run_control_schema") != 1:
            raise ValueError("unsupported run-control schema")
        if payload.get("proof_effect", "none") != "none" or bool(
            payload.get("promotion_authority", False)
        ):
            raise ValueError("run control cannot carry proof authority")
        return cls(
            control_id=str(payload["control_id"]),
            state=RunControlState(str(payload["state"])),
            updated_unix=float(payload["updated_unix"]),
        )


class FileRunControlStore:
    def __init__(self, root: str | Path, *, clock=time.time) -> None:
        self.root = Path(root).expanduser()
        self.root.mkdir(parents=True, exist_ok=True)
        self._clock = clock

    @staticmethod
    def _safe(control_id: str) -> str:
        if not control_id or len(control_id) > 128 or any(
            ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-"
            for ch in control_id
        ):
            raise ValueError("run control_id contains unsupported characters")
        return control_id

    def _path(self, control_id: str) -> Path:
        return self.root / f"{self._safe(control_id)}.json"

    def _lock(self, control_id: str) -> Path:
        return self.root / f".{self._safe(control_id)}.lock"

    def load(self, control_id: str) -> RunControlRecord | None:
        path = self._path(control_id)
        with CrossProcessFileLock(self._lock(control_id)):
            if not path.exists():
                return None
            raw = json.loads(path.read_text(encoding="utf-8"))
            payload = validate_hashed_envelope(
                raw,
                schema_key="run_control_envelope_schema",
                schema_value=1,
                digest_key="run_control_sha256",
                payload_key="control",
            )
            record = RunControlRecord.from_dict(payload)
            if record.control_id != control_id:
                raise ValueError("run-control filename/content mismatch")
            return record

    def set_state(
        self, control_id: str, state: RunControlState
    ) -> RunControlRecord:
        self._safe(control_id)
        record = RunControlRecord(
            control_id=control_id,
            state=state,
            updated_unix=float(self._clock()),
        )
        with CrossProcessFileLock(self._lock(control_id)):
            atomic_write_json(
                self._path(control_id),
                hashed_envelope(
                    schema_key="run_control_envelope_schema",
                    schema_value=1,
                    digest_key="run_control_sha256",
                    payload_key="control",
                    payload=record.to_dict(),
                ),
            )
        return record

    def ensure_running(self, control_id: str) -> RunControlRecord:
        current = self.load(control_id)
        if current is not None:
            return current
        return self.set_state(control_id, RunControlState.RUNNING)

    def state(self, control_id: str) -> str:
        record = self.load(control_id)
        return (
            record.state.value
            if record is not None
            else RunControlState.RUNNING.value
        )


@dataclass(frozen=True)
class RunArtifactRecord:
    artifact_id: str
    session_id: str
    cycle_index: int
    run_id: str
    report_sha256: str
    perception_sha256: str
    byte_count: int
    report: Mapping[str, Any]
    perception: Mapping[str, Any]
    proof_effect: str = "none"
    promotion_authority: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_artifact_schema": 1,
            "artifact_id": self.artifact_id,
            "session_id": self.session_id,
            "cycle_index": self.cycle_index,
            "run_id": self.run_id,
            "report_sha256": self.report_sha256,
            "perception_sha256": self.perception_sha256,
            "byte_count": self.byte_count,
            "report": dict(self.report),
            "perception": dict(self.perception),
            "proof_effect": "none",
            "promotion_authority": False,
        }


class FileRunArtifactStore:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).expanduser()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, artifact_id: str) -> Path:
        if len(artifact_id) != 64 or any(
            ch not in "0123456789abcdef" for ch in artifact_id
        ):
            raise ValueError("artifact_id must be lowercase SHA-256")
        return self.root / f"{artifact_id}.json"

    def save(
        self,
        *,
        result: RunResult,
        experiment_name: str,
        session_id: str,
        cycle_index: int,
        perception: Mapping[str, Any],
        max_bytes: int,
    ) -> RunArtifactRecord:
        report = run_report(result, experiment_name)
        report_text = json.dumps(
            report,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
            default=repr,
        )
        perception_text = json.dumps(
            dict(perception),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
            default=repr,
        )
        report_sha = hashlib.sha256(report_text.encode("utf-8")).hexdigest()
        perception_sha = hashlib.sha256(
            perception_text.encode("utf-8")
        ).hexdigest()
        identity = {
            "run_artifact_identity_schema": 1,
            "session_id": session_id,
            "cycle_index": cycle_index,
            "run_id": result.run_id,
            "report_sha256": report_sha,
            "perception_sha256": perception_sha,
        }
        artifact_id = sha256_identity(identity)
        record = RunArtifactRecord(
            artifact_id=artifact_id,
            session_id=session_id,
            cycle_index=cycle_index,
            run_id=result.run_id,
            report_sha256=report_sha,
            perception_sha256=perception_sha,
            byte_count=len(report_text.encode("utf-8"))
            + len(perception_text.encode("utf-8")),
            report=report,
            perception=dict(perception),
        )
        if record.byte_count > max_bytes:
            raise ValueError(
                f"run artifact exceeds configured byte budget: "
                f"{record.byte_count} > {max_bytes}"
            )
        path = self._path(artifact_id)
        with CrossProcessFileLock(self.root / f".{artifact_id}.lock"):
            envelope = hashed_envelope(
                schema_key="run_artifact_envelope_schema",
                schema_value=1,
                digest_key="run_artifact_sha256",
                payload_key="artifact",
                payload=record.to_dict(),
            )
            if path.exists():
                raw = json.loads(path.read_text(encoding="utf-8"))
                existing = validate_hashed_envelope(
                    raw,
                    schema_key="run_artifact_envelope_schema",
                    schema_value=1,
                    digest_key="run_artifact_sha256",
                    payload_key="artifact",
                )
                if existing != record.to_dict():
                    raise ValueError(
                        "artifact_id collision with different run artifact"
                    )
                return record
            atomic_write_json(path, envelope)
        return record

    def load(self, artifact_id: str) -> Mapping[str, Any] | None:
        path = self._path(artifact_id)
        with CrossProcessFileLock(self.root / f".{artifact_id}.lock"):
            if not path.exists():
                return None
            raw = json.loads(path.read_text(encoding="utf-8"))
            return validate_hashed_envelope(
                raw,
                schema_key="run_artifact_envelope_schema",
                schema_value=1,
                digest_key="run_artifact_sha256",
                payload_key="artifact",
            )


@dataclass(frozen=True)
class RecoveryInboxItem:
    item_id: str
    session_id: str
    operation_id: str
    category: str
    message: str
    run_artifact_id: str
    created_unix: float
    resolved: bool = False
    proof_effect: str = "none"
    promotion_authority: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "recovery_inbox_schema": 1,
            "item_id": self.item_id,
            "session_id": self.session_id,
            "operation_id": self.operation_id,
            "category": self.category,
            "message": self.message,
            "run_artifact_id": self.run_artifact_id,
            "created_unix": self.created_unix,
            "resolved": self.resolved,
            "proof_effect": "none",
            "promotion_authority": False,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "RecoveryInboxItem":
        if payload.get("recovery_inbox_schema") != 1:
            raise ValueError("unsupported recovery inbox schema")
        if payload.get("proof_effect", "none") != "none" or bool(
            payload.get("promotion_authority", False)
        ):
            raise ValueError("recovery inbox item cannot carry proof authority")
        return cls(
            item_id=str(payload["item_id"]),
            session_id=str(payload["session_id"]),
            operation_id=str(payload["operation_id"]),
            category=str(payload["category"]),
            message=str(payload["message"]),
            run_artifact_id=str(payload.get("run_artifact_id", "")),
            created_unix=float(payload["created_unix"]),
            resolved=bool(payload.get("resolved", False)),
        )


class FileRecoveryInbox:
    def __init__(self, root: str | Path, *, clock=time.time) -> None:
        self.root = Path(root).expanduser()
        self.root.mkdir(parents=True, exist_ok=True)
        self._clock = clock

    def _path(self, item_id: str) -> Path:
        if len(item_id) != 64 or any(
            ch not in "0123456789abcdef" for ch in item_id
        ):
            raise ValueError("recovery inbox item_id must be lowercase SHA-256")
        return self.root / f"{item_id}.json"

    def add(
        self,
        *,
        session_id: str,
        operation_id: str,
        category: str,
        message: str,
        run_artifact_id: str = "",
    ) -> RecoveryInboxItem:
        identity = {
            "recovery_inbox_identity_schema": 1,
            "session_id": session_id,
            "operation_id": operation_id,
            "category": category,
            "run_artifact_id": run_artifact_id,
        }
        item_id = sha256_identity(identity)
        path = self._path(item_id)
        with CrossProcessFileLock(self.root / f".{item_id}.lock"):
            if path.exists():
                raw = json.loads(path.read_text(encoding="utf-8"))
                payload = validate_hashed_envelope(
                    raw,
                    schema_key="recovery_inbox_envelope_schema",
                    schema_value=1,
                    digest_key="recovery_inbox_sha256",
                    payload_key="item",
                )
                return RecoveryInboxItem.from_dict(payload)
            item = RecoveryInboxItem(
                item_id=item_id,
                session_id=session_id,
                operation_id=operation_id,
                category=category,
                message=message,
                run_artifact_id=run_artifact_id,
                created_unix=float(self._clock()),
            )
            atomic_write_json(
                path,
                hashed_envelope(
                    schema_key="recovery_inbox_envelope_schema",
                    schema_value=1,
                    digest_key="recovery_inbox_sha256",
                    payload_key="item",
                    payload=item.to_dict(),
                ),
            )
            return item

    def find_open_by_operation(
        self, operation_id: str
    ) -> RecoveryInboxItem | None:
        for path in sorted(self.root.glob("*.json")):
            raw = json.loads(path.read_text(encoding="utf-8"))
            payload = validate_hashed_envelope(
                raw,
                schema_key="recovery_inbox_envelope_schema",
                schema_value=1,
                digest_key="recovery_inbox_sha256",
                payload_key="item",
            )
            item = RecoveryInboxItem.from_dict(payload)
            if item.operation_id == operation_id and not item.resolved:
                return item
        return None

    def list_open(self, *, session_id: str | None = None) -> tuple[RecoveryInboxItem, ...]:
        items: list[RecoveryInboxItem] = []
        for path in sorted(self.root.glob("*.json")):
            raw = json.loads(path.read_text(encoding="utf-8"))
            payload = validate_hashed_envelope(
                raw,
                schema_key="recovery_inbox_envelope_schema",
                schema_value=1,
                digest_key="recovery_inbox_sha256",
                payload_key="item",
            )
            item = RecoveryInboxItem.from_dict(payload)
            if item.resolved:
                continue
            if session_id is not None and item.session_id != session_id:
                continue
            items.append(item)
        return tuple(items)

    def resolve(self, item_id: str) -> RecoveryInboxItem:
        path = self._path(item_id)
        with CrossProcessFileLock(self.root / f".{item_id}.lock"):
            if not path.exists():
                raise ValueError("unknown recovery inbox item")
            raw = json.loads(path.read_text(encoding="utf-8"))
            payload = validate_hashed_envelope(
                raw,
                schema_key="recovery_inbox_envelope_schema",
                schema_value=1,
                digest_key="recovery_inbox_sha256",
                payload_key="item",
            )
            item = RecoveryInboxItem.from_dict(payload)
            if item.resolved:
                return item
            resolved = RecoveryInboxItem(
                item_id=item.item_id,
                session_id=item.session_id,
                operation_id=item.operation_id,
                category=item.category,
                message=item.message,
                run_artifact_id=item.run_artifact_id,
                created_unix=item.created_unix,
                resolved=True,
            )
            atomic_write_json(
                path,
                hashed_envelope(
                    schema_key="recovery_inbox_envelope_schema",
                    schema_value=1,
                    digest_key="recovery_inbox_sha256",
                    payload_key="item",
                    payload=resolved.to_dict(),
                ),
            )
            return resolved
