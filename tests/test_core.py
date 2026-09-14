from pathlib import Path
import pytest
from cace_studio.app import build_registry
from cace_studio.core import *
from cace_studio.core.module import ValidationError
from cace_studio.core.serialization import save_experiment, load_experiment


def demo():
    return Experiment(name="demo", nodes=[
        Node("a", "core.constant", {"value": 2}), Node("b", "core.constant", {"value": 3}), Node("s", "core.add")],
        edges=[Edge("a","value","s","a"), Edge("b","value","s","b")])

def test_executes_dag_and_certifies():
    result = GraphExecutor(build_registry()).run(demo())
    assert result.outputs["s"]["sum"] == 5
    assert len(result.certificates) == 3
    assert all(len(c.output_hash) == 64 for c in result.certificates)

def test_serialization_roundtrip(tmp_path):
    p = tmp_path / "x.cace"; save_experiment(demo(), p); loaded = load_experiment(p)
    assert loaded.name == "demo" and loaded.edges == demo().edges

def test_cycle_rejected():
    exp = demo(); exp.edges.append(Edge("s","sum","a","value"))
    with pytest.raises(ValidationError): GraphExecutor(build_registry()).run(exp)

def test_duplicate_target_port_rejected():
    exp = demo(); exp.edges.append(Edge("a","value","s","a"))
    with pytest.raises(ValidationError): GraphExecutor(build_registry()).run(exp)

def test_unknown_module_rejected():
    exp = Experiment(nodes=[Node("x", "fake.module")])
    with pytest.raises(ValidationError): GraphExecutor(build_registry()).run(exp)
