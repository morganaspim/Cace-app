from __future__ import annotations

import numpy as np
import pytest

from cace_studio.app import build_registry
from cace_studio.core.module import ExecutionContext, ValidationError
from cace_studio.core.science_objects import Atom, Bond, Molecule, ProteinSequence
from cace_studio.modules.molecular_materials import (
    MaterialCandidateSearchModule,
    ProteinCoarseFoldSearch,
    SafeHomeLabExperimentModule,
    coarse_protein_energy,
    parse_pdb_ca_structure,
    physics_canvas_object,
    safe_home_experiment,
    search_coarse_fold,
    search_material_candidates,
)


def _pdb_line(serial, residue, chain, index, x, y, z, bfactor):
    return (
        f"ATOM  {serial:5d}  CA  {residue:>3s} {chain}{index:4d}    "
        f"{x:8.3f}{y:8.3f}{z:8.3f}  1.00{bfactor:6.2f}           C"
    )


def test_atom_and_molecule_objects_are_typed_and_serializable():
    water = Molecule(
        atoms=(Atom("O"), Atom("H"), Atom("H")),
        bonds=(Bond(0, 1), Bond(0, 2)),
        name="water",
    )
    payload = water.to_dict()
    assert water.formula == "H2O"
    assert payload["atoms"][0]["atomic_number"] == 8
    assert payload["total_formal_charge"] == 0


def test_alphafold_style_pdb_import_preserves_attribution_metadata():
    pdb_text = "\n".join(
        (
            _pdb_line(1, "ALA", "A", 1, 0.0, 0.0, 0.0, 91.0),
            _pdb_line(2, "GLY", "A", 2, 3.8, 0.0, 0.0, 88.0),
        )
    )
    structure = parse_pdb_ca_structure(
        pdb_text,
        source="AlphaFold DB example",
        license_id="CC-BY-4.0",
        attribution="AlphaFold DB example attribution",
    )
    assert structure.sequence.sequence == "AG"
    assert structure.plddt == (91.0, 88.0)
    assert structure.provenance is not None
    assert structure.provenance.license_id == "CC-BY-4.0"
    assert structure.provenance.attribution == "AlphaFold DB example attribution"
    assert len(structure.provenance.content_sha256) == 64


def test_coarse_fold_search_is_deterministic_and_best_trace_is_monotone():
    sequence = "ACDEFGHIK"
    first_xyz, first_energy, first_trace = search_coarse_fold(
        sequence,
        seed=123,
        steps=80,
    )
    second_xyz, second_energy, second_trace = search_coarse_fold(
        sequence,
        seed=123,
        steps=80,
    )
    assert np.allclose(first_xyz, second_xyz)
    assert first_energy == pytest.approx(second_energy)
    assert np.allclose(first_trace, second_trace)
    assert np.all(np.diff(first_trace) <= 1e-12)
    assert coarse_protein_energy(sequence, first_xyz) == pytest.approx(first_energy)


def test_fold_module_never_emits_global_minimum_claim():
    module = ProteinCoarseFoldSearch()
    sequence = ProteinSequence("ACDEFGHIK")
    params = module.resolved_params({"steps": 40})
    module.validate({"sequence": sequence}, {"steps": 40})
    outputs = module.execute(
        {"sequence": sequence},
        params,
        ExecutionContext(run_id="test", seed=7),
    )
    assert outputs["global_minimum_claim"] is False
    assert any("no global-minimum claim" in item.lower() for item in outputs["structure"].limitations)
    records = module.verify(
        {"sequence": sequence},
        params,
        outputs,
        ExecutionContext(run_id="test", seed=7),
    )
    assert records
    assert all(record.passed for record in records)


def test_safe_home_lab_is_whitelist_only_and_fails_closed():
    plan = safe_home_experiment("salt_crystal_evaporation")
    assert plan["risk_level"] == "low"
    assert "unknown salts" in plan["prohibited_substitutions"]
    with pytest.raises(ValueError):
        safe_home_experiment("unknown_synthesis")

    module = SafeHomeLabExperimentModule()
    with pytest.raises(ValidationError):
        module.validate({}, {"experiment_id": "unknown_synthesis"})


def test_material_search_is_reproducible_reduced_and_has_no_synthesis_output():
    first = search_material_candidates(
        ("Al", "O", "Si", "Mg"),
        target="balanced",
        max_stoich=2,
        limit=12,
    )
    second = search_material_candidates(
        ("Al", "O", "Si", "Mg"),
        target="balanced",
        max_stoich=2,
        limit=12,
    )
    assert [item.formula for item in first] == [item.formula for item in second]
    assert [item.score for item in first] == pytest.approx([item.score for item in second])
    assert len({item.formula for item in first}) == len(first)
    assert all(item.to_dict()["synthesis_instructions"] is False for item in first)

    module = MaterialCandidateSearchModule()
    params = module.resolved_params({"elements_csv": "Al,O,Si,Mg", "limit": 5})
    outputs = module.execute({}, params, ExecutionContext(run_id="test", seed=0))
    assert len(outputs["candidates"]) == 5


def test_physics_catalog_separates_established_and_theoretical_objects():
    quark = physics_canvas_object("up_quark")
    string = physics_canvas_object("string_segment")
    assert quark.established is True
    assert "confined" in " ".join(quark.caveats).lower()
    assert string.established is False
    assert string.evidence_label == "theoretical-research-visualization"


def test_registry_exposes_new_science_canvas_modules():
    registry = build_registry()
    expected = {
        "chemistry.atom_object",
        "chemistry.molecule_json",
        "chemistry.safe_home_lab",
        "protein.sequence",
        "protein.alphafold_pdb_import",
        "protein.alphafold_api_import",
        "protein.coarse_fold_search",
        "materials.descriptor_search",
        "physics.canvas_object",
    }
    assert all(registry.contains(module_id) for module_id in expected)
