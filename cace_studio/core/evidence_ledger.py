from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from .reproducibility import canonical_json_bytes, canonical_json_text

EVIDENCE_BUNDLE_SCHEMA = "cace-evidence-bundle-v1"
EVIDENCE_LEDGER_SCHEMA = "cace-evidence-ledger-v1"
IDENTITY_ALGORITHM = "sha256/cace-canonical-json-v1"
MERKLE_ALGORITHM = "sha256/cace-merkle-v1"
CHAIN_ALGORITHM = "sha256/cace-ledger-chain-v1"
PROOF_EFFECT = "none"

_DOMAIN_ARTIFACT_LEAF = b"CACE:EVIDENCE:ARTIFACT-LEAF:v1\0"
_DOMAIN_MERKLE_NODE = b"CACE:EVIDENCE:MERKLE-NODE:v1\0"
_DOMAIN_BUNDLE = b"CACE:EVIDENCE:BUNDLE:v1\0"
_DOMAIN_LEDGER_ENTRY = b"CACE:EVIDENCE:LEDGER-ENTRY:v1\0"

_HEX = frozenset("0123456789abcdef")


class EvidenceLedgerError(ValueError):
    """Raised when evidence provenance fails closed validation."""


def _require_sha256(value: str, field_name: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(ch not in _HEX for ch in value):
        raise EvidenceLedgerError(f"{field_name} must be a lowercase 64-character SHA-256 hex digest")
    return value


def _domain_hash(domain: bytes, payload: Any) -> str:
    return hashlib.sha256(domain + canonical_json_bytes(payload)).hexdigest()


def sha256_bytes(data: bytes) -> str:
    if not isinstance(data, bytes):
        raise TypeError("sha256_bytes requires bytes")
    return hashlib.sha256(data).hexdigest()


@dataclass(frozen=True)
class EvidenceArtifact:
    artifact_id: str
    sha256: str
    size_bytes: int
    role: str
    media_type: str = "application/octet-stream"
    path: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.artifact_id, str) or not self.artifact_id:
            raise EvidenceLedgerError("artifact_id must be a non-empty string")
        _require_sha256(self.sha256, "artifact sha256")
        if not isinstance(self.size_bytes, int) or isinstance(self.size_bytes, bool) or self.size_bytes < 0:
            raise EvidenceLedgerError("size_bytes must be a non-negative integer")
        if not isinstance(self.role, str) or not self.role:
            raise EvidenceLedgerError("artifact role must be a non-empty string")
        if not isinstance(self.media_type, str) or not self.media_type:
            raise EvidenceLedgerError("media_type must be a non-empty string")
        if self.path is not None and not isinstance(self.path, str):
            raise EvidenceLedgerError("artifact path must be a string or null")
        if not isinstance(self.metadata, Mapping):
            raise EvidenceLedgerError("artifact metadata must be an object")

    @classmethod
    def from_bytes(
        cls,
        artifact_id: str,
        data: bytes,
        *,
        role: str,
        media_type: str = "application/octet-stream",
        path: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> "EvidenceArtifact":
        if not isinstance(data, bytes):
            raise TypeError("artifact data must be bytes")
        return cls(
            artifact_id=artifact_id,
            sha256=sha256_bytes(data),
            size_bytes=len(data),
            role=role,
            media_type=media_type,
            path=path,
            metadata={} if metadata is None else dict(metadata),
        )

    def payload(self) -> dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
            "role": self.role,
            "media_type": self.media_type,
            "path": self.path,
            "metadata": dict(self.metadata),
        }


def _sorted_artifacts(artifacts: Sequence[EvidenceArtifact]) -> tuple[EvidenceArtifact, ...]:
    ordered = tuple(sorted(artifacts, key=lambda item: (item.artifact_id, item.sha256)))
    ids = [item.artifact_id for item in ordered]
    if len(ids) != len(set(ids)):
        raise EvidenceLedgerError("artifact_id values must be unique within an evidence bundle")
    if not ordered:
        raise EvidenceLedgerError("an evidence bundle must contain at least one artifact")
    return ordered


def artifact_leaf_hash(artifact: EvidenceArtifact) -> str:
    return _domain_hash(_DOMAIN_ARTIFACT_LEAF, artifact.payload())


def merkle_root(artifacts: Sequence[EvidenceArtifact]) -> str:
    """Return a deterministic Merkle root over sorted artifact manifests.

    Caller ordering is deliberately ignored. If a level has an odd number of
    nodes, the last digest is duplicated before hashing the next level.
    """
    ordered = _sorted_artifacts(artifacts)
    level = [artifact_leaf_hash(item) for item in ordered]
    while len(level) > 1:
        if len(level) % 2:
            level.append(level[-1])
        next_level: list[str] = []
        for index in range(0, len(level), 2):
            left = _require_sha256(level[index], "left Merkle digest")
            right = _require_sha256(level[index + 1], "right Merkle digest")
            next_level.append(
                hashlib.sha256(
                    _DOMAIN_MERKLE_NODE + bytes.fromhex(left) + bytes.fromhex(right)
                ).hexdigest()
            )
        level = next_level
    return level[0]


