from __future__ import annotations

from cace_studio.core.autosave import autosave_exists, read_autosave, write_autosave
from cace_studio.core.edit_history import ExperimentHistory
from cace_studio.core.graph import Edge, Experiment, Node


def sample_experiment() -> Experiment:
    return Experiment(
        name="history",
        nodes=[
            Node("n1", "example.a", {"value": 1}, (10.0, 20.0)),
            Node("n2", "example.b", {}, (30.0, 40.0)),
        ],
        edges=[Edge("n1", "out", "n2", "in")],
        metadata={"note": "snapshot"},
    )


def test_history_undo_redo_uses_independent_snapshots():
    exp = sample_experiment()
    history = ExperimentHistory(limit=3)
    history.record(exp)
    exp.nodes[0].params["value"] = 2

    previous = history.undo(exp)
    assert previous is not None
    assert previous.nodes[0].params["value"] == 1
    previous.nodes[0].params["value"] = 999
    assert exp.nodes[0].params["value"] == 2

    following = history.redo(previous)
    assert following is not None
    assert following.nodes[0].params["value"] == 2


def test_history_limit_and_clear():
    history = ExperimentHistory(limit=2)
    exp = sample_experiment()
    for value in range(4):
        exp.nodes[0].params["value"] = value
        history.record(exp)
    assert history.can_undo
    assert history.undo(exp).nodes[0].params["value"] == 3
    assert history.undo(exp).nodes[0].params["value"] == 2
    assert history.undo(exp) is None
    history.clear()
    assert not history.can_undo
    assert not history.can_redo


def test_autosave_round_trip_is_atomic_and_schema_backed(tmp_path):
    path = tmp_path / "state" / "autosave.cace"
    exp = sample_experiment()
    written = write_autosave(exp, path)
    assert written == path
    assert autosave_exists(path)
    assert not path.with_suffix(".cace.tmp").exists()

    loaded = read_autosave(path)
    assert loaded.name == exp.name
    assert loaded.nodes == exp.nodes
    assert loaded.edges == exp.edges
    assert loaded.metadata == exp.metadata
