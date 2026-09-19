from __future__ import annotations

from dataclasses import dataclass

from cace_studio.ai.experiment_proposal import (
    PROPOSAL_STRATEGIES,
    materialize_experiment_proposal,
    propose_experiment_graph,
    propose_experiment_strategies,
)
from cace_studio.core.graph import Edge, Experiment, Node
from cace_studio.core.module import Module
from cace_studio.core.types import (
    ModuleMetadata,
    Maturity,
    PortSpec,
)


class Source(Module):
    metadata = ModuleMetadata(
        module_id="test.source",
        name="Source",
        version="1",
        category="test",
        description="source",
        maturity=Maturity.PROTOTYPE,
    )
    outputs = (PortSpec("out", "number", unit="m"),)

    def execute(self, inputs, params, ctx):
        return {"out": 1.0}


class Middle(Module):
    metadata = ModuleMetadata(
        module_id="test.middle",
        name="Middle",
        version="1",
        category="test",
        description="middle",
        maturity=Maturity.PROTOTYPE,
    )
    inputs = (PortSpec("x", "number", unit="m"),)
    outputs = (PortSpec("out", "number", unit="m"),)

    def execute(self, inputs, params, ctx):
        return {"out": inputs["x"]}


class Sink(Module):
    metadata = ModuleMetadata(
        module_id="test.sink",
        name="Sink",
        version="1",
        category="test",
        description="sink",
        maturity=Maturity.PROTOTYPE,
    )
    inputs = (PortSpec("x", "number", unit="m"),)

    def execute(self, inputs, params, ctx):
        return {}


class WrongUnit(Module):
    metadata = ModuleMetadata(
        module_id="test.wrong-unit",
        name="Wrong Unit",
        version="1",
        category="test",
        description="wrong unit",
        maturity=Maturity.PROTOTYPE,
    )
    inputs = (PortSpec("x", "number", unit="s"),)

    def execute(self, inputs, params, ctx):
        return {}


class RotorGeometry(Module):
    metadata = ModuleMetadata(
        module_id="test.rotor-geometry",
        name="Rotor Geometry",
        version="1",
        category="geometry",
        description="rotor geometry transform for creative pattern exploration",
        maturity=Maturity.PROTOTYPE,
    )
    inputs = (PortSpec("x", "number", unit="m"),)
    outputs = (PortSpec("out", "number", unit="m"),)

    def execute(self, inputs, params, ctx):
        return {"out": inputs["x"]}


class Unrelated(Module):
    metadata = ModuleMetadata(
        module_id="test.unrelated",
        name="Unrelated",
        version="1",
        category="other",
        description="completely unrelated thermal chemistry concept",
        maturity=Maturity.PROTOTYPE,
    )
    inputs = (PortSpec("x", "number", unit="s"),)

    def execute(self, inputs, params, ctx):
        return {}


class OptionalInput(Module):
    metadata = ModuleMetadata(
        module_id="test.optional",
        name="Optional",
        version="1",
        category="test",
        description="optional",
        maturity=Maturity.PROTOTYPE,
    )
    inputs = (PortSpec("x", "number", required=False, unit="m"),)

    def execute(self, inputs, params, ctx):
        return {}


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
    classes = (
        Source,
        Middle,
        Sink,
        WrongUnit,
        RotorGeometry,
        Unrelated,
        OptionalInput,
    )
    return FakeRegistry({cls.metadata.module_id: cls for cls in classes})


def test_proposal_builds_acyclic_compatible_pipeline():
    proposal = propose_experiment_graph(
        _registry(),
        ("test.source", "test.middle", "test.sink"),
        title="pipeline",
    )

    assert [node.proposal_id for node in proposal.nodes] == ["p1", "p2", "p3"]
    assert [node.module_id for node in proposal.nodes] == [
        "test.source",
        "test.middle",
        "test.sink",
    ]
    assert [(edge.source_node, edge.target_node) for edge in proposal.edges] == [
        ("p1", "p2"),
        ("p2", "p3"),
    ]
    assert all(
        int(edge.source_node[1:]) < int(edge.target_node[1:])
        for edge in proposal.edges
    )
    assert proposal.unresolved_required_inputs == ()
    assert proposal.is_execution_ready is True


def test_proposal_fails_closed_on_unit_mismatch():
    proposal = propose_experiment_graph(
        _registry(),
        ("test.source", "test.wrong-unit"),
    )
    assert proposal.edges == ()
    assert len(proposal.unresolved_required_inputs) == 1
    unresolved = proposal.unresolved_required_inputs[0]
    assert unresolved.module_id == "test.wrong-unit"
    assert unresolved.port_name == "x"
    assert unresolved.unit == "s"
    assert proposal.is_execution_ready is False


def test_optional_unconnected_input_is_not_reported_as_unresolved():
    proposal = propose_experiment_graph(
        _registry(),
        ("test.optional",),
    )
    assert proposal.unresolved_required_inputs == ()
    assert proposal.is_execution_ready is True


