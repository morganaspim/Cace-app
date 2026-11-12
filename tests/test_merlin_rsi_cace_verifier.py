import base64
import hashlib
import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cace_studio.core.attestation import (
    AttestationStatement,
    generate_ed25519_keypair_pem,
    public_key_id,
    sign_attestation,
)
from cace_studio.core.evidence_ledger import EvidenceArtifact, EvidenceBundle

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ops.oci_mcp.merlin_rsi_verifier import (
    attest_merlin_rsi_bundle,
    attest_merlin_rsi_reproduction,
    initialize_merlin_rsi_attestor,
    verify_merlin_rsi_attestation,
)


class MerlinRSICaceVerifierTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parents[1]
        self.private_pem, public_pem = generate_ed25519_keypair_pem()
        self.key_id = public_key_id(public_pem)
        self.claim_id = "merlin-rsi:sha256:" + "a" * 64
        self.source_repo = "Mannyspiro/expert-robot"
        self.source_commit = "d" * 40
        self.candidate_bytes = b"Merlin candidate artifact fixture v1\\n"
        benchmark = {
            "status": "frozen",
            "split": "held_out",
            "domains": ["mathematics", "lean", "research", "coding", "engineering"],
            "cases": [{"id": f"case-{i}", "domain": domain} for i, domain in enumerate(
                ["mathematics", "lean", "research", "coding", "engineering"] * 5
            )],
        }
        self.benchmark_bytes = json.dumps(
            benchmark, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        candidate_digest = hashlib.sha256(self.candidate_bytes).hexdigest()
        benchmark_digest = hashlib.sha256(self.benchmark_bytes).hexdigest()
        self.evaluator_id = "merlin-rsi-multidomain-evaluator"
        self.tool_identity = "merlin.rsi.evaluator@1"
        evaluator_receipt = {
            "schema": "merlin-rsi-evaluator-receipt-v1",
            "candidate_id": self.claim_id,
            "candidate_digest": candidate_digest,
            "benchmark_manifest_sha256": benchmark_digest,
            "source_repo": self.source_repo,
            "source_commit": self.source_commit,
            "evaluation_status": "passed",
            "held_out": True,
            "evaluator_id": self.evaluator_id,
            "tool_identity": self.tool_identity,
            "created_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        self.evaluator_receipt_bytes = json.dumps(
            evaluator_receipt, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        self.bindings = {
            "candidate_id": self.claim_id,
            "candidate_digest": candidate_digest,
            "benchmark_manifest_sha256": benchmark_digest,
            "evaluator_receipt_sha256": hashlib.sha256(self.evaluator_receipt_bytes).hexdigest(),
            "source_repo": self.source_repo,
            "source_commit": self.source_commit,
            "authority": "verification-only",
        }
        candidate_artifact = EvidenceArtifact.from_bytes(
            "merlin-rsi-candidate",
            self.candidate_bytes,
            role="candidate-artifact",
            media_type="application/octet-stream",
            path="merlin-rsi-candidate.bin",
            metadata={
                "candidate_id": self.claim_id,
                "source_repo": self.source_repo,
                "source_commit": self.source_commit,
            },
        )
        benchmark_artifact = EvidenceArtifact.from_bytes(
            "merlin-rsi-benchmark-manifest",
            self.benchmark_bytes,
            role="benchmark-manifest",
            media_type="application/json",
            path="merlin-rsi-benchmark-manifest.json",
            metadata={
                "source_repo": self.source_repo,
                "source_commit": self.source_commit,
                "status": "frozen",
                "split": "held_out",
            },
        )
        evaluator_artifact = EvidenceArtifact.from_bytes(
            "merlin-rsi-evaluator-receipt",
            self.evaluator_receipt_bytes,
            role="evaluator-receipt",
            media_type="application/json",
            path="merlin-rsi-evaluator-receipt.json",
            metadata={
                "candidate_id": self.claim_id,
                "candidate_digest": candidate_digest,
                "benchmark_manifest_sha256": benchmark_digest,
                "source_repo": self.source_repo,
                "source_commit": self.source_commit,
                "evaluator_id": self.evaluator_id,
                "tool_identity": self.tool_identity,
            },
        )
        self.bundle = EvidenceBundle(
            artifacts=(candidate_artifact, benchmark_artifact, evaluator_artifact),
            bindings=self.bindings,
            notes=("Merlin RSI exact-artifact independent verification; no proof or promotion authority",),
        )
        self.runner_provenance = {
            "run_id": 12345,
            "run_url": "https://github.com/morganaspim/Cace-app/actions/runs/12345",
            "repository": "morganaspim/Cace-app",
            "commit_sha": "e" * 40,
            "workflow_name": "Merlin OCI Job Gateway",
            "artifact_name": "merlin-oci-job-12345-1",
            "artifact_sha256": "f" * 64,
            "job_id": 67890,
            "job_name": "run-approved-profile",
            "runner_name": "cace-oci-a1",
            "conclusion": "success",
            "completed_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "evidence_bundle_sha256": self.bundle.bundle_sha256,
            "benchmark_manifest_sha256": benchmark_digest,
        }
        self.attestation = self._signed_attestation_at(
            datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        )
        self.trust_store = json.dumps({
            "schema": "merlin-cace-trust-store-v1",
            "keys": [{
                "key_id": self.key_id,
                "verifier_id": "cace",
                "status": "active",
            }],
        }, sort_keys=True, separators=(",", ":"))
        self.trust_digest = hashlib.sha256(self.trust_store.encode("utf-8")).hexdigest()

    def _artifact_bytes_b64(self):
        return {
            "merlin-rsi-candidate": base64.b64encode(self.candidate_bytes).decode("ascii"),
            "merlin-rsi-benchmark-manifest": base64.b64encode(self.benchmark_bytes).decode("ascii"),
            "merlin-rsi-evaluator-receipt": base64.b64encode(self.evaluator_receipt_bytes).decode("ascii"),
        }

    def verify(self, **overrides):
        args = {
            "bundle_payload": self.bundle.payload(),
            "attestation_payload": self.attestation,
            "expected_claim_id": self.claim_id,
            "expected_bindings": self.bindings,
            "artifact_bytes_b64": self._artifact_bytes_b64(),
            "trust_store_json": self.trust_store,
            "trust_store_sha256": self.trust_digest,
            "cace_app_root": self.root,
        }
        args.update(overrides)
        return verify_merlin_rsi_attestation(**args)

    def test_verifies_cace_native_bundle_and_attestation(self):
        result = self.verify()
        self.assertTrue(result["verified"])
        self.assertEqual(result["verifier_id"], "cace")
        self.assertEqual(result["verifier_key_id"], self.key_id)
        self.assertEqual(result["bundle_sha256"], self.bundle.bundle_sha256)
        self.assertEqual(result["runner_provenance"], self.runner_provenance)
        self.assertEqual(result["proof_effect"], "none")
        self.assertEqual(result["authority"], "verification-only")

    def test_missing_or_tampered_trust_store_fails_closed(self):
        with self.assertRaises(PermissionError):
            self.verify(trust_store_json="", trust_store_sha256="")
        with self.assertRaises(PermissionError):
            self.verify(trust_store_sha256="0" * 64)

    def test_unpinned_key_and_wrong_claim_are_rejected(self):
        forged = json.dumps({
            "schema": "merlin-cace-trust-store-v1",
            "keys": [{
                "key_id": "ed25519:" + "e" * 64,
                "verifier_id": "cace",
                "status": "active",
            }],
        }, sort_keys=True, separators=(",", ":"))
        with self.assertRaises(PermissionError):
            self.verify(
                trust_store_json=forged,
                trust_store_sha256=hashlib.sha256(forged.encode("utf-8")).hexdigest(),
            )
        with self.assertRaises(PermissionError):
            self.verify(expected_claim_id="another-candidate")

    def test_bundle_and_attestation_bindings_must_match_exactly(self):
        changed = dict(self.bindings)
        changed["candidate_digest"] = "f" * 64
        with self.assertRaises(PermissionError):
            self.verify(expected_bindings=changed)
        forged = json.loads(json.dumps(self.attestation))
        forged["statement"]["bindings"]["candidate_digest"] = "f" * 64
        with self.assertRaises(Exception):
            self.verify(attestation_payload=forged)

    def test_artifact_bytes_are_independently_hashed_and_size_checked(self):
        wrong = base64.b64encode(b'{"candidate":"tampered"}').decode("ascii")
        with self.assertRaises(Exception):
            self.verify(artifact_bytes_b64={
                "merlin-rsi-candidate": base64.b64encode(self.candidate_bytes).decode("ascii"),
                "merlin-rsi-evidence-manifest": wrong,
            })
        with self.assertRaises(PermissionError):
            self.verify(artifact_bytes_b64={})
        oversized = base64.b64encode(b"x" * (10 * 1024 * 1024 + 1)).decode("ascii")
        with self.assertRaises(ValueError):
            self.verify(artifact_bytes_b64={
                "merlin-rsi-candidate": base64.b64encode(self.candidate_bytes).decode("ascii"),
                "merlin-rsi-evidence-manifest": oversized,
            })

    def test_attestor_key_initializes_once_without_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            key_path = Path(temp) / "keys" / "merlin-rsi-attestor.pem"
            first = initialize_merlin_rsi_attestor(
                private_key_path=key_path, cace_app_root=self.root
            )
            original = key_path.read_bytes()
            second = initialize_merlin_rsi_attestor(
                private_key_path=key_path, cace_app_root=self.root
            )
            self.assertTrue(first["created"])
            self.assertFalse(second["created"])
            self.assertEqual(first["verifier_key_id"], second["verifier_key_id"])
            self.assertEqual(original, key_path.read_bytes())
            self.assertEqual(key_path.stat().st_mode & 0o777, 0o600)
            self.assertFalse(first["private_key_exposed"])

    def test_cace_signer_verifies_exact_bytes_before_signing(self):
        with tempfile.TemporaryDirectory() as temp:
            key_path = Path(temp) / "keys" / "merlin-rsi-attestor.pem"
            identity = initialize_merlin_rsi_attestor(
                private_key_path=key_path, cace_app_root=self.root
            )
            with self.assertRaises(PermissionError):
                attest_merlin_rsi_bundle(
                    bundle_payload=self.bundle.payload(),
                    expected_claim_id=self.claim_id,
                    expected_bindings=self.bindings,
                    artifact_bytes_b64={
                        "merlin-rsi-candidate": base64.b64encode(self.candidate_bytes).decode("ascii"),
                        "merlin-rsi-evidence-manifest": base64.b64encode(b"tampered").decode("ascii"),
                    },
                    private_key_path=key_path,
                    cace_app_root=self.root,
                )
            signed = attest_merlin_rsi_bundle(
                bundle_payload=self.bundle.payload(),
                expected_claim_id=self.claim_id,
                expected_bindings=self.bindings,
                artifact_bytes_b64={
                    "merlin-rsi-candidate": base64.b64encode(self.candidate_bytes).decode("ascii"),
                    "merlin-rsi-evidence-manifest": base64.b64encode(self.artifact_bytes).decode("ascii"),
                },
                private_key_path=key_path,
                cace_app_root=self.root,
            )
            key_store = json.dumps({
                "schema": "merlin-cace-trust-store-v1",
                "keys": [{
                    "key_id": identity["verifier_key_id"],
                    "verifier_id": "cace",
                    "status": "active",
                }],
            }, sort_keys=True, separators=(",", ":"))
            self.assertEqual(signed["purpose"], "artifact-integrity")
            with self.assertRaises(PermissionError):
                self.verify(
                    attestation_payload=signed["attestation"],
                    trust_store_json=key_store,
                    trust_store_sha256=hashlib.sha256(key_store.encode("utf-8")).hexdigest(),
                )

    def test_cace_signer_requires_initialized_private_key(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(PermissionError):
                attest_merlin_rsi_bundle(
                    bundle_payload=self.bundle.payload(),
                    expected_claim_id=self.claim_id,
                    expected_bindings=self.bindings,
                    artifact_bytes_b64={
                        "merlin-rsi-candidate": base64.b64encode(self.candidate_bytes).decode("ascii"),
                        "merlin-rsi-evidence-manifest": base64.b64encode(self.artifact_bytes).decode("ascii"),
                    },
                    private_key_path=Path(temp) / "missing.pem",
                    cace_app_root=self.root,
                )

    def test_verifier_rejects_artifact_integrity_as_independent_reproduction(self):
        integrity_only = self._signed_attestation_at(
            datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            purpose="artifact-integrity",
        )
        with self.assertRaises(PermissionError):
            self.verify(attestation_payload=integrity_only)

    def test_independent_reproduction_attestation_requires_successful_pinned_oci_run(self):
        benchmark = {
            "status": "frozen",
            "split": "held_out",
            "domains": ["mathematics", "lean", "research", "coding", "engineering"],
            "cases": [{"id": f"case-{i}", "domain": d} for i, d in enumerate(
                ["mathematics", "lean", "research", "coding", "engineering"] * 5
            )],
        }
        benchmark_bytes = json.dumps(benchmark, sort_keys=True, separators=(",", ":")).encode()
        benchmark_sha = hashlib.sha256(benchmark_bytes).hexdigest()
        bindings = dict(self.bindings)
        bindings["benchmark_manifest_sha256"] = benchmark_sha
        candidate_artifact = EvidenceArtifact.from_bytes(
            "merlin-rsi-candidate", self.candidate_bytes,
            role="candidate-artifact", media_type="application/octet-stream",
            path="merlin-rsi-candidate.bin",
        )
        manifest_artifact = EvidenceArtifact.from_bytes(
            "merlin-rsi-evidence-manifest", self.artifact_bytes,
            role="rsi-evidence-manifest", media_type="application/json",
            path="merlin-rsi-evidence-manifest.json",
        )
        bundle = EvidenceBundle(
            artifacts=(candidate_artifact, manifest_artifact),
            bindings=bindings,
            notes=("Merlin RSI exact-artifact independent verification",),
        )
        source_commit = bindings["source_commit"]
        run_sha = "e" * 40
        run_id = 98765
        request_path = "merlin/oci-requests/11111111-2222-4333-8444-555555555555.json"

        def git_blob_sha(raw):
            return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()

        source_file_paths = (
            "python/merlin/rsi_pipeline.py",
            "python/merlin/rsi.py",
            "python/merlin/event_outbox.py",
            "python/merlin/hermes_rsi_bridge.py",
            "python/merlin/hermes_worker.py",
            "python/merlin/telemetry.py",
            "python/merlin/hermes_outbox.py",
            "python/merlin/runtime_contracts.py",
            "python/merlin/sqlite_registry.py",
            "tests/test_rsi_pipeline.py",
            "tests/test_hermes_rsi_bridge.py",
            "tests/test_hermes_worker.py",
            "tests/test_event_outbox.py",
            "tests/test_hermes_outbox.py",
            "config/benchmarks/merlin_rsi_multidomain_holdout_v1.json",
        )
        source_file_contents = {
            path: (("pinned source " + path).encode("utf-8"))
            for path in source_file_paths
        }
        source_file_contents["config/benchmarks/merlin_rsi_multidomain_holdout_v1.json"] = benchmark_bytes
        source_blob_shas = {
            path: git_blob_sha(raw) for path, raw in source_file_contents.items()
        }
        request_doc = {
            "operation": "merlin_hermes_rsi_full_tests",
            "source_repo": bindings["source_repo"],
            "source_commit": source_commit,
            "source_blob_shas": source_blob_shas,
        }
        workflow_text = (
            'if request["operation"] == "merlin_hermes_rsi_full_tests":\\n'
            f'    if request["source_commit"] != "{source_commit}":\\n'
        )

        def encode_doc(value):
            return base64.b64encode(json.dumps(value).encode()).decode()

        def fake_fetch(url):
            if url.endswith(f"/actions/runs/{run_id}"):
                return {
                    "repository": {"full_name": "morganaspim/Cace-app"},
                    "status": "completed", "conclusion": "success", "event": "push",
                    "head_branch": "merlin/oci-jobs/reproduction-test",
                    "head_sha": run_sha,
                    "path": ".github/workflows/merlin-oci-job-gateway.yml@refs/heads/merlin/oci-jobs/reproduction-test",
                }
            if url.endswith(f"/commits/{run_sha}"):
                return {"files": [{"filename": request_path, "status": "added"}]}
            if "/contents/merlin/oci-requests/" in url:
                return {"encoding": "base64", "content": encode_doc(request_doc)}
            if "/contents/.github/workflows/" in url:
                return {"encoding": "base64", "content": base64.b64encode(workflow_text.encode()).decode()}
            for source_path, raw in source_file_contents.items():
                if f"/contents/{source_path}?" in url:
                    return {"encoding": "base64", "content": base64.b64encode(raw).decode()}
            if url.endswith(f"/actions/runs/{run_id}/jobs?per_page=100"):
                return {"jobs": [{
                    "id": 123456,
                    "name": "run-approved-profile",
                    "runner_name": "cace-oci-a1",
                    "conclusion": "success",
                    "steps": [
                        {"name": "Validate request and execute fixed inventory profile", "conclusion": "success"},
                        {"name": "Upload job receipt and inventory", "conclusion": "success"},
                    ],
                }]}
            if url.endswith(f"/actions/runs/{run_id}/artifacts?per_page=100"):
                return {"artifacts": [{
                    "name": f"merlin-oci-job-{run_id}-1",
                    "expired": False,
                    "digest": "sha256:" + "f" * 64,
                }]}
            raise AssertionError("unexpected GitHub API URL: " + url)

        artifact_bytes_b64 = {
            "merlin-rsi-candidate": base64.b64encode(self.candidate_bytes).decode("ascii"),
            "merlin-rsi-evidence-manifest": base64.b64encode(self.artifact_bytes).decode("ascii"),
        }
        with tempfile.TemporaryDirectory() as temp:
            key_path = Path(temp) / "keys" / "attestor.pem"
            identity = initialize_merlin_rsi_attestor(
                private_key_path=key_path, cace_app_root=self.root
            )
            signed = attest_merlin_rsi_reproduction(
                bundle_payload=bundle.payload(),
                expected_claim_id=self.claim_id,
                expected_bindings=bindings,
                artifact_bytes_b64=artifact_bytes_b64,
                github_run_id=run_id,
                private_key_path=key_path,
                cace_app_root=self.root,
                github_fetch=fake_fetch,
            )
        self.assertEqual(signed["purpose"], "independent-reproduction")
        self.assertEqual(signed["runner_provenance"]["run_id"], run_id)
        trust = json.dumps({
            "schema": "merlin-cace-trust-store-v1",
            "keys": [{
                "key_id": identity["verifier_key_id"],
                "verifier_id": "cace",
                "status": "active",
            }],
        }, sort_keys=True, separators=(",", ":"))
        verified = verify_merlin_rsi_attestation(
            bundle_payload=bundle.payload(),
            attestation_payload=signed["attestation"],
            expected_claim_id=self.claim_id,
            expected_bindings=bindings,
            artifact_bytes_b64=artifact_bytes_b64,
            trust_store_json=trust,
            trust_store_sha256=hashlib.sha256(trust.encode()).hexdigest(),
            cace_app_root=self.root,
        )
        self.assertTrue(verified["verified"])
        self.assertEqual(verified["runner_provenance"]["runner_name"], "cace-oci-a1")

    def test_independent_reproduction_rejects_failed_oci_run(self):
        # A failed or incomplete GitHub Actions run must never be attested.
        with tempfile.TemporaryDirectory() as temp:
            key_path = Path(temp) / "keys" / "attestor.pem"
            initialize_merlin_rsi_attestor(private_key_path=key_path, cace_app_root=self.root)
            with self.assertRaises(PermissionError):
                attest_merlin_rsi_reproduction(
                    bundle_payload=self.bundle.payload(),
                    expected_claim_id=self.claim_id,
                    expected_bindings=self.bindings,
                    artifact_bytes_b64={
                        "merlin-rsi-candidate": base64.b64encode(self.candidate_bytes).decode("ascii"),
                        "merlin-rsi-evidence-manifest": base64.b64encode(self.artifact_bytes).decode("ascii"),
                    },
                    github_run_id=98765,
                    private_key_path=key_path,
                    cace_app_root=self.root,
                    github_fetch=lambda url: {
                        "repository": {"full_name": "morganaspim/Cace-app"},
                        "status": "completed", "conclusion": "failure",
                        "event": "push", "head_branch": "merlin/oci-jobs/nope",
                    },
                )

    def test_cace_core_rejects_unknown_attestation_purpose(self):
        with self.assertRaises(ValueError):
            AttestationStatement(
                verifier_id="cace",
                verifier_key_id=self.key_id,
                claim_id=self.claim_id,
                bundle_sha256=self.bundle.bundle_sha256,
                created_at_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                purpose="unrecognized-purpose",
                bindings=self.bindings,
            )

    def _signed_attestation_at(self, created_at_utc, purpose="independent-reproduction"):
        statement_bindings = dict(self.bindings)
        if purpose == "independent-reproduction":
            statement_bindings["cace_runner_provenance"] = self.runner_provenance
        statement = AttestationStatement(
            verifier_id="cace",
            verifier_key_id=self.key_id,
            claim_id=self.claim_id,
            bundle_sha256=self.bundle.bundle_sha256,
            created_at_utc=created_at_utc,
            purpose=purpose,
            bindings=statement_bindings,
        )
        return sign_attestation(statement, self.private_pem).payload()

    def test_verification_authority_and_binding_schema_are_fixed(self):
        with self.assertRaises(PermissionError):
            self.verify(expected_bindings={**self.bindings, "authority": "production"})
        with self.assertRaises(ValueError):
            self.verify(expected_bindings={**self.bindings, "extra": "not-allowed"})
        with self.assertRaises(ValueError):
            self.verify(expected_bindings={**self.bindings, "candidate_digest": "not-a-digest"})
        with self.assertRaises(PermissionError):
            self.verify(expected_bindings={**self.bindings, "source_repo": "attacker/fork"})

    def test_stale_and_future_attestations_are_rejected(self):
        stale = (datetime.now(timezone.utc) - timedelta(days=31)).strftime("%Y-%m-%dT%H:%M:%SZ")
        future = (datetime.now(timezone.utc) + timedelta(minutes=10)).strftime("%Y-%m-%dT%H:%M:%SZ")
        for created_at in (stale, future):
            with self.assertRaises(PermissionError):
                self.verify(attestation_payload=self._signed_attestation_at(created_at))

    def test_artifact_base64_must_be_canonical(self):
        encoded = base64.b64encode(self.artifact_bytes).decode("ascii") + "\n"
        with self.assertRaises(ValueError):
            self.verify(artifact_bytes_b64={
                "merlin-rsi-candidate": base64.b64encode(self.candidate_bytes).decode("ascii"),
                "merlin-rsi-evidence-manifest": encoded,
            })

if __name__ == "__main__":
    unittest.main()
