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
    initialize_merlin_rsi_attestor,
    verify_merlin_rsi_attestation,
)


class MerlinRSICaceVerifierTests(unittest.TestCase):
    def setUp(self):
        self.claim_id = "merlin-rsi-candidate-001"
        self.bindings = {
            "candidate_id": self.claim_id,
            "candidate_digest": "a" * 64,
            "benchmark_manifest_sha256": "b" * 64,
            "evaluator_receipt_sha256": "c" * 64,
            "source_repo": "Mannyspiro/expert-robot",
            "source_commit": "d" * 40,
            "authority": "verification-only",
        }
        self.artifact_bytes = b'{"candidate":"merlin-rsi-candidate-001"}'
        artifact = EvidenceArtifact.from_bytes(
            "merlin-rsi-evidence-manifest",
            self.artifact_bytes,
            role="rsi-evidence-manifest",
            media_type="application/json",
            path="merlin-rsi-evidence-manifest.json",
        )
        self.bundle = EvidenceBundle(
            artifacts=(artifact,),
            bindings=self.bindings,
            notes=("Merlin RSI exact-artifact independent verification",),
        )
        self.private_pem, self.public_pem = generate_ed25519_keypair_pem()
        self.key_id = public_key_id(self.public_pem)
        statement = AttestationStatement(
            verifier_id="cace",
            verifier_key_id=self.key_id,
            claim_id=self.claim_id,
            bundle_sha256=self.bundle.bundle_sha256,
            created_at_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            purpose="independent-reproduction",
            bindings=self.bindings,
        )
        self.attestation = sign_attestation(statement, self.private_pem).payload()
        self.trust_store = json.dumps({
            "schema": "merlin-cace-trust-store-v1",
            "keys": [{
                "key_id": self.key_id,
                "verifier_id": "cace",
                "status": "active",
            }],
        }, sort_keys=True, separators=(",", ":"))
        self.trust_digest = hashlib.sha256(self.trust_store.encode("utf-8")).hexdigest()
        self.root = Path(__file__).resolve().parents[1]

    def verify(self, **overrides):
        args = {
            "bundle_payload": self.bundle.payload(),
            "attestation_payload": self.attestation,
            "expected_claim_id": self.claim_id,
            "expected_bindings": self.bindings,
            "artifact_bytes_b64": {
                "merlin-rsi-evidence-manifest": base64.b64encode(self.artifact_bytes).decode("ascii")
            },
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
            self.verify(artifact_bytes_b64={"merlin-rsi-evidence-manifest": wrong})
        with self.assertRaises(PermissionError):
            self.verify(artifact_bytes_b64={})
        oversized = base64.b64encode(b"x" * (10 * 1024 * 1024 + 1)).decode("ascii")
        with self.assertRaises(ValueError):
            self.verify(artifact_bytes_b64={"merlin-rsi-evidence-manifest": oversized})

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
                    artifact_bytes_b64={"merlin-rsi-evidence-manifest": base64.b64encode(b"tampered").decode("ascii")},
                    private_key_path=key_path,
                    cace_app_root=self.root,
                )
            signed = attest_merlin_rsi_bundle(
                bundle_payload=self.bundle.payload(),
                expected_claim_id=self.claim_id,
                expected_bindings=self.bindings,
                artifact_bytes_b64={
                    "merlin-rsi-evidence-manifest": base64.b64encode(self.artifact_bytes).decode("ascii")
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
            verified = self.verify(
                attestation_payload=signed["attestation"],
                trust_store_json=key_store,
                trust_store_sha256=hashlib.sha256(key_store.encode("utf-8")).hexdigest(),
            )
            self.assertEqual(signed["purpose"], "artifact-integrity")
            self.assertTrue(verified["verified"])
            self.assertEqual(verified["purpose"], "artifact-integrity")
            self.assertEqual(verified["artifact_bytes_verified"], len(self.artifact_bytes))
            self.assertEqual(verified["proof_effect"], "none")

    def test_cace_signer_requires_initialized_private_key(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(PermissionError):
                attest_merlin_rsi_bundle(
                    bundle_payload=self.bundle.payload(),
                    expected_claim_id=self.claim_id,
                    expected_bindings=self.bindings,
                    artifact_bytes_b64={
                        "merlin-rsi-evidence-manifest": base64.b64encode(self.artifact_bytes).decode("ascii")
                    },
                    private_key_path=Path(temp) / "missing.pem",
                    cace_app_root=self.root,
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
        statement = AttestationStatement(
            verifier_id="cace",
            verifier_key_id=self.key_id,
            claim_id=self.claim_id,
            bundle_sha256=self.bundle.bundle_sha256,
            created_at_utc=created_at_utc,
            purpose=purpose,
            bindings=self.bindings,
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
            self.verify(artifact_bytes_b64={"merlin-rsi-evidence-manifest": encoded})

if __name__ == "__main__":
    unittest.main()
