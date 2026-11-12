import base64
import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from merlin.event_outbox import MerlinEventOutbox
from merlin.hermes_rsi_bridge import (
    HermesFailureSigner, HermesRSIBridge, MerlinCandidateSigner,
)
from merlin.hermes_worker import HermesWorker
from merlin.rsi_pipeline import AppendOnlyLedger, canonical_json, sha256_hex


SOURCE_COMMIT = "d" * 40
ARTIFACT_SHA = "a" * 64


def private_pem(key):
    return key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode("ascii")


def public_pem(key):
    return key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("ascii")


def trust_env(hermes_key, source_key=None):
    issuers = {"hermes": {"hermes-key": public_pem(hermes_key)}}
    if source_key is not None:
        issuers["merlin-source"] = {"source-key": public_pem(source_key)}
    store = {"schema": "merlin-issuer-trust-store-v1", "issuers": issuers}
    raw = json.dumps(store, sort_keys=True, separators=(",", ":"))
    return {
        "MERLIN_ISSUER_TRUST_STORE_JSON": raw,
        "MERLIN_ISSUER_TRUST_STORE_SHA256": hashlib.sha256(raw.encode()).hexdigest(),
    }


def failure_record(event_id, run_id, *, corrective_steps=None):
    return {
        "schema": "merlin-hermes-failure/2",
        "event_id": event_id,
        "task_id": "task-" + event_id,
        "run_id": run_id,
        "worker_id": "hermes-worker-test",
        "stage": "proof",
        "failure_class": "TimeoutError",
        "summary": "Lean proof search exceeded its declared budget",
        "failure_signature": "lean-timeout:proof",
        "trigger_condition": "stage:proof-and-resource-budget",
        "corrective_steps": corrective_steps or [
            "bound proof search by the declared compute budget",
            "cache normalized goals before retry",
        ],
        "source_repo": "Mannyspiro/expert-robot",
        "source_commit": SOURCE_COMMIT,
        "artifact_sha256": ARTIFACT_SHA,
        "source_artifact_path": "proofs/Goal.lean",
    }


class HermesRSIBridgeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.ledger = AppendOnlyLedger(Path(self.temp.name) / "rsi.sqlite3")
        self.hermes_private = Ed25519PrivateKey.generate()
        self.source_private = Ed25519PrivateKey.generate()
        self.hermes_signer = HermesFailureSigner(
            key_id="hermes-key", private_key_pem=private_pem(self.hermes_private)
        )
        self.candidate_signer = MerlinCandidateSigner(
            key_id="source-key", private_key_pem=private_pem(self.source_private)
        )
        self.bridge = HermesRSIBridge(self.ledger)
        self.env = trust_env(self.hermes_private, self.source_private)

    def test_failure_receipt_binds_complete_record_and_is_idempotent(self):
        record = failure_record("failure-1", "run-1")
        receipt = self.hermes_signer.sign_failure(record)
        with patch.dict(os.environ, self.env):
            first = self.bridge.ingest_failure(record, receipt)
            replay_receipt = self.hermes_signer.sign_failure(record)
            replay = self.bridge.ingest_failure(record, replay_receipt)
        self.assertEqual(first["event_hash"], replay["event_hash"])
        self.assertTrue(replay["idempotent_replay"])
        tampered = dict(record)
        tampered["corrective_steps"] = ["skip verification"]
        with patch.dict(os.environ, self.env):
            with self.assertRaises(PermissionError):
                self.bridge.ingest_failure(tampered, receipt)

    def test_induction_requires_two_independent_runs_and_persists_candidate_bytes(self):
        with patch.dict(os.environ, self.env):
            for i in (1, 2):
                record = failure_record(f"failure-{i}", f"run-{i}")
                self.bridge.ingest_failure(record, self.hermes_signer.sign_failure(record))
            result = self.bridge.induce_candidate(
                skill_id="proof-search-budget-guard",
                version=1,
                purpose="Prevent repeated proof-search timeouts",
                failure_signature="lean-timeout:proof",
                guardrails=("Declarative only; no code execution",
                            "No promotion authority",
                            "Preserve the original proof obligation"),
                source_repo="Mannyspiro/expert-robot",
                source_commit=SOURCE_COMMIT,
                candidate_signer=self.candidate_signer,
            )
        self.assertEqual(len(result["induction_seed_event_hashes"]), 2)
        self.assertEqual(result["candidate"]["steps"], (
            "bound proof search by the declared compute budget",
            "cache normalized goals before retry",
        ))
        stored = self.ledger.get_artifact(result["artifact_sha256"])
        self.assertIsNotNone(stored)
        self.assertEqual(stored["artifact_bytes"], canonical_json(result["candidate"]))
        candidate_events = self.ledger.events(result["candidate_id"])
        payload = json.loads(candidate_events[0]["payload"])
        self.assertEqual(payload["induction_seed_event_hashes"], result["induction_seed_event_hashes"])
        self.assertTrue(self.ledger.verify_chain()["valid"])

    def test_same_run_cannot_supply_two_independent_trajectories(self):
        with patch.dict(os.environ, self.env):
            for i in (1, 2):
                record = failure_record(f"same-run-{i}", "run-shared")
                self.bridge.ingest_failure(record, self.hermes_signer.sign_failure(record))
            with self.assertRaises(ValueError):
                self.bridge.induce_candidate(
                    skill_id="proof-search-budget-guard", version=1,
                    purpose="Prevent proof-search timeouts",
                    failure_signature="lean-timeout:proof",
                    guardrails=("No code execution",),
                    source_repo="Mannyspiro/expert-robot", source_commit=SOURCE_COMMIT,
                    candidate_signer=self.candidate_signer,
                )

    def test_nonconvergent_repairs_do_not_induce_candidate(self):
        with patch.dict(os.environ, self.env):
            first = failure_record("repair-1", "run-1")
            second = failure_record("repair-2", "run-2",
                                    corrective_steps=["rewrite the theorem statement"])
            for record in (first, second):
                self.bridge.ingest_failure(record, self.hermes_signer.sign_failure(record))
            with self.assertRaises(ValueError):
                self.bridge.induce_candidate(
                    skill_id="proof-search-budget-guard", version=1,
                    purpose="Prevent proof-search timeouts",
                    failure_signature="lean-timeout:proof",
                    guardrails=("No code execution",),
                    source_repo="Mannyspiro/expert-robot", source_commit=SOURCE_COMMIT,
                    candidate_signer=self.candidate_signer,
                )

    def test_worker_failure_is_signed_and_ingested_before_retry(self):
        outbox = MerlinEventOutbox(Path(self.temp.name) / "hermes-outbox.sqlite3")
        task = {
            "schema": "merlin-research-task/1",
            "task_id": "task-worker-1", "hypothesis_id": "hypothesis-1",
            "objective": "Run bounded proof search", "stage": "proof",
            "resource_budget": {"cpu_cores": 1, "memory_bytes": 1024,
                                "max_wall_seconds": 10, "compute_budget_units": 10},
            "approval_ref": "approval:1", "lease_ref": "lease:1",
            "authority": "bounded_execution_only", "promotion_authority": False,
            "source_repo": "Mannyspiro/expert-robot", "source_commit": SOURCE_COMMIT,
            "artifact_sha256": ARTIFACT_SHA, "source_artifact_path": "proofs/Goal.lean",
            "failure_signature": "lean-timeout:proof",
            "trigger_condition": "stage:proof-and-resource-budget",
            "corrective_steps": ["bound proof search", "cache normalized goals"],
            "run_id": "run-worker-1",
        }
        outbox.enqueue("research-task:worker-1", "merlin.hermes.task", task, now=1)
        worker = HermesWorker(
            outbox, handlers={"proof": lambda task, ctx: (_ for _ in ()).throw(
                TimeoutError("proof search timed out"))},
            approval_validator=lambda ref, payload: True,
            lease_validator=lambda ref, budget: True,
            max_attempts=1, retry_delay_seconds=0,
            failure_signer=self.hermes_signer,
            failure_sink=self.bridge.ingest_failure,
        )
        with patch.dict(os.environ, self.env):
            result = worker.run_once(now=2)
        self.assertEqual(result["status"], "quarantined")
        self.assertEqual(result["failure_receipt_status"], "ingested")
        self.assertIsNotNone(result["rsi_seed_event_hash"])
        seeds = self.ledger.events_by_type("rsi.induction_seeded")
        self.assertEqual(len(seeds), 1)
        payload = json.loads(seeds[0]["payload"])
        self.assertEqual(payload["run_id"], "run-worker-1")
        self.assertEqual(payload["failure_signature"], "lean-timeout:proof")

    def test_worker_does_not_emit_rsi_seed_without_source_identity(self):
        outbox = MerlinEventOutbox(Path(self.temp.name) / "hermes-outbox-no-source.sqlite3")
        task = {
            "schema": "merlin-research-task/1",
            "task_id": "task-worker-2", "hypothesis_id": "hypothesis-2",
            "objective": "Run bounded proof search", "stage": "proof",
            "resource_budget": {"cpu_cores": 1, "memory_bytes": 1024,
                                "max_wall_seconds": 10, "compute_budget_units": 10},
            "approval_ref": "approval:1", "lease_ref": "lease:1",
            "authority": "bounded_execution_only", "promotion_authority": False,
        }
        outbox.enqueue("research-task:worker-2", "merlin.hermes.task", task, now=1)
        worker = HermesWorker(
            outbox, handlers={"proof": lambda task, ctx: (_ for _ in ()).throw(
                TimeoutError("proof search timed out"))},
            approval_validator=lambda ref, payload: True,
            lease_validator=lambda ref, budget: True,
            max_attempts=1, retry_delay_seconds=0,
            failure_signer=self.hermes_signer,
            failure_sink=self.bridge.ingest_failure,
        )
        result = worker.run_once(now=2)
        self.assertEqual(result["failure_receipt_status"], "source_identity_missing")
        self.assertEqual(self.ledger.events_by_type("rsi.induction_seeded"), [])


if __name__ == "__main__":
    unittest.main()
