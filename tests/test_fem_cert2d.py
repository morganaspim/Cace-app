import math
import numpy as np
import pytest

from cace_studio.core.module import ExecutionContext, ValidationError
from cace_studio.modules.fem_nd import SimplexMeshND, P1SimplexSpaceND, LinearSolverND
from cace_studio.modules.fem_cert import CertifiedPoissonAssembly
from cace_studio.modules.fem_cert2d import (
    CertifiedTriangleGeometry2D, CertifiedShapeRegularity2D, CertifiedElementStiffness2D, BubblePoissonProblem2D,
    BubbleContinuumEnergyCertificate2D, BubbleResidualEstimatorCertificate2D,
    BubbleReliabilityCertificate2D, ReliabilityTheoremObligation2D,
)

CTX=ExecutionContext(run_id='test')

def run(mod, inputs=None, params=None):
    inputs=inputs or {}; params=mod.resolved_params(params or {}); mod.validate(inputs,params); out=mod.execute(inputs,params,CTX); return out,mod.verify(inputs,params,out,CTX)

def mesh_obj():
    # Reference triangle split around an interior point. All cells are CCW.
    m=SimplexMeshND()
    out,_=run(m,params={
        'vertices':'[[0,0],[1,0],[0,1],[0.3333333333333333,0.3333333333333333]]',
        'elements':'[[0,1,3],[1,2,3],[2,0,3]]'})
    return out['mesh']

def pipeline():
    mesh=mesh_obj()
    sp,_=run(P1SimplexSpaceND(),{'mesh':mesh})
    geo,vg=run(CertifiedTriangleGeometry2D(),{'mesh':mesh})
    shape,vsh=run(CertifiedShapeRegularity2D(),{'geometry_certificate':geo['geometry_certificate']},{'max_ratio':20.0})
    stiff,vs=run(CertifiedElementStiffness2D(),{'mesh':mesh,'geometry_certificate':geo['geometry_certificate']})
    prob,vp=run(BubblePoissonProblem2D())
    asm,va=run(CertifiedPoissonAssembly(),{'mesh':mesh,'space':sp['space']},{'diffusion':'1.0','source_constant':0.0,'source_linear':'[2.0,2.0]'})
    sol,vsol=run(LinearSolverND(),{'system':asm['system']})
    cont,vc=run(BubbleContinuumEnergyCertificate2D(),{'mesh':mesh,'solution':sol['solution'],'problem':prob['problem'],'geometry_certificate':geo['geometry_certificate']})
    est,ve=run(BubbleResidualEstimatorCertificate2D(),{'mesh':mesh,'solution':sol['solution'],'geometry_certificate':geo['geometry_certificate']})
    rel,vr=run(BubbleReliabilityCertificate2D(),{'continuum_certificate':cont['continuum_certificate'],'estimator_certificate':est['estimator_certificate']},{'C_rel':1.0})
    return mesh,geo,shape,stiff,asm,sol,cont,est,rel,vg+vsh+vs+vp+va+vsol+vc+ve+vr

def test_certified_triangle_geometry_and_stiffness():
    mesh,geo,shape,stiff,*_=pipeline()
    assert len(geo['geometry_certificate']['elements'])==3
    assert shape['shape_certificate']['shape_regular_certified'] is True
    assert all(e['det_interval'][0]>0 for e in geo['geometry_certificate']['elements'])
    for e in stiff['stiffness_certificate']['elements']:
        K=e['stiffness_intervals']
        assert all(K[i][i][0]>0 for i in range(3))
        for i in range(3):
            for j in range(3):
                assert K[i][j][0] <= K[j][i][1] and K[j][i][0] <= K[i][j][1]

def test_bubble_continuum_and_estimator_are_intervals():
    *_,cont,est,rel,recs=pipeline()
    elo,ehi=cont['continuum_certificate']['energy_error_interval']
    etalo,etahi=est['estimator_certificate']['eta_interval']
    assert 0 < elo <= ehi < math.inf
    assert 0 < etalo <= etahi < math.inf
    assert rel['reliability_certificate']['certified'] is True
    assert ehi <= rel['reliability_certificate']['C_eta_lower']
    assert all(r.state.value != 'fail' for r in recs)

def test_orientation_ambiguity_rejected():
    mesh=mesh_obj(); mesh['elements'][0]=[0,3,1]
    mod=CertifiedTriangleGeometry2D(); p=mod.resolved_params({})
    with pytest.raises(ValidationError): mod.validate({'mesh':mesh},p)

def test_generic_reliability_remains_formal_obligation():
    out,recs=run(ReliabilityTheoremObligation2D())
    assert out['theorem_artifact']['machine_checked'] is False
    assert recs[0].state.value == 'not-run'
