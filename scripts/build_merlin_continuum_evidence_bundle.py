from __future__ import annotations

import base64
import hashlib
import json
import os
import platform
from pathlib import Path
from typing import Any

from cace_studio.core.evidence_ledger import EvidenceArtifact, EvidenceBundle, verify_bundle
from cace_studio.core.reproducibility import canonical_json_bytes


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "collaboration" / "merlin-continuum"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: Any) -> bytes:
    return canonical_json_bytes(value)


def _cxx_envelope_digest(fields: dict[str, str]) -> str:
    # Exact byte-compatible implementation of the C++ producer's length-prefixed
    # canonical envelope encoding (all fields are UTF-8 strings).
    chunks = []
    for name in (
        "source_commit", "algorithm_version", "input_digest", "output_digest",
        "runner_identity", "runner_execution_id", "environment",
        "reproducibility_receipt_digest",
    ):
        value = fields[name]
        encoded = value.encode("utf-8")
        chunks.append(name.encode("ascii") + b"=" + str(len(encoded)).encode("ascii")
                      + b":" + encoded + b"\n")
    return _sha256(b"".join(chunks))


def build() -> dict[str, Any]:
    runner_temp = os.environ.get("RUNNER_TEMP")
    artifact_dir_name = os.environ.get("CACE_ARTIFACT_DIR")
    if not runner_temp or not artifact_dir_name:
        raise RuntimeError("CACE artifact directory is unavailable; refusing to emit an incomplete evidence bundle")
    output_dir = Path(runner_temp) / artifact_dir_name
    cpp_receipt_path = output_dir / "merlin-continuum-cpp-reproduction-receipt.json"
    python_receipt_path = output_dir / "merlin-continuum-independent-reference-receipt.json"
    if not cpp_receipt_path.is_file() or not python_receipt_path.is_file():
        raise RuntimeError("both C++ and independent Python reproduction receipts are required")

    binding = json.loads((FIXTURE / "SOURCE_BINDING.json").read_text(encoding="utf-8"))
    cpp_receipt = json.loads(cpp_receipt_path.read_text(encoding="utf-8"))
    python_receipt = json.loads(python_receipt_path.read_text(encoding="utf-8"))
    source_repo = binding["source_repository"]
    source_commit = binding["source_commit"]
    if source_repo != "Mannyspiro/expert-robot":
        raise RuntimeError("source repository is not allowlisted")
    if cpp_receipt.get("source_commit") != source_commit or python_receipt.get("source_commit") != source_commit:
        raise RuntimeError("reproduction receipts do not bind the exact source commit")

    persistence = cpp_receipt.get("persistence") or {}
    algorithm_version = persistence.get("persistence_algorithm_version")
    input_digest = persistence.get("persistence_input_sha256")
    output_digest = persistence.get("persistence_output_sha256")
    if not algorithm_version or any(
        not isinstance(value, str) or len(value) != 64
        or any(ch not in "0123456789abcdef" for ch in value)
        for value in (input_digest, output_digest)
    ):
        raise RuntimeError("C++ receipt omitted the exact persistence algorithm/input/output digests")

    runner = cpp_receipt["runner"]
    workflow = cpp_receipt["workflow"]
    runner_identity = runner["identity"]
    runner_execution_id = cpp_receipt["execution_id"]
    environment = runner["compiler"] + ";" + runner["platform"]
    reproducibility_receipt_digest = _sha256(_canonical({
        "cpp_receipt": cpp_receipt,
        "python_receipt": python_receipt,
    }))
    envelope_fields = {
        "source_commit": source_commit,
        "algorithm_version": algorithm_version,
        "input_digest": input_digest,
        "output_digest": output_digest,
        "runner_identity": runner_identity,
        "runner_execution_id": runner_execution_id,
        "environment": environment,
        "reproducibility_receipt_digest": reproducibility_receipt_digest,
    }
    envelope = {
        "schema": "merlin-persistence-evidence-envelope-v1",
        **envelope_fields,
        "envelope_digest": _cxx_envelope_digest(envelope_fields),
    }

    artifacts: list[EvidenceArtifact] = []
    artifact_bytes: dict[str, bytes] = {}
    source_manifest: list[dict[str, Any]] = []
    for item in binding["source_files"]:
        raw = (ROOT / item["fixture_path"]).read_bytes()
        artifact_id = "source-" + item["source_path"].replace("/", "__")
        source_manifest.append({
            "source_path": item["source_path"],
            "git_blob_sha1": item["git_blob_sha1"],
            "sha256": _sha256(raw),
            "size_bytes": len(raw),
        })
        artifact_bytes[artifact_id] = raw
        artifacts.append(EvidenceArtifact.from_bytes(
            artifact_id, raw, role="candidate-source",
            media_type="application/octet-stream", path=item["source_path"],
            metadata={"source_commit": source_commit, "git_blob_sha1": item["git_blob_sha1"]},
        ))

    independent_test_path = (
        "collaboration/merlin-continuum/tests/test_independent_integer_homology_reference.py"
    )
    independent_test_bytes = (ROOT / independent_test_path).read_bytes()
    support_items = [
        ("source-binding", (FIXTURE / "SOURCE_BINDING.json").read_bytes(),
         "source-binding", "collaboration/merlin-continuum/SOURCE_BINDING.json"),
        ("independent-python-reference", independent_test_bytes,
         "independent-reference-implementation", independent_test_path),
        ("cpp-runner-receipt", cpp_receipt_path.read_bytes(),
         "runner-execution-receipt", cpp_receipt_path.name),
        ("python-runner-receipt", python_receipt_path.read_bytes(),
         "independent-runner-execution-receipt", python_receipt_path.name),
        ("persistence-envelope", _canonical(envelope),
         "persistence-evidence-envelope", "merlin-persistence-evidence-envelope.json"),
    ]
    for artifact_id, raw, role, path in support_items:
        artifact_bytes[artifact_id] = raw
        artifacts.append(EvidenceArtifact.from_bytes(
            artifact_id, raw, role=role, path=path,
            metadata={"source_commit": source_commit},
        ))

    candidate_digest = _sha256(_canonical(source_manifest))
    benchmark_manifest_sha256 = _sha256(_canonical({
        "schema": "merlin-continuum-independent-benchmark-v1",
        "reference_implementation_sha256": _sha256(independent_test_bytes),
        "cases": [
            "six-vertex-ten-facet-triangulated-rp2",
            "integral-homology-H0-Z-H1-Z2-H2-0",
            "mod2-betti-b0-b1-b2-equal-1",
            "small-integer-snf-determinantal-divisors",
            "unimodular-row-column-equivalence",
        ],
    }))
    evaluator_receipt_sha256 = reproducibility_receipt_digest
    bindings = {
        "candidate_id": "merlin.continuum.triangulated-rp2-snf-persistence.v1",
        "candidate_digest": candidate_digest,
        "benchmark_manifest_sha256": benchmark_manifest_sha256,
        "evaluator_receipt_sha256": evaluator_receipt_sha256,
        "source_repo": source_repo,
        "source_commit": source_commit,
        "authority": "verification-only",
    }
    bundle = EvidenceBundle(
        artifacts=tuple(artifacts),
        bindings=bindings,
        notes=(
            "Independent CACE OCI execution and independent pure-Python reference reproduction.",
            "The bundle is provenance-only; no proof effect, promotion authority, or signed attestation is implied.",
        ),
    )
    bundle_sha256 = verify_bundle(bundle, artifact_bytes=artifact_bytes)
    if bundle_sha256 != bundle.bundle_sha256:
        raise RuntimeError("CACE EvidenceBundle canonical digest mismatch")

    artifact_bytes_b64 = {
        artifact_id: base64.b64encode(raw).decode("ascii")
        for artifact_id, raw in sorted(artifact_bytes.items())
    }
    total_bytes = sum(len(raw) for raw in artifact_bytes.values())
    if total_bytes > 10 * 1024 * 1024 or len(artifact_bytes_b64) > 32:
        raise RuntimeError("candidate evidence exceeds the CACE attestation request limits")

    request = {
        "schema": "cace-merlin-continuum-attestation-request-v1",
        "claim_id": bindings["candidate_id"],
        "expected_bindings": bindings,
        "bundle_payload": bundle.payload(),
        "bundle_sha256": bundle_sha256,
        "artifact_bytes_b64": artifact_bytes_b64,
        "persistence_envelope": envelope,
        "runner_provenance": {
            "repository": workflow["repository"],
            "workflow": workflow["workflow"],
            "workflow_ref": workflow["workflow_ref"],
            "workflow_sha": workflow["workflow_sha"],
            "run_id": workflow["run_id"],
            "run_attempt": workflow["run_attempt"],
            "job": workflow["job"],
            "runner_name": runner["name"],
            "runner_os": runner["os"],
            "runner_arch": runner["arch"],
            "execution_id": runner_execution_id,
        },
        "submission_status": "prepared_not_signed",
        "signature": None,
        "proof_effect": "none",
        "authority": "verification-only",
        "signing_blocker": (
            "The CACE OCI runtime reports secret_access_exposed=false; this collaboration "
            "workflow has no writable signer endpoint or independently pinned signing key."
        ),
    }
    (output_dir / "merlin-continuum-cace-evidence-bundle.json").write_text(
        bundle.canonical_json() + "\n", encoding="utf-8"
    )
    (output_dir / "merlin-continuum-cace-attestation-request.json").write_bytes(
        _canonical(request) + b"\n"
    )
    summary = {
        "schema": "merlin-continuum-cace-evidence-build-result-v1",
        "bundle_sha256": bundle_sha256,
        "merkle_root_sha256": bundle.merkle_root_sha256,
        "artifact_count": len(artifacts),
        "artifact_bytes": total_bytes,
        "candidate_digest": candidate_digest,
        "benchmark_manifest_sha256": benchmark_manifest_sha256,
        "evaluator_receipt_sha256": evaluator_receipt_sha256,
        "persistence_envelope_digest": envelope["envelope_digest"],
        "source_commit": source_commit,
        "runner_execution_id": runner_execution_id,
        "signed": False,
        "proof_effect": "none",
        "authority": "verification-only",
    }
    (output_dir / "merlin-continuum-cace-evidence-summary.json").write_bytes(
        _canonical(summary) + b"\n"
    )
    return summary


if __name__ == "__main__":
    print(json.dumps(build(), indent=2, sort_keys=True))
