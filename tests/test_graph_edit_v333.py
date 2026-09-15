from __future__ import annotations

from copy import deepcopy

import pytest

from cace_studio.core.graph import Edge, Experiment, Node
from cace_studio.core.graph_edit import (
    align_node_positions,
    copy_graph_fragment,
    paste_graph_fragment,
)


def _experiment() -> Experiment:
    return Experiment(
        name="edit",
        nodes=[
            Node("a", "module.a", {"nested": {"value": 1}}, (10.0, 20.0)),
            Node("b", "module.b", {"value": 2}, (60.0, 80.0)),
            Node("c", "module.c", {}, (120.0, 140.0)),
        ],
        edges=[
            Edge("a", "out", "b", "in"),
            Edge("b", "out", "c", "in"),
        ],
    )


def test_copy_fragment_keeps_only_internal_edges_and_relative_positions():
    exp = _experiment()
    fragment = copy_graph_fragment(exp, ["a", "b"])
    assert fragment.origin == (10.0, 20.0)
    assert fragment.source_ids == ("a", "b")
    assert [node.relative_position for node in fragment.nodes] == [(0.0, 0.0), (50.0, 60.0)]
    assert fragment.edges == (Edge("a", "out", "b", "in"),)


def test_paste_fragment_remaps_ids_offsets_positions_and_deepcopies_params():
    exp = _experiment()
    fragment = copy_graph_fragment(exp, ["a", "b"])
    ids = iter(["new-a", "new-b"])
    new_ids = paste_graph_fragment(
        exp,
        fragment,
        offset=(30.0, 40.0),
        id_factory=lambda: next(ids),
    )
    assert new_ids == ("new-a", "new-b")
    node_map = exp.node_map()
    assert node_map["new-a"].position == (40.0, 60.0)
    assert node_map["new-b"].position == (90.0, 120.0)
    assert Edge("new-a", "out", "new-b", "in") in exp.edges

    node_map["new-a"].params["nested"]["value"] = 999
    assert node_map["a"].params["nested"]["value"] == 1


def test_paste_id_collision_fails_before_mutating_experiment():
    exp = _experiment()
    before = deepcopy(exp)
    fragment = copy_graph_fragment(exp, ["a", "b"])
    ids = iter(["fresh", "a"])
    with pytest.raises(ValueError, match="duplicate node id"):
        paste_graph_fragment(exp, fragment, id_factory=lambda: next(ids))
    assert exp == before


def test_copy_rejects_unknown_or_empty_selection():
    exp = _experiment()
    with pytest.raises(ValueError, match="at least one"):
        copy_graph_fragment(exp, [])
    with pytest.raises(ValueError, match="unknown node ids"):
        copy_graph_fragment(exp, ["missing"])


def test_align_left_top_and_mean_rows_are_deterministic():
    exp = _experiment()
    assert align_node_positions(exp, ["a", "b"], axis="x", strategy="min") == 10.0
    assert exp.node_map()["b"].position == (10.0, 80.0)

    assert align_node_positions(exp, ["a", "b"], axis="y", strategy="min") == 20.0
    assert exp.node_map()["b"].position == (10.0, 20.0)

    exp.node_map()["a"].position = (0.0, 10.0)
    exp.node_map()["b"].position = (20.0, 30.0)
    assert align_node_positions(exp, ["a", "b"], axis="x", strategy="mean") == 10.0
    assert align_node_positions(exp, ["a", "b"], axis="y", strategy="mean") == 20.0
    assert exp.node_map()["a"].position == (10.0, 20.0)
    assert exp.node_map()["b"].position == (10.0, 20.0)
