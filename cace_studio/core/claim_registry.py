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
class ClaimEntry:
    claim_id: str
    module_ids: tuple[str, ...]
    statement: str
    scope: str
    evidence_ceiling: str
    qualification_status: str
    current_head_qualified: bool
    attested_commit: str | None = None
    proof_artifact_sha256: str | None = None
    reason: str = ""
    nonclaims: tuple[str, ...] = ()

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "ClaimEntry":
        q = raw.get("qualification", {})
        entry = cls(
            claim_id=str(raw["claim_id"]),
            module_ids=tuple(str(x) for x in raw.get("module_ids", ())),
            statement=str(raw["statement"]),
            scope=str(raw.get("scope", "")),
            evidence_ceiling=str(raw.get("evidence_ceiling", "experimental")),
            qualification_status=str(q.get("status", "UNQUALIFIED")),
            current_head_qualified=bool(q.get("current_head_qualified", False)),
            attested_commit=(
                str(q["attested_commit"]).lower() if q.get("attested_commit") else None
            ),
            proof_artifact_sha256=(
                str(q["proof_artifact_sha256"]).lower()
                if q.get("proof_artifact_sha256")
                else None
            ),
            reason=str(q.get("reason", "")),
            nonclaims=tuple(str(x) for x in raw.get("nonclaims", ())),
        )
        if not entry.claim_id.strip():
            raise ValueError("claim_id must be non-empty")
        if entry.current_head_qualified:
            if entry.qualification_status != "PASS":
                raise ValueError(
                    f"{entry.claim_id}: current-head qualification requires status PASS"
                )
            if entry.evidence_ceiling not in {"formally-verified", "cross-verified"}:
                raise ValueError(
                    f"{entry.claim_id}: current-head FORMAL qualification requires "
                    "a formally-verified or cross-verified evidence ceiling"
                )
            if not _is_git_commit(entry.attested_commit):
                raise ValueError(
                    f"{entry.claim_id}: current-head formal qualification requires "
                    "a 40-hex attested_commit"
                )
            if not _is_sha256(entry.proof_artifact_sha256):
                raise ValueError(
                    f"{entry.claim_id}: current-head formal qualification requires "
                    "a 64-hex proof_artifact_sha256"
                )
        return entry


@dataclass(frozen=True)
class ClaimRegistry:
    schema_version: int
    policy: str
    claims: tuple[ClaimEntry, ...]
    registry_sha256: str

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "ClaimRegistry":
        payload = json.dumps(raw, sort_keys=True, separators=(",", ":")).encode()
        claims = tuple(ClaimEntry.from_mapping(x) for x in raw.get("claims", ()))
        seen_claims: set[str] = set()
        seen_modules: dict[str, str] = {}
        for claim in claims:
            if claim.claim_id in seen_claims:
                raise ValueError(f"duplicate claim_id: {claim.claim_id}")
            seen_claims.add(claim.claim_id)
            for module_id in claim.module_ids:
                prior = seen_modules.get(module_id)
                if prior is not None:
                    raise ValueError(
                        f"module {module_id!r} is mapped to multiple claims: "
                        f"{prior!r}, {claim.claim_id!r}"
                    )
                seen_modules[module_id] = claim.claim_id
        return cls(
            schema_version=int(raw.get("schema_version", 0)),
            policy=str(raw.get("policy", "fail-closed")),
            claims=claims,
            registry_sha256=hashlib.sha256(payload).hexdigest(),
        )

    @classmethod
    def load_default(cls) -> "ClaimRegistry":
        path = files("cace_studio").joinpath("data/claim_registry.json")
        raw = json.loads(path.read_text(encoding="utf-8"))
        return cls.from_mapping(raw)

    def for_module(self, module_id: str) -> ClaimEntry | None:
        for claim in self.claims:
            if module_id in claim.module_ids:
                return claim
        return None

    def by_id(self, claim_id: str) -> ClaimEntry | None:
        for claim in self.claims:
            if claim.claim_id == claim_id:
                return claim
        return None
