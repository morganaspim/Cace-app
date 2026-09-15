import json

import pytest

from cace_studio.core.graph import Edge, Experiment, ExperimentGroup, Node
from cace_studio.core.graph_groups import (
    create_group,
    group_node_ids,
    node_group_map,
    remove_group,
    remove_nodes_from_groups,
)
from cace_studio.core.reproducibility import experiment_fingerprint
from cace_studio.core.serialization import CURRENT_SCHEMA, load_experiment, save_experiment


def experiment():
    return Experiment(
        name="groups",
        nodes=[
            Node("a", "example.a", {}, (0.0, 0.0)),
            Node("b", "example.b", {}, (100.0, 0.0)),
            Node("c", "example.c", {}, (200.0, 0.0)),
        ],
        edges=[Edge("a", "out", "b", "in")],
        metadata={"note": "workspace"},
    )


def test_create_group_and_single_membership_policy():
    exp = experiment()
    group = create_group(exp, ["b", "a"], name=" upstream ", group_id="g1")
    assert group == ExperimentGroup("g1", "upstream", ("a", "b"))
    assert node_group_map(exp) == {"a": "g1", "b": "g1"}
    assert group_node_ids(exp, "g1") == ("a", "b")

    with pytest.raises(ValueError, match="already grouped"):
        create_group(exp, ["b", "c"], name="overlap", group_id="g2")
    with pytest.raises(ValueError, match="unknown nodes"):
        create_group(exp, ["missing"], name="missing", group_id="g2")


def test_remove_nodes_prunes_membership_and_empty_group():
    exp = experiment()
    create_group(exp, ["a", "b"], name="pair", group_id="g1")
    assert remove_nodes_from_groups(exp, ["a"]) == ("g1",)
    assert exp.groups == [ExperimentGroup("g1", "pair", ("b",))]
    assert remove_nodes_from_groups(exp, ["b"]) == ("g1",)
    assert exp.groups == []


def test_remove_group_is_explicit_and_fail_closed():
    exp = experiment()
    create_group(exp, ["a"], name="one", group_id="g1")
    removed = remove_group(exp, "g1")
    assert removed.id == "g1"
    assert exp.groups == []
    with pytest.raises(KeyError):
        remove_group(exp, "g1")


def test_groups_change_full_not_semantic_fingerprint():
    left = experiment()
    right = experiment()
    create_group(right, ["a", "b"], name="pair", group_id="g1")

    assert experiment_fingerprint(left, include_layout=False) == experiment_fingerprint(
        right, include_layout=False
    )
    assert experiment_fingerprint(left, include_layout=True) != experiment_fingerprint(
        right, include_layout=True
    )


def test_cace_schema_v2_round_trip_preserves_graph_schema_and_groups(tmp_path):
    exp = experiment()
    exp.schema_version = 1
    create_group(exp, ["a", "b"], name="pair", group_id="g1")
    path = tmp_path / "grouped.cace"
    save_experiment(exp, path)

    raw = json.loads(path.read_text(encoding="utf-8"))
    assert raw["schema_version"] == CURRENT_SCHEMA == 2
    assert raw["graph_schema_version"] == 1
    assert raw["groups"] == [{"id": "g1", "name": "pair", "node_ids": ["a", "b"]}]

    loaded = load_experiment(path)
    assert loaded.schema_version == 1
    assert loaded.nodes == exp.nodes
    assert loaded.edges == exp.edges
    assert loaded.groups == exp.groups
    assert loaded.metadata == exp.metadata


def test_cace_schema_v1_remains_loadable_and_migrates_to_empty_groups(tmp_path):
    path = tmp_path / "legacy.cace"
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "name": "legacy",
                "nodes": [
                    {
                        "id": "a",
                        "module_id": "example.a",
                        "params": {},
                        "position": [0.0, 0.0],
                    }
                ],
                "edges": [],
                "metadata": {"legacy": True},
            }
        ),
        encoding="utf-8",
    )

    loaded = load_experiment(path)
    assert loaded.schema_version == 1
    assert loaded.groups == []
    assert loaded.metadata == {"legacy": True}


def test_serialization_rejects_missing_and_overlapping_group_membership(tmp_path):
    exp = experiment()
    exp.groups = [ExperimentGroup("g1", "missing", ("missing",))]
    with pytest.raises(ValueError, match="missing nodes"):
        save_experiment(exp, tmp_path / "missing.cace")

    exp = experiment()
    exp.groups = [
        ExperimentGroup("g1", "one", ("a",)),
        ExperimentGroup("g2", "two", ("a", "b")),
    ]
    with pytest.raises(ValueError, match="only one experiment group"):
        save_experiment(exp, tmp_path / "overlap.cace")