@dataclass(frozen=True)
class EvidenceBundle:
    artifacts: tuple[EvidenceArtifact, ...]
    bindings: Mapping[str, Any] = field(default_factory=dict)
    notes: tuple[str, ...] = ()
    schema: str = EVIDENCE_BUNDLE_SCHEMA
    identity_algorithm: str = IDENTITY_ALGORITHM
    merkle_algorithm: str = MERKLE_ALGORITHM
    proof_effect: str = PROOF_EFFECT

    def __post_init__(self) -> None:
        if self.schema != EVIDENCE_BUNDLE_SCHEMA:
            raise EvidenceLedgerError(f"unsupported evidence bundle schema: {self.schema!r}")
        if self.identity_algorithm != IDENTITY_ALGORITHM:
            raise EvidenceLedgerError(f"unsupported identity algorithm: {self.identity_algorithm!r}")
        if self.merkle_algorithm != MERKLE_ALGORITHM:
            raise EvidenceLedgerError(f"unsupported Merkle algorithm: {self.merkle_algorithm!r}")
        if self.proof_effect != PROOF_EFFECT:
            raise EvidenceLedgerError(
                "evidence bundles are provenance-only and must have proof_effect='none'"
            )
        if not isinstance(self.bindings, Mapping):
            raise EvidenceLedgerError("evidence bundle bindings must be an object")
        if not isinstance(self.notes, tuple) or any(not isinstance(item, str) for item in self.notes):
            raise EvidenceLedgerError("evidence bundle notes must be a tuple of strings")
        _sorted_artifacts(self.artifacts)

    @property
    def merkle_root_sha256(self) -> str:
        return merkle_root(self.artifacts)

    def payload(self) -> dict[str, Any]:
        ordered = _sorted_artifacts(self.artifacts)
        return {
            "schema": self.schema,
            "identity_algorithm": self.identity_algorithm,
            "merkle_algorithm": self.merkle_algorithm,
            "proof_effect": self.proof_effect,
            "artifacts": [item.payload() for item in ordered],
            "merkle_root_sha256": self.merkle_root_sha256,
            "bindings": dict(self.bindings),
            "notes": list(self.notes),
        }

    @property
    def bundle_sha256(self) -> str:
        return _domain_hash(_DOMAIN_BUNDLE, self.payload())

    def canonical_json(self) -> str:
        return canonical_json_text(self.payload())


def verify_artifact_bytes(artifact: EvidenceArtifact, data: bytes) -> None:
    if len(data) != artifact.size_bytes:
        raise EvidenceLedgerError(
            f"artifact {artifact.artifact_id!r} size mismatch: "
            f"expected {artifact.size_bytes}, got {len(data)}"
        )
    actual = sha256_bytes(data)
    if actual != artifact.sha256:
        raise EvidenceLedgerError(
            f"artifact {artifact.artifact_id!r} SHA-256 mismatch: "
            f"expected {artifact.sha256}, got {actual}"
        )


def verify_bundle(
    bundle: EvidenceBundle,
    *,
    artifact_bytes: Mapping[str, bytes] | None = None,
) -> str:
    """Fail closed and return the canonical bundle digest when valid."""
    bundle.__post_init__()
    expected_root = merkle_root(bundle.artifacts)
    if expected_root != bundle.merkle_root_sha256:
        raise EvidenceLedgerError("evidence bundle Merkle root mismatch")
    if artifact_bytes is not None:
        expected_ids = {artifact.artifact_id for artifact in bundle.artifacts}
        supplied_ids = set(artifact_bytes)
        if supplied_ids != expected_ids:
            missing = sorted(expected_ids - supplied_ids)
            extra = sorted(supplied_ids - expected_ids)
            raise EvidenceLedgerError(
                f"artifact byte set mismatch; missing={missing}, extra={extra}"
            )
        for artifact in bundle.artifacts:
            verify_artifact_bytes(artifact, artifact_bytes[artifact.artifact_id])
    return bundle.bundle_sha256


