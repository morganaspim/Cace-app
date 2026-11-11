import base64
import json
import sqlite3
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python"))

from merlin import rsi_pipeline as rsi
from merlin.rsi_pipeline import (
    AppendOnlyLedger, ResearchMetadataCache, SignedReceipt,
    ingest_hermes_failure, optional_adapter_status,
    paired_adapter_gain, paired_adapter_gate,
)

TEST_KEYS = {"test-key": "test-public-key"}
ARTIFACT = "a" * 64
SUITE = "b" * 64
SOURCE_COMMIT = "c" * 40
CACE_KEY_ID = "ed25519:test-cace-key"

def receipt(issuer, claims, key_id="test-key"):
    return SignedReceipt(
        1, issuer, key_id, datetime.now(timezone.utc).isoformat(),
        claims, base64.b64encode(b"test-signature").decode("ascii"),
    )

def test_signature_verifier(payload, signature, pem):
    return signature == b"test-signature" and pem == "test-public-key"

def cace_signature_verifier(payload, signature, pem):
    return (signature == b"z" * 64 and pem == "test-cace-public-key",
            CACE_KEY_ID)

class RSIPipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db_path = Path(self.tmp.name) / "merlin.sqlite"
        self.ledger = AppendOnlyLedger(self.db_path)

    def source_receipt(self, candidate):
        return receipt("merlin-source", {
            "candidate_id": candidate,
            "artifact_sha256": ARTIFACT,
            "source_repo": "Mannyspiro/expert-robot",
            "source_commit": SOURCE_COMMIT,
        })

    def test_hermes_failure_requires_authenticated_bound_receipt_and_is_idempotent(self):
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
        with self.assertRaises(PermissionError):
            ingest_hermes_failure(
                self.ledger, record,
                receipt("hermes", {**claims, "source_commit": "d" * 40}),
                TEST_KEYS, verifier=test_signature_verifier,
            )
        signed = receipt("hermes", claims)
        first = ingest_hermes_failure(
            self.ledger, record, signed, TEST_KEYS, verifier=test_signature_verifier,
        )
        replay = ingest_hermes_failure(
            self.ledger, record, signed, TEST_KEYS, verifier=test_signature_verifier,
        )
        self.assertEqual(first["seq"], 0)
        self.assertTrue(replay["idempotent_replay"])
        self.assertEqual(first["event_hash"], replay["event_hash"])
        events = self.ledger.events("rsi-induction:hermes-17")
        self.assertEqual(len(events), 1)
        seed = json.loads(events[0]["payload"])
        self.assertFalse(seed["induction"]["promotion_authority"])
        self.assertTrue(self.ledger.verify_chain()["valid"])

    def test_candidate_lineage_requires_authenticated_source_and_valid_parent(self):
        with self.assertRaises(PermissionError):
            self.ledger.record_candidate(
                candidate_id="candidate-root", parent_candidate_id=None,
                source_receipt=self.source_receipt("candidate-root"),
                artifact_sha256=ARTIFACT, generator="hermes", mutation={},
                trusted_keys={}, verifier=test_signature_verifier,
            )
        with self.assertRaises(ValueError):
            self.ledger.record_candidate(
                candidate_id="candidate-child", parent_candidate_id="missing-parent",
                source_receipt=self.source_receipt("candidate-child"),
                artifact_sha256=ARTIFACT, generator="rsi", mutation={},
                trusted_keys=TEST_KEYS, verifier=test_signature_verifier,
            )
        root = self.ledger.record_candidate(
            candidate_id="candidate-root", parent_candidate_id=None,
            source_receipt=self.source_receipt("candidate-root"),
            artifact_sha256=ARTIFACT, generator="hermes", mutation={},
            trusted_keys=TEST_KEYS, verifier=test_signature_verifier,
        )
        child = self.ledger.record_candidate(
            candidate_id="candidate-child", parent_candidate_id="candidate-root",
            source_receipt=self.source_receipt("candidate-child"),
            artifact_sha256=ARTIFACT, generator="rsi", mutation={"fix":"bounded-search"},
            trusted_keys=TEST_KEYS, verifier=test_signature_verifier,
        )
        self.assertEqual(root["seq"], 0)
        self.assertEqual(child["seq"], 0)
        child_event = self.ledger.events("candidate-child")[0]
        self.assertEqual(json.loads(child_event["payload"])["parent_candidate_id"], "candidate-root")

    def _record_candidate_and_evaluation(self, candidate):
        self.ledger.record_candidate(
            candidate_id=candidate, parent_candidate_id=None,
            source_receipt=self.source_receipt(candidate),
            artifact_sha256=ARTIFACT, generator="rsi",
            mutation={"failure_class":"lean-timeout"},
            trusted_keys=TEST_KEYS, verifier=test_signature_verifier,
        )
        metrics = {"overall": 0.9, "lean": 0.95}
        metrics_sha = rsi.sha256_hex(rsi.canonical_json(metrics))
        evaluator = receipt("merlin-evaluator", {
            "candidate_id": candidate, "candidate_digest": ARTIFACT,
            "benchmark_manifest_sha256": SUITE, "metrics_sha256": metrics_sha,
            "status": "pass",
        })
        self.ledger.record_evaluation(
            candidate_id=candidate, artifact_sha256=ARTIFACT, suite_sha256=SUITE,
            metrics=metrics, passed=True, evaluator_receipt=evaluator,
            trusted_keys=TEST_KEYS, verifier=test_signature_verifier,
        )
        return evaluator

    def _make_cace_attestation(self, candidate, evaluator):
        _, _, bundle_sha, bindings = self.ledger._cace_evidence(
            candidate, candidate, ARTIFACT, SUITE
        )
        statement = {
            "schema": "cace-attestation-statement-v1",
            "signature_algorithm": "ed25519",
            "proof_effect": "none",
            "verifier_id": "cace",
            "verifier_key_id": CACE_KEY_ID,
            "claim_id": candidate,
            "bundle_sha256": bundle_sha,
            "created_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "purpose": "independent-reproduction",
            "bindings": bindings,
        }
        signing_bytes = rsi._CACE_ATTESTATION_DOMAIN + rsi.canonical_json(statement)
        attestation = {
            "schema": "cace-signed-attestation-v1",
            "signature_algorithm": "ed25519",
            "proof_effect": "none",
            "statement_sha256": rsi.sha256_hex(signing_bytes),
            "statement": statement,
            "public_key_pem": "test-cace-public-key",
            "signature_b64": base64.b64encode(b"z" * 64).decode("ascii"),
        }
        return attestation

    def test_cace_verification_and_separate_approval_gate_promotion(self):
        candidate = "candidate-promote"
        evaluator = self._record_candidate_and_evaluation(candidate)
        attestation = self._make_cace_attestation(candidate, evaluator)
        approved_cace_keys = {CACE_KEY_ID: "cace"}
        with self.assertRaises(PermissionError):
            self.ledger.record_cace_verification(
                candidate_id=candidate, attestation=attestation, approved_keys={},
                artifact_sha256=ARTIFACT, suite_sha256=SUITE,
                cace_verifier=cace_signature_verifier,
            )
        cace_event = self.ledger.record_cace_verification(
            candidate_id=candidate, attestation=attestation,
            approved_keys=approved_cace_keys, artifact_sha256=ARTIFACT,
            suite_sha256=SUITE, cace_verifier=cace_signature_verifier,
        )
        attestation_digest = rsi.sha256_hex(rsi.canonical_json(attestation))
        approval = receipt("merlin-approver", {
            "candidate_id": candidate, "candidate_digest": ARTIFACT,
            "benchmark_manifest_sha256": SUITE,
            "cace_attestation_sha256": attestation_digest,
            "action": "promote", "target": "qualified",
        })
        with self.assertRaises(PermissionError):
            self.ledger.record_promotion(
                candidate_id=candidate, artifact_sha256=ARTIFACT,
                suite_sha256=SUITE, attestation=attestation,
                cace_approved_keys=approved_cace_keys,
                approval_receipt=approval, approval_keys={},
                cace_verifier=cace_signature_verifier,
                approval_verifier=test_signature_verifier,
            )
        promoted = self.ledger.record_promotion(
            candidate_id=candidate, artifact_sha256=ARTIFACT,
            suite_sha256=SUITE, attestation=attestation,
            cace_approved_keys=approved_cace_keys,
            approval_receipt=approval, approval_keys=TEST_KEYS,
            cace_verifier=cace_signature_verifier,
            approval_verifier=test_signature_verifier,
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
            trusted_keys=TEST_KEYS, verifier=test_signature_verifier,
        )
        metrics = {"overall": 0.1}
        evaluator = receipt("merlin-evaluator", {
            "candidate_id": candidate, "candidate_digest": ARTIFACT,
            "benchmark_manifest_sha256": SUITE,
            "metrics_sha256": rsi.sha256_hex(rsi.canonical_json(metrics)),
            "status": "fail",
        })
        self.ledger.record_evaluation(
            candidate_id=candidate, artifact_sha256=ARTIFACT, suite_sha256=SUITE,
            metrics=metrics, passed=False, evaluator_receipt=evaluator,
            trusted_keys=TEST_KEYS, verifier=test_signature_verifier,
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
        self.assertFalse(optional_adapter_status("merlin_nonexistent_optional_adapter")["enabled"])

    def test_metadata_cache_normalizes_ids_and_detects_tampering(self):
        cache = ResearchMetadataCache(self.db_path)
        crossref_payload = json.dumps({"message": {"title": ["Example"]}}).encode()
        with patch.object(cache, "_request", return_value=crossref_payload) as request:
            result = cache.crossref_doi("https://doi.org/10.1234/example")
            self.assertEqual(result["message"]["title"], ["Example"])
            cached = cache.crossref_doi("10.1234/example")
            self.assertEqual(cached, result)
            request.assert_called_once()
        with sqlite3.connect(self.db_path) as db:
            db.execute(
                "UPDATE research_metadata_cache SET response_json='{}' WHERE provider='crossref'"
            )
        with self.assertRaises(RuntimeError):
            cache.crossref_doi("10.1234/example")

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

if __name__ == "__main__":
    unittest.main()
