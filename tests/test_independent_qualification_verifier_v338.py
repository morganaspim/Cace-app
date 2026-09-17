from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parents[1] / "scripts" / "verify_continuum_qualification_bundle.py"
spec = importlib.util.spec_from_file_location("independent_qualification_verifier", SCRIPT)
verify = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(verify)


def compact(value) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def pretty(value) -> bytes:
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


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build_fixture(tmp_path: Path) -> dict[str, object]:
    artifact_dir = tmp_path / "artifact"
    formal_dir = tmp_path / "formal"
    artifact_dir.mkdir()
    (formal_dir / "CACEFormal").mkdir(parents=True)

    audit_source_rel = "CACEFormal/V330AxiomAudit.lean"
    companion_rel = "CACEFormal/ContinuumEndpoint.lean"
    audit_source = (
        b"import CACEFormal.ContinuumEndpoint\n\n"
        b"theorem auditAnchor : True := by trivial\n"
    )
    companion_source = (
        b"theorem endpointOne : True := by trivial\n\n"
        b"theorem endpointTwo : True := by trivial\n"
    )
    (formal_dir / audit_source_rel).write_bytes(audit_source)
    (formal_dir / companion_rel).write_bytes(companion_source)
    manifest_bytes = b'{"version": "1.1.0", "packages": []}\n'
    (formal_dir / "lake-manifest.json").write_bytes(manifest_bytes)

    endpoints = ["CACEFormal.endpointOne", "CACEFormal.endpointTwo"]
    contract = {
        "allowed_axioms": ["Classical.choice"],
        "audited_source_files": [audit_source_rel, companion_rel],
        "build_target": "CACEFormal.V330AxiomAudit",
        "claim_id": verify.CLAIM_ID,
        "contract_id": "cace.proof.v330.test.v1",
        "dependency_pins": {
            "lean_toolchain": "leanprover/lean4:v4.32.1",
            "mathlib_commit": "5" * 40,
        },
        "endpoint_theorems": endpoints,
        "formal_system": "lean4",
        "nonclaims": ["Synthetic verifier test fixture only."],
        "required_checks": [
            "clean-tree",
            "lean-build",
            "kernel-axiom-audit",
            "lean-environment-theorem-metadata",
            "content-addressed-attestation",
        ],
        "theorem_dependency_metadata": {
            "note": "Synthetic Lean.Environment metadata test fixture.",
            "state": "LEAN_GENERATED",
        },
        "toolchain_file": "formal/cace_formal/lean-toolchain",
    }
    registry = {"contracts": [contract], "policy": "test", "schema_version": 1}
    proof_contracts = tmp_path / "proof_contracts.json"
    proof_contracts.write_bytes(pretty(registry))
    contract_sha = sha(compact(contract))

    audit = {
        "audit_source": audit_source_rel,
        "audit_source_sha256": sha(audit_source),
        "format": verify.AXIOM_AUDIT_FORMAT,
        "schema_version": 1,
        "theorem_count": len(endpoints),
        "theorems": [
            {"name": endpoints[0], "axioms": ["Classical.choice"]},
            {"name": endpoints[1], "axioms": []},
        ],
    }
    audit_bytes = pretty(audit)
    audit_sha = sha(audit_bytes)
    (artifact_dir / "v330_kernel_axiom_audit.json").write_bytes(audit_bytes)

    def endpoint_row(name: str, statement: str, direct: list[str], transitive: list[str]):
        direct = sorted(direct)
        transitive = sorted(transitive)
        return {
            "theorem": name,
            "declaration_kind": "theorem",
            "level_parameters": [],
            "statement_pp_all": statement,
            "statement_sha256": sha(statement.encode()),
            "statement_constants": ["True"],
            "direct_cace_theorem_dependencies": direct,
            "direct_cace_theorem_dependencies_sha256": sha(pretty(direct)),
            "transitive_cace_theorem_dependencies": transitive,
            "transitive_cace_theorem_dependencies_sha256": sha(pretty(transitive)),
        }

    rows = sorted(
        [
            endpoint_row(endpoints[0], "CACEFormal.endpointOne : True", [], []),
            endpoint_row(
                endpoints[1],
                "CACEFormal.endpointTwo : True",
                [endpoints[0]],
                [endpoints[0]],
            ),
        ],
        key=lambda item: item["theorem"],
    )
    git_commit = "e" * 40
    identity_payload = {
        "generator": verify.METADATA_GENERATOR,
        "provenance": verify.METADATA_PROVENANCE,
        "claim_id": verify.CLAIM_ID,
        "proof_contract_id": contract["contract_id"],
        "proof_contract_sha256": contract_sha,
        "git_commit": git_commit,
        "lean_version": "Lean (version 4.32.1, synthetic)",
        "lean_toolchain": contract["dependency_pins"]["lean_toolchain"],
        "mathlib_commit": contract["dependency_pins"]["mathlib_commit"],
        "kernel_axiom_audit_sha256": audit_sha,
        "kernel_axiom_audit_theorem_count": len(endpoints),
        "endpoints": rows,
    }
    identity_sha = sha(pretty(identity_payload))
    metadata = {
        "artifact_schema": verify.METADATA_SCHEMA,
        "claim_id": verify.CLAIM_ID,
        "endpoint_count": len(endpoints),
        "endpoints": rows,
        "generator": verify.METADATA_GENERATOR,
        "git_commit": git_commit,
        "identity_sha256": identity_sha,
        "kernel_axiom_audit_sha256": audit_sha,
        "kernel_axiom_audit_theorem_count": len(endpoints),
        "lean_toolchain": contract["dependency_pins"]["lean_toolchain"],
        "lean_version": identity_payload["lean_version"],
        "mathlib_commit": contract["dependency_pins"]["mathlib_commit"],
        "metadata_state": "LEAN_GENERATED",
        "proof_contract_id": contract["contract_id"],
        "proof_contract_sha256": contract_sha,
        "proof_effect": verify.METADATA_PROOF_EFFECT,
        "provenance": verify.METADATA_PROVENANCE,
    }
    metadata_bytes = pretty(metadata)
    metadata_sha = sha(metadata_bytes)
    (artifact_dir / "v330_lean_environment_metadata.json").write_bytes(metadata_bytes)

    source_digest = hashlib.sha256()
    for relative in contract["audited_source_files"]:
        source_digest.update(relative.encode())
        source_digest.update(b"\0")
        source_digest.update((formal_dir / relative).read_bytes())
        source_digest.update(b"\0")
    source_sha = source_digest.hexdigest()

    attestation = {
        "allowed_axioms": contract["allowed_axioms"],
        "attestation_schema": verify.ATTESTATION_SCHEMA,
        "audited_source_bundle_sha256": source_sha,
        "audited_source_files": contract["audited_source_files"],
        "build_target": contract["build_target"],
        "cache_policy": verify.CACHE_POLICY,
        "claim_id": verify.CLAIM_ID,
        "current_head_required": True,
        "endpoint_count": len(endpoints),
        "endpoint_theorems": endpoints,
        "formal_system": "lean4",
        "git_commit": git_commit,
        "kernel_axiom_audit_sha256": audit_sha,
        "lake_manifest_sha256": sha(manifest_bytes),
        "lean_environment_identity_sha256": identity_sha,
        "lean_environment_metadata_sha256": metadata_sha,
        "lean_toolchain": contract["dependency_pins"]["lean_toolchain"],
        "lean_version": identity_payload["lean_version"],
        "mathlib_commit": contract["dependency_pins"]["mathlib_commit"],
        "nonclaims": contract["nonclaims"],
        "proof_contract_id": contract["contract_id"],
        "proof_contract_sha256": contract_sha,
        "qualification_checks": contract["required_checks"],
        "qualification_run_id": "12345",
        "qualification_system": "github-actions",
        "runner_arch": "ARM64",
        "runner_name": "synthetic-runner",
        "status": "PASS",
        "workflow_run_attempt": 2,
        "workflow_run_id": 12345,
    }
    attestation_bytes = pretty(attestation)
    attestation_sha = sha(attestation_bytes)
    (artifact_dir / "cace_continuum_qualification_attestation.json").write_bytes(
        attestation_bytes
    )

    return {
        "artifact_dir": artifact_dir,
        "formal_dir": formal_dir,
        "proof_contracts": proof_contracts,
        "git_commit": git_commit,
        "attestation_sha": attestation_sha,
        "attestation": attestation,
        "contract_sha": contract_sha,
    }


