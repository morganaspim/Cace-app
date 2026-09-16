from pathlib import Path

from cace_studio.core.proof_contract import ProofContractRegistry


ROOT = Path(__file__).parents[1]
WORKFLOW = ROOT / ".github/workflows/cace-formal-v336-theorem-metadata.yml"


def _workflow_text() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def _push_paths_block(text: str) -> str:
    start = text.index("    paths:\n")
    end = text.index("\n\npermissions:", start)
    return text[start:end]


def test_canonical_workflow_push_paths_cover_proof_contract_audited_sources():
    text = _workflow_text()
    paths = _push_paths_block(text)
    contract = ProofContractRegistry.load_default().for_claim(
        "cace.v330.continuum-proof-strengthening"
    )
    assert contract is not None

    expected = [f"formal/cace_formal/{relative}" for relative in contract.audited_source_files]
    missing = [path for path in expected if f"'{path}'" not in paths]
    assert not missing, f"canonical qualification trigger misses audited sources: {missing}"


def test_canonical_workflow_wires_observability_and_authorized_dispatch_guards():
    text = _workflow_text()
    paths = _push_paths_block(text)
    trigger_section = text.split("\npermissions:", 1)[0]

    assert "\n  pull_request:" not in trigger_section
    assert "checks: write" in text
    assert "scripts/cace_github_live_check.py" in paths
    assert "tests/test_cace_github_ui_status.py" in paths
    assert "tests/test_canonical_qualification_workflow.py" in paths
    assert "tests/test_cace_github_ui_status.py" in text
    assert "tests/test_canonical_qualification_workflow.py" in text
    assert "github.repository == 'morganaspim/Cace-app'" in text
    assert "CACE_GITHUB_TOKEN: ${{ github.token }}" in text
    assert "runs-on: [self-hosted, cace, oci, aarch64]" in text