@dataclass(frozen=True)
class LedgerEntry:
    sequence: int
    timestamp_utc: str
    bundle_sha256: str
    merkle_root_sha256: str
    previous_entry_sha256: str | None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    schema: str = EVIDENCE_LEDGER_SCHEMA
    chain_algorithm: str = CHAIN_ALGORITHM
    proof_effect: str = PROOF_EFFECT
    entry_sha256: str = ""

    def __post_init__(self) -> None:
        if self.schema != EVIDENCE_LEDGER_SCHEMA:
            raise EvidenceLedgerError(f"unsupported ledger schema: {self.schema!r}")
        if self.chain_algorithm != CHAIN_ALGORITHM:
            raise EvidenceLedgerError(f"unsupported chain algorithm: {self.chain_algorithm!r}")
        if self.proof_effect != PROOF_EFFECT:
            raise EvidenceLedgerError(
                "ledger entries are provenance-only and must have proof_effect='none'"
            )
        if not isinstance(self.sequence, int) or isinstance(self.sequence, bool) or self.sequence < 0:
            raise EvidenceLedgerError("ledger sequence must be a non-negative integer")
        if not isinstance(self.timestamp_utc, str) or not self.timestamp_utc:
            raise EvidenceLedgerError("timestamp_utc must be a non-empty string")
        _require_sha256(self.bundle_sha256, "bundle_sha256")
        _require_sha256(self.merkle_root_sha256, "merkle_root_sha256")
        if self.previous_entry_sha256 is not None:
            _require_sha256(self.previous_entry_sha256, "previous_entry_sha256")
        if self.entry_sha256:
            _require_sha256(self.entry_sha256, "entry_sha256")
        if not isinstance(self.metadata, Mapping):
            raise EvidenceLedgerError("ledger entry metadata must be an object")

    def body_payload(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "chain_algorithm": self.chain_algorithm,
            "proof_effect": self.proof_effect,
            "sequence": self.sequence,
            "timestamp_utc": self.timestamp_utc,
            "bundle_sha256": self.bundle_sha256,
            "merkle_root_sha256": self.merkle_root_sha256,
            "previous_entry_sha256": self.previous_entry_sha256,
            "metadata": dict(self.metadata),
        }

    def computed_entry_sha256(self) -> str:
        return _domain_hash(_DOMAIN_LEDGER_ENTRY, self.body_payload())

    def payload(self) -> dict[str, Any]:
        return {**self.body_payload(), "entry_sha256": self.entry_sha256}


def append_entry(
    entries: Sequence[LedgerEntry],
    bundle: EvidenceBundle,
    *,
    timestamp_utc: str,
    metadata: Mapping[str, Any] | None = None,
) -> LedgerEntry:
    verify_ledger(entries)
    bundle_sha256 = verify_bundle(bundle)
    previous = entries[-1].entry_sha256 if entries else None
    draft = LedgerEntry(
        sequence=len(entries),
        timestamp_utc=timestamp_utc,
        bundle_sha256=bundle_sha256,
        merkle_root_sha256=bundle.merkle_root_sha256,
        previous_entry_sha256=previous,
        metadata={} if metadata is None else dict(metadata),
    )
    return LedgerEntry(
        sequence=draft.sequence,
        timestamp_utc=draft.timestamp_utc,
        bundle_sha256=draft.bundle_sha256,
        merkle_root_sha256=draft.merkle_root_sha256,
        previous_entry_sha256=draft.previous_entry_sha256,
        metadata=draft.metadata,
        schema=draft.schema,
        chain_algorithm=draft.chain_algorithm,
        proof_effect=draft.proof_effect,
        entry_sha256=draft.computed_entry_sha256(),
    )


def verify_ledger(
    entries: Sequence[LedgerEntry],
    *,
    bundles: Mapping[str, EvidenceBundle] | None = None,
) -> str | None:
    """Verify sequence, hashes and previous-hash links from genesis.

    Returns the tip digest, or None for an empty ledger.
    """
    previous: str | None = None
    for expected_sequence, entry in enumerate(entries):
        entry.__post_init__()
        if entry.sequence != expected_sequence:
            raise EvidenceLedgerError(
                f"ledger sequence mismatch: expected {expected_sequence}, got {entry.sequence}"
            )
        if entry.previous_entry_sha256 != previous:
            raise EvidenceLedgerError(
                f"ledger previous hash mismatch at sequence {entry.sequence}"
            )
        computed = entry.computed_entry_sha256()
        if entry.entry_sha256 != computed:
            raise EvidenceLedgerError(
                f"ledger entry hash mismatch at sequence {entry.sequence}: "
                f"expected {computed}, got {entry.entry_sha256 or '<empty>'}"
            )
        if bundles is not None:
            if entry.bundle_sha256 not in bundles:
                raise EvidenceLedgerError(
                    f"ledger bundle {entry.bundle_sha256} is unavailable for verification"
                )
            bundle = bundles[entry.bundle_sha256]
            actual_bundle = verify_bundle(bundle)
            if actual_bundle != entry.bundle_sha256:
                raise EvidenceLedgerError(
                    f"ledger bundle digest mismatch at sequence {entry.sequence}"
                )
            if bundle.merkle_root_sha256 != entry.merkle_root_sha256:
                raise EvidenceLedgerError(
                    f"ledger Merkle root mismatch at sequence {entry.sequence}"
                )
        previous = entry.entry_sha256
    return previous


