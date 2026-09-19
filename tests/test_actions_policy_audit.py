from __future__ import annotations

import re
import shutil
from pathlib import Path

from cace_studio.core.claim_registry import ClaimRegistry
from cace_studio.core.proof_ledger import ProofLedger
from scripts.audit_cace_actions_policy import audit

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
ACTIVE = (
    "cace-collaboration-validation.yml",
    "cace-formal-v336-theorem-metadata.yml",
    "cace-python-regression.yml",
    "cace-exact-pin-lean-preflight.yml",
    "cace-batch-exact-pin-lean-preflight.yml",
    "cace-lean-source-sanity.yml",
)


def _fixture(tmp_path: Path) -> Path:
    root = tmp_path / "workflows"
    root.mkdir()
    for name in ACTIVE:
        shutil.copy2(WORKFLOWS / name, root / name)
    return root


def _kinds(report: dict) -> set[str]:
    return {item["kind"] for item in report["violations"]}


def _pytest_paths(text: str) -> set[str]:
    return set(re.findall(r"tests/[A-Za-z0-9_./-]+\.py", text))


def _python_runtime_pin(text: str) -> tuple[str, str]:
    uv = re.search(r"UV_VERSION:\s*'([^']+)'", text)
    python = re.search(r"python install\s+([0-9]+(?:\.[0-9]+)+)", text)
    assert uv is not None
    assert python is not None
    return uv.group(1), python.group(1)


def test_repository_actions_policy_is_clean() -> None:
    assert audit(WORKFLOWS)["violations"] == []


def test_qualified_provenance_is_enrolled_consistently() -> None:
    registry = ClaimRegistry.load_default()
    ledger = ProofLedger.load_default()
    claim = registry.by_id("cace.v330.continuum-proof-strengthening")
    entry = ledger.for_claim("cace.v330.continuum-proof-strengthening")
    assert claim is not None and entry is not None
    assert claim.current_head_qualified is True
    assert entry.current_head_qualified is True
    assert claim.qualification_status == entry.status == "PASS"
    assert claim.attested_commit == entry.commit
    assert claim.attested_commit is not None and len(claim.attested_commit) == 40
    assert claim.proof_artifact_sha256 == entry.proof_artifact_sha256
    assert claim.proof_artifact_sha256 is not None and len(claim.proof_artifact_sha256) == 64
    assert entry.qualification_system == "github-actions"
    assert entry.qualification_run_id is not None and entry.qualification_run_id.isdigit()
    assert entry.workflow_run_id is not None and entry.workflow_run_id > 0
    assert entry.qualification_run_id == str(entry.workflow_run_id)


def test_collaboration_bug_sweep_uses_explicit_repository_import_root() -> None:
    text = (WORKFLOWS / "cace-collaboration-validation.yml").read_text(encoding="utf-8")
    safe = (
        'PYTHONPATH="$GITHUB_WORKSPACE" '
        '"$RUNNER_TEMP/cace-collaboration-tests/bin/python" scripts/check_bug_sweep.py'
    )
    assert safe in text


def test_collaboration_qualified_baseline_is_derived_from_canonical_provenance() -> None:
    text = (WORKFLOWS / "cace-collaboration-validation.yml").read_text(encoding="utf-8")
    assert "cace_studio/data/claim_registry.json" in text
    assert "cace_studio/data/proof_ledger.json" in text
    assert "claim registry/proof ledger qualified commit mismatch" in text
    assert not re.search(r"\bbaseline\s*=\s*[\"']?[0-9a-f]{40}\b", text)


def test_collaboration_gate_enrolls_both_qualification_verifiers() -> None:
    text = (WORKFLOWS / "cace-collaboration-validation.yml").read_text(encoding="utf-8")
    assert "tests/test_qualification_bundle_verifier_v338.py" in text
    assert "tests/test_qualification_source_binding_v339.py" in text
    run_block = text.split(
        "- name: Run collaboration plus canonical formal-preflight tests",
        1,
    )[1]
    assert "tests/test_qualification_bundle_verifier_v338.py" in run_block
    assert "tests/test_qualification_source_binding_v339.py" in run_block


def test_collaboration_covers_every_canonical_formal_preflight_test() -> None:
    formal = (WORKFLOWS / "cace-formal-v336-theorem-metadata.yml").read_text(encoding="utf-8")
    collaboration = (WORKFLOWS / "cace-collaboration-validation.yml").read_text(encoding="utf-8")
    formal_block = formal.split(
        "- name: Run truth architecture, proof-governance, attestation, and research tests",
        1,
    )[1].split("\n      - name:", 1)[0]
    collaboration_block = collaboration.split(
        "- name: Run collaboration plus canonical formal-preflight tests",
        1,
    )[1].split("\n      - name:", 1)[0]
    formal_tests = _pytest_paths(formal_block)
    collaboration_tests = _pytest_paths(collaboration_block)
    assert formal_tests
    assert formal_tests <= collaboration_tests, sorted(formal_tests - collaboration_tests)
    assert "tests/test_qualification_overlay_v337.py" in formal_tests


def test_collaboration_preflight_matches_canonical_python_runtime() -> None:
    formal = (WORKFLOWS / "cace-formal-v336-theorem-metadata.yml").read_text(encoding="utf-8")
    collaboration = (WORKFLOWS / "cace-collaboration-validation.yml").read_text(encoding="utf-8")
    assert _python_runtime_pin(collaboration) == _python_runtime_pin(formal)


