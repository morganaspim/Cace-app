from __future__ import annotations

from dataclasses import dataclass

from cace_studio.ai.experiment_proposal import propose_experiment_graph
from cace_studio.ai.strategy_compare import compare_proposal_strategies
from cace_studio.core.module import ExecutionContext, Module
from cace_studio.core.types import EvidenceKind, ModuleMetadata, Maturity, PortSpec
from cace_studio.core.verification import VerificationRecord, VerificationState


class SeedSource(Module):
    metadata = ModuleMetadata(
        module_id="cmp.seed",
        name="Seed Source",
        version="1",
        category="compare",
        description="returns the shared execution seed",
        maturity=Maturity.PROTOTYPE,
    )
    outputs = (PortSpec("value", "number", unit="1"),)

    def execute(self, inputs, params, ctx: ExecutionContext):
        return {"value": float(ctx.seed)}

    def verify(self, inputs, params, outputs, ctx):
        return [
            VerificationRecord(
                verifier="seed-check",
                kind=EvidenceKind.NUMERICAL,
                claim="output equals shared seed",
                state=(
                    VerificationState.PASS
                    if outputs["value"] == float(ctx.seed)
                    else VerificationState.FAIL
                ),
                method="direct equality",
            )
        ]


class PassThrough(Module):
    metadata = ModuleMetadata(
        module_id="cmp.pass",
        name="Pass Through",
        version="1",
        category="compare",
        description="passes a dimensionless number",
        maturity=Maturity.PROTOTYPE,
    )
    inputs = (PortSpec("x", "number", unit="1"),)
    outputs = (PortSpec("y", "number", unit="1"),)

    def execute(self, inputs, params, ctx):
        return {"y": float(inputs["x"])}


class Doubler(Module):
    metadata = ModuleMetadata(
        module_id="cmp.double",
        name="Doubler",
        version="1",
        category="compare",
        description="doubles a dimensionless number",
        maturity=Maturity.PROTOTYPE,
    )
    inputs = (PortSpec("x", "number", unit="1"),)
    outputs = (PortSpec("y", "number", unit="1"),)

    def execute(self, inputs, params, ctx):
        return {"y": 2.0 * float(inputs["x"])}


class ExternalInput(Module):
    metadata = ModuleMetadata(
        module_id="cmp.external",
        name="External Input Consumer",
        version="1",
        category="compare",
        description="requires an explicit dimensionless input",
        maturity=Maturity.PROTOTYPE,
    )
    inputs = (PortSpec("x", "number", unit="1"),)
    outputs = (PortSpec("y", "number", unit="1"),)

    def execute(self, inputs, params, ctx):
        return {"y": float(inputs["x"]) + float(ctx.seed)}


class WrongUnit(Module):
    metadata = ModuleMetadata(
        module_id="cmp.wrong",
        name="Wrong Unit",
        version="1",
        category="compare",
        description="requires seconds instead of dimensionless input",
        maturity=Maturity.PROTOTYPE,
    )
    inputs = (PortSpec("x", "number", unit="s"),)
    outputs = (PortSpec("y", "number", unit="s"),)

    def execute(self, inputs, params, ctx):
        return {"y": float(inputs["x"])}


@dataclass
class FakeRegistry:
    classes_by_id: dict[str, type[Module]]

    def contains(self, module_id: str) -> bool:
        return module_id in self.classes_by_id

    def create(self, module_id: str) -> Module:
        return self.classes_by_id[module_id]()

    def classes(self):
        return list(self.classes_by_id.values())


def _registry() -> FakeRegistry:
    classes = (SeedSource, PassThrough, Doubler, ExternalInput, WrongUnit)
    return FakeRegistry({cls.metadata.module_id: cls for cls in classes})


def _ready_proposals():
    registry = _registry()
    return {
        "minimal": propose_experiment_graph(
            registry,
            ("cmp.seed",),
            strategy="minimal",
        ),
        "balanced": propose_experiment_graph(
            registry,
            ("cmp.seed", "cmp.pass"),
            strategy="balanced",
        ),
        "exploratory": propose_experiment_graph(
            registry,
            ("cmp.seed", "cmp.pass", "cmp.double"),
            strategy="exploratory",
        ),
    }


def test_comparison_runs_ready_strategies_with_same_seed():
    comparison = compare_proposal_strategies(
        _registry(),
        _ready_proposals(),
        seed=37,
        gpu_enabled=False,
    )
    by = comparison.by_strategy()

    assert comparison.seed == 37
    assert set(by) == {"minimal", "balanced", "exploratory"}
    assert all(summary.run_attempted for summary in by.values())
    assert all(summary.completed for summary in by.values())
    assert all(summary.seed == 37 for summary in by.values())

    for summary in by.values():
        seed_output = next(
            output
            for output in summary.output_summaries
            if output.module_id == "cmp.seed"
        )
        assert "37" in seed_output.summary


