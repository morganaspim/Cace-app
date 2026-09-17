from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parents[1] / "scripts" / "verify_v330_qualification_source_binding.py"
spec = importlib.util.spec_from_file_location("source_binding_verifier", SCRIPT)
verifier = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(verifier)


def compact(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def pretty(value) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode()


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fixture(tmp_path: Path):
    root = tmp_path / "bundle"
    formal = tmp_path / "formal"
    root.mkdir()
    (formal / "CACEFormal").mkdir(parents=True)
    source_rel = "CACEFormal/V330AxiomAudit.lean"
    source = b"theorem T : True := by trivial\n"
    (formal / source_rel).write_bytes(source)
    manifest = b'{"version":"1.1.0","packages":[]}\n'
    (formal / "lake-manifest.json").write_bytes(manifest)
    (root / verifier.RESOLVED_MANIFEST).write_bytes(manifest)

    contract = {
        "contract_id": "contract.test",
        "claim_id": verifier.CLAIM_ID,
        "formal_system": "lean4",
        "build_target": "CACEFormal.V330AxiomAudit",
        "toolchain_file": "formal/cace_formal/lean-toolchain",
        "dependency_pins": {"lean_toolchain": "leanprover/lean4:v4.test", "mathlib_commit": "d" * 40},
        "endpoint_theorems": ["T"],
        "audited_source_files": [source_rel],
        "allowed_axioms": ["propext"],
        "required_checks": ["lean-build", "independent-source-bound-verification"],
        "nonclaims": ["synthetic"],
        "theorem_dependency_metadata": {"state": "LEAN_GENERATED", "note": "test"},
    }
    contracts = tmp_path / "proof_contracts.json"
    contracts.write_bytes(pretty({"schema_version": 1, "contracts": [contract]}))
    contract_sha = sha(compact(contract))

    audit = {
        "audit_source": source_rel,
        "audit_source_sha256": sha(source),
        "format": "cace.lean-theorem-metadata",
        "schema_version": 1,
        "theorem_count": 1,
        "theorems": [{"name": "T", "axioms": ["propext"]}],
    }
    audit_bytes = pretty(audit)
    (root / verifier.AXIOM_AUDIT).write_bytes(audit_bytes)
    audit_sha = sha(audit_bytes)

    commit = "c" * 40
    metadata = {
        "artifact_schema": "cace-lean-theorem-metadata-v3",
        "metadata_state": "LEAN_GENERATED",
        "generator": "CACEFormal.V330TheoremMetadata",
        "provenance": "Lean.Environment",
        "claim_id": verifier.CLAIM_ID,
        "proof_contract_id": contract["contract_id"],
        "proof_contract_sha256": contract_sha,
        "git_commit": commit,
        "lean_version": "Lean test",
        "lean_toolchain": contract["dependency_pins"]["lean_toolchain"],
        "mathlib_commit": contract["dependency_pins"]["mathlib_commit"],
        "kernel_axiom_audit_sha256": audit_sha,
        "kernel_axiom_audit_theorem_count": 1,
        "endpoints": [],
        "identity_sha256": "a" * 64,
        "endpoint_count": 1,
        "proof_effect": "metadata only",
    }
    meta_bytes = pretty(metadata)
    (root / verifier.METADATA).write_bytes(meta_bytes)

    source_digest = hashlib.sha256()
    source_digest.update(source_rel.encode())
    source_digest.update(b"\0")
    source_digest.update(source)
    source_digest.update(b"\0")
    attestation = {
        "attestation_schema": verifier.ATTESTATION_SCHEMA,
        "status": "PASS",
        "claim_id": verifier.CLAIM_ID,
        "proof_contract_id": contract["contract_id"],
        "proof_contract_sha256": contract_sha,
        "git_commit": commit,
        "formal_system": "lean4",
        "build_target": contract["build_target"],
        "lean_version": "Lean test",
        "lean_toolchain": contract["dependency_pins"]["lean_toolchain"],
        "mathlib_commit": contract["dependency_pins"]["mathlib_commit"],
        "audited_source_files": [source_rel],
        "audited_source_bundle_sha256": source_digest.hexdigest(),
        "endpoint_theorems": ["T"],
        "endpoint_count": 1,
        "allowed_axioms": ["propext"],
        "lake_manifest_sha256": sha(manifest),
        "kernel_axiom_audit_sha256": audit_sha,
        "lean_environment_metadata_sha256": sha(meta_bytes),
        "lean_environment_identity_sha256": "a" * 64,
        "qualification_checks": contract["required_checks"],
        "qualification_system": "github-actions",
        "qualification_run_id": "123",
        "workflow_run_id": 123,
        "workflow_run_attempt": 2,
        "runner_name": "test",
        "runner_arch": "ARM64",
        "current_head_required": True,
        "cache_policy": "test",
        "nonclaims": ["synthetic"],
    }
    att_bytes = pretty(attestation)
    (root / verifier.ATTESTATION).write_bytes(att_bytes)
    return {
        "root": root,
        "formal": formal,
        "contracts": contracts,
        "att_sha": sha(att_bytes),
        "commit": commit,
        "contract_sha": contract_sha,
    }


def run(fx):
    return verifier.verify_source_binding(
        fx["root"],
        formal_dir=fx["formal"],
        proof_contracts=fx["contracts"],
        expected_attestation_sha256=fx["att_sha"],
        expected_git_commit=fx["commit"],
        expected_workflow_run_id=123,
        expected_workflow_run_attempt=2,
    )


def test_valid_source_bound_bundle_passes(tmp_path: Path):
    fx = fixture(tmp_path)
    result = run(fx)
    assert result["status"] == "PASS"
    assert result["proof_contract_sha256"] == fx["contract_sha"]


def test_external_attestation_anchor_is_required(tmp_path: Path):
    fx = fixture(tmp_path)
    fx["att_sha"] = "0" * 64
    with pytest.raises(verifier.SourceBindingVerificationError, match="external SHA-256 trust anchor"):
        run(fx)


def test_source_byte_drift_is_rejected(tmp_path: Path):
    fx = fixture(tmp_path)
    path = fx["formal"] / "CACEFormal/V330AxiomAudit.lean"
    path.write_text(path.read_text() + "-- drift\n")
    with pytest.raises(verifier.SourceBindingVerificationError, match="source bundle"):
        run(fx)


def test_resolved_manifest_drift_is_rejected(tmp_path: Path):
    fx = fixture(tmp_path)
    path = fx["root"] / verifier.RESOLVED_MANIFEST
    path.write_text(path.read_text() + " ")
    with pytest.raises(verifier.SourceBindingVerificationError, match="Lake manifest"):
        run(fx)


def test_external_run_identity_is_enforced(tmp_path: Path):
    fx = fixture(tmp_path)
    with pytest.raises(verifier.SourceBindingVerificationError, match="workflow_run_id"):
        verifier.verify_source_binding(
            fx["root"],
            formal_dir=fx["formal"],
            proof_contracts=fx["contracts"],
            expected_attestation_sha256=fx["att_sha"],
            expected_git_commit=fx["commit"],
            expected_workflow_run_id=999,
            expected_workflow_run_attempt=2,
        )


def test_audit_source_digest_is_checked_against_source_bytes(tmp_path: Path):
    fx = fixture(tmp_path)
    audit_path = fx["root"] / verifier.AXIOM_AUDIT
    audit = json.loads(audit_path.read_text())
    audit["audit_source_sha256"] = "f" * 64
    audit_bytes = pretty(audit)
    audit_path.write_bytes(audit_bytes)

    meta_path = fx["root"] / verifier.METADATA
    meta = json.loads(meta_path.read_text())
    meta["kernel_axiom_audit_sha256"] = sha(audit_bytes)
    meta_bytes = pretty(meta)
    meta_path.write_bytes(meta_bytes)

    att_path = fx["root"] / verifier.ATTESTATION
    att = json.loads(att_path.read_text())
    att["kernel_axiom_audit_sha256"] = sha(audit_bytes)
    att["lean_environment_metadata_sha256"] = sha(meta_bytes)
    att_bytes = pretty(att)
    att_path.write_bytes(att_bytes)
    fx["att_sha"] = sha(att_bytes)

    with pytest.raises(verifier.SourceBindingVerificationError, match="audit source digest"):
        run(fx)
