from __future__ import annotations

import base64
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile

from cace_studio.core.evidence_ledger import EvidenceArtifact, EvidenceBundle


FIXTURE = Path(__file__).parent / "fixtures" / "titan-avrea-42090360334"
EXPECTED_ZIP_SHA256 = "0cd2040e9a426079bda9311937e55da9ae8b57d832908ff42f2e2c41c8d02eb6"
EXPECTED_SOURCE_COMMIT = "8e40cb034864f80e58aef7602c4cc4dd1e41ed57"
EXPECTED_PROVIDER_COMMIT = "5a1a854b0dc9f2141bdc771c555ee60c37950183"
EXPECTED_VECTOR_COMMIT = "b121fee031dc65d32c96f4109a42a10dacbe2076"


def test_cace_independently_verifies_actual_avrea_acvp_bundle() -> None:
    compressed = base64.b64decode(
        (FIXTURE / "original-artifact.zip.gz.b64").read_text(encoding="ascii").strip(),
        validate=True,
    )
    original_zip = gzip.decompress(compressed)
    assert hashlib.sha256(original_zip).hexdigest() == EXPECTED_ZIP_SHA256

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "artifacts"
        root.mkdir()
        with zipfile.ZipFile(__import__("io").BytesIO(original_zip)) as archive:
            names = set(archive.namelist())
            expected = {
                "titan-acvp-test.log", "titan-acvp-junit.xml",
                "titan-provider-provenance.txt", "titan-pqc-acvp-evidence.json",
            }
            assert names == expected
            for name in sorted(expected):
                (root / name).write_bytes(archive.read(name))

        provenance = (root / "titan-provider-provenance.txt").read_text()
        assert f"liboqs_commit={EXPECTED_PROVIDER_COMMIT}" in provenance
        assert f"acvp_server_commit={EXPECTED_VECTOR_COMMIT}" in provenance
        assert "runner=avrea-" in provenance

        evidence = json.loads((root / "titan-pqc-acvp-evidence.json").read_text())
        assert evidence["workflow"]["commit_sha"] == EXPECTED_SOURCE_COMMIT
        assert evidence["provider"]["commit"] == EXPECTED_PROVIDER_COMMIT
        assert evidence["vectors"]["commit"] == EXPECTED_VECTOR_COMMIT
        assert evidence["test_result"] == "pass"
        assert evidence["test_counts"] == {"tests": 54, "passed": 54, "skipped": 0, "failed": 0}
        assert evidence["junit_sha256"] == hashlib.sha256((root / "titan-acvp-junit.xml").read_bytes()).hexdigest()
        assert evidence["test_log_sha256"] == hashlib.sha256((root / "titan-acvp-test.log").read_bytes()).hexdigest()

        xml_root = ET.parse(root / "titan-acvp-junit.xml").getroot()
        suite_counts = {
            "FIPS203": {"passed": 0, "skipped": 0, "failed": 0},
            "FIPS204": {"passed": 0, "skipped": 0, "failed": 0},
            "FIPS205": {"passed": 0, "skipped": 0, "failed": 0},
        }
        for case in xml_root.iter("testcase"):
            name = case.attrib.get("name", "")
            suite = "FIPS203" if name.startswith("test_acvp_vec_kem_") and "[ML-KEM-" in name else (
                "FIPS204" if name.startswith("test_acvp_vec_ml_dsa_") and "[ML-DSA-" in name else (
                    "FIPS205" if name.startswith("test_acvp_vec_slh_dsa_") and "[SLH_DSA_PURE_" in name else None
                )
            )
            if suite is None:
                continue
            if case.find("skipped") is not None:
                suite_counts[suite]["skipped"] += 1
            elif case.find("failure") is not None or case.find("error") is not None:
                suite_counts[suite]["failed"] += 1
            else:
                suite_counts[suite]["passed"] += 1

        assert suite_counts["FIPS203"] == {"passed": 9, "skipped": 0, "failed": 0}
        assert suite_counts["FIPS204"] == {"passed": 9, "skipped": 0, "failed": 0}
        assert suite_counts["FIPS205"] == {"passed": 36, "skipped": 0, "failed": 0}

        artifacts = []
        for name, role in [
            ("titan-acvp-test.log", "acvp-test-log"),
            ("titan-acvp-junit.xml", "acvp-junit-results"),
            ("titan-provider-provenance.txt", "upstream-provenance"),
            ("titan-pqc-acvp-evidence.json", "workflow-evidence-manifest"),
        ]:
            data = (root / name).read_bytes()
            artifacts.append(EvidenceArtifact.from_bytes(
                name, data, role=role, media_type="application/octet-stream", path=name,
            ))

        bundle = EvidenceBundle(
            artifacts=tuple(artifacts),
            bindings={
                "source_repository": "Mannyspiro/expert-robot",
                "source_commit_sha": EXPECTED_SOURCE_COMMIT,
                "workflow_run_id": 42090360334,
                "provider_commit": EXPECTED_PROVIDER_COMMIT,
                "vector_source_commit": EXPECTED_VECTOR_COMMIT,
                "verification_scope": "NIST ACVP projection vectors: FIPS203=9/9, FIPS204=9/9, FIPS205=36/36; zero failures",
                "workflow_conclusion": "success",
                "runner_identity": "avrea-exe-01a1ad1a42ce7487a97f7485b68e7978",
                "original_workflow_artifact_sha256": EXPECTED_ZIP_SHA256,
                "test_counts": {"FIPS203_passed": 9, "FIPS204_passed": 9, "FIPS205_passed": 36, "failed": 0},
                "proof_effect": "none",
                "promotion_authority": False,
            },
            notes=("CACE independent verification of extracted bytes from the exact Avrea workflow artifact; no qualification effect.",),
        )
        bundle_path = Path(tmp) / "titan-bundle.json"
        bundle_path.write_text(json.dumps({
            "cli_schema": 1, "command": "titan-bundle", "proof_effect": "none",
            "bundle_sha256": bundle.bundle_sha256, "bundle": bundle.payload(),
        }, sort_keys=True), encoding="utf-8")
        result = subprocess.run(
            [sys.executable, "scripts/verify_titan_bundle.py", "--bundle", str(bundle_path),
             "--artifact-root", str(root)],
            capture_output=True, text=True, check=False,
        )
        assert result.returncode == 0, result.stderr
        verified = json.loads(result.stdout)
        assert verified["valid"] is True
        assert verified["artifact_count"] == 4
        assert verified["proof_effect"] == "none"
        assert verified["qualification_effect"] == "none"
