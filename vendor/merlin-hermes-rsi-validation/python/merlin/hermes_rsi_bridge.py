"""Authenticated Hermes-to-RSI bridge.

Hermes signs the complete failure envelope. Merlin verifies the signature,
persists the source event, and only induces declarative candidates from at
least two independent runs with convergent corrective steps.
"""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import base64
import json
import os
import re
from typing import Any, Mapping

from merlin import rsi
from merlin.rsi_pipeline import (
    AppendOnlyLedger, SignedReceipt, canonical_json, sha256_hex,
    ingest_hermes_failure,
)


class Ed25519ReceiptSigner:
    """Issuer-scoped signer. Private key material is injected, never persisted."""

    def __init__(self, *, issuer: str, key_id: str, private_key_pem: str):
        if not issuer or not key_id or not private_key_pem:
            raise ValueError("issuer, key_id and private_key_pem are required")
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        key = serialization.load_pem_private_key(private_key_pem.encode("utf-8"), password=None)
        if not isinstance(key, Ed25519PrivateKey):
            raise ValueError("receipt signing key must be Ed25519")
        self.issuer = issuer
        self.key_id = key_id
        self._private_key = key

    @classmethod
    def from_env(cls, *, issuer: str, key_id_env: str, private_key_env: str):
        key_id = os.environ.get(key_id_env, "").strip()
        private_key = os.environ.get(private_key_env, "")
        if not key_id or not private_key:
            raise RuntimeError(f"{issuer} signing capability unavailable: required secret is not configured")
        return cls(issuer=issuer, key_id=key_id, private_key_pem=private_key)

    def sign_claims(self, claims: Mapping[str, Any]) -> SignedReceipt:
        issued_at = datetime.now(timezone.utc).isoformat()
        unsigned = SignedReceipt(1, self.issuer, self.key_id, issued_at, dict(claims), "")
        signature = self._private_key.sign(canonical_json(unsigned.unsigned_payload()))
        return SignedReceipt(
            1, self.issuer, self.key_id, issued_at, dict(claims),
            base64.b64encode(signature).decode("ascii"),
        )


class HermesFailureSigner(Ed25519ReceiptSigner):
    def __init__(self, *, key_id: str, private_key_pem: str):
        super().__init__(issuer="hermes", key_id=key_id, private_key_pem=private_key_pem)

    @classmethod
    def from_env(cls):
        key_id = os.environ.get("HERMES_FAILURE_SIGNING_KEY_ID", "").strip()
        private_key = os.environ.get("HERMES_FAILURE_SIGNING_KEY_PEM", "")
        if not key_id or not private_key:
            raise RuntimeError("Hermes signing capability unavailable: required secret is not configured")
        return cls(key_id=key_id, private_key_pem=private_key)

    def sign_failure(self, record: Mapping[str, Any]) -> SignedReceipt:
        if record.get("schema") != "merlin-hermes-failure/2":
            raise ValueError("unsupported Hermes failure schema")
        required = ("event_id", "source_repo", "source_commit", "artifact_sha256", "failure_class")
        if any(not record.get(field) for field in required):
            raise ValueError("failure record lacks required source identity")
        record_sha = sha256_hex(canonical_json(dict(record)))
        return self.sign_claims({
            "subject": "hermes-failure:" + str(record["event_id"]),
            "record_sha256": record_sha,
            "source_repo": record["source_repo"],
            "source_commit": record["source_commit"],
            "artifact_sha256": record["artifact_sha256"],
            "failure_class": record["failure_class"],
        })


class MerlinCandidateSigner(Ed25519ReceiptSigner):
    def __init__(self, *, key_id: str, private_key_pem: str):
        super().__init__(issuer="merlin-source", key_id=key_id, private_key_pem=private_key_pem)

    @classmethod
    def from_env(cls):
        key_id = os.environ.get("MERLIN_SOURCE_SIGNING_KEY_ID", "").strip()
        private_key = os.environ.get("MERLIN_SOURCE_SIGNING_KEY_PEM", "")
        if not key_id or not private_key:
            raise RuntimeError("Merlin candidate signing capability unavailable: required secret is not configured")
        return cls(key_id=key_id, private_key_pem=private_key)


