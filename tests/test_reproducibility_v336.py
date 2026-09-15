from __future__ import annotations

import math

import pytest

from cace_studio.core.graph import Edge, Experiment, Node
from cace_studio.core.reproducibility import (
    canonical_json_text,
    drift_report,
    experiment_fingerprint,
    reproducibility_manifest,
)


class _Meta:
    module_id = "m.test"
    name = "Test"
    version = "1"
    category = "Tests"
    description = "test"
    maturity = type("M", (), {"value": "experimental"})()
    assumptions = ()


class _Proof:
    evidence = set()
    unit_tests = True
    property_tests = False
    regression_tests = False
    documentation = False
    benchmarked = False
    formal_artifact = None
    limitations = []


class _Port:
    def __init__(self, name):
        self.name = name
        self.type_name = "number"
        self.required = True


class _Module:
    metadata = _Meta()
    proof_status = _Proof()
    inputs = (_Port("x"),)
    outputs = (_Port("y"),)
    parameters = ()
    supports_gpu = False


class _Registry:
    def classes(self):
        return [_Module]


def exp(position=(0.0, 0.0), value=1, name="E") -> Experiment:
    return Experiment(
        name=name,
        nodes=[
            Node("a", "m.test", {"value": value}, position),
            Node("b", "m.test", {}, (2.0, 3.0)),
        ],
        edges=[Edge("a", "y", "b", "x")],
        metadata={"author": "test"},
    )


def test_canonical_json_sorts_keys_and_rejects_nonfinite():
    assert canonical_json_text({"b": 2, "a": 1}) == '{"a":1,"b":2}'
    with pytest.raises(ValueError):
        canonical_json_text({"x": math.nan})


def test_semantic_fingerprint_ignores_layout_name_and_metadata():
    first = exp(position=(0.0, 0.0), name="First")
    second = exp(position=(100.0, -20.0), name="Second")
    second.metadata = {"different": True}
    assert experiment_fingerprint(first) == experiment_fingerprint(second)
    assert experiment_fingerprint(first, include_layout=True) != experiment_fingerprint(
        second, include_layout=True
    )


def test_drift_report_distinguishes_layout_only_from_semantic_change():
    first = exp()
    moved = exp(position=(50.0, 60.0))
    layout = drift_report(first, moved)
    assert layout["semantic_equal"] is True
    assert layout["full_equal"] is False
    assert layout["layout_only"] is True
    assert layout["interpretation"] == "layout-or-presentation-only"

    changed = exp(value=2)
    semantic = drift_report(first, changed)
    assert semantic["semantic_equal"] is False
    assert semantic["changed_nodes"] == ["a"]
    assert semantic["interpretation"] == "scientific-graph-semantic-change"


def test_manifest_is_deterministic_and_explicitly_non_evidentiary():
    manifest1 = reproducibility_manifest(exp(), _Registry())
    manifest2 = reproducibility_manifest(exp(), _Registry())
    assert manifest1 == manifest2
    assert len(manifest1["semantic_experiment_sha256"]) == 64
    assert len(manifest1["full_experiment_sha256"]) == 64
    assert len(manifest1["module_contract_sha256"]) == 64
    assert any("not scientific correctness" in note for note in manifest1["notes"])