def test_unknown_modules_are_skipped_and_reported():
    proposal = propose_experiment_graph(
        _registry(),
        ("missing.module", "test.source"),
    )
    assert [node.module_id for node in proposal.nodes] == ["test.source"]
    assert proposal.skipped_modules == ("missing.module",)


def test_all_unknown_modules_produce_empty_non_mutating_proposal():
    requested = ["missing.one", "missing.two"]
    proposal = propose_experiment_graph(_registry(), requested)
    assert proposal.is_empty is True
    assert proposal.nodes == ()
    assert proposal.edges == ()
    assert proposal.skipped_modules == tuple(requested)
    assert requested == ["missing.one", "missing.two"]


def test_module_list_is_deduplicated_and_bounded():
    proposal = propose_experiment_graph(
        _registry(),
        (
            "test.source",
            "test.source",
            "test.middle",
            "test.sink",
            "test.optional",
        ),
        max_modules=3,
    )
    assert [node.module_id for node in proposal.nodes] == [
        "test.source",
        "test.middle",
        "test.sink",
    ]


def test_nearest_earlier_compatible_producer_is_preferred():
    proposal = propose_experiment_graph(
        _registry(),
        ("test.source", "test.middle", "test.sink"),
    )
    sink_edge = next(edge for edge in proposal.edges if edge.target_node == "p3")
    assert sink_edge.source_node == "p2"


def test_proposal_generation_does_not_need_or_mutate_experiment_state():
    registry = _registry()
    before = tuple(registry.classes_by_id)
    first = propose_experiment_graph(registry, ("test.source", "test.middle"))
    second = propose_experiment_graph(registry, ("test.source", "test.middle"))
    assert first == second
    assert tuple(registry.classes_by_id) == before


def test_materialization_copies_experiment_and_translates_edges():
    proposal = propose_experiment_graph(
        _registry(),
        ("test.source", "test.middle", "test.sink"),
        title="materialize",
        description="connect source to sink through middle",
    )
    original = Experiment(
        name="existing",
        nodes=[Node("existing", "test.source", {}, (10.0, 20.0))],
        edges=[],
    )
    ids = iter(("new_a", "new_b", "new_c"))

    updated, mapping = materialize_experiment_proposal(
        original,
        proposal,
        origin=(1000.0, 2000.0),
        id_factory=lambda: next(ids),
    )

    assert original.nodes == [Node("existing", "test.source", {}, (10.0, 20.0))]
    assert original.edges == []
    assert len(updated.nodes) == 4
    assert mapping == {"p1": "new_a", "p2": "new_b", "p3": "new_c"}
    assert updated.nodes[1].position == (1040.0, 2040.0)
    assert updated.edges == [
        Edge("new_a", "out", "new_b", "x"),
        Edge("new_b", "out", "new_c", "x"),
    ]
    assert proposal.description == "connect source to sink through middle"


def test_materialization_retries_colliding_node_ids():
    proposal = propose_experiment_graph(_registry(), ("test.source",))
    original = Experiment(nodes=[Node("taken", "test.source")])
    ids = iter(("taken", "fresh"))

    updated, mapping = materialize_experiment_proposal(
        original,
        proposal,
        id_factory=lambda: next(ids),
    )
    assert mapping["p1"] == "fresh"
    assert {node.id for node in updated.nodes} == {"taken", "fresh"}


def test_materialization_rejects_empty_proposal():
    proposal = propose_experiment_graph(_registry(), ("missing",))
    try:
        materialize_experiment_proposal(Experiment(), proposal)
    except ValueError as exc:
        assert "empty experiment proposal" in str(exc)
    else:
        raise AssertionError("empty proposal should fail")


def test_materialization_does_not_change_research_or_verification_metadata():
    proposal = propose_experiment_graph(_registry(), ("test.source",))
    original = Experiment(
        name="meta",
        metadata={"verification_note": "existing only", "research": {"idea": "x"}},
    )
    updated, _ = materialize_experiment_proposal(
        original,
        proposal,
        id_factory=lambda: "new_node",
    )
    assert original.metadata == {
        "verification_note": "existing only",
        "research": {"idea": "x"},
    }
    assert updated.metadata == original.metadata
    assert updated.metadata is not original.metadata


def test_three_strategy_set_is_complete_and_deterministic():
    registry = _registry()
    first = propose_experiment_strategies(
        registry,
        ("test.sink", "test.middle", "test.source"),
        title="Rotor geometry experiment",
        description="Explore rotor geometry with the pipeline.",
        idea_context="rotor geometry pattern",
    )
    second = propose_experiment_strategies(
        registry,
        ("test.sink", "test.middle", "test.source"),
        title="Rotor geometry experiment",
        description="Explore rotor geometry with the pipeline.",
        idea_context="rotor geometry pattern",
    )

    assert tuple(first) == PROPOSAL_STRATEGIES
    assert first == second
    assert {proposal.strategy for proposal in first.values()} == set(PROPOSAL_STRATEGIES)


