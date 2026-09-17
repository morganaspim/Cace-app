#!/usr/bin/env python3
"""Independently verify a CACE continuum qualification artifact bundle.

This verifier intentionally uses only Python's standard library and does not import
CACE's qualification builder or runtime verification helpers. It independently
recomputes the proof-contract identity, outer attestation digest, audited Lean source
bundle digest, Lake manifest digest, kernel-axiom audit digest/content, Lean.Environment
metadata record hashes, and the metadata identity digest.

It is a verifier of recorded evidence, not a theorem prover. A PASS means the supplied
bundle is internally consistent with the supplied external trust anchors and the
canonical proof contract; it does not replace the Lean kernel run that produced the
bundle.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys
from typing import Any, Mapping

CLAIM_ID = "cace.v330.continuum-proof-strengthening"
ATTESTATION_SCHEMA = "cace-continuum-qualification-attestation-v2"
METADATA_SCHEMA = "cace-lean-theorem-metadata-v3"
METADATA_GENERATOR = "CACEFormal.V330TheoremMetadata"
METADATA_PROVENANCE = "Lean.Environment"
METADATA_PROOF_EFFECT = "metadata-and-audit-binding only; does not independently qualify a theorem"
AXIOM_AUDIT_FORMAT = "cace.lean-theorem-metadata"
CACHE_POLICY = (
    "Pinned Lean/toolchain state and exact-pin dependencies may be reused only as inputs; "
    "CACE project build outputs, kernel audit results, theorem metadata, and attestations "
    "are regenerated in the isolated exact-head qualification run."
)

_HEX40_RE = re.compile(r"^[0-9a-f]{40}$")
_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
_ATTESTATION_KEYS = {
    "attestation_schema", "status", "claim_id", "proof_contract_id",
    "proof_contract_sha256", "git_commit", "formal_system", "build_target",
    "lean_version", "lean_toolchain", "mathlib_commit", "audited_source_files",
    "audited_source_bundle_sha256", "endpoint_theorems", "endpoint_count",
    "allowed_axioms", "lake_manifest_sha256", "kernel_axiom_audit_sha256",
    "lean_environment_metadata_sha256", "lean_environment_identity_sha256",
    "qualification_checks", "qualification_system", "qualification_run_id",
    "workflow_run_id", "workflow_run_attempt", "runner_name", "runner_arch",
    "current_head_required", "cache_policy", "nonclaims",
}
_METADATA_KEYS = {
    "artifact_schema", "metadata_state", "generator", "provenance", "claim_id",
    "proof_contract_id", "proof_contract_sha256", "git_commit", "lean_version",
    "lean_toolchain", "mathlib_commit", "kernel_axiom_audit_sha256",
    "kernel_axiom_audit_theorem_count", "endpoints", "identity_sha256",
    "endpoint_count", "proof_effect",
}
_ENDPOINT_KEYS = {
    "theorem", "declaration_kind", "level_parameters", "statement_pp_all",
    "statement_sha256", "statement_constants", "direct_cace_theorem_dependencies",
    "direct_cace_theorem_dependencies_sha256", "transitive_cace_theorem_dependencies",
    "transitive_cace_theorem_dependencies_sha256",
}
_AUDIT_KEYS = {
    "audit_source", "audit_source_sha256", "format", "schema_version",
    "theorem_count", "theorems",
}
_AUDIT_THEOREM_KEYS = {"name", "axioms"}


class VerificationError(RuntimeError):
    """Raised when the independent verifier cannot establish exact consistency."""


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_json_bytes(path: Path, label: str) -> tuple[bytes, Mapping[str, Any]]:
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise VerificationError(f"{label} is unreadable: {path}: {exc}") from exc
    try:
        payload = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise VerificationError(f"{label} must be valid UTF-8 JSON: {exc}") from exc
    if not isinstance(payload, Mapping):
        raise VerificationError(f"{label} must be a JSON object")
    return data, payload


def _canonical_compact_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _canonical_pretty_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            separators=(",", ": "),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _require_exact_keys(payload: Mapping[str, Any], expected: set[str], label: str) -> None:
    actual = set(payload)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise VerificationError(f"{label} keys mismatch; missing={missing}, extra={extra}")


def _require_nonempty(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise VerificationError(f"{label} must be a non-empty string")
    return value.strip()


def _require_hex(value: Any, length: int, label: str) -> str:
    normalized = _require_nonempty(value, label).lower()
    regex = _HEX40_RE if length == 40 else _HEX64_RE if length == 64 else None
    if regex is None or regex.fullmatch(normalized) is None:
        raise VerificationError(f"{label} must be lowercase {length}-hex")
    return normalized


def _require_positive_int(value: Any, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise VerificationError(f"{label} must be a positive integer")
    return value


def _require_string_list(value: Any, label: str, *, unique: bool = True) -> tuple[str, ...]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        raise VerificationError(f"{label} must be an array of non-empty strings")
    result = tuple(value)
    if unique and len(result) != len(set(result)):
        raise VerificationError(f"{label} must not contain duplicates")
    return result


def _safe_relative_path(value: str, *, suffix: str | None = None) -> str:
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or not path.name:
        raise VerificationError(f"unsafe relative path: {value!r}")
    if suffix is not None and path.suffix != suffix:
        raise VerificationError(f"path must end in {suffix}: {value!r}")
    return path.as_posix()


def _normalize_executable_bindings(raw: Any) -> list[dict[str, Any]]:
    if raw in (None, []):
        return []
    if not isinstance(raw, list):
        raise VerificationError("proof contract executable_bindings must be an array")
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in raw:
        if not isinstance(item, Mapping):
            raise VerificationError("proof contract executable binding must be an object")
        _require_exact_keys(
            item,
            {"module_id", "source_files", "source_bundle_sha256"},
            "proof contract executable binding",
        )
        module_id = _require_nonempty(item["module_id"], "executable binding module_id")
        if module_id in seen:
            raise VerificationError("proof contract executable_bindings repeats module_id")
        seen.add(module_id)
        source_files = sorted(
            _safe_relative_path(path)
            for path in _require_string_list(item["source_files"], "executable binding source_files")
        )
        normalized.append(
            {
                "module_id": module_id,
                "source_files": source_files,
                "source_bundle_sha256": _require_hex(
                    item["source_bundle_sha256"], 64, "executable binding source_bundle_sha256"
                ),
            }
        )
    return sorted(normalized, key=lambda item: item["module_id"])


def load_contract(
    proof_contracts_path: Path,
    claim_id: str = CLAIM_ID,
) -> tuple[dict[str, Any], str]:
    _, registry = _read_json_bytes(proof_contracts_path, "proof-contract registry")
    contracts = registry.get("contracts")
    if not isinstance(contracts, list):
        raise VerificationError("proof-contract registry contracts must be an array")
    matches = [
        item
        for item in contracts
        if isinstance(item, Mapping) and item.get("claim_id") == claim_id
    ]
    if len(matches) != 1:
        raise VerificationError(
            f"expected exactly one proof contract for {claim_id!r}, found {len(matches)}"
        )
    raw = matches[0]
    dependency_pins = raw.get("dependency_pins")
    metadata = raw.get("theorem_dependency_metadata")
    if not isinstance(dependency_pins, Mapping) or not dependency_pins:
        raise VerificationError("proof contract dependency_pins must be a non-empty object")
    if not isinstance(metadata, Mapping):
        raise VerificationError("proof contract theorem_dependency_metadata must be an object")

    endpoints = list(
        _require_string_list(raw.get("endpoint_theorems"), "proof contract endpoint_theorems")
    )
    sources = [
        _safe_relative_path(path, suffix=".lean")
        for path in _require_string_list(
            raw.get("audited_source_files"), "proof contract audited_source_files"
        )
    ]
    allowed_axioms = list(
        _require_string_list(raw.get("allowed_axioms"), "proof contract allowed_axioms")
    )
    checks = list(_require_string_list(raw.get("required_checks"), "proof contract required_checks"))
    nonclaims = list(_require_string_list(raw.get("nonclaims"), "proof contract nonclaims"))

    payload: dict[str, Any] = {
        "contract_id": _require_nonempty(raw.get("contract_id"), "proof contract contract_id"),
        "claim_id": _require_nonempty(raw.get("claim_id"), "proof contract claim_id"),
        "formal_system": _require_nonempty(raw.get("formal_system"), "proof contract formal_system"),
        "build_target": _require_nonempty(raw.get("build_target"), "proof contract build_target"),
        "toolchain_file": _require_nonempty(raw.get("toolchain_file"), "proof contract toolchain_file"),
        "dependency_pins": {
            _require_nonempty(str(k), "dependency pin name"): _require_nonempty(
                v, f"dependency pin {k}"
            )
            for k, v in dependency_pins.items()
        },
        "endpoint_theorems": endpoints,
        "audited_source_files": sources,
        "allowed_axioms": allowed_axioms,
        "required_checks": checks,
        "nonclaims": nonclaims,
        "theorem_dependency_metadata": {
            "state": _require_nonempty(metadata.get("state"), "theorem metadata state"),
            "note": _require_nonempty(metadata.get("note"), "theorem metadata note"),
        },
    }
    bindings = _normalize_executable_bindings(raw.get("executable_bindings", []))
    if bindings:
        payload["executable_bindings"] = bindings
    return payload, _sha256_bytes(_canonical_compact_bytes(payload))


def audited_source_bundle_sha256(formal_dir: Path, source_files: tuple[str, ...]) -> str:
    root = formal_dir.resolve()
    digest = hashlib.sha256()
    for relative in source_files:
        relative = _safe_relative_path(relative, suffix=".lean")
        candidate = (root / PurePosixPath(relative)).resolve()
        try:
            candidate.relative_to(root)
        except ValueError as exc:
            raise VerificationError(f"audited source escapes formal directory: {relative}") from exc
        if not candidate.is_file():
            raise VerificationError(f"audited source file is missing: {relative}")
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(candidate.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def verify_axiom_audit(
    audit_bytes: bytes,
    audit: Mapping[str, Any],
    *,
    contract: Mapping[str, Any],
    formal_dir: Path,
    expected_sha256: str,
) -> str:
    actual_sha = _sha256_bytes(audit_bytes)
    if actual_sha != _require_hex(
        expected_sha256, 64, "attested kernel_axiom_audit_sha256"
    ):
        raise VerificationError("kernel axiom audit SHA-256 differs from attestation")
    _require_exact_keys(audit, _AUDIT_KEYS, "kernel axiom audit")
    if audit["format"] != AXIOM_AUDIT_FORMAT:
        raise VerificationError("kernel axiom audit format mismatch")
    if audit["schema_version"] != 1:
        raise VerificationError("kernel axiom audit schema_version mismatch")
    audit_source = _safe_relative_path(
        _require_nonempty(audit["audit_source"], "kernel axiom audit source"), suffix=".lean"
    )
    if audit_source not in set(contract["audited_source_files"]):
        raise VerificationError("kernel axiom audit source is outside the audited source bundle")
    formal_root = formal_dir.resolve()
    audit_source_path = (formal_root / PurePosixPath(audit_source)).resolve()
    try:
        audit_source_path.relative_to(formal_root)
    except ValueError as exc:
        raise VerificationError("kernel axiom audit source escapes formal directory") from exc
    if not audit_source_path.is_file():
        raise VerificationError(f"kernel axiom audit source is missing: {audit_source}")
    recorded_source_sha = _require_hex(
        audit["audit_source_sha256"], 64, "kernel axiom audit source SHA-256"
    )
    if _sha256_bytes(audit_source_path.read_bytes()) != recorded_source_sha:
        raise VerificationError("kernel axiom audit source SHA-256 mismatch")

    expected_endpoints = tuple(contract["endpoint_theorems"])
    if audit["theorem_count"] != len(expected_endpoints):
        raise VerificationError("kernel axiom audit theorem_count differs from proof contract")
    rows = audit["theorems"]
    if not isinstance(rows, list):
        raise VerificationError("kernel axiom audit theorems must be an array")
    allowed = set(contract["allowed_axioms"])
    names: list[str] = []
    for row in rows:
        if not isinstance(row, Mapping):
            raise VerificationError("kernel axiom audit theorem record must be an object")
        _require_exact_keys(row, _AUDIT_THEOREM_KEYS, "kernel axiom theorem record")
        name = _require_nonempty(row["name"], "kernel axiom theorem name")
        axioms = _require_string_list(row["axioms"], f"{name}.axioms")
        unexpected = sorted(set(axioms) - allowed)
        if unexpected:
            raise VerificationError(f"{name}: non-whitelisted axioms: {unexpected}")
        if "sorryAx" in axioms:
            raise VerificationError(f"{name}: sorryAx is forbidden")
        names.append(name)
    if len(names) != len(set(names)):
        raise VerificationError("kernel axiom audit contains duplicate theorem records")
    if set(names) != set(expected_endpoints):
        raise VerificationError("kernel axiom audit theorem set differs from proof contract")
    return actual_sha


def _verify_sorted_string_list(value: Any, label: str) -> tuple[str, ...]:
    values = _require_string_list(value, label)
    if list(values) != sorted(values):
        raise VerificationError(f"{label} must be canonically sorted")
    return values


def verify_environment_metadata(
    metadata_bytes: bytes,
    metadata: Mapping[str, Any],
    *,
    contract: Mapping[str, Any],
    contract_sha256: str,
    attestation: Mapping[str, Any],
    kernel_axiom_audit_sha256: str,
) -> tuple[str, str]:
    metadata_sha = _sha256_bytes(metadata_bytes)
    if metadata_sha != _require_hex(
        attestation["lean_environment_metadata_sha256"],
        64,
        "attested lean_environment_metadata_sha256",
    ):
        raise VerificationError("Lean environment metadata SHA-256 differs from attestation")
    _require_exact_keys(metadata, _METADATA_KEYS, "Lean environment metadata")
    expected_scalar = {
        "artifact_schema": METADATA_SCHEMA,
        "metadata_state": "LEAN_GENERATED",
        "generator": METADATA_GENERATOR,
        "provenance": METADATA_PROVENANCE,
        "claim_id": contract["claim_id"],
        "proof_contract_id": contract["contract_id"],
        "proof_contract_sha256": contract_sha256,
        "git_commit": attestation["git_commit"],
        "lean_version": attestation["lean_version"],
        "lean_toolchain": attestation["lean_toolchain"],
        "mathlib_commit": attestation["mathlib_commit"],
        "kernel_axiom_audit_sha256": kernel_axiom_audit_sha256,
        "kernel_axiom_audit_theorem_count": len(contract["endpoint_theorems"]),
        "endpoint_count": len(contract["endpoint_theorems"]),
        "proof_effect": METADATA_PROOF_EFFECT,
    }
    for field, expected in expected_scalar.items():
        if metadata[field] != expected:
            raise VerificationError(
                f"Lean environment metadata {field} mismatch: "
                f"expected {expected!r}, got {metadata[field]!r}"
            )

    rows = metadata["endpoints"]
    if not isinstance(rows, list):
        raise VerificationError("Lean environment metadata endpoints must be an array")
    expected_endpoints = tuple(contract["endpoint_theorems"])
    normalized_rows: list[Mapping[str, Any]] = []
    names: list[str] = []
    for row in rows:
        if not isinstance(row, Mapping):
            raise VerificationError("Lean endpoint record must be an object")
        _require_exact_keys(row, _ENDPOINT_KEYS, "Lean endpoint record")
        theorem = _require_nonempty(row["theorem"], "Lean endpoint theorem")
        if row["declaration_kind"] != "theorem":
            raise VerificationError(f"{theorem}: declaration_kind must be theorem")
        statement = _require_nonempty(row["statement_pp_all"], f"{theorem}.statement_pp_all")
        if _sha256_bytes(statement.encode("utf-8")) != _require_hex(
            row["statement_sha256"], 64, f"{theorem}.statement_sha256"
        ):
            raise VerificationError(f"{theorem}: statement_sha256 mismatch")

        level_parameters = _verify_sorted_string_list(
            row["level_parameters"], f"{theorem}.level_parameters"
        )
        statement_constants = _verify_sorted_string_list(
            row["statement_constants"], f"{theorem}.statement_constants"
        )
        direct = _verify_sorted_string_list(
            row["direct_cace_theorem_dependencies"],
            f"{theorem}.direct_cace_theorem_dependencies",
        )
        transitive = _verify_sorted_string_list(
            row["transitive_cace_theorem_dependencies"],
            f"{theorem}.transitive_cace_theorem_dependencies",
        )
        if theorem in direct or theorem in transitive:
            raise VerificationError(f"{theorem}: self-dependency is forbidden")
        if not set(direct).issubset(set(transitive)):
            raise VerificationError(
                f"{theorem}: transitive dependency closure omits direct dependencies"
            )
        direct_sha = _sha256_bytes(_canonical_pretty_bytes(list(direct)))
        transitive_sha = _sha256_bytes(_canonical_pretty_bytes(list(transitive)))
        if direct_sha != _require_hex(
            row["direct_cace_theorem_dependencies_sha256"],
            64,
            f"{theorem}.direct_cace_theorem_dependencies_sha256",
        ):
            raise VerificationError(f"{theorem}: direct dependency digest mismatch")
        if transitive_sha != _require_hex(
            row["transitive_cace_theorem_dependencies_sha256"],
            64,
            f"{theorem}.transitive_cace_theorem_dependencies_sha256",
        ):
            raise VerificationError(f"{theorem}: transitive dependency digest mismatch")
        names.append(theorem)
        normalized_rows.append(
            {
                "theorem": theorem,
                "declaration_kind": "theorem",
                "level_parameters": list(level_parameters),
                "statement_pp_all": statement,
                "statement_sha256": row["statement_sha256"],
                "statement_constants": list(statement_constants),
                "direct_cace_theorem_dependencies": list(direct),
                "direct_cace_theorem_dependencies_sha256": row[
                    "direct_cace_theorem_dependencies_sha256"
                ],
                "transitive_cace_theorem_dependencies": list(transitive),
                "transitive_cace_theorem_dependencies_sha256": row[
                    "transitive_cace_theorem_dependencies_sha256"
                ],
            }
        )
    if len(names) != len(set(names)):
        raise VerificationError("Lean environment metadata contains duplicate theorem records")
    if set(names) != set(expected_endpoints):
        raise VerificationError("Lean environment metadata theorem set differs from proof contract")
    if names != sorted(names):
        raise VerificationError("Lean environment metadata endpoint records must be canonically sorted")

    identity_payload = {
        "generator": METADATA_GENERATOR,
        "provenance": METADATA_PROVENANCE,
        "claim_id": contract["claim_id"],
        "proof_contract_id": contract["contract_id"],
        "proof_contract_sha256": contract_sha256,
        "git_commit": attestation["git_commit"],
        "lean_version": attestation["lean_version"],
        "lean_toolchain": attestation["lean_toolchain"],
        "mathlib_commit": attestation["mathlib_commit"],
        "kernel_axiom_audit_sha256": kernel_axiom_audit_sha256,
        "kernel_axiom_audit_theorem_count": len(expected_endpoints),
        "endpoints": normalized_rows,
    }
    identity_sha = _sha256_bytes(_canonical_pretty_bytes(identity_payload))
    recorded_identity = _require_hex(metadata["identity_sha256"], 64, "metadata identity_sha256")
    if identity_sha != recorded_identity:
        raise VerificationError("Lean environment metadata identity_sha256 mismatch")
    if identity_sha != _require_hex(
        attestation["lean_environment_identity_sha256"],
        64,
        "attested lean_environment_identity_sha256",
    ):
        raise VerificationError("Lean environment identity differs from attestation")
    return metadata_sha, identity_sha


def verify_bundle(
    *,
    artifact_dir: Path,
    proof_contracts_path: Path,
    formal_dir: Path,
    expected_git_commit: str,
    expected_attestation_sha256: str,
    expected_workflow_run_id: int | None,
    expected_workflow_run_attempt: int | None,
) -> dict[str, Any]:
    expected_commit = _require_hex(expected_git_commit, 40, "expected_git_commit")
    expected_attestation_sha = _require_hex(
        expected_attestation_sha256, 64, "expected_attestation_sha256"
    )
    contract, contract_sha = load_contract(proof_contracts_path)

    attestation_path = artifact_dir / "cace_continuum_qualification_attestation.json"
    metadata_path = artifact_dir / "v330_lean_environment_metadata.json"
    audit_path = artifact_dir / "v330_kernel_axiom_audit.json"
    attestation_bytes, attestation = _read_json_bytes(attestation_path, "qualification attestation")
    metadata_bytes, metadata = _read_json_bytes(metadata_path, "Lean environment metadata")
    audit_bytes, audit = _read_json_bytes(audit_path, "kernel axiom audit")

    actual_attestation_sha = _sha256_bytes(attestation_bytes)
    if actual_attestation_sha != expected_attestation_sha:
        raise VerificationError("qualification attestation SHA-256 differs from external trust anchor")
    _require_exact_keys(attestation, _ATTESTATION_KEYS, "qualification attestation")
    if attestation["attestation_schema"] != ATTESTATION_SCHEMA:
        raise VerificationError("qualification attestation schema mismatch")
    if attestation["status"] != "PASS":
        raise VerificationError("qualification attestation status must be PASS")
    if attestation["current_head_required"] is not True:
        raise VerificationError("qualification attestation must require exact current head")
    if attestation["cache_policy"] != CACHE_POLICY:
        raise VerificationError("qualification attestation cache policy mismatch")
    if attestation["claim_id"] != contract["claim_id"]:
        raise VerificationError("qualification attestation claim_id differs from proof contract")
    if attestation["proof_contract_id"] != contract["contract_id"]:
        raise VerificationError("qualification attestation proof_contract_id differs from proof contract")
    if _require_hex(attestation["proof_contract_sha256"], 64, "proof_contract_sha256") != contract_sha:
        raise VerificationError("qualification attestation proof_contract_sha256 mismatch")
    attested_commit = _require_hex(attestation["git_commit"], 40, "attested git_commit")
    if attested_commit != expected_commit:
        raise VerificationError("qualification attestation does not bind expected Git commit")
    if attestation["formal_system"] != contract["formal_system"]:
        raise VerificationError("qualification attestation formal_system mismatch")
    if attestation["build_target"] != contract["build_target"]:
        raise VerificationError("qualification attestation build_target mismatch")
    if attestation["lean_toolchain"] != contract["dependency_pins"].get("lean_toolchain"):
        raise VerificationError("qualification attestation Lean toolchain pin mismatch")
    attested_mathlib_commit = _require_hex(
        attestation["mathlib_commit"], 40, "attested mathlib_commit"
    )
    if attested_mathlib_commit != contract["dependency_pins"].get("mathlib_commit"):
        raise VerificationError("qualification attestation Mathlib pin mismatch")
    _require_nonempty(attestation["lean_version"], "attested lean_version")
    attested_sources = _require_string_list(
        attestation["audited_source_files"], "attested audited_source_files"
    )
    if attested_sources != tuple(contract["audited_source_files"]):
        raise VerificationError("qualification attestation audited_source_files mismatch")
    attested_endpoints = _require_string_list(
        attestation["endpoint_theorems"], "attested endpoint_theorems"
    )
    if attested_endpoints != tuple(contract["endpoint_theorems"]):
        raise VerificationError("qualification attestation endpoint_theorems mismatch")
    if attestation["endpoint_count"] != len(contract["endpoint_theorems"]):
        raise VerificationError("qualification attestation endpoint_count mismatch")
    attested_axioms = _require_string_list(attestation["allowed_axioms"], "attested allowed_axioms")
    if attested_axioms != tuple(contract["allowed_axioms"]):
        raise VerificationError("qualification attestation allowed_axioms mismatch")
    attested_checks = _require_string_list(
        attestation["qualification_checks"], "attested qualification_checks"
    )
    if attested_checks != tuple(contract["required_checks"]):
        raise VerificationError("qualification attestation qualification_checks mismatch")
    attested_nonclaims = _require_string_list(attestation["nonclaims"], "attested nonclaims")
    if attested_nonclaims != tuple(contract["nonclaims"]):
        raise VerificationError("qualification attestation nonclaims mismatch")

    qualification_system = _require_nonempty(attestation["qualification_system"], "qualification_system")
    qualification_run_id = _require_nonempty(attestation["qualification_run_id"], "qualification_run_id")
    workflow_run_id = _require_positive_int(attestation["workflow_run_id"], "workflow_run_id")
    workflow_run_attempt = _require_positive_int(
        attestation["workflow_run_attempt"], "workflow_run_attempt"
    )
    _require_nonempty(attestation["runner_name"], "runner_name")
    _require_nonempty(attestation["runner_arch"], "runner_arch")
    if qualification_system == "github-actions":
        if qualification_run_id != str(workflow_run_id):
            raise VerificationError("GitHub qualification_run_id must equal workflow_run_id")
        if expected_workflow_run_id is None:
            raise VerificationError(
                "expected_workflow_run_id is required for GitHub qualification evidence"
            )
    elif qualification_system != "local-exact-head":
        raise VerificationError(f"unsupported qualification_system: {qualification_system!r}")
    if expected_workflow_run_id is not None and workflow_run_id != expected_workflow_run_id:
        raise VerificationError("workflow_run_id differs from external trust anchor")
    if expected_workflow_run_attempt is not None and workflow_run_attempt != expected_workflow_run_attempt:
        raise VerificationError("workflow_run_attempt differs from external trust anchor")

    source_files = tuple(contract["audited_source_files"])
    source_bundle_sha = audited_source_bundle_sha256(formal_dir, source_files)
    if source_bundle_sha != _require_hex(
        attestation["audited_source_bundle_sha256"], 64, "audited_source_bundle_sha256"
    ):
        raise VerificationError("audited Lean source bundle SHA-256 differs from attestation")

    manifest_path = formal_dir / "lake-manifest.json"
    if not manifest_path.is_file():
        raise VerificationError(f"resolved Lake manifest is missing: {manifest_path}")
    manifest_sha = _sha256_bytes(manifest_path.read_bytes())
    if manifest_sha != _require_hex(
        attestation["lake_manifest_sha256"], 64, "lake_manifest_sha256"
    ):
        raise VerificationError("Lake manifest SHA-256 differs from attestation")

    audit_sha = verify_axiom_audit(
        audit_bytes,
        audit,
        contract=contract,
        formal_dir=formal_dir,
        expected_sha256=attestation["kernel_axiom_audit_sha256"],
    )
    metadata_sha, metadata_identity_sha = verify_environment_metadata(
        metadata_bytes,
        metadata,
        contract=contract,
        contract_sha256=contract_sha,
        attestation=attestation,
        kernel_axiom_audit_sha256=audit_sha,
    )

    return {
        "schema": "cace-independent-qualification-verification-v1",
        "status": "PASS",
        "proof_effect": "verification-of-recorded-evidence-only",
        "claim_id": contract["claim_id"],
        "proof_contract_id": contract["contract_id"],
        "proof_contract_sha256": contract_sha,
        "git_commit": expected_commit,
        "workflow_run_id": workflow_run_id,
        "workflow_run_attempt": workflow_run_attempt,
        "attestation_sha256": actual_attestation_sha,
        "audited_source_bundle_sha256": source_bundle_sha,
        "lake_manifest_sha256": manifest_sha,
        "kernel_axiom_audit_sha256": audit_sha,
        "lean_environment_metadata_sha256": metadata_sha,
        "lean_environment_identity_sha256": metadata_identity_sha,
        "endpoint_count": len(contract["endpoint_theorems"]),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--proof-contracts", type=Path, required=True)
    parser.add_argument("--formal-dir", type=Path, required=True)
    parser.add_argument("--expected-git-commit", required=True)
    parser.add_argument("--expected-attestation-sha256", required=True)
    parser.add_argument("--expected-workflow-run-id", type=int)
    parser.add_argument("--expected-workflow-run-attempt", type=int)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    try:
        report = verify_bundle(
            artifact_dir=args.artifact_dir,
            proof_contracts_path=args.proof_contracts,
            formal_dir=args.formal_dir,
            expected_git_commit=args.expected_git_commit,
            expected_attestation_sha256=args.expected_attestation_sha256,
            expected_workflow_run_id=args.expected_workflow_run_id,
            expected_workflow_run_attempt=args.expected_workflow_run_attempt,
        )
    except (VerificationError, OSError, ValueError, TypeError) as exc:
        print(f"independent qualification verification FAIL: {exc}", file=sys.stderr)
        return 2

    rendered = _canonical_pretty_bytes(report)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(rendered)
        args.output.with_suffix(args.output.suffix + ".sha256").write_text(
            f"{_sha256_bytes(rendered)}  {args.output.name}\n", encoding="utf-8"
        )
    sys.stdout.write(rendered.decode("utf-8"))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
