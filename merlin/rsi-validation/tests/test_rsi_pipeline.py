import base64
import json
import sqlite3
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python"))

from merlin import rsi_pipeline as rsi
from merlin.rsi_pipeline import (
    AppendOnlyLedger, ResearchMetadataCache, SignedReceipt,
    ingest_hermes_failure, optional_adapter_status,
    paired_adapter_gain, paired_adapter_gate,
)

ARTIFACT = "a" * 64
SUITE = "b" * 64
SOURCE_COMMIT = "c" * 40

def public_pem(private_key):
    return private_key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("ascii")

def sign_receipt(issuer, claims, key_id, private_key):
    unsigned = SignedReceipt(
        1, issuer, key_id, datetime.now(timezone.utc).isoformat(),
        claims, "",
    )
    signature = private_key.sign(rsi.canonical_json(unsigned.unsigned_payload()))
    return SignedReceipt(
        1, issuer, key_id, unsigned.issued_at, claims,
        base64.b64encode(signature).decode("ascii"),
    )

class RSIPipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db_path = Path(self.tmp.name) / "merlin.sqlite"
        self.ledger = AppendOnlyLedger(self.db_path)

        self.hermes_private = Ed25519PrivateKey.generate()
        self.source_private = Ed25519PrivateKey.generate()
        self.evaluator_private = Ed25519PrivateKey.generate()
        self.approver_private = Ed25519PrivateKey.generate()
        self.cace_private = Ed25519PrivateKey.generate()

        self.hermes_keys = {"hermes-key": public_pem(self.hermes_private)}
        self.source_keys = {"source-key": public_pem(self.source_private)}
        self.evaluator_keys = {"evaluator-key": public_pem(self.evaluator_private)}
        self.approver_keys = {"approver-key": public_pem(self.approver_private)}
        cace_raw = self.cace_private.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw
        )
        self.cace_key_id = "ed25519:" + rsi.sha256_hex(cace_raw)
        self.cace_keys = {self.cace_key_id: "cace"}

    def source_receipt(self, candidate):
        return sign_receipt("merlin-source", {
            "candidate_id": candidate,
            "artifact_sha256": ARTIFACT,
            "source_repo": "Mannyspiro/expert-robot",
            "source_commit": SOURCE_COMMIT,
        }, "source-key", self.source_private)

    def test_hermes_failure_requires_authentic_signature_and_is_idempotent(self):
        record = {
            "event_id": "hermes-17", "failure_class": "lean-timeout",
            "summary": "Proof search exceeded its budget",
            "source_repo": "Mannyspiro/expert-robot",
            "source_commit": SOURCE_COMMIT, "artifact_sha256": ARTIFACT,
        }
        claims = {
            "subject": "hermes-failure:hermes-17",
            "source_repo": record["source_repo"],
            "source_commit": SOURCE_COMMIT,
            "artifact_sha256": ARTIFACT, "failure_class": "lean-timeout",
        }
        forged = sign_receipt("hermes", {
            **claims, "source_commit": "d" * 40
        }, "hermes-key", self.hermes_private)
        with self.assertRaises(PermissionError):
            ingest_hermes_failure(self.ledger, record, forged, self.hermes_keys)
        signed = sign_receipt("hermes", claims, "hermes-key", self.hermes_private)
        first = ingest_hermes_failure(self.ledger, record, signed, self.hermes_keys)
        replay = ingest_hermes_failure(self.ledger, record, signed, self.hermes_keys)
        self.assertEqual(first["seq"], 0)
        self.assertTrue(replay["idempotent_replay"])
        self.assertEqual(first["event_hash"], replay["event_hash"])
        events = self.ledger.events("rsi-induction:hermes-17")
        self.assertEqual(len(events), 1)
        seed = json.loads(events[0]["payload"])
        self.assertFalse(seed["induction"]["promotion_authority"])
        self.assertTrue(self.ledger.verify_chain()["valid"])

    def test_candidate_lineage_requires_signed_source_and_valid_parent(self):
        source = self.source_receipt("candidate-root")
        with self.assertRaises(PermissionError):
            self.ledger.record_candidate(
                candidate_id="candidate-root", parent_candidate_id=None,
                source_receipt=source, artifact_sha256=ARTIFACT,
                generator="hermes", mutation={}, trusted_keys={},
            )
        with self.assertRaises(ValueError):
            self.ledger.record_candidate(
                candidate_id="candidate-child", parent_candidate_id="missing-parent",
                source_receipt=self.source_receipt("candidate-child"),
                artifact_sha256=ARTIFACT, generator="rsi", mutation={},
                trusted_keys=self.source_keys,
            )
        root = self.ledger.record_candidate(
            candidate_id="candidate-root", parent_candidate_id=None,
            source_receipt=source, artifact_sha256=ARTIFACT,
            generator="hermes", mutation={}, trusted_keys=self.source_keys,
        )
        child = self.ledger.record_candidate(
            candidate_id="candidate-child", parent_candidate_id="candidate-root",
            source_receipt=self.source_receipt("candidate-child"),
            artifact_sha256=ARTIFACT, generator="rsi",
            mutation={"fix": "bounded-search"}, trusted_keys=self.source_keys,
        )
        self.assertEqual(root["seq"], 0)
        self.assertEqual(child["seq"], 0)
        child_event = self.ledger.events("candidate-child")[0]
        self.assertEqual(json.loads(child_event["payload"])["parent_candidate_id"], "candidate-root")

    def test_rsi_candidate_binds_authenticated_hermes_seed(self):
        failure = {
            "event_id": "hermes-seed-42",
            "failure_class": "formalization-timeout",
            "summary": "Lean proof search timed out",
            "source_repo": "Mannyspiro/expert-robot",
            "source_commit": SOURCE_COMMIT,
            "artifact_sha256": ARTIFACT,
        }
        hermes_receipt = sign_receipt("hermes", {
            "subject": "hermes-failure:hermes-seed-42",
            "source_repo": failure["source_repo"],
            "source_commit": SOURCE_COMMIT,
            "artifact_sha256": ARTIFACT,
            "failure_class": failure["failure_class"],
        }, "hermes-key", self.hermes_private)
        seed = ingest_hermes_failure(
            self.ledger, failure, hermes_receipt, self.hermes_keys
        )
        candidate_id = "candidate-from-hermes-seed"
        claims = {
            "candidate_id": candidate_id,
            "artifact_sha256": ARTIFACT,
            "source_repo": "Mannyspiro/expert-robot",
            "source_commit": SOURCE_COMMIT,
            "induction_seed_event_hash": seed["event_hash"],
        }
        with self.assertRaises(PermissionError):
            self.ledger.record_candidate(
                candidate_id=candidate_id, parent_candidate_id=None,
                source_receipt=self.source_receipt(candidate_id),
                artifact_sha256=ARTIFACT, generator="rsi",
                mutation={"origin": "hermes-failure"},
                trusted_keys=self.source_keys,
                induction_seed_event_hash=seed["event_hash"],
            )
        signed_source = sign_receipt(
            "merlin-source", claims, "source-key", self.source_private
        )
        created = self.ledger.record_candidate(
            candidate_id=candidate_id, parent_candidate_id=None,
            source_receipt=signed_source, artifact_sha256=ARTIFACT,
            generator="rsi", mutation={"origin": "hermes-failure"},
            trusted_keys=self.source_keys,
            induction_seed_event_hash=seed["event_hash"],
        )
        payload = json.loads(self.ledger.events(candidate_id)[0]["payload"])
        self.assertEqual(created["seq"], 0)
        self.assertEqual(payload["induction_seed_event_hash"], seed["event_hash"])

    def _record_candidate_and_evaluation(self, candidate):
        self.ledger.record_candidate(
            candidate_id=candidate, parent_candidate_id=None,
            source_receipt=self.source_receipt(candidate),
            artifact_sha256=ARTIFACT, generator="rsi",
            mutation={"failure_class": "lean-timeout"},
            trusted_keys=self.source_keys,
        )
        metrics = {"overall": 0.9, "lean": 0.95}
        metrics_sha = rsi.sha256_hex(rsi.canonical_json(metrics))
        evaluator = sign_receipt("merlin-evaluator", {
            "candidate_id": candidate, "candidate_digest": ARTIFACT,
            "benchmark_manifest_sha256": SUITE, "metrics_sha256": metrics_sha,
            "status": "pass",
        }, "evaluator-key", self.evaluator_private)
        self.ledger.record_evaluation(
            candidate_id=candidate, artifact_sha256=ARTIFACT,
            suite_sha256=SUITE, metrics=metrics, passed=True,
            evaluator_receipt=evaluator, trusted_keys=self.evaluator_keys,
        )
        return evaluator

    def _make_cace_attestation(self, candidate):
        _, _, bundle_sha, bindings = self.ledger._cace_evidence(
            candidate, candidate, ARTIFACT, SUITE
        )
        statement = {
            "schema": "cace-attestation-statement-v1",
            "signature_algorithm": "ed25519",
            "proof_effect": "none",
            "verifier_id": "cace",
            "verifier_key_id": self.cace_key_id,
            "claim_id": candidate,
            "bundle_sha256": bundle_sha,
            "created_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "purpose": "independent-reproduction",
            "bindings": bindings,
        }
        signing_bytes = rsi._CACE_ATTESTATION_DOMAIN + rsi.canonical_json(statement)
        signature = self.cace_private.sign(signing_bytes)
        return {
            "schema": "cace-signed-attestation-v1",
            "signature_algorithm": "ed25519",
            "proof_effect": "none",
            "statement_sha256": rsi.sha256_hex(signing_bytes),
            "statement": statement,
            "public_key_pem": public_pem(self.cace_private),
            "signature_b64": base64.b64encode(signature).decode("ascii"),
        }

    def test_cace_verification_and_separate_approval_gate_promotion(self):
        candidate = "candidate-promote"
        self._record_candidate_and_evaluation(candidate)
        attestation = self._make_cace_attestation(candidate)
        with self.assertRaises(PermissionError):
            self.ledger.record_cace_verification(
                candidate_id=candidate, attestation=attestation, approved_keys={},
                artifact_sha256=ARTIFACT, suite_sha256=SUITE,
            )
        cace_event = self.ledger.record_cace_verification(
            candidate_id=candidate, attestation=attestation,
            approved_keys=self.cace_keys, artifact_sha256=ARTIFACT,
            suite_sha256=SUITE,
        )
        attestation_digest = rsi.sha256_hex(rsi.canonical_json(attestation))
        approval = sign_receipt("merlin-approver", {
            "candidate_id": candidate, "candidate_digest": ARTIFACT,
            "benchmark_manifest_sha256": SUITE,
            "cace_attestation_sha256": attestation_digest,
            "action": "promote", "target": "qualified",
        }, "approver-key", self.approver_private)
        with self.assertRaises(PermissionError):
            self.ledger.record_promotion(
                candidate_id=candidate, artifact_sha256=ARTIFACT,
                suite_sha256=SUITE, attestation=attestation,
                cace_approved_keys=self.cace_keys,
                approval_receipt=approval, approval_keys={},
            )
        promoted = self.ledger.record_promotion(
            candidate_id=candidate, artifact_sha256=ARTIFACT,
            suite_sha256=SUITE, attestation=attestation,
            cace_approved_keys=self.cace_keys,
            approval_receipt=approval, approval_keys=self.approver_keys,
        )
        self.assertEqual(cace_event["seq"], 2)
        self.assertEqual(promoted["seq"], 3)
        self.assertTrue(self.ledger.verify_chain(candidate)["valid"])

    def test_promotion_rejects_failed_evaluation(self):
        candidate = "candidate-fail"
        self.ledger.record_candidate(
            candidate_id=candidate, parent_candidate_id=None,
            source_receipt=self.source_receipt(candidate),
            artifact_sha256=ARTIFACT, generator="rsi", mutation={},
            trusted_keys=self.source_keys,
        )
        metrics = {"overall": 0.1}
        evaluator = sign_receipt("merlin-evaluator", {
            "candidate_id": candidate, "candidate_digest": ARTIFACT,
            "benchmark_manifest_sha256": SUITE,
            "metrics_sha256": rsi.sha256_hex(rsi.canonical_json(metrics)),
            "status": "fail",
        }, "evaluator-key", self.evaluator_private)
        self.ledger.record_evaluation(
            candidate_id=candidate, artifact_sha256=ARTIFACT,
            suite_sha256=SUITE, metrics=metrics, passed=False,
            evaluator_receipt=evaluator, trusted_keys=self.evaluator_keys,
        )
        with self.assertRaises(PermissionError):
            self.ledger._cace_evidence(candidate, candidate, ARTIFACT, SUITE)

    def test_sqlite_ledger_rejects_update_and_delete(self):
        self.ledger.append("test.event", "episode-test", {"value": 1})
        with sqlite3.connect(self.db_path) as db:
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute(
                    "UPDATE research_episode_events SET episode_id='tampered' WHERE episode_id='episode-test'"
                )
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute(
                    "DELETE FROM research_episode_events WHERE episode_id='episode-test'"
                )

    def test_fixed_holdout_covers_all_five_domains(self):
        manifest_path = (
            Path(__file__).resolve().parents[1] /
            "config/benchmarks/merlin_rsi_multidomain_holdout_v1.json"
        )
        manifest = json.loads(manifest_path.read_text())
        self.assertEqual(manifest["status"], "frozen")
        self.assertEqual(set(manifest["domains"]), {
            "mathematics", "lean", "research", "coding", "engineering"
        })
        self.assertEqual(len(manifest["cases"]), 25)
        self.assertEqual(len({case["id"] for case in manifest["cases"]}), 25)

    def test_optional_adapters_require_paired_multidomain_gain(self):
        self.assertFalse(paired_adapter_gain([0.5] * 5, [0.8] * 5)["eligible"])
        self.assertTrue(paired_adapter_gain([0.5] * 25, [0.6] * 25)["eligible"])
        self.assertFalse(paired_adapter_gain([0.5] * 25, [0.501] * 25)["eligible"])
        baseline = {d: [0.5] * 5 for d in (
            "mathematics", "lean", "research", "coding", "engineering"
        )}
        candidate = {d: [0.6] * 5 for d in baseline}
        self.assertTrue(paired_adapter_gate(baseline, candidate)["eligible"])
        candidate["lean"] = [0.4] * 5
        self.assertFalse(paired_adapter_gate(baseline, candidate)["eligible"])
        self.assertFalse(optional_adapter_status(
            "merlin_nonexistent_optional_adapter")["enabled"])

    def test_cace_bundle_digest_matches_pinned_oci_implementation(self):
        actual = rsi.cace_rsi_bundle_sha256(
            candidate_id="merlin-rsi-bridge-contract-test-1",
            candidate_digest="a" * 64,
            benchmark_manifest_sha256="b" * 64,
            evaluator_receipt_sha256="c" * 64,
            source_repo="Mannyspiro/expert-robot",
            source_commit="d" * 40,
        )
        self.assertEqual(
            actual,
            "0898289d4c6267dbc8de6e595e56f8f035ad0344b65431f8deb11be0972b0272",
        )

    def test_metadata_cache_normalizes_doi_and_detects_tampering(self):
        cache = ResearchMetadataCache(self.db_path)
        raw = json.dumps({"message": {"title": ["Example"]}}).encode()
        from unittest.mock import patch
        with patch.object(cache, "_request", return_value=raw) as request:
            first = cache.crossref_doi("https://doi.org/10.1234/example")
            second = cache.crossref_doi("10.1234/example")
            self.assertEqual(first, second)
            request.assert_called_once()
        with sqlite3.connect(self.db_path) as db:
            db.execute(
                "UPDATE research_metadata_cache SET response_json='{}' WHERE provider='crossref'"
            )
        with self.assertRaises(RuntimeError):
            cache.crossref_doi("10.1234/example")

if __name__ == "__main__":
    unittest.main()
