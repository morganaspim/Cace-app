#!/usr/bin/env python3
"""Independently verify a CACE v3.30 qualification evidence bundle.

This verifier is intentionally standard-library-only and does not import the CACE
attestation producer or invoke Lean. It checks the already-produced evidence as an
independent consumer: content hashes, theorem identities, dependency identities,
axiom policy, and cross-artifact claim/contract/commit/run bindings.

Passing this verifier establishes internal integrity and consistency of the evidence
bundle. It does not independently re-prove the Lean theorems or establish the
identity/independence of the machine or person that produced the bundle.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import re
import tempfile
from typing import Any, Iterator, Mapping
import zipfile

ATTESTATION = "cace_continuum_qualification_attestation.json"
METADATA = "v330_lean_environment_metadata.json"
AXIOM_AUDIT = "v330_kernel_axiom_audit.json"
COMMIT_MARKER = "commit.txt"
RUN_ID_MARKER = "workflow_run_id.txt"
RUN_ATTEMPT_MARKER = "workflow_run_attempt.txt"
EXPECTED_ATTESTATION_SCHEMA = "cace-continuum-qualification-attestation-v2"
EXPECTED_METADATA_SCHEMA = "cace-lean-theorem-metadata-v3"
EXPECTED_AUDIT_FORMAT = "cace.lean-theorem-metadata"
EXPECTED_CLAIM = "cace.v330.continuum-proof-strengthening"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_GIT_COMMIT = re.compile(r"^[0-9a-f]{40}$")


class BundleVerificationError(RuntimeError):
    """Raised when qualification evidence fails independent verification."""


def canonical_json_bytes(value: Any) -> bytes:
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


def compact_identity_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise BundleVerificationError(message)


def require_sha256(value: Any, field: str) -> str:
    result = str(value).strip().lower()
    require(bool(_SHA256.fullmatch(result)), f"{field} must be lowercase 64-hex SHA-256")
    return result


def require_commit(value: Any, field: str) -> str:
    result = str(value).strip().lower()
    require(bool(_GIT_COMMIT.fullmatch(result)), f"{field} must be lowercase 40-hex Git commit")
    return result


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BundleVerificationError(f"cannot load JSON {path.name}: {exc}") from exc
    require(isinstance(value, dict), f"{path.name} must contain a JSON object")
    return value


def verify_hash_sidecar(path: Path) -> str:
    sidecar = path.with_suffix(path.suffix + ".sha256")
    require(sidecar.is_file(), f"missing hash sidecar: {sidecar.name}")
    fields = sidecar.read_text(encoding="utf-8").strip().split()
    require(len(fields) == 2, f"malformed hash sidecar: {sidecar.name}")
    expected = require_sha256(fields[0], f"{sidecar.name} digest")
    require(fields[1] == path.name, f"{sidecar.name} names {fields[1]!r}, expected {path.name!r}")
    actual = sha256_bytes(path.read_bytes())
    require(actual == expected, f"hash mismatch for {path.name}: expected {expected}, got {actual}")
    return actual


def verify_endpoint_record(item: Mapping[str, Any]) -> str:
    theorem = str(item.get("theorem", ""))
    require(bool(theorem), "metadata endpoint theorem name must be non-empty")
    require(item.get("declaration_kind") == "theorem", f"{theorem}: declaration_kind must be theorem")

    statement = item.get("statement_pp_all")
    require(isinstance(statement, str) and bool(statement.strip()), f"{theorem}: empty theorem statement")
    statement_hash = require_sha256(item.get("statement_sha256"), f"{theorem}.statement_sha256")
    require(sha256_bytes(statement.encode("utf-8")) == statement_hash, f"{theorem}: statement SHA-256 mismatch")

    direct = item.get("direct_cace_theorem_dependencies")
    transitive = item.get("transitive_cace_theorem_dependencies")
    require(isinstance(direct, list) and all(isinstance(x, str) and x for x in direct), f"{theorem}: invalid direct dependencies")
    require(isinstance(transitive, list) and all(isinstance(x, str) and x for x in transitive), f"{theorem}: invalid transitive dependencies")
    require(len(direct) == len(set(direct)), f"{theorem}: duplicate direct dependencies")
    require(len(transitive) == len(set(transitive)), f"{theorem}: duplicate transitive dependencies")
    require(theorem not in direct and theorem not in transitive, f"{theorem}: self-dependency")
    require(set(direct) <= set(transitive), f"{theorem}: transitive closure omits direct dependencies")

    direct_hash = require_sha256(item.get("direct_cace_theorem_dependencies_sha256"), f"{theorem}.direct dependency hash")
    transitive_hash = require_sha256(item.get("transitive_cace_theorem_dependencies_sha256"), f"{theorem}.transitive dependency hash")
    require(sha256_bytes(canonical_json_bytes(sorted(direct))) == direct_hash, f"{theorem}: direct dependency SHA-256 mismatch")
    require(sha256_bytes(canonical_json_bytes(sorted(transitive))) == transitive_hash, f"{theorem}: transitive dependency SHA-256 mismatch")
    return theorem


def verify_metadata_identity(metadata: Mapping[str, Any]) -> str:
    endpoints = metadata.get("endpoints")
    require(isinstance(endpoints, list) and endpoints, "metadata endpoints must be a non-empty array")
    names = [verify_endpoint_record(item) for item in endpoints if isinstance(item, Mapping)]
    require(len(names) == len(endpoints), "metadata endpoint must be an object")
    require(len(names) == len(set(names)), "metadata contains duplicate theorem records")
    require(metadata.get("endpoint_count") == len(names), "metadata endpoint_count mismatch")

    identity_payload = {
        "generator": metadata.get("generator"),
        "provenance": metadata.get("provenance"),
        "claim_id": metadata.get("claim_id"),
        "proof_contract_id": metadata.get("proof_contract_id"),
        "proof_contract_sha256": metadata.get("proof_contract_sha256"),
        "git_commit": metadata.get("git_commit"),
        "lean_version": metadata.get("lean_version"),
        "lean_toolchain": metadata.get("lean_toolchain"),
        "mathlib_commit": metadata.get("mathlib_commit"),
        "kernel_axiom_audit_sha256": metadata.get("kernel_axiom_audit_sha256"),
        "kernel_axiom_audit_theorem_count": metadata.get("kernel_axiom_audit_theorem_count"),
        "endpoints": endpoints,
    }
    actual = sha256_bytes(canonical_json_bytes(identity_payload))
    recorded = require_sha256(metadata.get("identity_sha256"), "metadata.identity_sha256")
    require(actual == recorded, f"Lean environment identity mismatch: expected {recorded}, got {actual}")
    return actual


def verify_axiom_audit(audit: Mapping[str, Any], *, allowed_axioms: set[str]) -> set[str]:
    require(audit.get("format") == EXPECTED_AUDIT_FORMAT, "unexpected kernel axiom audit format")
    theorems = audit.get("theorems")
    require(isinstance(theorems, list) and theorems, "kernel axiom audit theorem list must be non-empty")
    names: list[str] = []
    for item in theorems:
        require(isinstance(item, Mapping), "kernel axiom audit theorem record must be an object")
        name = str(item.get("name", ""))
        require(bool(name), "kernel axiom audit theorem name must be non-empty")
        axioms = item.get("axioms")
        require(isinstance(axioms, list) and all(isinstance(x, str) for x in axioms), f"{name}: invalid axiom list")
        require("sorryAx" not in axioms, f"{name}: sorryAx is forbidden")
        unexpected = sorted(set(axioms) - allowed_axioms)
        require(not unexpected, f"{name}: non-whitelisted axioms: {unexpected}")
        names.append(name)
    require(len(names) == len(set(names)), "kernel axiom audit contains duplicate theorem records")
    require(audit.get("theorem_count") == len(names), "kernel axiom audit theorem_count mismatch")
    return set(names)


def verify_proof_contract_file(path: Path, attestation: Mapping[str, Any]) -> None:
    raw = load_json(path)
    contracts = raw.get("contracts")
    require(isinstance(contracts, list), "proof-contract file contracts must be an array")
    wanted = [item for item in contracts if isinstance(item, Mapping) and item.get("contract_id") == attestation.get("proof_contract_id")]
    require(len(wanted) == 1, "expected exactly one matching proof contract")
    contract = dict(wanted[0])
    if not contract.get("executable_bindings"):
        contract.pop("executable_bindings", None)
    actual = sha256_bytes(compact_identity_bytes(contract))
    expected = require_sha256(attestation.get("proof_contract_sha256"), "attestation.proof_contract_sha256")
    require(actual == expected, f"proof-contract SHA-256 mismatch: expected {expected}, got {actual}")

    bindings = {
        "claim_id": "claim_id",
        "formal_system": "formal_system",
        "build_target": "build_target",
        "endpoint_theorems": "endpoint_theorems",
        "audited_source_files": "audited_source_files",
        "allowed_axioms": "allowed_axioms",
        "required_checks": "qualification_checks",
        "nonclaims": "nonclaims",
    }
    for contract_field, attestation_field in bindings.items():
        require(
            contract.get(contract_field) == attestation.get(attestation_field),
            f"proof-contract/attestation {contract_field} mismatch",
        )
    pins = contract.get("dependency_pins")
    require(isinstance(pins, Mapping), "proof contract dependency_pins must be an object")
    require(pins.get("lean_toolchain") == attestation.get("lean_toolchain"), "proof-contract/attestation Lean toolchain mismatch")
    require(pins.get("mathlib_commit") == attestation.get("mathlib_commit"), "proof-contract/attestation Mathlib commit mismatch")


def verify_bundle(root: Path, *, proof_contracts: Path | None = None) -> dict[str, Any]:
    att_path = root / ATTESTATION
    meta_path = root / METADATA
    audit_path = root / AXIOM_AUDIT
    for path in (att_path, meta_path, audit_path):
        require(path.is_file(), f"missing bundle file: {path.name}")

    att_hash = verify_hash_sidecar(att_path)
    meta_hash = verify_hash_sidecar(meta_path)
    audit_hash = verify_hash_sidecar(audit_path)
    att = load_json(att_path)
    meta = load_json(meta_path)
    audit = load_json(audit_path)

    require(att.get("attestation_schema") == EXPECTED_ATTESTATION_SCHEMA, "unsupported attestation schema")
    require(att.get("status") == "PASS", "attestation status must be PASS")
    require(att.get("claim_id") == EXPECTED_CLAIM, "unexpected claim_id")
    require(meta.get("artifact_schema") == EXPECTED_METADATA_SCHEMA, "unsupported theorem-metadata schema")
    require(meta.get("metadata_state") == "LEAN_GENERATED", "theorem metadata is not LEAN_GENERATED")

    commit = require_commit(att.get("git_commit"), "attestation.git_commit")
    require_commit(meta.get("git_commit"), "metadata.git_commit")
    require(meta.get("git_commit") == commit, "metadata/attestation commit mismatch")
    require(att.get("claim_id") == meta.get("claim_id"), "metadata/attestation claim mismatch")
    require(att.get("proof_contract_id") == meta.get("proof_contract_id"), "metadata/attestation proof-contract id mismatch")
    require(att.get("proof_contract_sha256") == meta.get("proof_contract_sha256"), "metadata/attestation proof-contract hash mismatch")
    require(att.get("lean_toolchain") == meta.get("lean_toolchain"), "metadata/attestation Lean toolchain mismatch")
    require(att.get("mathlib_commit") == meta.get("mathlib_commit"), "metadata/attestation Mathlib commit mismatch")

    require(require_sha256(att.get("lean_environment_metadata_sha256"), "attestation.lean_environment_metadata_sha256") == meta_hash, "attestation theorem-metadata file hash mismatch")
    require(require_sha256(att.get("kernel_axiom_audit_sha256"), "attestation.kernel_axiom_audit_sha256") == audit_hash, "attestation axiom-audit file hash mismatch")
    metadata_identity = verify_metadata_identity(meta)
    require(require_sha256(att.get("lean_environment_identity_sha256"), "attestation.lean_environment_identity_sha256") == metadata_identity, "attestation theorem-metadata identity mismatch")
    require(meta.get("kernel_axiom_audit_sha256") == audit_hash, "metadata axiom-audit hash mismatch")

    att_endpoints = att.get("endpoint_theorems")
    require(isinstance(att_endpoints, list) and len(att_endpoints) == len(set(att_endpoints)), "attestation endpoints must be unique array")
    meta_endpoints = {str(item.get("theorem")) for item in meta["endpoints"]}
    audit_endpoints = verify_axiom_audit(audit, allowed_axioms=set(att.get("allowed_axioms", [])))
    require(set(att_endpoints) == meta_endpoints == audit_endpoints, "endpoint theorem sets differ across attestation/metadata/audit")
    require(att.get("endpoint_count") == len(att_endpoints), "attestation endpoint_count mismatch")
    require(meta.get("kernel_axiom_audit_theorem_count") == len(audit_endpoints), "metadata axiom theorem count mismatch")

    markers = {
        COMMIT_MARKER: commit,
        RUN_ID_MARKER: str(att.get("workflow_run_id")),
        RUN_ATTEMPT_MARKER: str(att.get("workflow_run_attempt")),
    }
    for name, expected in markers.items():
        path = root / name
        require(path.is_file(), f"missing bundle marker: {name}")
        require(path.read_text(encoding="utf-8").strip() == expected, f"{name} mismatch")
    if att.get("qualification_system") == "github-actions":
        require(str(att.get("qualification_run_id")) == str(att.get("workflow_run_id")), "GitHub qualification run id mismatch")

    if proof_contracts is not None:
        verify_proof_contract_file(proof_contracts, att)

    return {
        "schema_version": 1,
        "status": "PASS",
        "claim_id": att["claim_id"],
        "git_commit": commit,
        "proof_contract_id": att["proof_contract_id"],
        "proof_contract_sha256": att["proof_contract_sha256"],
        "attestation_sha256": att_hash,
        "lean_environment_metadata_sha256": meta_hash,
        "lean_environment_identity_sha256": metadata_identity,
        "kernel_axiom_audit_sha256": audit_hash,
        "endpoint_count": len(att_endpoints),
        "workflow_run_id": att.get("workflow_run_id"),
        "workflow_run_attempt": att.get("workflow_run_attempt"),
        "proof_contract_file_verified": proof_contracts is not None,
        "verification_scope": "offline internal integrity/cross-binding; does not rerun Lean or establish producer independence",
    }


@contextmanager
def bundle_root(path: Path) -> Iterator[Path]:
    if path.is_dir():
        yield path
        return
    require(path.is_file() and zipfile.is_zipfile(path), "bundle must be a directory or ZIP archive")
    with tempfile.TemporaryDirectory(prefix="cace-qualification-verify-") as tmp:
        root = Path(tmp)
        with zipfile.ZipFile(path) as archive:
            for info in archive.infolist():
                target = (root / info.filename).resolve()
                require(root.resolve() in target.parents or target == root.resolve(), f"unsafe ZIP member path: {info.filename}")
            archive.extractall(root)
        yield root


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path, help="qualification artifact directory or ZIP archive")
    parser.add_argument("--proof-contracts", type=Path, help="optional canonical proof_contracts.json to verify contract identity")
    parser.add_argument("--output", type=Path, help="optional JSON verification report")
    args = parser.parse_args(argv)
    try:
        with bundle_root(args.bundle) as root:
            result = verify_bundle(root, proof_contracts=args.proof_contracts)
        code = 0
    except (BundleVerificationError, OSError, ValueError, zipfile.BadZipFile) as exc:
        result = {"schema_version": 1, "status": "FAIL", "error_type": type(exc).__name__, "error": str(exc)}
        code = 1
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
