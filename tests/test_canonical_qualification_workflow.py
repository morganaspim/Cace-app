from pathlib import Path

from cace_studio.core.proof_contract import ProofContractRegistry


ROOT = Path(__file__).parents[1]
WORKFLOW = ROOT / ".github/workflows/cace-formal-v336-theorem-metadata.yml"
H1_BESSEL_RIESZ = (
    ROOT / "formal/cace_formal/CACEFormal/H1BesselRieszReduction.lean"
)
LEGACY_PROOF_WORKFLOWS = (
    ROOT / ".github/workflows/cace-formal-v330.yml",
    ROOT / ".github/workflows/cace-h1-reconstruction-v337.yml",
)


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
    assert "branches: [main, implement/cace-rigor-playground-v337]" in trigger_section
    assert "staging/" not in trigger_section
    assert "checks: write" in text
    assert "scripts/cace_github_live_check.py" in paths
    assert "tests/test_cace_github_ui_status.py" in paths
    assert "tests/test_canonical_qualification_workflow.py" in paths
    assert "tests/test_cace_github_ui_status.py" in text
    assert "tests/test_canonical_qualification_workflow.py" in text
    assert "github.repository == 'morganaspim/Cace-app'" in text
    assert "CACE_GITHUB_TOKEN: ${{ github.token }}" in text
    assert "runs-on: [self-hosted, cace, oci, aarch64]" in text


def test_legacy_proof_workflows_cannot_claim_self_hosted_runner_automatically():
    for workflow in LEGACY_PROOF_WORKFLOWS:
        text = workflow.read_text(encoding="utf-8")
        trigger_section = text.split("\npermissions:", 1)[0]
        assert "runs-on: [self-hosted" not in text, workflow
        assert "runs-on: self-hosted" not in text, workflow
        assert "\n  push:" not in trigger_section, workflow
        assert "\n  pull_request:" not in trigger_section, workflow
        assert "\n  workflow_dispatch:" in trigger_section, workflow


def test_h1_bessel_riesz_uses_semantic_regression_boundaries():
    """Guard the proof patterns introduced after canonical qualification flushed brittle rewrites.

    These checks intentionally target bug classes rather than theorem output: Sobolev-order
    arithmetic must be normalized explicitly, multiplier growth must be composed from the named
    symbol theorem, real/complex normalization must cross an explicit semantic boundary, and
    inverse Fourier additivity must use the Fourier API rather than generic `map_add` rewriting.
    """
    text = H1_BESSEL_RIESZ.read_text(encoding="utf-8")

    assert "convert huNegOne using 1 <;> norm_num" in text
    assert "convert hdu using 1 <;> norm_num" in text
    assert "simpa using huNegOne" not in text
    assert "simpa using hdu" not in text

    assert "simpa only [weakPartial, h1RieszSymbol]" in text
    assert "(h1RieszSymbol_hasTemperateGrowth i).mul" in text

    assert "have hreal :" in text
    assert "congrArg Complex.ofReal hreal" in text
    assert "Complex.ofReal_sum" in text

    assert "exact fourierInv_add _ _" in text
    assert "rw [map_add]" not in text
