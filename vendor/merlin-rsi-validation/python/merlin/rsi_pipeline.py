"""Evidence-bound RSI ingress sharing the canonical C++ research episode ledger.

Hermes and evaluator receipts use Ed25519 envelopes. CACE verification accepts
the existing cace-signed-attestation-v1 format and requires a separately pinned
verifier-key allowlist. Missing trust anchors fail closed.

The SQLite adapter writes the exact research_episode_events schema and hash
algorithm used by expert_robot::research::ResearchEpisodeLedger. It does not
create a second RSI event table.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
import base64
import hashlib
import importlib.util
import json
import math
import os
import re
import sqlite3
import statistics
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Mapping


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def sha256_hex(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _is_sha256(value: Any) -> bool:
    return (isinstance(value, str) and len(value) == 64
            and all(c in "0123456789abcdef" for c in value))


def _is_git_commit(value: Any) -> bool:
    return (isinstance(value, str) and len(value) == 40
            and all(c in "0123456789abcdef" for c in value))


def _parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("receipt timestamp must be timezone-aware")
    return parsed.astimezone(timezone.utc)


@dataclass(frozen=True)
class SignedReceipt:
    """Domain receipt signed by a trusted Ed25519 issuer."""
    schema_version: int
    issuer: str
    key_id: str
    issued_at: str
    claims: Mapping[str, Any]
    signature_b64: str

    def unsigned_payload(self) -> dict[str, Any]:
        return {"schema_version": self.schema_version, "issuer": self.issuer,
                "key_id": self.key_id, "issued_at": self.issued_at,
                "claims": dict(self.claims)}

    @property
    def receipt_digest(self) -> str:
        return sha256_hex(canonical_json(
            {**self.unsigned_payload(), "signature_b64": self.signature_b64}))


def verify_signed_receipt(
    receipt: SignedReceipt,
    trusted_keys: Mapping[str, str],
    *,
    expected_issuer: str | None = None,
    expected_claims: Mapping[str, Any] | None = None,
    now: datetime | None = None,
    max_age: timedelta = timedelta(days=7),
) -> bool:
    """Verify Ed25519 over canonical JSON using only the trusted issuer key."""
    if receipt.schema_version != 1 or not receipt.issuer or not receipt.key_id:
        return False
    if expected_issuer is not None and receipt.issuer != expected_issuer:
        return False
    pem = trusted_keys.get(receipt.key_id)
    if not pem:
        return False
    try:
        issued = _parse_time(receipt.issued_at)
        current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        if issued > current + timedelta(minutes=5) or current - issued > max_age:
            return False
        if expected_claims and any(receipt.claims.get(k) != v
                                    for k, v in expected_claims.items()):
            return False
        signature = base64.b64decode(receipt.signature_b64, validate=True)
        payload = canonical_json(receipt.unsigned_payload())
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        key = serialization.load_pem_public_key(pem.encode("utf-8"))
        if not isinstance(key, Ed25519PublicKey):
            return False
        key.verify(signature, payload)
        return True
    except Exception:
        return False


# CACE's Ed25519 attestation profile and domain separators.
_CACE_ATTESTATION_DOMAIN = b"CACE:SIGNED-ATTESTATION:v1\0"
_CACE_BUNDLE_DOMAIN = b"CACE:EVIDENCE:BUNDLE:v1\0"
_CACE_ARTIFACT_LEAF_DOMAIN = b"CACE:EVIDENCE:ARTIFACT-LEAF:v1\0"


def cace_rsi_bundle_sha256(
    *, candidate_id: str, candidate_digest: str,
    benchmark_manifest_sha256: str, evaluator_receipt_sha256: str,
    source_repo: str, source_commit: str,
) -> str:
    """Reproduce CACE EvidenceBundle v1 identity for a one-artifact RSI manifest."""
    manifest = {
        "schema": "merlin-rsi-evidence-manifest-v1",
        "candidate_id": candidate_id, "candidate_digest": candidate_digest,
        "benchmark_manifest_sha256": benchmark_manifest_sha256,
        "evaluator_receipt_sha256": evaluator_receipt_sha256,
        "source_repo": source_repo, "source_commit": source_commit,
    }
    manifest_bytes = canonical_json(manifest)
    artifact = {
        "artifact_id": "merlin-rsi-evidence-manifest",
        "sha256": sha256_hex(manifest_bytes), "size_bytes": len(manifest_bytes),
        "role": "rsi-evidence-manifest", "media_type": "application/json",
        "path": "merlin-rsi-evidence-manifest.json", "metadata": {},
    }
    leaf = sha256_hex(_CACE_ARTIFACT_LEAF_DOMAIN + canonical_json(artifact))
    bindings = {
        "candidate_id": candidate_id, "candidate_digest": candidate_digest,
        "benchmark_manifest_sha256": benchmark_manifest_sha256,
        "evaluator_receipt_sha256": evaluator_receipt_sha256,
        "source_repo": source_repo, "source_commit": source_commit,
        "authority": "verification-only",
    }
    bundle = {
        "schema": "cace-evidence-bundle-v1",
        "identity_algorithm": "sha256/cace-canonical-json-v1",
        "merkle_algorithm": "sha256/cace-merkle-v1",
        "proof_effect": "none", "artifacts": [artifact],
        "merkle_root_sha256": leaf, "bindings": bindings,
        "notes": ["Merlin RSI exact-artifact independent verification"],
    }
    return sha256_hex(_CACE_BUNDLE_DOMAIN + canonical_json(bundle))


def _load_approved_cace_keys() -> dict[str, str]:
    """Load a server-pinned CACE key allowlist; never accept caller-supplied trust."""
    raw = os.environ.get("MERLIN_CACE_TRUST_STORE_JSON", "")
    expected_digest = os.environ.get("MERLIN_CACE_TRUST_STORE_SHA256", "")
    if not raw or not _is_sha256(expected_digest):
        raise PermissionError("independent CACE trust store is not configured")
    if sha256_hex(raw.encode("utf-8")) != expected_digest:
        raise PermissionError("independent CACE trust store digest mismatch")
    try:
        document = json.loads(raw)
    except (TypeError, ValueError) as exc:
        raise PermissionError("independent CACE trust store is invalid JSON") from exc
    if (not isinstance(document, Mapping)
        or set(document) != {"schema", "keys"}
        or document.get("schema") != "merlin-cace-trust-store-v1"
        or not isinstance(document.get("keys"), list)):
        raise PermissionError("independent CACE trust store schema mismatch")
    approved: dict[str, str] = {}
    for entry in document["keys"]:
        if (not isinstance(entry, Mapping)
            or set(entry) != {"key_id", "verifier_id", "status"}
            or entry.get("verifier_id") != "cace"
            or entry.get("status") != "active"):
            raise PermissionError("CACE trust store contains an invalid or inactive key")
        key_id = entry.get("key_id")
        if not isinstance(key_id, str) or not re.fullmatch(r"ed25519:[0-9a-f]{64}", key_id):
            raise PermissionError("CACE trust store key ID is invalid")
        if key_id in approved:
            raise PermissionError("CACE trust store contains duplicate key IDs")
        approved[key_id] = "cace"
    if not approved:
        raise PermissionError("CACE trust store contains no active verifier keys")
    return approved


def verify_cace_attestation(
    attestation: Mapping[str, Any], approved_keys: Mapping[str, str], *,
    expected_claim_id: str, expected_bundle_sha256: str,
    expected_bindings: Mapping[str, Any], expected_verifier_id: str = "cace",
    now: datetime | None = None, max_age: timedelta = timedelta(days=30),
) -> dict[str, str]:
    """Verify CACE cace-signed-attestation-v1 and an independently pinned key."""
    envelope_keys = {"schema", "signature_algorithm", "proof_effect",
                     "statement_sha256", "statement", "public_key_pem", "signature_b64"}
    statement_keys = {"schema", "signature_algorithm", "proof_effect", "verifier_id",
                      "verifier_key_id", "claim_id", "bundle_sha256",
                      "created_at_utc", "purpose", "bindings"}
    if not isinstance(attestation, Mapping) or set(attestation) != envelope_keys:
        raise PermissionError("CACE attestation envelope schema mismatch")
    statement = attestation.get("statement")
    if not isinstance(statement, Mapping) or set(statement) != statement_keys:
        raise PermissionError("CACE attestation statement schema mismatch")
    if (attestation.get("schema") != "cace-signed-attestation-v1"
        or attestation.get("signature_algorithm") != "ed25519"
        or attestation.get("proof_effect") != "none"
        or statement.get("schema") != "cace-attestation-statement-v1"
        or statement.get("signature_algorithm") != "ed25519"
        or statement.get("proof_effect") != "none"
        or statement.get("purpose") != "independent-reproduction"):
        raise PermissionError("CACE attestation profile or purpose is not accepted")
    if statement.get("verifier_id") != expected_verifier_id:
        raise PermissionError("CACE verifier identity mismatch")
    if statement.get("claim_id") != expected_claim_id:
        raise PermissionError("CACE claim ID does not bind this candidate")
    if statement.get("bundle_sha256") != expected_bundle_sha256:
        raise PermissionError("CACE evidence bundle digest mismatch")
    bindings = statement.get("bindings")
    if (not isinstance(bindings, Mapping) or set(bindings) != set(expected_bindings)
        or any(bindings.get(k) != v for k, v in expected_bindings.items())):
        raise PermissionError("CACE attestation bindings do not match candidate evidence")
    created_text = str(statement.get("created_at_utc", ""))
    created = datetime.strptime(created_text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if created > current + timedelta(minutes=5) or current - created > max_age:
        raise PermissionError("CACE attestation is stale or future-dated")
    signing_bytes = _CACE_ATTESTATION_DOMAIN + canonical_json(dict(statement))
    statement_digest = sha256_hex(signing_bytes)
    if statement_digest != attestation.get("statement_sha256"):
        raise PermissionError("CACE statement digest mismatch")
    try:
        signature = base64.b64decode(str(attestation.get("signature_b64", "")), validate=True)
    except Exception as exc:
        raise PermissionError("CACE signature encoding is invalid") from exc
    if len(signature) != 64:
        raise PermissionError("CACE Ed25519 signature must be 64 bytes")
    public_pem = str(attestation.get("public_key_pem", ""))
    if not public_pem:
        raise PermissionError("CACE public key is missing")
    try:
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        key = serialization.load_pem_public_key(public_pem.encode("ascii"))
        if not isinstance(key, Ed25519PublicKey):
            raise PermissionError("CACE public key is not Ed25519")
        raw = key.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        actual_key_id = "ed25519:" + sha256_hex(raw)
        key.verify(signature, signing_bytes)
    except PermissionError:
        raise
    except Exception as exc:
        raise PermissionError("CACE Ed25519 signature verification failed") from exc
    if statement.get("verifier_key_id") != actual_key_id:
        raise PermissionError("CACE verifier key ID does not match public key")
    if approved_keys.get(actual_key_id) != expected_verifier_id:
        raise PermissionError("CACE verifier key is not independently approved")
    return {
        "attestation_sha256": sha256_hex(canonical_json(dict(attestation))),
        "statement_sha256": statement_digest, "verifier_key_id": actual_key_id,
        "verifier_id": expected_verifier_id, "bundle_sha256": expected_bundle_sha256,
    }


class AppendOnlyLedger:
    """Adapter over the canonical C++ ResearchEpisodeLedger SQLite schema."""

    def __init__(self, database: str | Path):
        self.database = str(database)
        with self._connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS research_episode_events (
                    episode_id TEXT NOT NULL, sequence INTEGER NOT NULL,
                    event_type TEXT NOT NULL, payload TEXT NOT NULL,
                    payload_sha256 TEXT NOT NULL, previous_event_hash TEXT NOT NULL,
                    event_hash TEXT NOT NULL,
                    recorded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY(episode_id, sequence), UNIQUE(event_hash)
                );
                CREATE INDEX IF NOT EXISTS idx_research_episode
                    ON research_episode_events(episode_id, sequence);
                CREATE TRIGGER IF NOT EXISTS research_episode_events_no_update
                BEFORE UPDATE ON research_episode_events
                BEGIN SELECT RAISE(ABORT, 'append-only research episode ledger'); END;
                CREATE TRIGGER IF NOT EXISTS research_episode_events_no_delete
                BEFORE DELETE ON research_episode_events
                BEGIN SELECT RAISE(ABORT, 'append-only research episode ledger'); END;
            """)

    def _connect(self):
        db = sqlite3.connect(self.database, timeout=15)
        db.row_factory = sqlite3.Row
        return db

    @staticmethod
    def _event_hash(episode_id: str, sequence: int, event_type: str,
                    payload_sha256: str, previous_hash: str) -> str:
        material = (f"episode={episode_id}\nsequence={sequence}\n"
                    f"type={event_type}\npayload_sha256={payload_sha256}\n"
                    f"previous_event_hash={previous_hash}\n")
        return sha256_hex(material.encode("utf-8"))

    def append(self, event_type: str, entity_id: str,
               payload: Mapping[str, Any]) -> dict[str, Any]:
        if not event_type or not entity_id:
            raise ValueError("event_type and episode_id are required")
        payload_text = canonical_json(dict(payload)).decode("utf-8")
        payload_hash = sha256_hex(payload_text.encode("utf-8"))
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            last = db.execute(
                "SELECT sequence,event_hash FROM research_episode_events "
                "WHERE episode_id=? ORDER BY sequence DESC LIMIT 1",
                (entity_id,)).fetchone()
            sequence = int(last["sequence"]) + 1 if last else 0
            previous = str(last["event_hash"]) if last else ""
            event_hash = self._event_hash(
                entity_id, sequence, event_type, payload_hash, previous)
            db.execute(
                """INSERT INTO research_episode_events
                   (episode_id,sequence,event_type,payload,payload_sha256,
                    previous_event_hash,event_hash) VALUES (?,?,?,?,?,?,?)""",
                (entity_id, sequence, event_type, payload_text, payload_hash,
                 previous, event_hash))
            return {"seq": sequence, "event_id": event_hash[:32],
                    "event_hash": event_hash, "episode_id": entity_id}

    def events(self, episode_id: str) -> list[dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute(
                "SELECT * FROM research_episode_events WHERE episode_id=? ORDER BY sequence",
                (episode_id,)).fetchall()
        return [dict(row) for row in rows]

    def _candidate_event(self, episode_id: str, event_type: str,
                         candidate_id: str) -> dict[str, Any] | None:
        for row in self.events(episode_id):
            if row["event_type"] == event_type:
                payload = json.loads(row["payload"])
                if payload.get("candidate_id") == candidate_id:
                    return payload
        return None

    def verify_chain(self, episode_id: str | None = None) -> dict[str, Any]:
        with self._connect() as db:
            if episode_id is None:
                rows = db.execute(
                    "SELECT * FROM research_episode_events ORDER BY episode_id,sequence").fetchall()
            else:
                rows = db.execute(
                    "SELECT * FROM research_episode_events WHERE episode_id=? ORDER BY sequence",
                    (episode_id,)).fetchall()
        previous_by_episode: dict[str, str] = {}
        next_sequence: dict[str, int] = {}
        checked = 0
        for row in rows:
            episode = row["episode_id"]
            previous = previous_by_episode.get(episode, "")
            expected_sequence = next_sequence.get(episode, 0)
            payload_hash = sha256_hex(row["payload"].encode("utf-8"))
            calculated = self._event_hash(
                episode, row["sequence"], row["event_type"], payload_hash, previous)
            if (row["sequence"] != expected_sequence
                or row["payload_sha256"] != payload_hash
                or row["previous_event_hash"] != previous
                or row["event_hash"] != calculated):
                return {"valid": False, "checked": checked,
                        "failed_episode_id": episode, "failed_sequence": row["sequence"]}
            previous_by_episode[episode] = calculated
            next_sequence[episode] = expected_sequence + 1
            checked += 1
        return {"valid": True, "checked": checked, "heads": previous_by_episode}

    def record_candidate(
        self, *, candidate_id: str, parent_candidate_id: str | None,
        source_receipt: SignedReceipt, artifact_sha256: str,
        generator: str, mutation: Mapping[str, Any],
        trusted_keys: Mapping[str, str], episode_id: str | None = None,
        induction_seed_event_hash: str | None = None,
    ) -> dict[str, Any]:
        episode = episode_id or candidate_id
        if not _is_sha256(artifact_sha256):
            raise ValueError("artifact_sha256 must be lowercase SHA-256")
        if not candidate_id or not generator:
            raise ValueError("candidate_id and generator are required")
        required = {"candidate_id": candidate_id, "artifact_sha256": artifact_sha256}
        if induction_seed_event_hash is not None:
            if not _is_sha256(induction_seed_event_hash):
                raise ValueError("induction_seed_event_hash must be lowercase SHA-256")
            with self._connect() as db:
                seed = db.execute(
                    "SELECT episode_id FROM research_episode_events "
                    "WHERE event_hash=? AND event_type='rsi.induction_seeded'",
                    (induction_seed_event_hash,),
                ).fetchone()
            if seed is None:
                raise ValueError("candidate induction seed is absent from authenticated Hermes failure history")
            required["induction_seed_event_hash"] = induction_seed_event_hash
        if not verify_signed_receipt(source_receipt, trusted_keys,
            expected_issuer="merlin-source", expected_claims=required):
            raise PermissionError("candidate source receipt is missing, untrusted, or mismatched")
        source_repo = source_receipt.claims.get("source_repo")
        source_commit = source_receipt.claims.get("source_commit")
        if not isinstance(source_repo, str) or not source_repo.strip() or not _is_git_commit(source_commit):
            raise ValueError("candidate source receipt must bind source_repo and exact 40-hex source_commit")
        if parent_candidate_id:
            with self._connect() as db:
                rows = db.execute(
                    "SELECT payload FROM research_episode_events WHERE event_type='candidate.created'"
                ).fetchall()
            if not any(json.loads(row["payload"]).get("candidate_id") == parent_candidate_id
                       for row in rows):
                raise ValueError("parent candidate is absent from append-only lineage")
        return self.append("candidate.created", episode, {
            "candidate_id": candidate_id, "parent_candidate_id": parent_candidate_id,
            "source_receipt_digest": source_receipt.receipt_digest,
            "source_claims": dict(source_receipt.claims),
            "source_repo": source_repo, "source_commit": source_commit,
            "artifact_sha256": artifact_sha256, "generator": generator,
            "induction_seed_event_hash": induction_seed_event_hash,
            "mutation": dict(mutation),
        })

    def record_evaluation(
        self, *, candidate_id: str, artifact_sha256: str,
        suite_sha256: str, metrics: Mapping[str, float], passed: bool,
        evaluator_receipt: SignedReceipt, trusted_keys: Mapping[str, str],
        episode_id: str | None = None,
    ) -> dict[str, Any]:
        episode = episode_id or candidate_id
        if not _is_sha256(artifact_sha256) or not _is_sha256(suite_sha256):
            raise ValueError("candidate and benchmark digests must be SHA-256")
        normalized = {str(k): float(v) for k, v in metrics.items()}
        if any(not math.isfinite(v) for v in normalized.values()):
            raise ValueError("evaluation metrics must be finite")
        metrics_sha = sha256_hex(canonical_json(normalized))
        expected = {"candidate_id": candidate_id, "candidate_digest": artifact_sha256,
                    "benchmark_manifest_sha256": suite_sha256,
                    "metrics_sha256": metrics_sha,
                    "status": "pass" if passed else "fail"}
        if not verify_signed_receipt(evaluator_receipt, trusted_keys,
            expected_issuer="merlin-evaluator", expected_claims=expected):
            raise PermissionError("evaluator receipt is missing, untrusted, or mismatched")
        candidate = self._candidate_event(episode, "candidate.created", candidate_id)
        if not candidate or candidate.get("artifact_sha256") != artifact_sha256:
            raise ValueError("evaluation does not bind a recorded candidate artifact")
        return self.append("candidate.evaluated", episode, {
            "candidate_id": candidate_id, "artifact_sha256": artifact_sha256,
            "suite_sha256": suite_sha256, "metrics": normalized,
            "metrics_sha256": metrics_sha, "passed": bool(passed),
            "evaluator_receipt_digest": evaluator_receipt.receipt_digest,
        })

    def _cace_evidence(self, episode_id: str, candidate_id: str,
                       artifact_sha256: str, suite_sha256: str):
        candidate = self._candidate_event(episode_id, "candidate.created", candidate_id)
        evaluation = self._candidate_event(episode_id, "candidate.evaluated", candidate_id)
        if not candidate or not evaluation:
            raise PermissionError("candidate lineage or evaluation evidence is absent")
        if candidate.get("artifact_sha256") != artifact_sha256:
            raise PermissionError("candidate artifact digest does not match lineage")
        if (evaluation.get("artifact_sha256") != artifact_sha256
            or evaluation.get("suite_sha256") != suite_sha256):
            raise PermissionError("evaluation is not bound to exact candidate and frozen suite")
        if evaluation.get("passed") is not True:
            raise PermissionError("only passing held-out evaluations may be independently verified")
        bindings = {
            "candidate_id": candidate_id, "candidate_digest": artifact_sha256,
            "benchmark_manifest_sha256": suite_sha256,
            "evaluator_receipt_sha256": evaluation["evaluator_receipt_digest"],
            "source_repo": candidate["source_repo"], "source_commit": candidate["source_commit"],
            "authority": "verification-only",
        }
        bundle_sha = cace_rsi_bundle_sha256(
            candidate_id=candidate_id, candidate_digest=artifact_sha256,
            benchmark_manifest_sha256=suite_sha256,
            evaluator_receipt_sha256=evaluation["evaluator_receipt_digest"],
            source_repo=candidate["source_repo"], source_commit=candidate["source_commit"])
        return candidate, evaluation, bundle_sha, bindings

    def record_cace_verification(
        self, *, candidate_id: str, attestation: Mapping[str, Any],
        artifact_sha256: str, suite_sha256: str,
        episode_id: str | None = None,
    ) -> dict[str, Any]:
        episode = episode_id or candidate_id
        _, _, bundle_sha, bindings = self._cace_evidence(
            episode, candidate_id, artifact_sha256, suite_sha256)
        approved_keys = _load_approved_cace_keys()
        verified = verify_cace_attestation(
            attestation, approved_keys, expected_claim_id=candidate_id,
            expected_bundle_sha256=bundle_sha, expected_bindings=bindings)
        return self.append("candidate.cace_verified", episode, {
            "candidate_id": candidate_id, "artifact_sha256": artifact_sha256,
            "suite_sha256": suite_sha256, "bundle_sha256": bundle_sha,
            "attestation_sha256": verified["attestation_sha256"],
            "statement_sha256": verified["statement_sha256"],
            "verifier_id": verified["verifier_id"],
            "verifier_key_id": verified["verifier_key_id"],
            "authority": "verification-only",
        })

    def record_promotion(
        self, *, candidate_id: str, artifact_sha256: str,
        suite_sha256: str, attestation: Mapping[str, Any],
        approval_receipt: SignedReceipt, approval_keys: Mapping[str, str],
        episode_id: str | None = None,
    ) -> dict[str, Any]:
        episode = episode_id or candidate_id
        _, _, bundle_sha, bindings = self._cace_evidence(
            episode, candidate_id, artifact_sha256, suite_sha256)
        cace_approved_keys = _load_approved_cace_keys()
        verified = verify_cace_attestation(
            attestation, cace_approved_keys, expected_claim_id=candidate_id,
            expected_bundle_sha256=bundle_sha, expected_bindings=bindings)
        expected_approval = {
            "candidate_id": candidate_id, "candidate_digest": artifact_sha256,
            "benchmark_manifest_sha256": suite_sha256,
            "cace_attestation_sha256": verified["attestation_sha256"],
            "action": "promote", "target": "qualified",
        }
        if not verify_signed_receipt(approval_receipt, approval_keys,
            expected_issuer="merlin-approver", expected_claims=expected_approval):
            raise PermissionError("separate signed promotion approval is missing or invalid")
        cace_event = self._candidate_event(episode, "candidate.cace_verified", candidate_id)
        if (not cace_event or cace_event.get("artifact_sha256") != artifact_sha256
            or cace_event.get("suite_sha256") != suite_sha256
            or cace_event.get("attestation_sha256") != verified["attestation_sha256"]):
            raise PermissionError("independent CACE verification event is absent or mismatched")
        if not self.verify_chain(episode)["valid"]:
            raise RuntimeError("canonical research episode ledger integrity check failed")
        return self.append("candidate.promoted", episode, {
            "candidate_id": candidate_id, "artifact_sha256": artifact_sha256,
            "suite_sha256": suite_sha256, "bundle_sha256": bundle_sha,
            "cace_attestation_sha256": verified["attestation_sha256"],
            "approval_receipt_digest": approval_receipt.receipt_digest,
            "promotion_authority": "explicit-signed-approval",
        })


def ingest_hermes_failure(
    ledger: AppendOnlyLedger, record: Mapping[str, Any],
    receipt: SignedReceipt, trusted_keys: Mapping[str, str],
) -> dict[str, Any]:
    """Authenticate a Hermes failure and append an idempotent RSI induction seed."""
    required_fields = ("event_id", "failure_class", "summary", "source_repo",
                       "source_commit", "artifact_sha256")
    if any(not record.get(k) for k in required_fields):
        raise ValueError("Hermes failure record is incomplete")
    if not _is_git_commit(record["source_commit"]) or not _is_sha256(record["artifact_sha256"]):
        raise ValueError("Hermes failure must bind exact source commit and artifact SHA-256")
    episode_id = "rsi-induction:" + str(record["event_id"])
    claims = {
        "subject": "hermes-failure:" + str(record["event_id"]),
        "source_repo": record["source_repo"], "source_commit": record["source_commit"],
        "artifact_sha256": record["artifact_sha256"],
        "failure_class": record["failure_class"],
    }
    if not verify_signed_receipt(receipt, trusted_keys, expected_issuer="hermes",
                                 expected_claims=claims):
        raise PermissionError("Hermes failure lacks an authenticated source receipt")
    existing = ledger.events(episode_id)
    if existing:
        seed_row = next((row for row in existing if row["event_type"] == "rsi.induction_seeded"), None)
        seed = json.loads(seed_row["payload"]) if seed_row else None
        if seed and seed.get("source_receipt_digest") == receipt.receipt_digest:
            return {"seq": seed_row["sequence"], "event_hash": seed_row["event_hash"],
                    "episode_id": episode_id, "idempotent_replay": True}
        raise PermissionError("Hermes event ID replayed with different evidence")
    return ledger.append("rsi.induction_seeded", episode_id, {
        "hermes_event_id": record["event_id"],
        "failure_class": record["failure_class"], "summary": record["summary"],
        "source_repo": record["source_repo"], "source_commit": record["source_commit"],
        "artifact_sha256": record["artifact_sha256"],
        "source_receipt_digest": receipt.receipt_digest,
        "induction": {
            "generalize_failure": True, "generate_counterexample": True,
            "propose_regression_test": True, "compare_alternative_representation": True,
            "promotion_authority": False,
        },
    })


def dispatch_rsi_induction_seed(
    ledger: AppendOnlyLedger,
    seed_event_hash: str,
    transport: Any,
    trusted_worker_keys: Mapping[str, str],
) -> dict[str, Any]:
    """Dispatch one authenticated Hermes seed and persist a signed worker ACK.

    The transport is deliberately injected at the boundary. No endpoint,
    credentials, or worker capability is assumed to exist. Missing transport
    fails closed; the ACK must be signed by a separately trusted RSI worker.
    """
    if not _is_sha256(seed_event_hash):
        raise ValueError("seed_event_hash must be lowercase SHA-256")
    if transport is None:
        raise RuntimeError("RSI induction transport is unavailable")
    seed_row = None
    with ledger._connect() as db:
        seed_row = db.execute(
            "SELECT episode_id,event_type,payload,event_hash "
            "FROM research_episode_events WHERE event_hash=?",
            (seed_event_hash,),
        ).fetchone()
    if seed_row is None or seed_row["event_type"] != "rsi.induction_seeded":
        raise ValueError("dispatch target is not an authenticated Hermes induction seed")
    episode_id = str(seed_row["episode_id"])
    if not ledger.verify_chain(episode_id)["valid"]:
        raise RuntimeError("refusing RSI dispatch from an invalid episode chain")
    seed_payload = json.loads(seed_row["payload"])
    existing = next(
        (event for event in ledger.events(episode_id)
         if event["event_type"] == "rsi.induction_dispatched"
         and json.loads(event["payload"]).get("seed_event_hash") == seed_event_hash),
        None,
    )
    if existing is not None:
        return {
            "seq": existing["sequence"], "event_hash": existing["event_hash"],
            "episode_id": episode_id, "idempotent_replay": True,
        }
    idempotency_key = "merlin-rsi-seed:" + seed_event_hash
    acknowledgement = transport.submit_induction(
        seed_event_hash=seed_event_hash,
        episode_id=episode_id,
        idempotency_key=idempotency_key,
        seed=seed_payload,
    )
    if not isinstance(acknowledgement, SignedReceipt):
        raise PermissionError("RSI worker must return a signed receipt envelope")
    expected = {
        "seed_event_hash": seed_event_hash,
        "episode_id": episode_id,
        "idempotency_key": idempotency_key,
        "status": "accepted",
    }
    if not verify_signed_receipt(
        acknowledgement, trusted_worker_keys,
        expected_issuer="merlin-rsi-worker", expected_claims=expected,
    ):
        raise PermissionError("RSI worker acknowledgement is unauthenticated or mismatched")
    worker_id = acknowledgement.claims.get("worker_id")
    task_id = acknowledgement.claims.get("task_id")
    if not isinstance(worker_id, str) or not worker_id.strip():
        raise PermissionError("RSI worker acknowledgement omitted worker_id")
    if not isinstance(task_id, str) or not task_id.strip():
        raise PermissionError("RSI worker acknowledgement omitted task_id")
    return ledger.append("rsi.induction_dispatched", episode_id, {
        "seed_event_hash": seed_event_hash,
        "idempotency_key": idempotency_key,
        "worker_id": worker_id,
        "task_id": task_id,
        "acknowledgement_receipt_digest": acknowledgement.receipt_digest,
        "status": "accepted",
        "promotion_authority": False,
    })


class ResearchMetadataCache:
    """Persistent Crossref/arXiv cache with cross-process host rate limits."""

    def __init__(self, database: str | Path, *, crossref_interval: float = 1.0,
                 arxiv_interval: float = 3.0, cache_ttl_seconds: int = 30 * 86400,
                 user_agent: str = "MerlinResearch/1.0 (+https://github.com/Mannyspiro/expert-robot)"):
        self.database = str(database)
        self.intervals = {"api.crossref.org": max(1.0, crossref_interval),
                          "export.arxiv.org": max(3.0, arxiv_interval)}
        self.cache_ttl_seconds = max(60, int(cache_ttl_seconds))
        self.user_agent = user_agent
        with sqlite3.connect(self.database, timeout=15) as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS research_metadata_cache (
                    provider TEXT NOT NULL, identifier TEXT NOT NULL,
                    response_json TEXT NOT NULL, response_sha256 TEXT NOT NULL,
                    retrieved_at TEXT NOT NULL, PRIMARY KEY(provider,identifier)
                );
                CREATE TABLE IF NOT EXISTS research_request_clock (
                    host TEXT PRIMARY KEY, next_allowed_epoch REAL NOT NULL
                );
            """)

    def _cached(self, provider: str, identifier: str) -> dict[str, Any] | None:
        with sqlite3.connect(self.database, timeout=15) as db:
            row = db.execute(
                "SELECT response_json,response_sha256,retrieved_at "
                "FROM research_metadata_cache WHERE provider=? AND identifier=?",
                (provider, identifier)).fetchone()
        if not row:
            return None
        raw = row[0].encode("utf-8")
        if sha256_hex(raw) != row[1]:
            raise RuntimeError("research metadata cache integrity failure")
        retrieved = _parse_time(row[2])
        if (datetime.now(timezone.utc) - retrieved).total_seconds() > self.cache_ttl_seconds:
            return None
        return json.loads(row[0])

    def _reserve_rate_slot(self, host: str) -> None:
        interval = self.intervals[host]
        with sqlite3.connect(self.database, timeout=15) as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT next_allowed_epoch FROM research_request_clock WHERE host=?",
                (host,)).fetchone()
            now = time.time()
            slot = max(now, float(row[0]) if row else now)
            db.execute(
                """INSERT INTO research_request_clock(host,next_allowed_epoch)
                   VALUES(?,?) ON CONFLICT(host) DO UPDATE SET
                   next_allowed_epoch=excluded.next_allowed_epoch""",
                (host, slot + interval))
        delay = slot - time.time()
        if delay > 0:
            time.sleep(delay)

    def _request(self, host: str, url: str) -> bytes:
        for attempt in range(3):
            self._reserve_rate_slot(host)
            request = urllib.request.Request(
                url, headers={"User-Agent": self.user_agent,
                              "Accept": "application/json, application/atom+xml"})
            try:
                with urllib.request.urlopen(request, timeout=20) as response:
                    raw = response.read(2_000_000 + 1)
                if len(raw) > 2_000_000:
                    raise ValueError("metadata response exceeds 2 MB")
                return raw
            except urllib.error.HTTPError as exc:
                if exc.code not in (429, 500, 502, 503, 504) or attempt == 2:
                    raise
                retry_after = exc.headers.get("Retry-After", "")
                try:
                    delay = min(30.0, max(1.0, float(retry_after)))
                except (TypeError, ValueError):
                    delay = float(2 ** (attempt + 1))
                time.sleep(delay)
        raise RuntimeError("metadata request retry budget exhausted")

    def _get(self, provider: str, identifier: str, url: str) -> dict[str, Any]:
        cached = self._cached(provider, identifier)
        if cached is not None:
            return cached
        host = urllib.parse.urlparse(url).hostname or ""
        raw = self._request(host, url)
        if provider == "crossref":
            parsed = json.loads(raw.decode("utf-8"))
        else:
            root = ET.fromstring(raw)
            ns = {"a": "http://www.w3.org/2005/Atom"}
            entries = []
            for entry in root.findall("a:entry", ns):
                entries.append({
                    "id": entry.findtext("a:id", default="", namespaces=ns),
                    "title": " ".join(entry.findtext("a:title", default="", namespaces=ns).split()),
                    "summary": " ".join(entry.findtext("a:summary", default="", namespaces=ns).split()),
                    "published": entry.findtext("a:published", default="", namespaces=ns),
                    "authors": [a.findtext("a:name", default="", namespaces=ns)
                                for a in entry.findall("a:author", ns)],
                })
            parsed = {"feed": entries}
        encoded = canonical_json(parsed).decode("utf-8")
        digest = sha256_hex(encoded.encode("utf-8"))
        with sqlite3.connect(self.database, timeout=15) as db:
            db.execute(
                """INSERT INTO research_metadata_cache
                   (provider,identifier,response_json,response_sha256,retrieved_at)
                   VALUES (?,?,?,?,?)
                   ON CONFLICT(provider,identifier) DO UPDATE SET
                   response_json=excluded.response_json,
                   response_sha256=excluded.response_sha256,
                   retrieved_at=excluded.retrieved_at""",
                (provider, identifier, encoded, digest,
                 datetime.now(timezone.utc).isoformat()))
        return parsed

    def crossref_doi(self, doi: str) -> dict[str, Any]:
        normalized = doi.strip().removeprefix("https://doi.org/").removeprefix("http://doi.org/")
        if not normalized or len(normalized) > 512:
            raise ValueError("invalid DOI")
        url = "https://api.crossref.org/works/" + urllib.parse.quote(normalized, safe="/")
        return self._get("crossref", normalized, url)

    def arxiv_id(self, arxiv_id: str) -> dict[str, Any]:
        normalized = arxiv_id.strip().removeprefix("https://arxiv.org/abs/")
        if not normalized or len(normalized) > 128:
            raise ValueError("invalid arXiv identifier")
        url = "https://export.arxiv.org/api/query?id_list=" + urllib.parse.quote(normalized, safe=".")
        return self._get("arxiv", normalized, url)


def paired_adapter_gain(baseline: list[float], candidate: list[float],
                        *, minimum_cases: int = 20,
                        minimum_gain: float = 0.01) -> dict[str, Any]:
    if len(baseline) != len(candidate) or len(baseline) < minimum_cases:
        return {"eligible": False, "reason": "insufficient_paired_cases"}
    deltas = [float(b) - float(a) for a, b in zip(baseline, candidate)]
    if any(not math.isfinite(x) for x in deltas):
        return {"eligible": False, "reason": "non_finite_measurement"}
    mean = statistics.mean(deltas)
    se = statistics.stdev(deltas) / math.sqrt(len(deltas)) if len(deltas) > 1 else math.inf
    lower = mean - 1.96 * se
    return {"eligible": lower >= minimum_gain, "mean_gain": mean,
            "lower_95_bound": lower, "cases": len(deltas),
            "reason": "measured_gain" if lower >= minimum_gain else "no_reliable_gain"}


def paired_adapter_gate(
    baseline_by_domain: Mapping[str, list[float]],
    candidate_by_domain: Mapping[str, list[float]],
    *, minimum_total_cases: int = 20, minimum_gain: float = 0.01,
) -> dict[str, Any]:
    domains = {"mathematics", "lean", "research", "coding", "engineering"}
    if set(baseline_by_domain) != domains or set(candidate_by_domain) != domains:
        return {"eligible": False, "reason": "all_five_domains_required"}
    base = [x for domain in sorted(domains) for x in baseline_by_domain[domain]]
    cand = [x for domain in sorted(domains) for x in candidate_by_domain[domain]]
    aggregate = paired_adapter_gain(base, cand, minimum_cases=minimum_total_cases,
                                    minimum_gain=minimum_gain)
    domain_gains = {}
    for domain in sorted(domains):
        a, b = baseline_by_domain[domain], candidate_by_domain[domain]
        if not a or len(a) != len(b):
            return {"eligible": False, "reason": "unpaired_domain:" + domain}
        if any(not math.isfinite(float(x)) for x in a + b):
            return {"eligible": False, "reason": "non_finite_domain:" + domain}
        domain_gains[domain] = statistics.mean(float(y) - float(x) for x, y in zip(a, b))
    regressions = {d: gain for d, gain in domain_gains.items() if gain < 0.0}
    eligible = bool(aggregate["eligible"] and not regressions)
    return {**aggregate, "eligible": eligible, "domain_mean_gains": domain_gains,
            "domain_regressions": regressions,
            "reason": "measured_gain_all_domains" if eligible else
                      "domain_regression" if regressions else aggregate["reason"]}


def optional_adapter_status(
    package: str,
    baseline_by_domain: Mapping[str, list[float]] | None = None,
    candidate_by_domain: Mapping[str, list[float]] | None = None,
) -> dict[str, Any]:
    try:
        installed = importlib.util.find_spec(package) is not None
    except (ImportError, ModuleNotFoundError, ValueError):
        installed = False
    result = {"adapter": package, "installed": installed, "enabled": False,
              "reason": "not_installed" if not installed else
                        "awaiting_paired_heldout_evidence"}
    if installed and baseline_by_domain is not None and candidate_by_domain is not None:
        result.update(paired_adapter_gate(baseline_by_domain, candidate_by_domain))
    return result
