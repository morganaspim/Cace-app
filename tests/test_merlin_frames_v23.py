"""CACE PR-scoped classical reference-frame regressions, no physical claims."""
from __future__ import annotations
import random
import pytest
from research.merlin_frames_v23.classical import (
    RigidFrame2D, AffineMovingMesh2D, DomainError,
    acceleration_terms, transition, cocycle_error,
)

def close_vec(a,b,tol=1e-10):
    assert all(abs(x-y)<tol for x,y in zip(a,b)),(a,b)

def test_roundtrip_rotating_accelerating_frames():
    frame=RigidFrame2D((.3,-1.2),(2.,.4),(.7,-.5),.15,.6,-.2)
    for t in (0.,.3,1.,2.2):
        for q in ((1.,-2.),(-.3,.8),(0.,0.)):
            close_vec(frame.to_local(frame.to_inertial(q,t),t),q)

def test_classical_three_frame_cocycle_metamorphic():
    rng=random.Random(20261030)
    for _ in range(75):
        frames=[RigidFrame2D(
            tuple(rng.uniform(-2,2) for _ in range(2)),
            tuple(rng.uniform(-1,1) for _ in range(2)),
            tuple(rng.uniform(-.5,.5) for _ in range(2)),
            rng.uniform(-3,3),rng.uniform(-2,2),rng.uniform(-1,1)) for _ in range(3)]
        q=(rng.uniform(-5,5),rng.uniform(-5,5))
        t=rng.uniform(-3,3)
        assert cocycle_error(*frames,q,t)<2e-14
        close_vec(transition(frames[1],frames[0],
                 transition(frames[0],frames[1],q,t),t),q)

def test_acceleration_terms_coriolis_euler_centripetal():
    frame=RigidFrame2D((0.,0.),(0.,0.),(0.,0.),0.,2.,3.)
    terms=acceleration_terms(frame,(1.,2.),(3.,4.),0.)
    close_vec(terms["coriolis"],(-16.,12.))
    close_vec(terms["euler"],(-6.,3.))
    close_vec(terms["centripetal"],(-4.,-8.))
    close_vec(frame.acceleration_inertial((1.,2.),(3.,4.),(0.,0.),0.),(-26.,7.))

def test_relative_acceleration_inverse():
    frame=RigidFrame2D((1.,2.),(2.,-1.),(.4,1.5),.2,-.5,.7)
    q=(1.2,-.9);v=(.2,.3);a=(2.,-3.)
    inertial=frame.acceleration_inertial(q,v,a,.8)
    close_vec(frame.acceleration_relative(q,v,inertial,.8),a)

def test_galilean_uniform_translation_acceleration():
    frame=RigidFrame2D((2.,-1.),(8.,-3.),(0.,0.),0.,0.,0.)
    close_vec(frame.acceleration_inertial((1.,2.),(.3,.4),(.8,-.1),1.4),(.8,-.1))

def test_accelerating_frame_apparent_force():
    frame=RigidFrame2D((0.,0.),(0.,0.),(2.,-3.),0.,0.,0.)
    close_vec(frame.acceleration_relative((0.,0.),(1.,0.),(0.,0.),.2),(-2.,3.))

def test_affine_mesh_geometric_conservation():
    mesh=AffineMovingMesh2D((.2,-.8),(.4,.7),1.2,.2,.9,.15,.4,.3)
    for t in (0.,.5,1.5):
        q=(.2,-.4)
        close_vec(mesh.to_local(mesh.to_inertial(q,t),t),q)
        metric=mesh.metric(t)
        assert metric[0][0]*metric[1][1]==pytest.approx(mesh.jacobian(t)**2)
        assert abs(mesh.geometric_conservation_residual(t))<1e-12

def test_moving_mesh_jacobian_finite_difference():
    mesh=AffineMovingMesh2D((.1,-.4),(.7,-.6),1.2,.1,.8,.05,.4,1.1)
    h=1e-5
    for t in (0.,1.,4.):
        p=mesh.to_inertial((.4,-.3),t)
        pu=mesh.to_inertial((.4+h,-.3),t)
        pv=mesh.to_inertial((.4,-.3+h),t)
        ux,uy=((pu[i]-p[i])/h for i in (0,1))
        vx,vy=((pv[i]-p[i])/h for i in (0,1))
        assert ux*vy-uy*vx==pytest.approx(mesh.jacobian(t),rel=2e-9)

def test_expanding_mesh_jacobian_is_not_constant_mass():
    mesh=AffineMovingMesh2D((0.,0.),(0.,0.),1.,.5,1.,0.,0.,0.)
    assert mesh.jacobian(1.)>mesh.jacobian(0.)
    assert mesh.jacobian_rate(1.)==pytest.approx(mesh.mesh_flux_divergence(1.))

def test_frame_invalid_domain_and_nonfinite_rejected():
    with pytest.raises(DomainError):
        RigidFrame2D((float("nan"),0.),(0.,0.),(0.,0.),0.,0.,0.)
    mesh=AffineMovingMesh2D((0.,0.),(0.,0.),1.,-1.,1.,0.,0.,0.)
    for t in (1.,2.,float("nan")):
        with pytest.raises(DomainError): mesh.metric(t)
    with pytest.raises(DomainError): mesh.to_local((float("inf"),0.),0.)