def test_minimal_is_no_larger_than_balanced_and_keeps_useful_connection():
    proposals = propose_experiment_strategies(
        _registry(),
        ("test.source", "test.middle", "test.sink", "test.optional"),
        title="small pipeline",
    )
    minimal = proposals["minimal"]
    balanced = proposals["balanced"]

    assert len(minimal.nodes) <= len(balanced.nodes)
    assert len(minimal.nodes) <= 3
    assert minimal.edges or minimal.is_execution_ready
    assert all(
        int(edge.source_node[1:]) < int(edge.target_node[1:])
        for edge in minimal.edges
    )


def test_balanced_recovers_producer_first_order_from_scrambled_modules():
    balanced = propose_experiment_strategies(
        _registry(),
        ("test.sink", "test.middle", "test.source"),
        title="scrambled",
    )["balanced"]

    assert [node.module_id for node in balanced.nodes] == [
        "test.source",
        "test.middle",
        "test.sink",
    ]
    assert [(edge.source_node, edge.target_node) for edge in balanced.edges] == [
        ("p1", "p2"),
        ("p2", "p3"),
    ]
    assert balanced.is_execution_ready is True


def test_exploratory_adds_bounded_idea_relevant_connected_novelty():
    proposals = propose_experiment_strategies(
        _registry(),
        ("test.source", "test.middle", "test.sink"),
        title="Rotor geometry discovery",
        description="Try a rotor geometry transform as a new pattern.",
        idea_context="rotor geometry creative pattern",
    )
    balanced_ids = {node.module_id for node in proposals["balanced"].nodes}
    exploratory_ids = [node.module_id for node in proposals["exploratory"].nodes]
    extras = [module_id for module_id in exploratory_ids if module_id not in balanced_ids]

    assert "test.rotor-geometry" in extras
    assert "test.unrelated" not in extras
    assert len(extras) <= 2
    assert len(proposals["exploratory"].nodes) <= 8
    assert all(
        edge.source_node != edge.target_node
        for edge in proposals["exploratory"].edges
    )


def test_exploratory_does_not_bypass_type_or_unit_compatibility():
    exploratory = propose_experiment_strategies(
        _registry(),
        ("test.source", "test.wrong-unit"),
        title="Rotor geometry",
        idea_context="rotor geometry",
    )["exploratory"]

    # Any edge entering WrongUnit would require unit s and must not be created
    # from the meter-valued source or rotor geometry outputs.
    wrong_node = next(
        node.proposal_id
        for node in exploratory.nodes
        if node.module_id == "test.wrong-unit"
    )
    assert all(edge.target_node != wrong_node for edge in exploratory.edges)
    assert any(
        item.node_id == wrong_node and item.unit == "s"
        for item in exploratory.unresolved_required_inputs
    )


def test_strategy_rationales_are_explicit():
    proposals = propose_experiment_strategies(
        _registry(),
        ("test.source", "test.middle"),
        title="rationale",
        idea_context="rotor geometry",
    )
    assert proposals["minimal"].rationale.startswith("Minimal strategy:")
    assert proposals["balanced"].rationale.startswith("Balanced strategy:")
    assert proposals["exploratory"].rationale.startswith("Exploratory strategy:")


def test_minimal_recovers_compatible_pair_from_scrambled_order():
    minimal = propose_experiment_strategies(
        _registry(),
        ("test.sink", "test.middle", "test.source"),
        title="minimal scrambled",
    )["minimal"]

    assert len(minimal.nodes) <= 2
    assert minimal.edges
    assert minimal.is_execution_ready is True
    assert minimal.nodes[0].module_id == "test.source"


def test_all_strategies_preserve_unknown_associated_modules():
    proposals = propose_experiment_strategies(
        _registry(),
        ("missing.module", "test.source", "test.middle"),
        title="unknown module reporting",
        idea_context="rotor geometry",
    )

    for proposal in proposals.values():
        assert "missing.module" in proposal.skipped_modules


def test_selected_strategy_materialization_reflects_that_strategy_only():
    proposals = propose_experiment_strategies(
        _registry(),
        ("test.source", "test.middle", "test.sink"),
        title="Rotor geometry discovery",
        idea_context="rotor geometry",
    )
    minimal = proposals["minimal"]
    exploratory = proposals["exploratory"]

    minimal_graph, _ = materialize_experiment_proposal(
        Experiment(),
        minimal,
        id_factory=iter(("m1", "m2", "m3")).__next__,
    )
    exploratory_ids = iter(
        ("e1", "e2", "e3", "e4", "e5", "e6", "e7", "e8")
    )
    exploratory_graph, _ = materialize_experiment_proposal(
        Experiment(),
        exploratory,
        id_factory=exploratory_ids.__next__,
    )

    assert len(minimal_graph.nodes) == len(minimal.nodes)
    assert len(exploratory_graph.nodes) == len(exploratory.nodes)
    assert [node.module_id for node in minimal_graph.nodes] == [
        node.module_id for node in minimal.nodes
    ]
    assert [node.module_id for node in exploratory_graph.nodes] == [
        node.module_id for node in exploratory.nodes
    ]
