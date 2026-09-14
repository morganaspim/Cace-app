from __future__ import annotations

from dataclasses import dataclass
from importlib.resources import files
import hashlib
import json
from typing import Any, Mapping


def _is_sha256(value: str | None) -> bool:
    if not value:
        return False
    value = value.strip().lower()
    return len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def _is_git_commit(value: str | None) -> bool:
    if not value:
        return False
    value = value.strip().lower()
    return len(value) == 40 and all(c in "0123456789abcdef" for c in value)


@dataclass(frozen=True)
class ProofLedgerEntry:
    release: str
    claim_ids: tuple[str, ...]
    status: str
    current_head_qualified: bool
    commit: str | None = None
    proof_artifact_sha256: str | None = None
    workflow_run_id: int | None = None
    checks: tuple[str, ...] = ()
    blockers: tuple[str, ...] = ()

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "ProofLedgerEntry":
        entry = cls(
            release=str(raw["release"]),
            claim_ids=tuple(str(x) for x in raw.get("claim_ids", ())),
            status=str(raw.get("status", "NOT_RUN")),
            current_head_qualified=bool(raw.get("current_head_qualified", False)),
            commit=(str(raw["commit"]).lower() if raw.get("commit") else None),
            proof_artifact_sha256=(
                str(raw["proof_artifact_sha256"]).lower()
                if raw.get("proof_artifact_sha256")
                else None
            ),
            workflow_run_id=(
                int(raw["workflow_run_id"]) if raw.get("workflow_run_id") is not None else None
            ),
            checks=tuple(str(x) for x in raw.get("checks", ())),
            blockers=tuple(str(x) for x in raw.get("blockers", ())),
        )
        if not entry.release.strip():
            raise ValueError("proof-ledger release must be non-empty")
        if not entry.claim_ids or any(not claim_id.strip() for claim_id in entry.claim_ids):
            raise ValueError(f"{entry.release}: proof-ledger claim_ids must be non-empty")
        if entry.current_head_qualified:
            if entry.status != "PASS":
                raise ValueError(
                    f"{entry.release}: current-head qualification requires status PASS"
                )
            if not _is_git_commit(entry.commit):
                raise ValueError(
                    f"{entry.release}: current-head qualification requires a 40-hex commit"
                )
            if not _is_sha256(entry.proof_artifact_sha256):
                raise ValueError(
                    f"{entry.release}: current-head qualification requires a 64-hex artifact hash"
                )
            if entry.workflow_run_id is None or entry.workflow_run_id <= 0:
                raise ValueError(
                    f"{entry.release}: current-head qualification requires a positive workflow_run_id"
                )
            if not entry.checks:
                raise ValueError(
                    f"{entry.release}: current-head qualification requires recorded qualification checks"
                )
            if entry.blockers:
                raise ValueError(
                    f"{entry.release}: current-head qualification cannot retain blockers"
                )
        return entry


@dataclass(frozen=True)
class ProofLedger:
    schema_version: int
    policy: str
    entries: tuple[ProofLedgerEntry, ...]
    ledger_sha256: str

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "ProofLedger":
        payload = json.dumps(raw, sort_keys=True, separators=(",", ":")).encode()
        entries = tuple(ProofLedgerEntry.from_mapping(x) for x in raw.get("entries", ()))
        seen: dict[str, str] = {}
        for entry in entries:
            for claim_id in entry.claim_ids:
                if claim_id in seen:
                    raise ValueError(
                        f"claim {claim_id!r} appears in multiple proof-ledger entries: "
                        f"{seen[claim_id]!r}, {entry.release!r}"
                    )
                seen[claim_id] = entry.release
        return cls(
            schema_version=int(raw.get("schema_version", 0)),
            policy=str(raw.get("policy", "fail-closed")),
            entries=entries,
            ledger_sha256=hashlib.sha256(payload).hexdigest(),
        )

    @classmethod
    def load_default(cls) -> "ProofLedger":
        path = files("cace_studio").joinpath("data/proof_ledger.json")
        raw = json.loads(path.read_text(encoding="utf-8"))
        return cls.from_mapping(raw)

    def for_claim(self, claim_id: str) -> ProofLedgerEntry | None:
        for entry in self.entries:
            if claim_id in entry.claim_ids:
                return entry
        return None
