from __future__ import annotations

import shutil
from pathlib import Path

from scripts.audit_cace_actions_policy import audit

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
ACTIVE = (
    "cace-collaboration-validation.yml",
    "cace-formal-v336-theorem-metadata.yml",
    "cace-python-regression.yml",
)


def _fixture(tmp_path: Path) -> Path:
    root = tmp_path / "workflows"
    root.mkdir()
    for name in ACTIVE:
        shutil.copy2(WORKFLOWS / name, root / name)
    return root


def _kinds(report: dict) -> set[str]:
    return {item["kind"] for item in report["violations"]}


def test_repository_actions_policy_is_clean() -> None:
    assert audit(WORKFLOWS)["violations"] == []


def test_regression_locked_branch_cannot_broaden(tmp_path: Path) -> None:
    root = _fixture(tmp_path)
    path = root / "cace-python-regression.yml"
    text = path.read_text().replace(
        "branches: [executor/cace-regression-locked]",
        "branches: [main]",
    )
    path.write_text(text)
    assert "locked-push-scope" in _kinds(audit(root))


def test_regression_locked_path_cannot_broaden(tmp_path: Path) -> None:
    root = _fixture(tmp_path)
    path = root / "cace-python-regression.yml"
    text = path.read_text().replace(
        "- '.github/workflows/cace-python-regression.yml'",
        "- '**'",
    )
    path.write_text(text)
    assert "locked-push-scope" in _kinds(audit(root))


def test_regression_cannot_gain_second_automatic_trigger(tmp_path: Path) -> None:
    root = _fixture(tmp_path)
    path = root / "cace-python-regression.yml"
    text = path.read_text().replace(
        "  workflow_dispatch:\n",
        "  workflow_dispatch:\n  pull_request:\n",
        1,
    )
    path.write_text(text)
    assert "automatic-trigger-set" in _kinds(audit(root))


def test_collaboration_trigger_must_cover_policy_test(tmp_path: Path) -> None:
    root = _fixture(tmp_path)
    path = root / "cace-collaboration-validation.yml"
    text = path.read_text().replace(
        "      - 'tests/test_actions_policy_audit.py'\n",
        "",
    )
    path.write_text(text)
    assert "collaboration-trigger-paths" in _kinds(audit(root))