def test_collaboration_trigger_is_lightweight_only() -> None:
    text = (WORKFLOWS / "cace-collaboration-validation.yml").read_text(encoding="utf-8")
    for path in (
        "collaboration/**",
        "quality/**",
        "security/**",
        "scripts/**",
        "ops/**",
        "tests/**",
        "pyproject.toml",
        ".github/workflows/cace-*.yml",
    ):
        assert f"- '{path}'" in text
    for heavy in ("formal/**", "cace_studio/**", "schema/**"):
        assert f"- '{heavy}'" not in text


def test_collaboration_workflow_contains_no_lean_execution() -> None:
    text = (WORKFLOWS / "cace-collaboration-validation.yml").read_text(encoding="utf-8")
    assert "Exact-pin targeted Lean compile" not in text
    assert "Exact-pin audited-root compile" not in text
    assert "lake build" not in text
    assert "lake env lean" not in text
    assert "elan toolchain" not in text


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


def test_collaboration_trigger_must_keep_scripts_surface(tmp_path: Path) -> None:
    root = _fixture(tmp_path)
    path = root / "cace-collaboration-validation.yml"
    text = path.read_text().replace("      - 'scripts/**'\n", "", 1)
    path.write_text(text)
    assert "collaboration-trigger-paths" in _kinds(audit(root))


def test_collaboration_trigger_must_keep_security_surface(tmp_path: Path) -> None:
    root = _fixture(tmp_path)
    path = root / "cace-collaboration-validation.yml"
    text = path.read_text().replace("      - 'security/**'\n", "", 1)
    path.write_text(text)
    assert "collaboration-trigger-paths" in _kinds(audit(root))


def test_collaboration_trigger_rejects_formal_surface(tmp_path: Path) -> None:
    root = _fixture(tmp_path)
    path = root / "cace-collaboration-validation.yml"
    text = path.read_text().replace(
        "      - 'scripts/**'\n",
        "      - 'scripts/**'\n      - 'formal/**'\n",
        1,
    )
    path.write_text(text)
    assert "collaboration-trigger-paths" in _kinds(audit(root))


def test_collaboration_trigger_rejects_cace_source_surface(tmp_path: Path) -> None:
    root = _fixture(tmp_path)
    path = root / "cace-collaboration-validation.yml"
    text = path.read_text().replace(
        "      - 'scripts/**'\n",
        "      - 'scripts/**'\n      - 'cace_studio/**'\n",
        1,
    )
    path.write_text(text)
    assert "collaboration-trigger-paths" in _kinds(audit(root))


def test_lean_source_sanity_trigger_cannot_broaden(tmp_path: Path) -> None:
    root = _fixture(tmp_path)
    path = root / "cace-lean-source-sanity.yml"
    text = path.read_text(encoding="utf-8").replace(
        "      - 'formal/**/*.lean'\n",
        "      - 'formal/**/*.lean'\n      - '**'\n",
        1,
    )
    path.write_text(text, encoding="utf-8")
    assert "lean-sanity-trigger-paths" in _kinds(audit(root))


def test_batched_exact_pin_is_manual_only_and_serialized() -> None:
    text = (WORKFLOWS / "cace-batch-exact-pin-lean-preflight.yml").read_text(
        encoding="utf-8"
    )
    assert "workflow_dispatch:" in text
    for automatic in (
        "pull_request:",
        "pull_request_target:",
        "schedule:",
        "workflow_run:",
        "repository_dispatch:",
    ):
        assert automatic not in text
    assert "group: cace-canonical-qualification-oci" in text
    assert "cancel-in-progress: false" in text
    assert "runs-on: [self-hosted, cace, oci, aarch64]" in text
    assert "cace_batch_proof_targets.py" in text
    assert "quarantined-standalone" in (
        ROOT / "scripts" / "cace_batch_proof_targets.py"
    ).read_text(encoding="utf-8")
    assert "qualification=false" in text
    assert "lake build CACEFormal" not in text


def test_batched_exact_pin_collects_all_target_failures() -> None:
    text = (WORKFLOWS / "cace-batch-exact-pin-lean-preflight.yml").read_text(
        encoding="utf-8"
    )
    assert "cace-batch-compile-status.tsv" in text
    assert "cace-batch-compile-failures.txt" in text
    assert "CACE_BATCH_PREFLIGHT_FAILURES" in text
    assert 'continue-on-error: true' in text
    assert 'while IFS= read -r module' in text


def test_lean_source_sanity_tracks_batched_preflight_surface() -> None:
    text = (WORKFLOWS / "cace-lean-source-sanity.yml").read_text(encoding="utf-8")
    assert ".github/workflows/cace-batch-exact-pin-lean-preflight.yml" in text
    assert "scripts/cace_batch_proof_targets.py" in text
    assert "tests/test_cace_batch_proof_targets.py" in text


def test_collaboration_serialization_exempts_only_source_sanity() -> None:
    text = (WORKFLOWS / "cace-collaboration-validation.yml").read_text(
        encoding="utf-8"
    )
    expected = (
        'run: python scripts/cace_actions_serialization_guard.py '
        '--current-run-id "${GITHUB_RUN_ID}" '
        '--ignore-workflow-name "CACE Lean Source Sanity"'
    )
    assert expected in text
    assert text.count("--ignore-workflow-name") == 1
