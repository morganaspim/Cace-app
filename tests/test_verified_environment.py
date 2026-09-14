import math
from cace_studio.app import build_registry
from cace_studio.core import GraphExecutor, Experiment, Node, Edge, DeviceManager
from cace_studio.core.serialization import load_experiment
from cace_studio.core.report import run_report


def test_verified_quadratic_example_passes():
    exp=load_experiment("examples/verified_quadratic.cace")
    r=GraphExecutor(build_registry()).run(exp)
    assert r.outputs["verify"]["verified"] is True
    assert r.outputs["verify"]["max_abs_residual"] <= 1e-9
    assert r.all_verifiers_passed
    cert=next(c for c in r.certificates if c.node_id=="verify")
    assert "numerical" in cert.evidence


def test_gpu_policy_is_recorded_and_falls_back_safely_when_unavailable():
    exp=Experiment(nodes=[Node("g","science.grid1d",{"points":5})])
    r=GraphExecutor(build_registry(),gpu_enabled=True).run(exp)
    c=r.certificates[0]
    assert c.requested_device=="gpu"
    if DeviceManager.gpu_available():
        assert c.actual_device=="gpu"
    else:
        assert c.actual_device=="cpu" and c.backend=="numpy"


def test_interval_square_encloses_expected_range():
    exp=load_experiment("examples/interval_square.cace")
    r=GraphExecutor(build_registry()).run(exp)
    lo,hi=r.outputs["s"]["squared"]
    assert lo <= 0.0
    assert hi >= 9.0
    assert r.all_verifiers_passed
    cert=next(c for c in r.certificates if c.node_id=="s")
    assert "interval-certified" in cert.evidence


def test_failed_verifier_is_preserved_as_result_not_hidden():
    exp=Experiment(nodes=[Node("v","verify.constant_residual",{"target":2.0,"tolerance":1e-12})])
    r=GraphExecutor(build_registry()).run(exp,external_inputs={"v":{"values":[1.0,2.0,3.0]}})
    assert r.outputs["v"]["verified"] is False
    assert not r.all_verifiers_passed
    assert r.verification["v"][0].state.value=="fail"


def test_run_report_contains_environment_and_verification():
    exp=load_experiment("examples/verified_quadratic.cace")
    r=GraphExecutor(build_registry()).run(exp)
    report=run_report(r,exp.name)
    assert report["run_id"]==r.run_id
    assert report["environment"]["python"]
    assert report["verification"]["verify"][0]["state"]=="pass"
