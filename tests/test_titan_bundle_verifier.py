from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from cace_studio.core.evidence_ledger import EvidenceArtifact, EvidenceBundle


def _make_bundle(tmp_path: Path) -> tuple[Path, Path]:
    artifact_root = tmp_path / "artifacts"
    artifact_root.mkdir()
    data = b'{"result":"verified-by-test-fixture"}\n'
    (artifact_root / "run-manifest.json").write_bytes(data)
    artifact = EvidenceArtifact.from_bytes(
        "titan-run-manifest",
        data,
        role="execution-manifest",
        media_type="application/json",
        path="run-manifest.json",
    )
    bundle = EvidenceBundle(
        artifacts=(artifact,),
        bindings={
            "source_repository": "Mannyspiro/expert-robot",
            "source_commit_sha": "a" * 40,
            "workflow_run_id": 123,
            "provider_commit": "b" * 40,
            "vector_source_commit": "c" * 40,
            "verification_scope": "bundle verifier test only",
        },
        notes=("test fixture; no qualification effect",),
    )
    bundle_file = tmp_path / "bundle.json"
    bundle_file.write_text(json.dumps({
        "cli_schema": 1,
        "command": "titan-bundle",
        "proof_effect": "none",
        "bundle_sha256": bundle.bundle_sha256,
        "bundle": bundle.payload(),
    }, sort_keys=True), encoding="utf-8")
    return bundle_file, artifact_root


def test_cace_recomputes_bundle_and_artifact_hashes(tmp_path: Path) -> None:
    bundle_file, artifact_root = _make_bundle(tmp_path)
    result = subprocess.run(
        [sys.executable, "scripts/verify_titan_bundle.py", "--bundle", str(bundle_file),
         "--artifact-root", str(artifact_root)],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["valid"] is True
    assert payload["proof_effect"] == "none"
    assert payload["qualification_effect"] == "none"


def test_cace_rejects_tampered_artifact_bytes(tmp_path: Path) -> None:
    bundle_file, artifact_root = _make_bundle(tmp_path)
    (artifact_root / "run-manifest.json").write_text("tampered", encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "scripts/verify_titan_bundle.py", "--bundle", str(bundle_file),
         "--artifact-root", str(artifact_root)],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 2
    assert "mismatch" in result.stderr.lower()
