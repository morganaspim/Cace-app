from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts" / "cace_proof_guardrails.py"


def _guardrails():
    spec = importlib.util.spec_from_file_location("cace_proof_guardrails", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_current_audited_root_matches_guardrail_policy():
    guard = _guardrails()
    config = guard.load_config()
    guard.validate(config)


def test_promoted_hdiv_modules_leave_quarantine_and_enter_audited_root():
    guard = _guardrails()
    config = guard.load_config()
    root = ROOT / config["audited_root"]
    imports = set(guard.parse_imports(root))
    quarantined = set(config["quarantined_root_imports"])
    promoted = {
        "CACEFormal.PositiveLaplacianAnnihilator",
        "CACEFormal.HDivGraphAnnihilator",
        "CACEFormal.OrthogonalClosure",
        "CACEFormal.HDivDensityReduction",
    }
    assert imports.isdisjoint(quarantined)
    assert promoted.isdisjoint(quarantined)
    assert promoted <= imports


def test_root_closure_contains_new_graded_geometry_and_promoted_hdiv_modules():
    guard = _guardrails()
    config = guard.load_config()
    module_root = ROOT / config["module_root"]
    root = ROOT / config["audited_root"]
    graph = guard.cace_module_graph(module_root)
    closure = guard.root_closure(guard.parse_imports(root), graph)

    assert "CACEFormal.AffineGeometry" in closure
    assert "CACEFormal.ExteriorPowerTransport" in closure
    assert "CACEFormal.DualBladePiola" in closure
    assert "CACEFormal.AffineP1RT0Transport" in closure
    assert "CACEFormal.AffineAssemblyTransport" in closure
    assert "CACEFormal.MeshElementGeometry" in closure
    assert "CACEFormal.PhysicalP1RT0Element" in closure
    assert "CACEFormal.ExecutableRationalGeometry" in closure
    assert "CACEFormal.RuntimeApproximationContract" in closure
    assert "CACEFormal.PositiveLaplacianAnnihilator" in closure
    assert "CACEFormal.HDivGraphAnnihilator" in closure
    assert "CACEFormal.OrthogonalClosure" in closure
    assert "CACEFormal.HDivDensityReduction" in closure
    assert closure.isdisjoint(set(config["quarantined_root_imports"]))


def test_missing_recursive_internal_module_is_rejected_by_graph_check():
    guard = _guardrails()
    graph = {
        "CACEFormal.A": ("CACEFormal.Missing",),
    }
    closure = guard.root_closure(("CACEFormal.A",), graph)
    assert guard.missing_internal_modules(closure, graph) == ["CACEFormal.Missing"]


def test_dependency_first_order_puts_dependencies_before_dependents():
    guard = _guardrails()
    graph = {
        "CACEFormal.A": (),
        "CACEFormal.B": ("CACEFormal.A",),
        "CACEFormal.C": ("CACEFormal.B",),
    }
    order = guard.dependency_first_order(
        {"CACEFormal.A", "CACEFormal.B", "CACEFormal.C"},
        graph,
    )
    assert order.index("CACEFormal.A") < order.index("CACEFormal.B")
    assert order.index("CACEFormal.B") < order.index("CACEFormal.C")


def test_plan_hash_is_deterministic_and_content_addressed():
    guard = _guardrails()
    config = guard.load_config()
    args = SimpleNamespace(
        toolchain="leanprover/lean4:v4.32.1",
        mathlib_commit="520045ab14e26149ee970e2e617ca04b09bde5d6",
        target="CACEFormal/P1RT0Element.lean",
        compile_root="true",
        impacted_file=None,
    )
    first = guard.proof_plan(config, args)
    second = guard.proof_plan(config, args)
    assert first == second
    assert len(first["plan_sha256"]) == 64
    assert first["guardrail_config_sha256"]
    assert len(first["guardrail_sources"]) >= 6
    assert any(
        record["path"] == ".github/workflows/cace-exact-pin-lean-preflight.yml"
        for record in first["guardrail_sources"]
    )
    assert any(
        record.get("module") == "CACEFormal.ExteriorPowerTransport"
        for record in first["root_sources"]
    )


def test_canary_is_configured_but_not_promoted_into_audited_root():
    guard = _guardrails()
    config = guard.load_config()
    root = ROOT / config["audited_root"]
    imports = set(guard.parse_imports(root))
    assert config["canary_module"] == "CACEFormal.GuardrailCanaries"
    assert config["canary_module"] not in imports
    assert guard.module_to_path(
        ROOT / config["module_root"],
        config["canary_module"],
    ).is_file()


def test_validate_can_run_silently_for_machine_outputs(capsys):
    guard = _guardrails()
    config = guard.load_config()
    guard.validate(config, emit=False)
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


def test_proof_plan_payload_is_json_serializable_without_status_prefix():
    guard = _guardrails()
    config = guard.load_config()
    args = SimpleNamespace(
        toolchain="leanprover/lean4:v4.32.1",
        mathlib_commit="520045ab14e26149ee970e2e617ca04b09bde5d6",
        target="CACEFormal/P1RT0Element.lean",
        compile_root="true",
        impacted_file=None,
    )
    import json
    encoded = json.dumps(guard.proof_plan(config, args), sort_keys=True)
    decoded = json.loads(encoded)
    assert decoded["plan_sha256"]


def test_no_reserved_by_identifier_in_rcases_patterns():
    import re
    paths = (
        ROOT / "formal" / "cace_formal" / "CACEFormal" / "ExteriorPowerTransport.lean",
        ROOT / "formal" / "cace_formal" / "CACEFormal" / "AffineP1RT0Transport.lean",
        ROOT / "formal" / "cace_formal" / "CACEFormal" / "DualBladePiola.lean",
    )
    for path in paths:
        text = path.read_text(encoding="utf-8")
        bad = re.findall(r"rcases[^\n]*with\s+⟨[^\n⟩]*\bby\b[^\n⟩]*⟩", text)
        assert bad == [], f"{path.name}: {bad}"



def test_exact_pin_workflow_supports_quarantined_standalone_without_root_promotion():
    workflow = (
        ROOT / ".github" / "workflows" / "cace-exact-pin-lean-preflight.yml"
    ).read_text(encoding="utf-8")
    assert 'COMPILE_ROOT: ${{ inputs.compile_root }}' in workflow
    assert 'test "$COMPILE_ROOT" = "false"' in workflow
    assert "quarantined_root_imports" in workflow
    assert 'target_class="quarantined-standalone"' in workflow
    assert "Requested non-root module is not explicitly quarantined" in workflow
    assert "standalone quarantine compilation requires compile_root=false" in workflow


def test_exact_pin_workflow_collects_compile_failure_frontier():
    workflow = (
        ROOT / ".github" / "workflows" / "cace-exact-pin-lean-preflight.yml"
    ).read_text(encoding="utf-8")
    canonical = (
        ROOT / "ci" / "cace-exact-pin-lean-preflight.canonical.yml"
    ).read_text(encoding="utf-8")
    assert workflow == canonical
    assert workflow.count("continue-on-error: true") == 5
    assert "Aggregate diagnostic sweep failures" in workflow
    assert "CACE_DIAGNOSTIC_SWEEP_FAILURES" in workflow


def test_real_division_proof_defs_are_explicitly_noncomputable():
    checks = {
        ROOT / "formal" / "cace_formal" / "CACEFormal" / "Piola.lean": (
            "noncomputable def piolaVector",
        ),
        ROOT / "formal" / "cace_formal" / "CACEFormal" / "DualBladePiola.lean": (
            "noncomputable def piolaSequence",
        ),
        ROOT / "formal" / "cace_formal" / "CACEFormal" / "AffineP1RT0Transport.lean": (
            "noncomputable def piolaRT0",
            "noncomputable def pullP1",
            "noncomputable def transportRT0SourceToTarget",
            "noncomputable def transportP1SourceToTarget",
        ),
        ROOT / "formal" / "cace_formal" / "CACEFormal" / "ReferenceSimplexNormalization.lean": (
            "noncomputable def inverseEdgeLinear",
            "noncomputable def normalizer",
            "noncomputable def certifiedNondegenerate",
            "noncomputable def certifiedPositive",
        ),
        ROOT / "formal" / "cace_formal" / "CACEFormal" / "PhysicalP1RT0Element.lean": (
            "noncomputable def cellPairing",
            "noncomputable def cellDivergence",
        ),
    }
    for path, required in checks.items():
        text = path.read_text(encoding="utf-8")
        for declaration in required:
            assert declaration in text, f"{path.name} missing {declaration}"



def test_rational_recenter_to_real_normalizes_point_casts():
    path = (
        ROOT
        / "formal"
        / "cace_formal"
        / "CACEFormal"
        / "ExecutableRationalGeometry.lean"
    )
    text = path.read_text(encoding="utf-8")
    start = text.find("theorem recenterMap_toReal")
    end = text.find("@[simp] theorem inverseEdgeLinear_toReal")
    assert start >= 0 and end > start
    body = text[start:end]
    assert "Point.toReal" in body