class HermesRSIBridge:
    """Idempotent authenticated ingestion and convergent failure induction."""

    def __init__(self, ledger: AppendOnlyLedger):
        self.ledger = ledger

    def ingest_failure(self, record: Mapping[str, Any], receipt: SignedReceipt) -> dict[str, Any]:
        return ingest_hermes_failure(self.ledger, record, receipt)

    def _trajectories(self, failure_signature: str):
        chain = self.ledger.verify_chain()
        if not chain.get("valid"):
            raise RuntimeError("RSI ledger integrity check failed")
        rows = self.ledger.events_by_type("rsi.induction_seeded")
        selected = []
        for row in rows:
            payload = json.loads(row["payload"])
            if payload.get("failure_signature") != failure_signature:
                continue
            if (not payload.get("corrective_steps") or not payload.get("run_id")
                    or not payload.get("trigger_condition")):
                continue
            selected.append((row, payload))
        one_per_run = {}
        for row, payload in selected:
            one_per_run.setdefault(payload["run_id"], (row, payload))
        selected = list(one_per_run.values())
        run_ids = {payload["run_id"] for _, payload in selected}
        failure_ids = {payload["hermes_event_id"] for _, payload in selected}
        receipt_digests = {payload["source_receipt_digest"] for _, payload in selected}
        if min(len(run_ids), len(failure_ids), len(receipt_digests)) < 2:
            raise ValueError("induction requires two distinct authenticated failure events from independent runs")
        trajectories = []
        for _, payload in selected:
            trajectories.append(rsi.FailureTrajectory(
                failure_id=str(payload["hermes_event_id"]),
                failure_signature=str(payload["failure_signature"]),
                trigger_condition=str(payload["trigger_condition"]),
                corrective_steps=tuple(payload["corrective_steps"]),
                source_commit_sha=str(payload["source_commit"]),
                source_artifact_sha256=str(payload["artifact_sha256"]),
            ))
        return trajectories, [row["event_hash"] for row, _ in selected], selected

    def induce_candidate(
        self, *, skill_id: str, version: int, purpose: str,
        failure_signature: str, guardrails: tuple[str, ...],
        source_repo: str, source_commit: str,
        candidate_signer: MerlinCandidateSigner,
        parent_candidate_id: str | None = None,
    ) -> dict[str, Any]:
        if len(source_commit) != 40 or any(c not in "0123456789abcdef" for c in source_commit):
            raise ValueError("candidate generator source commit must be a lowercase Git SHA")
        if not isinstance(source_repo, str) or not re.fullmatch(
                r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", source_repo):
            raise ValueError("candidate generator source_repo must be owner/name")
        trajectories, seed_hashes, selected = self._trajectories(failure_signature)
        candidate = rsi.induce_skill_candidate(
            skill_id=skill_id, version=version, purpose=purpose,
            trajectories=trajectories, guardrails=guardrails,
        )
        artifact_bytes = canonical_json(asdict(candidate))
        artifact_sha = sha256_hex(artifact_bytes)
        candidate_id = f"rsi-candidate:{artifact_sha[:32]}"
        claims = {
            "candidate_id": candidate_id,
            "artifact_sha256": artifact_sha,
            "source_repo": source_repo,
            "source_commit": source_commit,
            "induction_seed_event_hashes": sorted(seed_hashes),
            "source_failure_ids": sorted(candidate.source_failure_ids),
            "authority": "candidate-provenance-only",
        }
        source_receipt = candidate_signer.sign_claims(claims)
        event = self.ledger.record_candidate(
            candidate_id=candidate_id, parent_candidate_id=parent_candidate_id,
            source_receipt=source_receipt, artifact_sha256=artifact_sha,
            generator="merlin.rsi.induce_skill_candidate",
            mutation={
                "skill_procedure": asdict(candidate),
                "failure_signature": failure_signature,
                "source_failure_ids": sorted(candidate.source_failure_ids),
                "source_run_ids": sorted({payload["run_id"] for _, payload in selected}),
            },
            induction_seed_event_hashes=seed_hashes,
            artifact_bytes=artifact_bytes,
            artifact_media_type="application/vnd.merlin.skill-procedure+json",
        )
        return {
            "candidate_id": candidate_id, "candidate": asdict(candidate),
            "artifact_sha256": artifact_sha, "artifact_size_bytes": len(artifact_bytes),
            "induction_seed_event_hashes": sorted(seed_hashes),
            "ledger_event": event, "promotion_authority": False,
        }
