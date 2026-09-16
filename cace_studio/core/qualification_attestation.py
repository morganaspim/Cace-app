from __future__ import annotations

"""Fail-closed validation for exact-head formal qualification artifacts.

Qualification artifacts are deliberately external to the source commit they attest.
Committing a PASS record into that same source tree would change the Git commit and
make the record self-invalidating.  This module therefore validates an external
content-addressed attestation against an independently supplied artifact digest and
current Git commit before it can be used as a read-only ProofExplorer overlay.
"""

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from .proof_contract import ProofContractRegistry

ATTESTATION_SCHEMA = "cace-continuum-qualification-attestation-v2"
CACHE_POLICY = (
    "Pinned Lean/toolchain state and exact-pin dependencies may be reused only as inputs; "
    "CACE project build outputs, kernel audit results, theorem metadata, and attestations "
    "are regenerated in the isolated exact-head qualification run."
)
_ALLOWED_SYSTEMS = frozenset({"github-actions", "local-exact-head"})
_HEX = frozenset("0123456789abcdef")
_EXPECTED_KEYS = frozenset(
    {
        "attestation_schema",
        "status",
        "claim_id",
        "proof_contract_id",
        "proof_contract_sha256",
        "git_commit",
        "formal_system",
        "build_target",
        "lean_version",
        "lean_toolchain",
        "mathlib_commit",
        "audited_source_files",
        "audited_source_bundle_sha256",
        "endpoint_theorems",
        "endpoint_count",
        "allowed_axioms",
        "lake_manifest_sha256",
        "kernel_axiom_audit_sha256",
        "lean_environment_metadata_sha256",
        "lean_environment_identity_sha256",
        "qualification_checks",
        "qualification_system",
        "qualification_run_id",
        "workflow_run_id",
        "workflow_run_attempt",
        "runner_name",
        "runner_arch",
        "current_head_required",
        "cache_policy",
        "nonclaims",
    }
)


class QualificationAttestationError(ValueError):
    """Raised when an external qualification artifact cannot be trusted exactly."""


def _require_hex(value: Any, length: int, field: str) -> str:
    if not isinstance(value, str):
        raise QualificationAttestationError(f"{field} must be a string")
    normalized = value.strip().lower()
    if len(normalized) != length or any(ch not in _HEX for ch in normalized):
        raise QualificationAttestationError(f"{field} must be lowercase {length}-hex")
    return normalized


