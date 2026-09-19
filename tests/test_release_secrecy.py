from __future__ import annotations

import json
import zipfile
from pathlib import Path

from scripts.check_release_secrecy import scan


ROOT = Path(__file__).resolve().parents[1]
POLICY = json.loads(
    (ROOT / "security" / "release_secrecy_policy.json").read_text(encoding="utf-8")
)


def test_clean_release_directory_passes(tmp_path: Path) -> None:
    release = tmp_path / "release"
    release.mkdir()
    (release / "app.bin").write_bytes(b"public customer binary")
    (release / "manifest.json").write_text('{"version":1}', encoding="utf-8")

    report, code = scan(release, POLICY)

    assert code == 0
    assert report["status"] == "PASS"
    assert report["file_count"] == 2
    assert len(report["manifest_sha256"]) == 64


def test_formal_source_is_rejected(tmp_path: Path) -> None:
    release = tmp_path / "release"
    target = release / "formal" / "cace_formal"
    target.mkdir(parents=True)
    (target / "Secret.lean").write_text("theorem secret : True := by trivial\n", encoding="utf-8")

    report, code = scan(release, POLICY)

    assert code == 1
    assert any(i["kind"] == "forbidden-path" for i in report["issues"])


def test_source_map_is_rejected(tmp_path: Path) -> None:
    release = tmp_path / "release"
    release.mkdir()
    (release / "bundle.js.map").write_text("{}", encoding="utf-8")

    report, code = scan(release, POLICY)

    assert code == 1
    assert any(i["kind"] == "forbidden-suffix" for i in report["issues"])


def test_trade_secret_marker_is_rejected(tmp_path: Path) -> None:
    release = tmp_path / "release"
    release.mkdir()
    (release / "notes.txt").write_text("CACE_TRADE_SECRET", encoding="utf-8")

    report, code = scan(release, POLICY)

    assert code == 1
    assert any(i["kind"] == "forbidden-text-marker" for i in report["issues"])


def test_runner_path_marker_is_rejected_in_zip(tmp_path: Path) -> None:
    artifact = tmp_path / "client.zip"
    with zipfile.ZipFile(artifact, "w") as zf:
        zf.writestr("app/config.txt", "/opt/actions-runner/_work/Cace-app/Cace-app")

    report, code = scan(artifact, POLICY)

    assert code == 1
    assert any(i["kind"] == "forbidden-text-marker" for i in report["issues"])


def test_empty_release_fails_closed(tmp_path: Path) -> None:
    release = tmp_path / "release"
    release.mkdir()

    report, code = scan(release, POLICY)

    assert code == 1
    assert report["status"] == "FAIL"
    assert report["issues"][0]["kind"] == "empty-artifact"
