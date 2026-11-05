from __future__ import annotations

import base64
from datetime import datetime, timezone
import gzip
import hashlib
import io
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile

import oqs

from cace_studio.core.evidence_ledger import EvidenceArtifact, EvidenceBundle, verify_bundle
from cace_studio.core.pqc_attestation import public_key_id, sign_ml_dsa65, verify_ml_dsa65

FIXTURE = Path(__file__).parent / "fixtures" / "titan-avrea-42087925099"
ZIP_SHA256 = "466c1d227bb13ae8ec1d8b51fd9d3722c76df2934fd1dd2e200b0b391f2b643d"
SOURCE_COMMIT = "0f3ca6ae38d4ac745855c49509bf6992694cb522"
PROVIDER_COMMIT = "5a1a854b0dc9f2141bdc771c555ee60c37950183"
VECTOR_COMMIT = "b121fee031dc65d32c96f4109a42a10dacbe2076"


def test_actual_avrea_bundle_ml_dsa65_receipt_roundtrip() -> None:
    packed = base64.b64decode((FIXTURE / "original-artifact.zip.gz.b64").read_text().strip(), validate=True)
    archive_bytes = gzip.decompress(packed)
    assert hashlib.sha256(archive_bytes).hexdigest() == ZIP_SHA256

    with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
        files = {name: archive.read(name) for name in archive.namelist()}
    assert len(files) == 4

    suite_counts = {"FIPS203": 0, "FIPS204": 0, "FIPS205": 0}
    junit = ET.fromstring(files["titan-acvp-junit.xml"])
    for case in junit.iter("testcase"):
        name = case.attrib.get("name", "")
        if case.find("skipped") is not None or case.find("failure") is not None or case.find("error") is not None:
            continue
        if name.startswith("test_acvp_vec_kem_") and "[ML-KEM-" in name:
            suite_counts["FIPS203"] += 1
        elif name.startswith("test_acvp_vec_ml_dsa_") and "[ML-DSA-" in name:
            suite_counts["FIPS204"] += 1
        elif name.startswith("test_acvp_vec_slh_dsa_") and "[SLH_DSA_PURE_" in name:
            suite_counts["FIPS205"] += 1
    assert suite_counts == {"FIPS203": 9, "FIPS204": 9, "FIPS205": 36}

    artifacts = []
    artifact_bytes = {}
    for name, role in [
        ("titan-acvp-test.log", "acvp-test-log"),
        ("titan-acvp-junit.xml", "acvp-junit-results"),
        ("titan-provider-provenance.txt", "upstream-provenance"),
        ("titan-pqc-acvp-evidence.json", "workflow-evidence-manifest"),
    ]:
        data = files[name]
        artifact = EvidenceArtifact.from_bytes(name, data, role=role, media_type="application/octet-stream", path=name)
        artifacts.append(artifact)
        artifact_bytes[artifact.artifact_id] = data

    bundle = EvidenceBundle(
        artifacts=tuple(artifacts),
        bindings={
            "source_repository": "Mannyspiro/expert-robot",
            "source_commit_sha": SOURCE_COMMIT,
            "workflow_run_id": 42087925099,
            "provider_commit": PROVIDER_COMMIT,
            "vector_source_commit": VECTOR_COMMIT,
            "verification_scope": "FIPS203=9/9, FIPS204=9/9, FIPS205=36/36; zero failures",
            "source_workflow_artifact_sha256": ZIP_SHA256,
            "proof_effect": "none",
            "promotion_authority": False,
        },
        notes=("Ephemeral ML-DSA-65 receipt test over actual Avrea evidence; no production key or qualification effect.",),
    )
    assert verify_bundle(bundle, artifact_bytes=artifact_bytes) == bundle.bundle_sha256

    with oqs.Signature("ML-DSA-65") as keygen:
        public_key = keygen.generate_keypair()
        secret_key = keygen.export_secret_key()
    statement = {
        "schema": "cace-attestation-statement-v2",
        "signature_algorithm": "ML-DSA-65",
        "proof_effect": "none",
        "verifier_id": "cace-titan-avrea-ephemeral-test",
        "verifier_key_id": public_key_id(public_key),
        "claim_id": "titan:avrea:42087925099",
        "bundle_sha256": bundle.bundle_sha256,
        "created_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "purpose": "independent-reproduction",
        "bindings": {
            "source_repository": "Mannyspiro/expert-robot",
            "source_commit_sha": SOURCE_COMMIT,
            "workflow_run_id": 42087925099,
            "provider_commit": PROVIDER_COMMIT,
            "vector_source_commit": VECTOR_COMMIT,
            "verification_scope": "actual Avrea ACVP bundle integrity plus ephemeral ML-DSA-65 roundtrip",
        },
    }
    envelope = sign_ml_dsa65(statement, secret_key, public_key)
    assert verify_ml_dsa65(envelope, trusted_verifier_id="cace-titan-avrea-ephemeral-test") == public_key_id(public_key)
    changed = dict(envelope)
    changed["statement"] = dict(envelope["statement"])
    changed["statement"]["bundle_sha256"] = "0" * 64
    try:
        verify_ml_dsa65(changed)
    except ValueError:
        pass
    else:
        raise AssertionError("tampered actual-bundle attestation was accepted")
