import math
import numpy as np
from cace_studio.app import build_registry
from cace_studio.core.serialization import load_experiment
from cace_studio.core.executor import GraphExecutor
from cace_studio.core.graph import Experiment, Node, Edge


def run_example():
    exp=load_experiment('examples/verified_poisson_adaptive.cace')
    return exp, GraphExecutor(build_registry(),gpu_enabled=False).run(exp)


def test_verified_poisson_pipeline_passes():
    exp,r=run_example()
    assert r.all_verifiers_passed
    assert r.outputs['certificate']['certificate_summary']['residual_pass'] is True
    assert r.outputs['residual']['residual_inf'] < 1e-10
    lo,hi=r.outputs['interval']['error_interval']
    assert 0 <= lo <= hi
    assert 'interval-certified' in next(c for c in r.certificates if c.node_id=='interval').evidence


def test_poisson_nodal_solution_matches_exact_benchmark():
    exp,r=run_example()
    x=np.asarray(r.outputs['mesh']['mesh']['vertices'])
    u=np.asarray(r.outputs['solve']['solution']['values'])
    exact=x*(1-x)/2
    assert np.max(np.abs(u-exact)) < 1e-12


def test_p1_partition_of_unity_is_symbolically_recorded():
    _,r=run_example()
    recs=r.verification['space']
    assert any(rec.kind.value=='symbolic' and rec.passed for rec in recs)


def test_sparse_assembly_is_symmetric_and_positive_definite():
    _,r=run_example()
    rec=r.verification['assemble'][0]
    assert rec.passed
    assert rec.metrics['symmetry_error'] < 1e-12
    assert rec.metrics['min_eigenvalue'] > 0
    assert rec.metrics['nnz'] > 0


def test_adaptive_refinement_preserves_domain_and_adds_marked_midpoints():
    _,r=run_example()
    old=r.outputs['mesh']['mesh']['vertices']; new=r.outputs['adapt']['refined_mesh']['vertices']; marked=r.outputs['adapt']['marked']
    assert new[0]==old[0] and new[-1]==old[-1]
    assert len(new)==len(old)+len(marked)
    assert len(marked)>=1
    assert all(a<b for a,b in zip(new,new[1:]))


def test_interval_contains_exact_energy_error_from_closed_form_interpolation_error():
    _,r=run_example()
    # For quadratic exact u with P1 nodal interpolation, ||u'-I_hu'||^2 = sum h^3/12.
    x=np.asarray(r.outputs['mesh']['mesh']['vertices']); exact=math.sqrt(float(np.sum(np.diff(x)**3))/12.0)
    lo,hi=r.outputs['interval']['error_interval']
    assert lo <= exact <= hi


def test_bad_mesh_rejected():
    exp=Experiment(nodes=[Node('m','fem.mesh1d',{'vertices':'0,0.5,0.4,1'})])
    import pytest
    with pytest.raises(Exception): GraphExecutor(build_registry()).run(exp)

def test_graph_certificate_is_content_addressed_and_preserves_evidence_scope():
    from cace_studio.core.report import graph_certificate
    _,r=run_example(); gc=graph_certificate(r)
    assert gc['all_verifiers_passed'] is True
    assert 'interval-certified' in gc['evidence_generated']
    assert 'symbolic' in gc['evidence_generated']
    assert len(gc['certificate_hash']) == 64
