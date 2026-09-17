from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts import verify_v330_qualification_bundle as verifier


def _write_json(path: Path, value: dict) -> str:
    data = verifier.canonical_json_bytes(value)
    path.write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()
    path.with_suffix(path.suffix + ".sha256").write_text(f"{digest}  {path.name}\n")
    return digest


def _bundle(tmp_path: Path) -> Path:
    theorem = "CACEFormal.Continuum.synthetic"
    statement = "Synthetic : True"
    direct: list[str] = []
    transitive: list[str] = []
    endpoint = {
        "theorem": theorem,
        "declaration_kind": "theorem",
        "level_parameters": [],
        "statement_pp_all": statement,
        "statement_sha256": hashlib.sha256(statement.encode()).hexdigest(),
        "statement_constants": ["True"],
        "direct_cace_theorem_dependencies": direct,
        "direct_cace_theorem_dependencies_sha256": hashlib.sha256(verifier.canonical_json_bytes(direct)).hexdigest(),
        "transitive_cace_theorem_dependencies": transitive,
        "transitive_cace_theorem_dependencies_sha256": hashlib.sha256(verifier.canonical_json_bytes(transitive)).hexdigest(),
    }
    audit = {
        "audit_source": "CACEFormal/V330AxiomAudit.lean",
        "audit_source_sha256": "a" * 64,
        "format": verifier.EXPECTED_AUDIT_FORMAT,
        "schema_version": 1,
        "theorem_count": 1,
        "theorems": [{"name": theorem, "axioms": ["propext"]}],
    }
    audit_hash = _write_json(tmp_path / verifier.AXIOM_AUDIT, audit)
    identity_payload = {
        "generator": "CACEFormal.V330TheoremMetadata",
        "provenance": "Lean.Environment",
        "claim_id": verifier.EXPECTED_CLAIM,
        "proof_contract_id": "contract.test",
        "proof_contract_sha256": "b" * 64,
        "git_commit": "c" * 40,
        "lean_version": "Lean test",
        "lean_toolchain": "leanprover/lean4:v4.test",
        "mathlib_commit": "d" * 40,
        "kernel_axiom_audit_sha256": audit_hash,
        "kernel_axiom_audit_theorem_count": 1,
        "endpoints": [endpoint],
    }
    metadata = {
        "artifact_schema": verifier.EXPECTED_METADATA_SCHEMA,
        "metadata_state": "LEAN_GENERATED",
        **identity_payload,
        "identity_sha256": hashlib.sha256(verifier.canonical_json_bytes(identity_payload)).hexdigest(),
        "endpoint_count": 1,
        "proof_effect": "metadata only",
    }
    metadata_hash = _write_json(tmp_path / verifier.METADATA, metadata)
    attestation = {
        "attestation_schema": verifier.EXPECTED_ATTESTATION_SCHEMA,
        "status": "PASS",
        "claim_id": verifier.EXPECTED_CLAIM,
        "proof_contract_id": "contract.test",
        "proof_contract_sha256": "b" * 64,
        "git_commit": "c" * 40,
        "formal_system": "lean4",
        "build_target": "CACEFormal.V330AxiomAudit",
        "lean_version": "Lean test",
        "lean_toolchain": "leanprover/lean4:v4.test",
        "mathlib_commit": "d" * 40,
        "audited_source_files": ["CACEFormal/V330AxiomAudit.lean"],
        "audited_source_bundle_sha256": "e" * 64,
        "endpoint_theorems": [theorem],
        "endpoint_count": 1,
        "allowed_axioms": ["propext"],
        "lake_manifest_sha256": "f" * 64,
        "kernel_axiom_audit_sha256": audit_hash,
        "lean_environment_metadata_sha256": metadata_hash,
        "lean_environment_identity_sha256": metadata["identity_sha256"],
        "qualification_checks": ["lean-build"],
        "qualification_system": "github-actions",
        "qualification_run_id": "123",
        "workflow_run_id": 123,
        "workflow_run_attempt": 1,
        "runner_name": "test",
        "runner_arch": "ARM64",
        "current_head_required": True,
        "cache_policy": "test",
        "nonclaims": ["synthetic"],
    }
    _write_json(tmp_path / verifier.ATTESTATION, attestation)
    (tmp_path / verifier.COMMIT_MARKER).write_text("c" * 40 + "\n")
    (tmp_path / verifier.RUN_ID_MARKER).write_text("123\n")
    (tmp_path / verifier.RUN_ATTEMPT_MARKER).write_text("1\n")
    return tmp_path