def run_verify(fx: dict[str, object]):
    return verify.verify_bundle(
        artifact_dir=fx["artifact_dir"],
        proof_contracts_path=fx["proof_contracts"],
        formal_dir=fx["formal_dir"],
        expected_git_commit=fx["git_commit"],
        expected_attestation_sha256=fx["attestation_sha"],
        expected_workflow_run_id=12345,
        expected_workflow_run_attempt=2,
    )


def test_valid_bundle_is_independently_rederived(tmp_path: Path):
    fx = build_fixture(tmp_path)
    report = run_verify(fx)
    assert report["status"] == "PASS"
    assert report["proof_effect"] == "verification-of-recorded-evidence-only"
    assert report["git_commit"] == fx["git_commit"]
    assert report["proof_contract_sha256"] == fx["contract_sha"]
    assert report["attestation_sha256"] == fx["attestation_sha"]
    assert report["endpoint_count"] == 2


def test_audited_source_byte_drift_is_rejected(tmp_path: Path):
    fx = build_fixture(tmp_path)
    source = fx["formal_dir"] / "CACEFormal/ContinuumEndpoint.lean"
    source.write_text(source.read_text() + "\n-- drift\n", encoding="utf-8")
    with pytest.raises(verify.VerificationError, match="source bundle"):
        run_verify(fx)


