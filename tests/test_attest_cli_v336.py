from __future__ import annotations

import json

from cace_studio.attest_cli import main
from cace_studio.core.evidence_ledger import EvidenceArtifact, EvidenceBundle


def _bundle_document(path):
    artifact = EvidenceArtifact.from_bytes(
        "proof",
        b"proof-bytes",
        role="proof",
    )
    bundle = EvidenceBundle(
        artifacts=(artifact,),
        bindings={"claim_id": "claim.test"},
    )
    path.write_text(
        json.dumps(
            {
                "cli_schema": 1,
                "command": "evidence-bundle",
                "proof_effect": "none",
                "bundle_sha256": bundle.bundle_sha256,
                "bundle": bundle.payload(),
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )


def test_attest_cli_keygen_sign_verify_roundtrip(tmp_path, capsys):
    private_key = tmp_path / "verifier.key"
    public_key = tmp_path / "verifier.pub"
    bundle = tmp_path / "bundle.json"
    attestation = tmp_path / "attestation.json"
    _bundle_document(bundle)

    assert main(
        [
            "keygen",
            "--private-key",
            str(private_key),
            "--public-key",
            str(public_key),
        ]
    ) == 0
    keygen_output = json.loads(capsys.readouterr().out)
    assert keygen_output["proof_effect"] == "none"
    assert keygen_output["verifier_key_id"].startswith("ed25519:")

    assert main(
        [
            "sign",
            "--bundle",
            str(bundle),
            "--private-key",
            str(private_key),
            "--verifier-id",
            "lab-a",
            "--claim-id",
            "claim.test",
            "--qualified-commit",
            "a" * 40,
            "--proof-artifact-sha256",
            "b" * 64,
            "--created-at-utc",
            "2026-09-15T01:00:00Z",
            "--output",
            str(attestation),
        ]
    ) == 0
    sign_output = json.loads(capsys.readouterr().out)
    assert sign_output["proof_effect"] == "none"

    assert main(["verify", str(attestation)]) == 0
    verify_output = json.loads(capsys.readouterr().out)
    assert verify_output["valid"] is True
    assert verify_output["verifier_id"] == "lab-a"
    assert verify_output["proof_effect"] == "none"


def test_attest_cli_refuses_key_overwrite(tmp_path, capsys):
    private_key = tmp_path / "verifier.key"
    public_key = tmp_path / "verifier.pub"
    args = [
        "keygen",
        "--private-key",
        str(private_key),
        "--public-key",
        str(public_key),
    ]
    assert main(args) == 0
    capsys.readouterr()
    assert main(args) == 2
    error = json.loads(capsys.readouterr().err)
    assert error["error_type"] == "FileExistsError"
