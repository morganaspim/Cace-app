from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import time
from typing import Any, Callable, Mapping

from cace_studio.core.graph import Experiment
from cace_studio.core.reproducibility import experiment_fingerprint
from cace_studio.core.serialization import experiment_from_data, experiment_to_data

from .durability import (
    CrossProcessFileLock,
    atomic_write_json,
    hashed_envelope,
    validate_hashed_envelope,
)


class WorkspaceConflictError(ValueError):
    pass


def _safe_workspace_id(workspace_id: str) -> str:
    if not isinstance(workspace_id, str) or not workspace_id:
        raise ValueError("workspace_id must be non-empty")
    if len(workspace_id) > 128 or any(
        ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-"
        for ch in workspace_id
    ):
        raise ValueError("workspace_id contains unsafe characters")
    return workspace_id


def _require_sha256(value: str, *, name: str) -> str:
    if len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value):
        raise ValueError(f"{name} must be lowercase SHA-256")
    return value


@dataclass(frozen=True)
class WorkspaceCommitReceipt:
    version: int
    parent_version: int
    committed_unix: float
    operation_id: str
    preview_id: str
    lease_id: str
    lease_generation: int
    base_semantic_sha256: str
    base_full_sha256: str
    target_semantic_sha256: str
    target_full_sha256: str
    proof_effect: str = "none"
    promotion_authority: bool = False

    def __post_init__(self) -> None:
        if self.version <= 0:
            raise ValueError("workspace receipt version must be positive")
        if self.parent_version != self.version - 1:
            raise ValueError("workspace receipt parent_version must equal version - 1")
        if not self.operation_id or not self.preview_id or not self.lease_id:
            raise ValueError("workspace receipt transaction identities must be non-empty")
        if self.lease_generation <= 0:
            raise ValueError("workspace receipt lease_generation must be positive")
        for name in (
            "base_semantic_sha256",
            "base_full_sha256",
            "target_semantic_sha256",
            "target_full_sha256",
        ):
            _require_sha256(getattr(self, name), name=name)
        if self.proof_effect != "none" or self.promotion_authority:
            raise ValueError("workspace receipt cannot carry proof authority")

    def to_dict(self) -> dict[str, Any]:
        return {
            "workspace_receipt_schema": 1,
            "version": self.version,
            "parent_version": self.parent_version,
            "committed_unix": self.committed_unix,
            "operation_id": self.operation_id,
            "preview_id": self.preview_id,
            "lease_id": self.lease_id,
            "lease_generation": self.lease_generation,
            "base_semantic_sha256": self.base_semantic_sha256,
            "base_full_sha256": self.base_full_sha256,
            "target_semantic_sha256": self.target_semantic_sha256,
            "target_full_sha256": self.target_full_sha256,
            "proof_effect": "none",
            "promotion_authority": False,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "WorkspaceCommitReceipt":
        if payload.get("workspace_receipt_schema") != 1:
            raise ValueError("unsupported workspace receipt schema")
        return cls(
            version=int(payload["version"]),
            parent_version=int(payload["parent_version"]),
            committed_unix=float(payload["committed_unix"]),
            operation_id=str(payload["operation_id"]),
            preview_id=str(payload["preview_id"]),
            lease_id=str(payload["lease_id"]),
            lease_generation=int(payload["lease_generation"]),
            base_semantic_sha256=str(payload["base_semantic_sha256"]),
            base_full_sha256=str(payload["base_full_sha256"]),
            target_semantic_sha256=str(payload["target_semantic_sha256"]),
            target_full_sha256=str(payload["target_full_sha256"]),
            proof_effect=str(payload.get("proof_effect", "none")),
            promotion_authority=bool(payload.get("promotion_authority", False)),
        )


@dataclass(frozen=True)
class WorkspaceVersionRecord:
    workspace_id: str
    version: int
    parent_version: int | None
    committed_unix: float
    operation_id: str
    preview_id: str
    lease_id: str
    lease_generation: int
    base_semantic_sha256: str
    base_full_sha256: str
    target_semantic_sha256: str
    target_full_sha256: str
    experiment: Mapping[str, Any]
    history: tuple[WorkspaceCommitReceipt, ...] = ()
    proof_effect: str = "none"
    promotion_authority: bool = False

    def __post_init__(self) -> None:
        _safe_workspace_id(self.workspace_id)
        if self.version < 0:
            raise ValueError("workspace version must be non-negative")
        if self.parent_version is not None and self.parent_version != self.version - 1:
            raise ValueError("workspace parent_version must be exactly version - 1")
        if self.lease_generation < 0:
            raise ValueError("workspace lease_generation must be non-negative")
        for name in (
            "base_semantic_sha256",
            "base_full_sha256",
            "target_semantic_sha256",
            "target_full_sha256",
        ):
            _require_sha256(getattr(self, name), name=name)
        if any(not isinstance(item, WorkspaceCommitReceipt) for item in self.history):
            raise TypeError("workspace history must contain WorkspaceCommitReceipt objects")
        if self.proof_effect != "none" or self.promotion_authority:
            raise ValueError("workspace version cannot carry proof authority")

    def to_dict(self) -> dict[str, Any]:
        return {
            "workspace_version_schema": 1,
            "workspace_id": self.workspace_id,
            "version": self.version,
            "parent_version": self.parent_version,
            "committed_unix": self.committed_unix,
            "operation_id": self.operation_id,
            "preview_id": self.preview_id,
            "lease_id": self.lease_id,
            "lease_generation": self.lease_generation,
            "base_semantic_sha256": self.base_semantic_sha256,
            "base_full_sha256": self.base_full_sha256,
            "target_semantic_sha256": self.target_semantic_sha256,
            "target_full_sha256": self.target_full_sha256,
            "experiment": dict(self.experiment),
            "history": [item.to_dict() for item in self.history],
            "proof_effect": "none",
            "promotion_authority": False,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "WorkspaceVersionRecord":
        if payload.get("workspace_version_schema") != 1:
            raise ValueError("unsupported workspace version schema")
        experiment = payload.get("experiment")
        history = payload.get("history", [])
        if not isinstance(experiment, Mapping):
            raise ValueError("workspace experiment payload must be an object")
        if not isinstance(history, list) or not all(
            isinstance(item, Mapping) for item in history
        ):
            raise ValueError("workspace history must be an array of objects")
        return cls(
            workspace_id=str(payload["workspace_id"]),
            version=int(payload["version"]),
            parent_version=(
                int(payload["parent_version"])
                if payload.get("parent_version") is not None
                else None
            ),
            committed_unix=float(payload["committed_unix"]),
            operation_id=str(payload.get("operation_id", "")),
            preview_id=str(payload.get("preview_id", "")),
            lease_id=str(payload.get("lease_id", "")),
            lease_generation=int(payload.get("lease_generation", 0)),
            base_semantic_sha256=str(payload["base_semantic_sha256"]),
            base_full_sha256=str(payload["base_full_sha256"]),
            target_semantic_sha256=str(payload["target_semantic_sha256"]),
            target_full_sha256=str(payload["target_full_sha256"]),
            experiment=dict(experiment),
            history=tuple(WorkspaceCommitReceipt.from_dict(item) for item in history),
            proof_effect=str(payload.get("proof_effect", "none")),
            promotion_authority=bool(payload.get("promotion_authority", False)),
        )


class FileExperimentWorkspace:
    """Single-file atomic workspace state with optimistic version checks.

    One durable envelope binds the current experiment, version, preview,
    operation/fencing identity, and a compact transaction receipt lineage.
    """

    def __init__(
        self,
        root: str | Path,
        *,
        workspace_id: str,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.root = Path(root).expanduser()
        self.root.mkdir(parents=True, exist_ok=True)
        self.workspace_id = _safe_workspace_id(workspace_id)
        self._clock = clock

    @property
    def path(self) -> Path:
        return self.root / f"{self.workspace_id}.workspace.json"

    @property
    def lock_path(self) -> Path:
        return self.root / f".{self.workspace_id}.workspace.lock"

    @staticmethod
    def _hashes(experiment: Experiment) -> tuple[str, str]:
        return (
            experiment_fingerprint(experiment, include_layout=False),
            experiment_fingerprint(experiment, include_layout=True),
        )

    @staticmethod
    def _validate_history(record: WorkspaceVersionRecord) -> None:
        if record.version == 0:
            if record.history:
                raise WorkspaceConflictError("workspace version 0 cannot have mutation history")
            return
        if len(record.history) != record.version:
            raise WorkspaceConflictError(
                "workspace transaction receipt history length must equal current version"
            )
        expected_versions = tuple(range(1, record.version + 1))
        actual_versions = tuple(item.version for item in record.history)
        if actual_versions != expected_versions:
            raise WorkspaceConflictError("workspace receipt versions are not contiguous")
        operation_ids = [item.operation_id for item in record.history]
        if len(operation_ids) != len(set(operation_ids)):
            raise WorkspaceConflictError("workspace receipt operation IDs must be unique")
        last = record.history[-1]
        top_level = (
            record.version,
            record.parent_version,
            record.committed_unix,
            record.operation_id,
            record.preview_id,
            record.lease_id,
            record.lease_generation,
            record.base_semantic_sha256,
            record.base_full_sha256,
            record.target_semantic_sha256,
            record.target_full_sha256,
        )
        receipt = (
            last.version,
            last.parent_version,
            last.committed_unix,
            last.operation_id,
            last.preview_id,
            last.lease_id,
            last.lease_generation,
            last.base_semantic_sha256,
            last.base_full_sha256,
            last.target_semantic_sha256,
            last.target_full_sha256,
        )
        if top_level != receipt:
            raise WorkspaceConflictError(
                "workspace current transaction metadata does not match final receipt"
            )
        for previous, current in zip(record.history, record.history[1:]):
            if previous.target_semantic_sha256 != current.base_semantic_sha256:
                raise WorkspaceConflictError(
                    "workspace receipt semantic hash chain is broken"
                )
            if previous.target_full_sha256 != current.base_full_sha256:
                raise WorkspaceConflictError("workspace receipt full hash chain is broken")

    def _validate_record(self, record: WorkspaceVersionRecord) -> Experiment:
        if record.workspace_id != self.workspace_id:
            raise WorkspaceConflictError("workspace record identity mismatch")
        experiment = experiment_from_data(dict(record.experiment))
        semantic, full = self._hashes(experiment)
        if semantic != record.target_semantic_sha256:
            raise WorkspaceConflictError("workspace semantic hash/content mismatch")
        if full != record.target_full_sha256:
            raise WorkspaceConflictError("workspace full hash/content mismatch")
        self._validate_history(record)
        if record.version == 0:
            if record.parent_version is not None:
                raise WorkspaceConflictError("workspace version 0 cannot have a parent")
            if record.operation_id or record.preview_id or record.lease_id:
                raise WorkspaceConflictError("workspace version 0 cannot claim a mutation")
            if record.lease_generation != 0:
                raise WorkspaceConflictError("workspace version 0 cannot carry a lease generation")
            if (
                record.base_semantic_sha256 != record.target_semantic_sha256
                or record.base_full_sha256 != record.target_full_sha256
            ):
                raise WorkspaceConflictError("workspace version 0 base/target hashes must match")
        else:
            if not record.operation_id or not record.preview_id or not record.lease_id:
                raise WorkspaceConflictError("mutated workspace version missing transaction identity")
            if record.lease_generation <= 0:
                raise WorkspaceConflictError("mutated workspace version missing fencing generation")
        return experiment

    def _load_unlocked(self) -> tuple[WorkspaceVersionRecord, Experiment] | None:
        if not self.path.exists():
            return None
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        payload = validate_hashed_envelope(
            raw,
            schema_key="workspace_envelope_schema",
            schema_value=1,
            digest_key="workspace_sha256",
            payload_key="workspace",
        )
        record = WorkspaceVersionRecord.from_dict(payload)
        return record, self._validate_record(record)

    def _save_unlocked(self, record: WorkspaceVersionRecord) -> None:
        envelope = hashed_envelope(
            schema_key="workspace_envelope_schema",
            schema_value=1,
            digest_key="workspace_sha256",
            payload_key="workspace",
            payload=record.to_dict(),
        )
        atomic_write_json(self.path, envelope)

    def initialize(self, experiment: Experiment) -> WorkspaceVersionRecord:
        semantic, full = self._hashes(experiment)
        with CrossProcessFileLock(self.lock_path):
            existing = self._load_unlocked()
            if existing is not None:
                record, persisted = existing
                persisted_semantic, persisted_full = self._hashes(persisted)
                if persisted_semantic != semantic or persisted_full != full:
                    raise WorkspaceConflictError(
                        "workspace already exists with different experiment content"
                    )
                return record
            record = WorkspaceVersionRecord(
                workspace_id=self.workspace_id,
                version=0,
                parent_version=None,
                committed_unix=float(self._clock()),
                operation_id="",
                preview_id="",
                lease_id="",
                lease_generation=0,
                base_semantic_sha256=semantic,
                base_full_sha256=full,
                target_semantic_sha256=semantic,
                target_full_sha256=full,
                experiment=experiment_to_data(experiment),
                history=(),
            )
            self._save_unlocked(record)
            loaded = self._load_unlocked()
            if loaded is None:
                raise WorkspaceConflictError("workspace initialization was not durable")
            return loaded[0]

    def load(self) -> tuple[WorkspaceVersionRecord, Experiment]:
        with CrossProcessFileLock(self.lock_path):
            loaded = self._load_unlocked()
            if loaded is None:
                raise WorkspaceConflictError("workspace is not initialized")
            return loaded

    def commit(
        self,
        *,
        candidate: Experiment,
        expected_version: int,
        expected_base_semantic_sha256: str,
        expected_base_full_sha256: str,
        target_semantic_sha256: str,
        target_full_sha256: str,
        preview_id: str,
        operation_id: str,
        run_id: str,
        lease_id: str,
        lease_generation: int,
        assert_lease_current: Callable[[str, str, int], Any] | None = None,
    ) -> WorkspaceVersionRecord:
        candidate_semantic, candidate_full = self._hashes(candidate)
        if candidate_semantic != target_semantic_sha256:
            raise WorkspaceConflictError("candidate semantic hash does not match approved target")
        if candidate_full != target_full_sha256:
            raise WorkspaceConflictError("candidate full hash does not match approved target")

        with CrossProcessFileLock(self.lock_path):
            loaded = self._load_unlocked()
            if loaded is None:
                raise WorkspaceConflictError("workspace is not initialized")
            current, current_experiment = loaded

            matching_receipts = [
                item for item in current.history if item.operation_id == operation_id
            ]
            if matching_receipts:
                receipt = matching_receipts[0]
                if (
                    receipt.preview_id == preview_id
                    and receipt.target_semantic_sha256 == target_semantic_sha256
                    and receipt.target_full_sha256 == target_full_sha256
                ):
                    raise WorkspaceConflictError(
                        "operation was already committed in an earlier workspace version"
                    )
                raise WorkspaceConflictError(
                    "operation_id is already bound to a different workspace commit"
                )

            current_semantic, current_full = self._hashes(current_experiment)
            if current.version != expected_version:
                raise WorkspaceConflictError(
                    f"workspace version changed: expected {expected_version}, found {current.version}"
                )
            if current_semantic != expected_base_semantic_sha256:
                raise WorkspaceConflictError("workspace semantic base changed since preview")
            if current_full != expected_base_full_sha256:
                raise WorkspaceConflictError("workspace full base changed since preview")

            if assert_lease_current is None:
                raise WorkspaceConflictError(
                    "workspace mutation requires a transaction-bound lease assertion"
                )
            try:
                assert_lease_current(run_id, lease_id, lease_generation)
            except Exception as exc:
                raise WorkspaceConflictError(
                    f"workspace lease fencing changed at commit boundary: {exc}"
                ) from exc

            committed_unix = float(self._clock())
            next_version = current.version + 1
            receipt = WorkspaceCommitReceipt(
                version=next_version,
                parent_version=current.version,
                committed_unix=committed_unix,
                operation_id=operation_id,
                preview_id=preview_id,
                lease_id=lease_id,
                lease_generation=lease_generation,
                base_semantic_sha256=current_semantic,
                base_full_sha256=current_full,
                target_semantic_sha256=target_semantic_sha256,
                target_full_sha256=target_full_sha256,
            )
            record = WorkspaceVersionRecord(
                workspace_id=self.workspace_id,
                version=next_version,
                parent_version=current.version,
                committed_unix=committed_unix,
                operation_id=operation_id,
                preview_id=preview_id,
                lease_id=lease_id,
                lease_generation=lease_generation,
                base_semantic_sha256=current_semantic,
                base_full_sha256=current_full,
                target_semantic_sha256=target_semantic_sha256,
                target_full_sha256=target_full_sha256,
                experiment=experiment_to_data(candidate),
                history=current.history + (receipt,),
            )
            self._save_unlocked(record)

            verified = self._load_unlocked()
            if verified is None:
                raise WorkspaceConflictError("workspace commit disappeared after atomic replace")
            persisted_record, persisted_experiment = verified
            persisted_semantic, persisted_full = self._hashes(persisted_experiment)
            if persisted_record.version != record.version:
                raise WorkspaceConflictError("workspace version verification failed")
            if persisted_record.operation_id != operation_id:
                raise WorkspaceConflictError("workspace operation identity verification failed")
            if persisted_semantic != target_semantic_sha256:
                raise WorkspaceConflictError("workspace semantic post-commit verification failed")
            if persisted_full != target_full_sha256:
                raise WorkspaceConflictError("workspace full post-commit verification failed")
            return persisted_record

    def reconcile(
        self,
        *,
        operation_id: str,
        preview_id: str,
        target_semantic_sha256: str,
        target_full_sha256: str,
    ) -> WorkspaceCommitReceipt | None:
        with CrossProcessFileLock(self.lock_path):
            loaded = self._load_unlocked()
            if loaded is None:
                return None
            record, _experiment = loaded
            for receipt in reversed(record.history):
                if receipt.operation_id != operation_id:
                    continue
                if (
                    receipt.preview_id == preview_id
                    and receipt.target_semantic_sha256 == target_semantic_sha256
                    and receipt.target_full_sha256 == target_full_sha256
                ):
                    return receipt
                raise WorkspaceConflictError(
                    "operation_id receipt does not match requested preview/target"
                )
            return None
