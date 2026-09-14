import math, os
import numpy as np

from cace_studio.modules.fem_v010 import _verified_enclosure, VerifiedSparseSolutionEnclosure, SolutionEnclosurePlot
from cace_studio.modules.fem_nd import _csr_from_dense
from cace_studio.core.module import ExecutionContext


def ctx(): return ExecutionContext(run_id='test')


def test_verified_enclosure_contains_exact_solution_spd():
    A=np.array([[4.0,-1.0,0.0],[-1.0,4.0,-1.0],[0.0,-1.0,3.0]])
    b=np.array([15.0,10.0,10.0]); xhat=np.linalg.solve(A,b)
    # perturb one ulp-ish amount so the enclosure must do real work
    xhat=xhat.copy(); xhat[1]=math.nextafter(float(xhat[1]), math.inf)
    c=_verified_enclosure(A,b,xhat)
    assert c['certified'] and c['q_upper'] < 1.0 and c['krawczyk_inclusion']
    exact=np.linalg.solve(A,b)
    for xi,(lo,hi) in zip(exact,c['solution_intervals']): assert lo <= xi <= hi


def test_verified_enclosure_general_nonsymmetric_system():
    A=np.array([[3.0,1.0],[0.5,2.0]])
    b=np.array([1.0,4.0]); x=np.linalg.solve(A,b)
    c=_verified_enclosure(A,b,x)
    assert c['certified'] and c['q_upper'] < 1.0


def test_verified_enclosure_refuses_singular():
    A=np.array([[1.0,2.0],[2.0,4.0]]); b=np.array([1.0,2.0]); x=np.zeros(2)
    c=_verified_enclosure(A,b,x)
    assert not c['certified']


def test_module_certificate_for_csr_system():
    A=np.array([[2.0,-1.0],[-1.0,2.0]]); b=np.array([1.0,0.0]); x=np.linalg.solve(A,b)
    sys={'matrix':_csr_from_dense(A),'rhs':b.tolist(),'interior_dofs':[1,2],'boundary_dofs':[0,3],'full_dofs':4}
    sol={'interior':x.tolist(),'values':[0.0,*x.tolist(),0.0]}
    m=VerifiedSparseSolutionEnclosure(); out=m.execute({'system':sys,'solution':sol},{},ctx())
    rec=m.verify({'system':sys,'solution':sol},{},out,ctx())[0]
    assert out['solution_enclosure']['certified'] and rec.passed


def test_visualization_from_verified_enclosure(tmp_path):
    A=np.array([[2.0,-1.0],[-1.0,2.0]]); b=np.array([1.0,0.0]); x=np.linalg.solve(A,b)
    c=_verified_enclosure(A,b,x); path=tmp_path/'enclosure.png'
    m=SolutionEnclosurePlot(); out=m.execute({'solution_enclosure':c,'solution':{'interior':x.tolist()}},{'output_path':str(path)},ctx())
    assert path.exists() and path.stat().st_size>1000
    assert path.read_bytes()[:8] == b'\x89PNG\r\n\x1a\n'
    assert m.verify({}, {}, out, ctx())[0].passed