def _require_nonempty(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise QualificationAttestationError(f"{field} must be a non-empty string")
    return value.strip()


def _require_string_list(value: Any, field: str) -> tuple[str, ...]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise QualificationAttestationError(f"{field} must be a string array")
    return tuple(value)


def _require_positive_int(value: Any, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise QualificationAttestationError(f"{field} must be a positive integer")
    return value


@dataclass(frozen=True)
class VerifiedQualification:
    """A qualification artifact validated against an external digest and exact head."""

    claim_id: str
    proof_contract_id: str
    proof_contract_sha256: str
    git_commit: str
    proof_artifact_sha256: str
    qualification_system: str
    qualification_run_id: str
    workflow_run_id: int
    workflow_run_attempt: int
    checks: tuple[str, ...]
    endpoint_theorems: tuple[str, ...]
    source: str = "external-attestation"


def verify_qualification_attestation_bytes(
    data: bytes,
    *,
    expected_git_commit: str,
    expected_artifact_sha256: str,
    contracts: ProofContractRegistry | None = None,
) -> VerifiedQualification:
    """Validate exact artifact bytes against current head and the canonical contract.

    `expected_artifact_sha256` is intentionally required and must come from a trust
    channel outside the artifact bytes themselves (for example the accepted CI run
    metadata or a release manifest).  Supplying only a JSON file is insufficient.
    """

    if not isinstance(data, bytes):
        raise TypeError("qualification attestation data must be bytes")

    expected_commit = _require_hex(expected_git_commit, 40, "expected_git_commit")
    expected_digest = _require_hex(
        expected_artifact_sha256, 64, "expected_artifact_sha256"
    )
    actual_digest = hashlib.sha256(data).hexdigest()
    if actual_digest != expected_digest:
        raise QualificationAttestationError(
            "qualification artifact SHA-256 differs from the external trust anchor"
        )

    try:
        payload = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise QualificationAttestationError(
            "qualification artifact must be valid UTF-8 JSON"
        ) from exc
    if not isinstance(payload, Mapping):
        raise QualificationAttestationError("qualification artifact must be a JSON object")

    actual_keys = set(payload)
    if actual_keys != _EXPECTED_KEYS:
        missing = sorted(_EXPECTED_KEYS - actual_keys)
        extra = sorted(actual_keys - _EXPECTED_KEYS)
        raise QualificationAttestationError(
            f"qualification artifact keys mismatch; missing={missing}, extra={extra}"
        )

    if payload["attestation_schema"] != ATTESTATION_SCHEMA:
        raise QualificationAttestationError(
            f"unsupported qualification schema: {payload['attestation_schema']!r}"
        )
    if payload["status"] != "PASS":
        raise QualificationAttestationError("qualification artifact status must be PASS")
    if payload["current_head_required"] is not True:
        raise QualificationAttestationError("qualification artifact must require current head")

    claim_id = _require_nonempty(payload["claim_id"], "claim_id")
    registry = contracts or ProofContractRegistry.load_default()
    contract = registry.for_claim(claim_id)
    if contract is None:
        raise QualificationAttestationError(
            f"no canonical proof contract is bound to claim {claim_id!r}"
        )

    if payload["proof_contract_id"] != contract.contract_id:
        raise QualificationAttestationError("proof_contract_id differs from canonical contract")
    contract_sha = _require_hex(
        payload["proof_contract_sha256"], 64, "proof_contract_sha256"
    )
    if contract_sha != contract.contract_sha256:
        raise QualificationAttestationError(
            "proof_contract_sha256 differs from canonical contract"
        )

    git_commit = _require_hex(payload["git_commit"], 40, "git_commit")
    if git_commit != expected_commit:
        raise QualificationAttestationError(
            "qualification artifact does not attest the expected current Git commit"
        )

    if payload["formal_system"] != contract.formal_system:
        raise QualificationAttestationError("formal_system differs from canonical contract")
    if payload["build_target"] != contract.build_target:
        raise QualificationAttestationError("build_target differs from canonical contract")
    _require_nonempty(payload["lean_version"], "lean_version")
    lean_toolchain = _require_nonempty(payload["lean_toolchain"], "lean_toolchain")
    expected_toolchain = contract.dependency_pins.get("lean_toolchain")
    if not expected_toolchain:
        raise QualificationAttestationError(
            "canonical proof contract is missing the Lean toolchain dependency pin"
        )
    if lean_toolchain != expected_toolchain:
        raise QualificationAttestationError("Lean toolchain differs from canonical pin")

    mathlib_commit = _require_hex(payload["mathlib_commit"], 40, "mathlib_commit")
    if mathlib_commit != contract.dependency_pins.get("mathlib_commit"):
        raise QualificationAttestationError("Mathlib commit differs from canonical pin")

    source_files = _require_string_list(payload["audited_source_files"], "audited_source_files")
    if source_files != contract.audited_source_files:
        raise QualificationAttestationError(
            "audited_source_files differ from canonical proof contract"
        )

    endpoints = _require_string_list(payload["endpoint_theorems"], "endpoint_theorems")
    if endpoints != contract.endpoint_theorems:
        raise QualificationAttestationError(
            "endpoint_theorems differ from canonical proof contract"
        )
    if payload["endpoint_count"] != len(contract.endpoint_theorems):
        raise QualificationAttestationError("endpoint_count differs from canonical contract")

    axioms = _require_string_list(payload["allowed_axioms"], "allowed_axioms")
    if axioms != contract.allowed_axioms:
        raise QualificationAttestationError("allowed_axioms differ from canonical contract")

    checks = _require_string_list(payload["qualification_checks"], "qualification_checks")
    if checks != contract.required_checks or len(checks) != len(set(checks)):
        raise QualificationAttestationError(
            "qualification_checks differ from canonical proof contract"
        )

    nonclaims = _require_string_list(payload["nonclaims"], "nonclaims")
    if nonclaims != contract.nonclaims:
        raise QualificationAttestationError("nonclaims differ from canonical proof contract")

    for field in (
        "audited_source_bundle_sha256",
        "lake_manifest_sha256",
        "kernel_axiom_audit_sha256",
        "lean_environment_metadata_sha256",
        "lean_environment_identity_sha256",
    ):
        _require_hex(payload[field], 64, field)

    qualification_system = _require_nonempty(
        payload["qualification_system"], "qualification_system"
    )
    if qualification_system not in _ALLOWED_SYSTEMS:
        raise QualificationAttestationError(
            f"unsupported qualification_system: {qualification_system!r}"
        )
    qualification_run_id = _require_nonempty(
        payload["qualification_run_id"], "qualification_run_id"
    )
    workflow_run_id = _require_positive_int(payload["workflow_run_id"], "workflow_run_id")
    workflow_run_attempt = _require_positive_int(
        payload["workflow_run_attempt"], "workflow_run_attempt"
    )
    _require_nonempty(payload["runner_name"], "runner_name")
    _require_nonempty(payload["runner_arch"], "runner_arch")
    cache_policy = _require_nonempty(payload["cache_policy"], "cache_policy")
    if cache_policy != CACHE_POLICY:
        raise QualificationAttestationError(
            "cache_policy differs from the fail-closed qualification policy"
        )

    if qualification_system == "github-actions" and qualification_run_id != str(workflow_run_id):
        raise QualificationAttestationError(
            "GitHub qualification_run_id must equal workflow_run_id"
        )

    return VerifiedQualification(
        claim_id=claim_id,
        proof_contract_id=contract.contract_id,
        proof_contract_sha256=contract.contract_sha256,
        git_commit=git_commit,
        proof_artifact_sha256=actual_digest,
        qualification_system=qualification_system,
        qualification_run_id=qualification_run_id,
        workflow_run_id=workflow_run_id,
        workflow_run_attempt=workflow_run_attempt,
        checks=checks,
        endpoint_theorems=endpoints,
    )


def load_qualification_attestation(
    path: Path,
    *,
    expected_git_commit: str,
    expected_artifact_sha256: str,
    contracts: ProofContractRegistry | None = None,
) -> VerifiedQualification:
    return verify_qualification_attestation_bytes(
        path.read_bytes(),
        expected_git_commit=expected_git_commit,
        expected_artifact_sha256=expected_artifact_sha256,
        contracts=contracts,
    )
