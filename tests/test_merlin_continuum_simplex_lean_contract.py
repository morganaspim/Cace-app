from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "formal" / "cace_formal" / "CACEFormal" / "ContinuumSimplexCore.lean"
GUARDRAILS = ROOT / "formal" / "cace_formal" / "proof_guardrails.json"
AGGREGATE = ROOT / "formal" / "cace_formal" / "CACEFormal.lean"


def test_continuum_simplex_core_is_explicitly_quarantined() -> None:
    config = json.loads(GUARDRAILS.read_text(encoding="utf-8"))
    assert "CACEFormal.ContinuumSimplexCore" in config["quarantined_root_imports"]
    assert "CACEFormal.ContinuumSimplexCore" not in config["allowed_root_imports"]
    assert "import CACEFormal.ContinuumSimplexCore" not in AGGREGATE.read_text(
        encoding="utf-8"
    )


def test_continuum_simplex_core_contains_required_definitions_and_no_holes() -> None:
    source = MODULE.read_text(encoding="utf-8")
    required = (
        "abbrev PairState := ℝ × ℝ",
        "structure PairedContinuumTriangle",
        "def EndpointGluing",
        "map_preserves_endpoint_gluing",
        "map_preserves_continuity",
        "theorem comp_assoc",
        "theorem id_comp",
        "theorem comp_id",
        "def triangleLoop",
        "theorem pair_channels_reconstruct",
    )
    for declaration in required:
        assert declaration in source, declaration

    lowered = source.lower()
    assert "sorry" not in lowered
    assert "admit" not in lowered
    assert "axiom " not in lowered
