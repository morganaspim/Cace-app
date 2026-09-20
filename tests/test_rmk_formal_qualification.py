from __future__ import annotations

from pathlib import Path

from cace_studio.core.lean_theorem_metadata import discover_audited_theorems
from cace_studio.core.proof_contract import ProofContractRegistry


ROOT = Path(__file__).parents[1]
FORMAL = ROOT / "formal" / "cace_formal"
CLAIM_ID = "cace.rmk.runtime-formal-linkage-v1"
BRIDGES = (
    "CACEFormal.RuntimeRMKCoreBridge",
    "CACEFormal.RuntimeGroupExteriorBridge",
)


def _contract():
    contract = ProofContractRegistry.load_default().for_claim(CLAIM_ID)
    assert contract is not None
    return contract


def test_rmk_bridges_are_in_audited_root_and_not_quarantine() -> None:
    import json

    guardrails = json.loads((FORMAL / "proof_guardrails.json").read_text(encoding="utf-8"))
    root = (FORMAL / "CACEFormal.lean").read_text(encoding="utf-8")

    for module in BRIDGES:
        assert module in guardrails["allowed_root_imports"]
        assert module not in guardrails["quarantined_root_imports"]
        assert f"import {module}" in root


def test_rmk_axiom_audit_exactly_matches_proof_contract() -> None:
    contract = _contract()
    audit_path = FORMAL / "CACEFormal" / "RMKAxiomAudit.lean"
    audited = set(discover_audited_theorems(audit_path.read_text(encoding="utf-8")))

    assert audited == set(contract.endpoint_theorems)
    assert contract.build_target == "CACEFormal.RMKAxiomAudit"
    assert contract.allowed_axioms == ("Classical.choice", "Quot.sound", "propext")


def test_rmk_contract_binds_all_promoted_sources() -> None:
    contract = _contract()
    expected = {
        "CACEFormal/RuntimeRMKCoreBridge.lean",
        "CACEFormal/RuntimeGroupExteriorBridge.lean",
        "CACEFormal/RMKAxiomAudit.lean",
    }
    assert set(contract.audited_source_files) == expected
    for relative in contract.audited_source_files:
        assert (FORMAL / relative).is_file()


def test_rmk_contract_keeps_runtime_nonclaims_explicit() -> None:
    contract = _contract()
    joined = "\n".join(contract.nonclaims)
    assert "C++" in joined
    assert "RREF" in joined
    assert "CSR" in joined
    assert "polynomial" in joined
    assert "permutation-group" in joined