def test_comparison_preserves_verifier_counts_without_ranking_winner():
    comparison = compare_proposal_strategies(
        _registry(),
        _ready_proposals(),
        seed=2,
    )
    for summary in comparison.summaries:
        assert summary.verifier_pass == 1
        assert summary.verifier_fail == 0
        assert summary.verifier_not_run == 0
        assert summary.verifier_record_count == 1
        assert summary.all_verifiers_passed is True

    assert not hasattr(comparison, "winner")
    assert not hasattr(comparison, "best_strategy")


def test_comparison_reports_structural_novelty_descriptively():
    comparison = compare_proposal_strategies(
        _registry(),
        _ready_proposals(),
        seed=0,
    )
    by = comparison.by_strategy()

    assert comparison.common_modules == ("cmp.seed",)
    assert by["minimal"].novel_modules == ()
    assert by["minimal"].novelty_fraction == 0.0
    assert by["balanced"].novel_modules == ("cmp.pass",)
    assert "cmp.double" in by["exploratory"].novel_modules
    assert by["exploratory"].novelty_fraction > by["balanced"].novelty_fraction


def test_partial_proposal_is_not_run_without_required_input():
    registry = _registry()
    proposals = {
        "minimal": propose_experiment_graph(
            registry,
            ("cmp.external",),
            strategy="minimal",
        )
    }

    comparison = compare_proposal_strategies(registry, proposals, seed=5)
    summary = comparison.summaries[0]

    assert summary.runnable is False
    assert summary.run_attempted is False
    assert summary.completed is False
    assert summary.unresolved_required_inputs == 1
    assert summary.runtime_seconds is None
    assert summary.error == "unresolved required inputs"


def test_explicit_input_can_make_partial_proposal_runnable():
    registry = _registry()
    proposals = {
        "minimal": propose_experiment_graph(
            registry,
            ("cmp.external",),
            strategy="minimal",
        )
    }

    comparison = compare_proposal_strategies(
        registry,
        proposals,
        seed=5,
        external_inputs={
            "minimal": {
                "p1": {"x": 10.0},
            }
        },
    )
    summary = comparison.summaries[0]

    assert summary.runnable is True
    assert summary.completed is True
    assert summary.unresolved_required_inputs == 0
    assert summary.output_summaries[0].module_id == "cmp.external"
    assert "15" in summary.output_summaries[0].summary


def test_wrong_unit_connection_stays_not_runnable_without_explicit_input():
    registry = _registry()
    proposal = propose_experiment_graph(
        registry,
        ("cmp.seed", "cmp.wrong"),
        strategy="balanced",
    )
    assert len(proposal.unresolved_required_inputs) == 1

    comparison = compare_proposal_strategies(
        registry,
        {"balanced": proposal},
        seed=1,
    )
    summary = comparison.summaries[0]
    assert summary.runnable is False
    assert summary.run_attempted is False


def test_unknown_external_input_proposal_node_fails_explicitly():
    registry = _registry()
    proposal = propose_experiment_graph(
        registry,
        ("cmp.external",),
        strategy="minimal",
    )
    try:
        compare_proposal_strategies(
            registry,
            {"minimal": proposal},
            external_inputs={
                "minimal": {
                    "p1": {"x": 1.0},
                    "missing": {"x": 2.0},
                }
            },
        )
    except ValueError as exc:
        assert "unknown proposal node" in str(exc)
    else:
        raise AssertionError("unknown proposal-node input should fail")


def test_output_hashes_are_populated_for_completed_runs():
    comparison = compare_proposal_strategies(
        _registry(),
        _ready_proposals(),
        seed=9,
    )
    for summary in comparison.summaries:
        assert summary.output_summaries
        assert all(len(output.output_hash) == 64 for output in summary.output_summaries)


def test_runtime_is_descriptive_positive_wall_clock_sample():
    comparison = compare_proposal_strategies(
        _registry(),
        _ready_proposals(),
        seed=0,
    )
    for summary in comparison.summaries:
        assert summary.runtime_seconds is not None
        assert summary.runtime_seconds >= 0.0


def test_comparison_does_not_modify_proposals():
    proposals = _ready_proposals()
    before = repr(proposals)
    compare_proposal_strategies(_registry(), proposals, seed=11)
    assert repr(proposals) == before
