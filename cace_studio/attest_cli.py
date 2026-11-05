"""Headless CACE provenance attestation and E5 cross-verification interface."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
from typing import Any

from .core.attestation import (
    AttestationStatement,
    SignedAttestation,
    attestation_from_payload,
    generate_ed25519_keypair_pem,
    public_key_id,
    sign_attestation,
    verify_attestation,
)
from .core.cross_verification import evaluate_e5
from .core.evidence_ledger import EvidenceBundle, EvidenceLedgerError, bundle_from_payload, verify_bundle


def _render(payload: Any) -> str:
    return json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n"


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_bundle(path: Path) -> EvidenceBundle:
    document = _read_json(path)
    if not isinstance(document, dict):
        raise EvidenceLedgerError("bundle document must be a JSON object")
    if "bundle" in document:
        allowed = {"cli_schema", "command", "proof_effect", "bundle_sha256", "bundle"}
        extra = sorted(set(document) - allowed)
        if extra:
            raise EvidenceLedgerError(f"bundle document has unknown keys: {extra}")
        if document.get("proof_effect") != "none":
            raise EvidenceLedgerError("bundle document proof_effect must be 'none'")
        bundle = bundle_from_payload(document["bundle"])
        if document.get("bundle_sha256") != bundle.bundle_sha256:
            raise EvidenceLedgerError("bundle document SHA-256 mismatch")
    else:
        bundle = bundle_from_payload(document)
    verify_bundle(bundle)
    return bundle


def _load_attestation(path: Path) -> SignedAttestation:
    document = _read_json(path)
    if not isinstance(document, dict):
        raise ValueError("attestation document must be a JSON object")
    if "attestation" in document:
        allowed = {"cli_schema", "command", "proof_effect", "attestation"}
        extra = sorted(set(document) - allowed)
        if extra:
            raise ValueError(f"attestation document has unknown keys: {extra}")
        if document.get("proof_effect") != "none":
            raise ValueError("attestation document proof_effect must be 'none'")
        document = document["attestation"]
    return attestation_from_payload(document)


def _key_value(spec: str, label: str) -> tuple[str, str]:
    if "=" not in spec:
        raise ValueError(f"{label} must use KEY=VALUE syntax")
    key, value = spec.split("=", 1)
    key = key.strip()
    value = value.strip()
    if not key or not value:
        raise ValueError(f"{label} requires non-empty KEY and VALUE")
    return key, value


def _write_bytes(path: Path, data: bytes, *, force: bool, mode: int | None = None) -> None:
    if path.exists() and not force:
        raise FileExistsError(f"refusing to overwrite existing file: {path}")
    path.write_bytes(data)
    if mode is not None:
        try:
            os.chmod(path, mode)
        except OSError:
            pass


def _write_text(path: Path, text: str, *, force: bool) -> None:
    if path.exists() and not force:
        raise FileExistsError(f"refusing to overwrite existing file: {path}")
    path.write_text(text, encoding="utf-8")


def _created_at() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    keygen = sub.add_parser("keygen", help="Generate an Ed25519 verifier keypair")
    keygen.add_argument("--private-key", type=Path, required=True)
    keygen.add_argument("--public-key", type=Path, required=True)
    keygen.add_argument("--force", action="store_true")

    sign = sub.add_parser("sign", help="Sign an independent-reproduction attestation")
    sign.add_argument("--bundle", type=Path, required=True)
    sign.add_argument("--private-key", type=Path, required=True)
    sign.add_argument("--verifier-id", required=True)
    sign.add_argument("--claim-id", required=True)
    sign.add_argument("--qualified-commit", required=True)
    sign.add_argument("--proof-artifact-sha256", required=True)
    sign.add_argument("--created-at-utc")
    sign.add_argument("--output", type=Path, required=True)
    sign.add_argument("--force", action="store_true")

    verify = sub.add_parser("verify", help="Verify one signed attestation")
    verify.add_argument("attestation", type=Path)

    cross = sub.add_parser(
        "cross-verify",
        help="Evaluate E5 eligibility for approved independent attestations",
    )
    cross.add_argument("--claim-id", required=True)
    cross.add_argument("--bundle", type=Path, required=True)
    cross.add_argument("--attestation", action="append", type=Path, required=True)
    cross.add_argument(
        "--approve-key",
        action="append",
        default=[],
        metavar="KEY_ID=VERIFIER_ID",
        help="Explicit approved verifier-key binding; repeat for each verifier",
    )

    pqc_keygen = sub.add_parser("pqc-keygen", help="Generate an ML-DSA-65 verifier keypair")
    pqc_keygen.add_argument("--private-key", type=Path, required=True)
    pqc_keygen.add_argument("--public-key", type=Path, required=True)
    pqc_keygen.add_argument("--force", action="store_true")

    pqc_sign = sub.add_parser("pqc-sign", help="Sign a CACE evidence bundle with ML-DSA-65")
    pqc_sign.add_argument("--bundle", type=Path, required=True)
    pqc_sign.add_argument("--artifact-root", type=Path, required=True)
    pqc_sign.add_argument("--private-key", type=Path, required=True)
    pqc_sign.add_argument("--public-key", type=Path, required=True)
    pqc_sign.add_argument("--bindings", type=Path, required=True)
    pqc_sign.add_argument("--verifier-id", required=True)
    pqc_sign.add_argument("--claim-id", required=True)
    pqc_sign.add_argument("--purpose", choices=["artifact-integrity", "independent-reproduction"], default="independent-reproduction")
    pqc_sign.add_argument("--created-at-utc")
    pqc_sign.add_argument("--output", type=Path, required=True)
    pqc_sign.add_argument("--force", action="store_true")

    pqc_verify = sub.add_parser("pqc-verify", help="Verify one ML-DSA-65 CACE attestation")
    pqc_verify.add_argument("attestation", type=Path)
    pqc_verify.add_argument("--trusted-verifier-id")

    args = parser.parse_args(argv)
    try:
        if args.command == "keygen":
            private_pem, public_pem = generate_ed25519_keypair_pem()
            _write_bytes(args.private_key, private_pem, force=args.force, mode=0o600)
            _write_bytes(args.public_key, public_pem, force=args.force, mode=0o644)
            payload = {
                "cli_schema": 1,
                "command": "keygen",
                "proof_effect": "none",
                "verifier_key_id": public_key_id(public_pem),
                "private_key_path": str(args.private_key),
                "public_key_path": str(args.public_key),
                "note": "Keep the private key secret. Key possession does not establish mathematical truth.",
            }
            status = 0
        elif args.command == "pqc-keygen":
            from .core.pqc_attestation import _provider, public_key_id
            oqs = _provider()
            with oqs.Signature("ML-DSA-65") as keygen:
                public_key = keygen.generate_keypair()
                secret_key = keygen.export_secret_key()
            _write_bytes(args.private_key, secret_key, force=args.force, mode=0o600)
            _write_bytes(args.public_key, public_key, force=args.force, mode=0o644)
            payload = {
                "cli_schema": 1, "command": "pqc-keygen", "proof_effect": "none",
                "signature_algorithm": "ML-DSA-65",
                "verifier_key_id": public_key_id(public_key),
                "private_key_path": str(args.private_key),
                "public_key_path": str(args.public_key),
                "note": "Keep the private key outside Git and CI artifacts; key possession does not establish claim correctness.",
            }
            status = 0
        elif args.command == "sign":
            bundle = _load_bundle(args.bundle)
            private_pem = args.private_key.read_bytes()
            from cryptography.hazmat.primitives import serialization
            private_key = serialization.load_pem_private_key(private_pem, password=None)
            public_pem = private_key.public_key().public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
            statement = AttestationStatement(
                verifier_id=args.verifier_id,
                verifier_key_id=public_key_id(public_pem),
                claim_id=args.claim_id,
                bundle_sha256=bundle.bundle_sha256,
                created_at_utc=args.created_at_utc or _created_at(),
                purpose="independent-reproduction",
                bindings={
                    "qualified_commit": args.qualified_commit.lower(),
                    "proof_artifact_sha256": args.proof_artifact_sha256.lower(),
                },
            )
            attestation = sign_attestation(statement, private_pem)
            document = {
                "cli_schema": 1,
                "command": "sign",
                "proof_effect": "none",
                "attestation": attestation.payload(),
            }
            _write_text(args.output, _render(document), force=args.force)
            payload = {
                "cli_schema": 1,
                "command": "sign",
                "proof_effect": "none",
                "output": str(args.output),
                "verifier_key_id": statement.verifier_key_id,
                "statement_sha256": statement.statement_sha256,
                "bundle_sha256": bundle.bundle_sha256,
            }
            status = 0
        elif args.command == "pqc-sign":
            from .core.pqc_attestation import public_key_id, sign_ml_dsa65
            bundle = _load_bundle(args.bundle)
            artifact_bytes = {}
            artifact_root = args.artifact_root.resolve()
            for artifact in bundle.artifacts:
                relative = Path(artifact.path or "")
                if relative.is_absolute() or ".." in relative.parts or not relative.parts:
                    raise ValueError(f"unsafe or missing artifact path: {artifact.artifact_id}")
                target = (artifact_root / relative).resolve()
                if artifact_root not in target.parents:
                    raise ValueError(f"artifact escapes artifact root: {artifact.artifact_id}")
                artifact_bytes[artifact.artifact_id] = target.read_bytes()
            verify_bundle(bundle, artifact_bytes=artifact_bytes)
            secret_key = args.private_key.read_bytes()
            public_key = args.public_key.read_bytes()
            bindings = _read_json(args.bindings)
            if not isinstance(bindings, dict):
                raise ValueError("bindings file must contain a JSON object")
            statement = {
                "schema": "cace-attestation-statement-v2",
                "signature_algorithm": "ML-DSA-65",
                "proof_effect": "none",
                "verifier_id": args.verifier_id,
                "verifier_key_id": public_key_id(public_key),
                "claim_id": args.claim_id,
                "bundle_sha256": bundle.bundle_sha256,
                "created_at_utc": args.created_at_utc or _created_at(),
                "purpose": args.purpose,
                "bindings": bindings,
            }
            envelope = sign_ml_dsa65(statement, secret_key, public_key)
            document = {"cli_schema": 1, "command": "pqc-sign", "proof_effect": "none", "attestation": envelope}
            _write_text(args.output, _render(document), force=args.force)
            payload = {
                "cli_schema": 1, "command": "pqc-sign", "proof_effect": "none",
                "output": str(args.output), "verifier_key_id": statement["verifier_key_id"],
                "statement_sha256": envelope["statement_sha256"], "bundle_sha256": bundle.bundle_sha256,
            }
            status = 0
        elif args.command == "pqc-verify":
            from .core.pqc_attestation import verify_ml_dsa65
            document = _read_json(args.attestation)
            if isinstance(document, dict) and "attestation" in document:
                if document.get("proof_effect") != "none":
                    raise ValueError("attestation document proof_effect must be none")
                envelope = document["attestation"]
            else:
                envelope = document
            key_id = verify_ml_dsa65(envelope, trusted_verifier_id=args.trusted_verifier_id)
            payload = {
                "cli_schema": 1, "command": "pqc-verify", "proof_effect": "none",
                "valid": True, "signature_algorithm": "ML-DSA-65",
                "verifier_key_id": key_id, "claim_id": envelope["statement"]["claim_id"],
                "bundle_sha256": envelope["statement"]["bundle_sha256"],
                "statement_sha256": envelope["statement_sha256"],
                "note": "Signature validity authenticates provenance; it does not prove the claim.",
            }
            status = 0
        elif args.command == "verify":
            attestation = _load_attestation(args.attestation)
            key_id = verify_attestation(attestation)
            payload = {
                "cli_schema": 1,
                "command": "verify",
                "proof_effect": "none",
                "valid": True,
                "verifier_id": attestation.statement.verifier_id,
                "verifier_key_id": key_id,
                "claim_id": attestation.statement.claim_id,
                "bundle_sha256": attestation.statement.bundle_sha256,
                "statement_sha256": attestation.statement_sha256,
                "note": "Signature validity authenticates an attestation; it does not prove the claim.",
            }
            status = 0
        else:
            bundle = _load_bundle(args.bundle)
            attestations = [_load_attestation(path) for path in args.attestation]
            approved: dict[str, str] = {}
            for spec in args.approve_key:
                key_id, verifier_id = _key_value(spec, "approved key")
                if key_id in approved and approved[key_id] != verifier_id:
                    raise ValueError(f"approved key is bound to multiple verifier IDs: {key_id}")
                approved[key_id] = verifier_id
            result = evaluate_e5(
                args.claim_id,
                bundle.bundle_sha256,
                attestations,
                approved,
            )
            payload = {
                "cli_schema": 1,
                "command": "cross-verify",
                **result.to_dict(),
                "note": (
                    "E5 is independent cross-verification over an already-qualified claim; "
                    "it cannot create proof qualification."
                ),
            }
            status = 0 if result.eligible else 3

        sys.stdout.write(_render(payload))
        return status
    except Exception as exc:
        sys.stderr.write(
            json.dumps(
                {
                    "cli_schema": 1,
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                },
                sort_keys=True,
            )
            + "\n"
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
