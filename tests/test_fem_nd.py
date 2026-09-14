import json, numpy as np, pytest
from cace_studio.app import build_registry
from cace_studio.core.graph import Experiment, Node, Edge
from cace_studio.core.executor import GraphExecutor
from cace_studio.core.serialization import load_experiment


def one_node(mid, params):
    return GraphExecutor(build_registry()).run(Experiment(nodes=[Node('n',mid,params)]))


def test_triangle_mesh_and_p1_identities():
    V='[[0,0],[1,0],[0,1]]'; E='[[0,1,2]]'
    exp=Experiment(nodes=[Node('m','fem_nd.mesh',{'vertices':V,'elements':E}),Node('s','fem_nd.p1_space',{})],edges=[Edge('m','mesh','s','mesh')])
    r=GraphExecutor(build_registry()).run(exp)
    assert r.all_verifiers_passed
    assert r.outputs['m']['mesh']['dimension']==2
    assert r.outputs['s']['space']['local'][0]['volume']==pytest.approx(0.5)
    assert r.verification['s'][0].metrics['max_identity_error'] < 1e-12


def test_tetrahedral_mesh_basis_and_poisson_spd():
    # Unit tetra with its centroid as one interior vertex, subdivided into four tetrahedra.
    V=[[0,0,0],[1,0,0],[0,1,0],[0,0,1],[0.25,0.25,0.25]]
    E=[[4,1,2,3],[0,4,2,3],[0,1,4,3],[0,1,2,4]]
    exp=Experiment(nodes=[
        Node('m','fem_nd.mesh',{'vertices':json.dumps(V),'elements':json.dumps(E)}),
        Node('s','fem_nd.p1_space',{}),Node('a','fem_nd.poisson_assemble',{}),Node('u','fem_nd.linear_solve',{})],edges=[
        Edge('m','mesh','s','mesh'),Edge('m','mesh','a','mesh'),Edge('s','space','a','space'),Edge('a','system','u','system')])
    r=GraphExecutor(build_registry()).run(exp)
    assert r.all_verifiers_passed
    assert r.outputs['m']['mesh']['dimension']==3
    assert r.outputs['a']['system']['interior_dofs']==[4]
    assert r.verification['a'][0].metrics['min_eigenvalue'] > 0
    assert r.outputs['u']['solution']['values'][4] > 0


def test_centroid_quadrature_degree_one_exactness():
    V='[[0,0],[2,0],[0,1]]'; E='[[0,1,2]]'
    exp=Experiment(nodes=[Node('m','fem_nd.mesh',{'vertices':V,'elements':E}),Node('q','fem_nd.quadrature',{})],edges=[Edge('m','mesh','q','mesh')])
    r=GraphExecutor(build_registry()).run(exp)
    assert r.all_verifiers_passed
    q=r.outputs['q']['quadrature']['cells'][0]
    assert q['weight']==pytest.approx(1.0)
    assert q['point']==pytest.approx([2/3,1/3])


def test_2d_poisson_pipeline_residual_and_estimator():
    exp=load_experiment('examples/poisson_2d_simplex.cace')
    r=GraphExecutor(build_registry()).run(exp)
    assert r.all_verifiers_passed
    assert r.outputs['residual']['residual_inf'] < 1e-10
    assert r.outputs['solve']['solution']['values'][4] > 0
    assert r.outputs['estimator']['estimator']['eta'] > 0


def test_uniform_triangle_refinement_is_conforming_and_quadruplicates_cells():
    exp=load_experiment('examples/poisson_2d_simplex.cace')
    r=GraphExecutor(build_registry()).run(exp)
    old=r.outputs['mesh']['mesh']; new=r.outputs['refine']['refined_mesh']
    assert len(new['elements']) == 4*len(old['elements'])
    assert r.verification['refine'][0].passed


def test_convergence_history_refines_h_and_keeps_small_residuals():
    exp=load_experiment('examples/poisson_2d_simplex.cace')
    r=GraphExecutor(build_registry()).run(exp)
    hist=r.outputs['history']['history']['records']
    assert len(hist)==3
    assert all(b['h_max'] < a['h_max'] for a,b in zip(hist,hist[1:]))
    assert max(x['residual_inf'] for x in hist) < 1e-10


def test_tetrahedral_refinement_is_explicitly_not_claimed():
    V=[[0,0,0],[1,0,0],[0,1,0],[0,0,1]]; E=[[0,1,2,3]]
    exp=Experiment(nodes=[Node('m','fem_nd.mesh',{'vertices':json.dumps(V),'elements':json.dumps(E)}),Node('r','fem_nd.refine',{})],edges=[Edge('m','mesh','r','mesh')])
    with pytest.raises(Exception): GraphExecutor(build_registry()).run(exp)


def test_nonmanifold_mesh_rejected():
    # Three triangles sharing edge (0,1).
    V=[[0,0],[1,0],[0,1],[0,-1],[0.5,1]]; E=[[0,1,2],[1,0,3],[0,1,4]]
    exp=Experiment(nodes=[Node('m','fem_nd.mesh',{'vertices':json.dumps(V),'elements':json.dumps(E)})])
    with pytest.raises(Exception): GraphExecutor(build_registry()).run(exp)


def test_adaptive_2d_dorfler_red_green_refinement_is_conforming():
    exp=load_experiment('examples/poisson_2d_simplex.cace')
    r=GraphExecutor(build_registry()).run(exp)
    assert r.verification['adapt'][0].passed
    assert len(r.outputs['adapt']['marked']) >= 1
    assert len(r.outputs['adapt']['refined_mesh']['elements']) > len(r.outputs['mesh']['mesh']['elements'])
    assert r.outputs['certificate_nd']['certificate_summary']['residual_pass'] is True
