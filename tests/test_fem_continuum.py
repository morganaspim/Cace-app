import math
import pytest
from cace_studio.app import build_registry
from cace_studio.core.executor import GraphExecutor
from cace_studio.core.serialization import load_experiment
from cace_studio.core.graph import Experiment,Node,Edge


def test_v05_continuum_pipeline_certifies_total_energy_error():
    r=GraphExecutor(build_registry()).run(load_experiment('examples/certified_continuum_poisson1d_v05.cace'))
    assert r.all_verifiers_passed
    c=r.outputs['cont']['continuum_certificate']
    assert c['certified'] is True
    assert c['theorem_id']=='poisson1d-p1-constant-v1'
    lo,hi=c['energy_error_interval']
    assert 0 < lo <= hi
    t=r.outputs['total']['total_error_certificate']
    assert t['certified'] is True
    assert t['upper'] >= hi
    assert r.verification['lean'][1].state.value == 'not-run'


def test_continuum_interval_contains_closed_form_float_reference():
    r=GraphExecutor(build_registry()).run(load_experiment('examples/certified_continuum_poisson1d_v05.cace'))
    mesh=r.outputs['mesh']['mesh']; xs=[p[0] for p in mesh['vertices']]
    ref=math.sqrt(sum(abs(xs[b]-xs[a])**3/12.0 for a,b in mesh['elements']))
    lo,hi=r.outputs['cont']['continuum_certificate']['energy_error_interval']
    assert lo <= ref <= hi


def test_shape_certificate_has_interval_lengths_in_1d():
    r=GraphExecutor(build_registry()).run(load_experiment('examples/certified_continuum_poisson1d_v05.cace'))
    s=r.outputs['shape']['shape_certificate']
    assert s['dimension']==1 and s['shape_regular']
    assert all(row['h_interval'][0] <= row['h_interval'][1] and row['h_interval'][0] > 0 for row in s['elements'])


def test_continuum_theorem_rejects_wrong_diffusion():
    V='[[0.0],[0.5],[1.0]]'; E='[[0,1],[1,2]]'
    exp=Experiment(nodes=[
        Node('m','fem_nd.mesh',{'vertices':V,'elements':E}),Node('p','fem_nd.p1_space',{}),Node('s','fem_cont.mesh_shape',{}),
        Node('a','fem_cert.poisson_assemble',{'diffusion':'2.0','source_constant':1.0,'source_linear':'[]'}),
        Node('c','fem_cont.poisson1d_continuum',{})],edges=[
        Edge('m','mesh','p','mesh'),Edge('m','mesh','s','mesh'),Edge('m','mesh','a','mesh'),Edge('p','space','a','space'),
        Edge('m','mesh','c','mesh'),Edge('a','problem','c','problem'),Edge('s','shape_certificate','c','shape_certificate')])
    with pytest.raises(Exception): GraphExecutor(build_registry()).run(exp)


def test_continuum_theorem_rejects_gapped_mesh():
    V='[[0.0],[0.4],[0.6],[1.0]]'; E='[[0,1],[2,3]]'
    exp=Experiment(nodes=[Node('m','fem_nd.mesh',{'vertices':V,'elements':E}),Node('s','fem_cont.mesh_shape',{}),
        Node('c','fem_cont.poisson1d_continuum',{})],edges=[Edge('m','mesh','s','mesh'),Edge('m','mesh','c','mesh'),Edge('s','shape_certificate','c','shape_certificate')])
    problem={'dimension':1,'diffusion':1.0,'source_constant':1.0,'source_linear':[]}
    with pytest.raises(Exception): GraphExecutor(build_registry()).run(exp,external_inputs={'c':{'problem':problem}})


def test_lean_export_is_obligation_not_formal_evidence():
    r=GraphExecutor(build_registry()).run(load_experiment('examples/certified_continuum_poisson1d_v05.cace'))
    a=r.outputs['lean']['theorem_artifact']
    assert a['machine_checked'] is False
    assert a['status']=='obligation-only'
    assert 'TODO' in a['lean_source']