def test_valid_synthetic_bundle_passes(tmp_path: Path):
    result = verifier.verify_bundle(_bundle(tmp_path))
    assert result["status"] == "PASS"
    assert result["endpoint_count"] == 1


def test_statement_drift_is_rejected_even_if_outer_file_hash_is_refreshed(tmp_path: Path):
    root = _bundle(tmp_path)
    path = root / verifier.METADATA
    metadata = json.loads(path.read_text())
    metadata["endpoints"][0]["statement_pp_all"] = "Synthetic : False"
    metadata_hash = _write_json(path, metadata)
    att_path = root / verifier.ATTESTATION
    attestation = json.loads(att_path.read_text())
    attestation["lean_environment_metadata_sha256"] = metadata_hash
    _write_json(att_path, attestation)
    with pytest.raises(verifier.BundleVerificationError, match="statement SHA-256 mismatch"):
        verifier.verify_bundle(root)


def test_forbidden_axiom_is_rejected():
    audit = {
        "format": verifier.EXPECTED_AUDIT_FORMAT,
        "theorem_count": 1,
        "theorems": [{"name": "T", "axioms": ["sorryAx"]}],
    }
    with pytest.raises(verifier.BundleVerificationError, match="sorryAx"):
        verifier.verify_axiom_audit(audit, allowed_axioms={"propext"})


def test_marker_mismatch_is_rejected(tmp_path: Path):
    root = _bundle(tmp_path)
    (root / verifier.COMMIT_MARKER).write_text("0" * 40 + "\n")
    with pytest.raises(verifier.BundleVerificationError, match="commit.txt mismatch"):
        verifier.verify_bundle(root)


def test_contract_cross_binding_rejects_semantic_endpoint_mismatch(tmp_path: Path):
    contract = {
        "contract_id": "contract.test",
        "claim_id": verifier.EXPECTED_CLAIM,
        "formal_system": "lean4",
        "build_target": "CACEFormal.V330AxiomAudit",
        "toolchain_file": "formal/cace_formal/lean-toolchain",
        "dependency_pins": {"lean_toolchain": "leanprover/lean4:v4.test", "mathlib_commit": "d" * 40},
        "endpoint_theorems": ["T.actual"],
        "audited_source_files": ["CACEFormal/V330AxiomAudit.lean"],
        "allowed_axioms": ["propext"],
        "required_checks": ["lean-build"],
        "nonclaims": ["synthetic"],
        "theorem_dependency_metadata": {"state": "LEAN_GENERATED", "note": "test"},
    }
    path = tmp_path / "proof_contracts.json"
    path.write_text(json.dumps({"schema_version": 1, "contracts": [contract]}))
    attestation = {
        "proof_contract_id": "contract.test",
        "proof_contract_sha256": hashlib.sha256(verifier.compact_identity_bytes(contract)).hexdigest(),
        "claim_id": verifier.EXPECTED_CLAIM,
        "formal_system": "lean4",
        "build_target": "CACEFormal.V330AxiomAudit",
        "endpoint_theorems": ["T.different"],
        "audited_source_files": ["CACEFormal/V330AxiomAudit.lean"],
        "allowed_axioms": ["propext"],
        "qualification_checks": ["lean-build"],
        "nonclaims": ["synthetic"],
        "lean_toolchain": "leanprover/lean4:v4.test",
        "mathlib_commit": "d" * 40,
    }
    with pytest.raises(verifier.BundleVerificationError, match="endpoint_theorems mismatch"):
        verifier.verify_proof_contract_file(path, attestation)