def test_kernel_audit_byte_drift_is_rejected(tmp_path: Path):
    fx = build_fixture(tmp_path)
    path = fx["artifact_dir"] / "v330_kernel_axiom_audit.json"
    payload = json.loads(path.read_text())
    payload["theorems"][0]["axioms"] = []
    path.write_bytes(pretty(payload))
    with pytest.raises(verify.VerificationError, match="axiom audit SHA-256"):
        run_verify(fx)


def test_metadata_statement_drift_is_rejected(tmp_path: Path):
    fx = build_fixture(tmp_path)
    path = fx["artifact_dir"] / "v330_lean_environment_metadata.json"
    payload = json.loads(path.read_text())
    payload["endpoints"][0]["statement_pp_all"] += " -- tampered"
    path.write_bytes(pretty(payload))
    with pytest.raises(verify.VerificationError, match="metadata SHA-256"):
        run_verify(fx)


def test_lake_manifest_drift_is_rejected(tmp_path: Path):
    fx = build_fixture(tmp_path)
    path = fx["formal_dir"] / "lake-manifest.json"
    path.write_text(path.read_text() + " ", encoding="utf-8")
    with pytest.raises(verify.VerificationError, match="Lake manifest SHA-256"):
        run_verify(fx)


def test_external_workflow_run_anchor_is_enforced(tmp_path: Path):
    fx = build_fixture(tmp_path)
    with pytest.raises(verify.VerificationError, match="workflow_run_id differs"):
        verify.verify_bundle(
            artifact_dir=fx["artifact_dir"],
            proof_contracts_path=fx["proof_contracts"],
            formal_dir=fx["formal_dir"],
            expected_git_commit=fx["git_commit"],
            expected_attestation_sha256=fx["attestation_sha"],
            expected_workflow_run_id=99999,
            expected_workflow_run_attempt=2,
        )


def test_coordinated_inner_rehash_cannot_replace_external_attestation_anchor(tmp_path: Path):
    fx = build_fixture(tmp_path)
    metadata_path = fx["artifact_dir"] / "v330_lean_environment_metadata.json"
    metadata = json.loads(metadata_path.read_text())
    row = metadata["endpoints"][0]
    row["statement_pp_all"] = "CACEFormal.endpointOne : False"
    row["statement_sha256"] = sha(row["statement_pp_all"].encode())

    identity_payload = {
        key: metadata[key]
        for key in (
            "generator",
            "provenance",
            "claim_id",
            "proof_contract_id",
            "proof_contract_sha256",
            "git_commit",
            "lean_version",
            "lean_toolchain",
            "mathlib_commit",
            "kernel_axiom_audit_sha256",
            "kernel_axiom_audit_theorem_count",
            "endpoints",
        )
    }
    metadata["identity_sha256"] = sha(pretty(identity_payload))
    metadata_bytes = pretty(metadata)
    metadata_path.write_bytes(metadata_bytes)

    att_path = fx["artifact_dir"] / "cace_continuum_qualification_attestation.json"
    attestation = copy.deepcopy(fx["attestation"])
    attestation["lean_environment_metadata_sha256"] = sha(metadata_bytes)
    attestation["lean_environment_identity_sha256"] = metadata["identity_sha256"]
    att_path.write_bytes(pretty(attestation))

    with pytest.raises(verify.VerificationError, match="external trust anchor"):
        run_verify(fx)


def test_malformed_attestation_list_is_rejected_as_a_list(tmp_path: Path):
    fx = build_fixture(tmp_path)
    path = fx["artifact_dir"] / "cace_continuum_qualification_attestation.json"
    payload = json.loads(path.read_text())
    payload["endpoint_theorems"] = "not-a-list"
    data = pretty(payload)
    path.write_bytes(data)
    fx["attestation_sha"] = sha(data)
    with pytest.raises(verify.VerificationError, match="must be an array"):
        run_verify(fx)