def provenance_has_proof_effect(_: EvidenceBundle | LedgerEntry) -> bool:
    """Always false by design: provenance integrity cannot promote a proof claim."""
    return False


def _require_exact_keys(
    payload: Mapping[str, Any],
    expected: set[str],
    context: str,
) -> None:
    actual = set(payload)
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    if missing or extra:
        raise EvidenceLedgerError(
            f"{context} keys mismatch; missing={missing}, extra={extra}"
        )


def artifact_from_payload(payload: Mapping[str, Any]) -> EvidenceArtifact:
    if not isinstance(payload, Mapping):
        raise EvidenceLedgerError("artifact payload must be an object")
    _require_exact_keys(
        payload,
        {
            "artifact_id",
            "sha256",
            "size_bytes",
            "role",
            "media_type",
            "path",
            "metadata",
        },
        "artifact",
    )
    metadata = payload["metadata"]
    if not isinstance(metadata, Mapping):
        raise EvidenceLedgerError("artifact metadata must be an object")
    path = payload["path"]
    if path is not None and not isinstance(path, str):
        raise EvidenceLedgerError("artifact path must be a string or null")
    return EvidenceArtifact(
        artifact_id=payload["artifact_id"],
        sha256=payload["sha256"],
        size_bytes=payload["size_bytes"],
        role=payload["role"],
        media_type=payload["media_type"],
        path=path,
        metadata=dict(metadata),
    )


def bundle_from_payload(payload: Mapping[str, Any]) -> EvidenceBundle:
    """Parse a serialized evidence-bundle payload and verify its declared root."""
    if not isinstance(payload, Mapping):
        raise EvidenceLedgerError("evidence bundle payload must be an object")
    _require_exact_keys(
        payload,
        {
            "schema",
            "identity_algorithm",
            "merkle_algorithm",
            "proof_effect",
            "artifacts",
            "merkle_root_sha256",
            "bindings",
            "notes",
        },
        "evidence bundle",
    )
    raw_artifacts = payload["artifacts"]
    if not isinstance(raw_artifacts, list):
        raise EvidenceLedgerError("evidence bundle artifacts must be an array")
    bindings = payload["bindings"]
    if not isinstance(bindings, Mapping):
        raise EvidenceLedgerError("evidence bundle bindings must be an object")
    notes = payload["notes"]
    if not isinstance(notes, list) or any(not isinstance(item, str) for item in notes):
        raise EvidenceLedgerError("evidence bundle notes must be an array of strings")
    declared_root = _require_sha256(
        payload["merkle_root_sha256"], "merkle_root_sha256"
    )
    bundle = EvidenceBundle(
        artifacts=tuple(artifact_from_payload(item) for item in raw_artifacts),
        bindings=dict(bindings),
        notes=tuple(notes),
        schema=payload["schema"],
        identity_algorithm=payload["identity_algorithm"],
        merkle_algorithm=payload["merkle_algorithm"],
        proof_effect=payload["proof_effect"],
    )
    if bundle.merkle_root_sha256 != declared_root:
        raise EvidenceLedgerError(
            "serialized evidence bundle Merkle root does not match its artifact manifests"
        )
    return bundle


def ledger_entry_from_payload(payload: Mapping[str, Any]) -> LedgerEntry:
    if not isinstance(payload, Mapping):
        raise EvidenceLedgerError("ledger entry payload must be an object")
    _require_exact_keys(
        payload,
        {
            "schema",
            "chain_algorithm",
            "proof_effect",
            "sequence",
            "timestamp_utc",
            "bundle_sha256",
            "merkle_root_sha256",
            "previous_entry_sha256",
            "metadata",
            "entry_sha256",
        },
        "ledger entry",
    )
    metadata = payload["metadata"]
    if not isinstance(metadata, Mapping):
        raise EvidenceLedgerError("ledger entry metadata must be an object")
    return LedgerEntry(
        sequence=payload["sequence"],
        timestamp_utc=payload["timestamp_utc"],
        bundle_sha256=payload["bundle_sha256"],
        merkle_root_sha256=payload["merkle_root_sha256"],
        previous_entry_sha256=payload["previous_entry_sha256"],
        metadata=dict(metadata),
        schema=payload["schema"],
        chain_algorithm=payload["chain_algorithm"],
        proof_effect=payload["proof_effect"],
        entry_sha256=payload["entry_sha256"],
    )


def ledger_from_payload(payload: Any) -> tuple[LedgerEntry, ...]:
    """Parse an array of serialized ledger entries and verify the full chain."""
    if not isinstance(payload, list):
        raise EvidenceLedgerError("evidence ledger document must be an array")
    entries = tuple(ledger_entry_from_payload(item) for item in payload)
    verify_ledger(entries)
    return entries
