from __future__ import annotations

from copy import deepcopy
from types import SimpleNamespace

from cace_studio.ai.protein_play import (
    ProteinHeartbeatPlayEngine,
    adapt_protein_structure,
    discover_protein_outputs,
)


class _Sequence:
    def __init__(self, sequence):
        self.sequence = sequence


class _Provenance:
    source = "AlphaFold DB example"
    license_id = "CC-BY-4.0"
    attribution = "Example AlphaFold DB attribution"


class _Structure:
    def __init__(self):
        self.sequence = _Sequence("ACDE")
        self.ca_coordinates = (
            (0.0, 0.0, 0.0),
            (3.8, 0.0, 0.0),
            (7.6, 0.0, 0.0),
            (3.8, 4.0, 0.0),
        )
        self.plddt = (95.0, 80.0, 55.0, 70.0)
        self.chain_ids = ("A", "A", "A", "A")
        self.provenance = _Provenance()
        self.method = "pdb-ca-import"
        self.limitations = ("prediction/model only",)


def test_adapter_preserves_attribution_without_importing_model_classes():
    view = adapt_protein_structure(_Structure(), source_node_id="protein-node")
    assert view.sequence == "ACDE"
    assert view.license_id == "CC-BY-4.0"
    assert "AlphaFold DB" in view.source
    assert "attribution" in view.attribution.lower()


def test_discovery_finds_structure_output_and_ignores_unrelated_nodes():
    result = SimpleNamespace(
        outputs={
            "protein": {"structure": _Structure()},
            "number": {"value": 3.0},
        }
    )
    found = discover_protein_outputs(result)
    assert len(found) == 1
    assert found[0][0] == "protein"


def test_protein_play_is_deterministic_and_read_only():
    structure = _Structure()
    before = deepcopy(structure.ca_coordinates)
    view = adapt_protein_structure(structure, source_node_id="protein")
    left = ProteinHeartbeatPlayEngine(view, seed=3).step(focus_budget=2)
    right = ProteinHeartbeatPlayEngine(view, seed=3).step(focus_budget=2)
    assert left.focus_indices == right.focus_indices
    assert left.focus_reasons == right.focus_reasons
    assert structure.ca_coordinates == before


def test_residue_heartbeat_never_claims_verified_without_records():
    view = adapt_protein_structure(_Structure(), source_node_id="protein")
    step = ProteinHeartbeatPlayEngine(view).step(focus_budget=2)
    assert all(node.verification_summary == "not-run" for node in step.frame.nodes)
    assert all(node.state.value != "verified" for node in step.frame.nodes)


def test_protein_play_context_preserves_safety_and_license_boundary():
    view = adapt_protein_structure(_Structure(), source_node_id="protein")
    step = ProteinHeartbeatPlayEngine(view).step(focus_budget=2)
    assert "CC-BY-4.0" in step.context
    assert "Read-only" in step.context
    assert "clinical evidence" in step.context
    assert "Do not provide biological-agent redesign" in step.context
