"""Research-only classical reference frames and affine moving-grid identities.

Independent standard-library numerical oracle. NOT the canonical CACE C++ kernel,
formal verification, a quantum physical state, or a validated measurement.
"""
from __future__ import annotations
from dataclasses import dataclass
from math import cos, sin, isfinite
from typing import ClassVar


class DomainError(ValueError):
    pass


def _finite(*values):
    if not all(type(v) in (int, float) and isfinite(v) for v in values):
        raise DomainError("finite real-number coordinates required")


def _vec(value):
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise DomainError("expected a length-two vector")
    _finite(*value)
    return float(value[0]), float(value[1])


def add(a, b): return a[0] + b[0], a[1] + b[1]
def sub(a, b): return a[0] - b[0], a[1] - b[1]
def scale(k, x): return k * x[0], k * x[1]
def skew(x): return -x[1], x[0]
def rot(theta, x):
    c, s = cos(theta), sin(theta)
    return c * x[0] - s * x[1], s * x[0] + c * x[1]


@dataclass(frozen=True)
class RigidFrame2D:
    """x = origin(t) + R(theta(t)) q, with SI meters, seconds, radians."""
    origin0: tuple[float, float]
    velocity0: tuple[float, float]
    acceleration0: tuple[float, float]
    angle0: float
    omega0: float
    alpha: float
    units: ClassVar[dict[str,str]] = {"length":"m", "time":"s", "angle":"rad"}

    def __post_init__(self):
        for key in ("origin0","velocity0","acceleration0"):
            object.__setattr__(self, key, _vec(getattr(self, key)))
        _finite(self.angle0, self.omega0, self.alpha)

    def origin(self, t):
        _finite(t)
        return add(self.origin0, add(scale(t,self.velocity0),
                                     scale(0.5*t*t,self.acceleration0)))
    def theta(self, t):
        _finite(t)
        return self.angle0 + self.omega0*t + 0.5*self.alpha*t*t
    def omega(self, t):
        _finite(t)
        return self.omega0 + self.alpha*t
    def to_inertial(self, q, t):
        return add(self.origin(t), rot(self.theta(t),_vec(q)))
    def to_local(self, x, t):
        return rot(-self.theta(t), sub(_vec(x),self.origin(t)))
    def velocity_inertial(self, q, qdot, t):
        q, qdot = _vec(q), _vec(qdot)
        return add(add(self.velocity0,scale(t,self.acceleration0)),
                   rot(self.theta(t),add(qdot,scale(self.omega(t),skew(q)))))
    def acceleration_inertial(self, q, qdot, qddot, t):
        q, qdot, qddot = _vec(q), _vec(qdot), _vec(qddot)
        local = qddot
        for term in acceleration_terms(self,q,qdot,t).values():
            local = add(local,term)
        return add(self.acceleration0,rot(self.theta(t),local))
    def acceleration_relative(self, q, qdot, xacc, t):
        q, qdot = _vec(q), _vec(qdot)
        local = rot(-self.theta(t),sub(_vec(xacc),self.acceleration0))
        for term in acceleration_terms(self,q,qdot,t).values():
            local = sub(local,term)
        return local


def acceleration_terms(frame:RigidFrame2D, q, qdot, t):
    q, qdot = _vec(q), _vec(qdot)
    omega=frame.omega(t)
    return {
        "coriolis": scale(2*omega,skew(qdot)),
        "euler": scale(frame.alpha,skew(q)),
        "centripetal": scale(-omega*omega,q),
    }


def transition(from_frame:RigidFrame2D,to_frame:RigidFrame2D,q,t):
    return to_frame.to_local(from_frame.to_inertial(q,t),t)


def cocycle_error(a,b,c,q,t):
    via = transition(b,c,transition(a,b,q,t),t)
    direct=transition(a,c,q,t)
    return max(abs(v-w) for v,w in zip(via,direct))


@dataclass(frozen=True)
class AffineMovingMesh2D:
    """x = origin0 + velocity0*t + R(theta0+omega*t) diag(a,b) q.

    At time t, a(t)=a0+a_rate*t and b(t)=b0+b_rate*t must both
    be strictly positive. A changing mesh is not a physical flow.
    """
    origin0:tuple[float,float]
    velocity0:tuple[float,float]
    a0:float
    a_rate:float
    b0:float
    b_rate:float
    theta0:float
    omega:float

    def __post_init__(self):
        object.__setattr__(self,"origin0",_vec(self.origin0))
        object.__setattr__(self,"velocity0",_vec(self.velocity0))
        _finite(self.a0,self.a_rate,self.b0,self.b_rate,self.theta0,self.omega)

    def scales(self,t):
        _finite(t)
        a,b=self.a0+self.a_rate*t,self.b0+self.b_rate*t
        if a<=0 or b<=0:
            raise DomainError("mesh chart degenerates or reverses orientation")
        return a,b

    def origin(self,t):
        _finite(t)
        return add(self.origin0,scale(t,self.velocity0))

    def to_inertial(self,q,t):
        q=_vec(q)
        a,b=self.scales(t)
        return add(self.origin(t),rot(self.theta0+self.omega*t,
                                      (a*q[0],b*q[1])))

    def to_local(self,x,t):
        x=_vec(x)
        a,b=self.scales(t)
        z=rot(-(self.theta0+self.omega*t),sub(x,self.origin(t)))
        return z[0]/a,z[1]/b

    def metric(self,t):
        a,b=self.scales(t)
        return ((a*a,0.),(0.,b*b))

    def jacobian(self,t):
        a,b=self.scales(t)
        return a*b

    def jacobian_rate(self,t):
        a,b=self.scales(t)
        return self.a_rate*b+a*self.b_rate

    def mesh_flux_divergence(self,t):
        """div_q(det(M) M^-1 * partial_t(F)) for affine M=R diag(a,b)."""
        a,b=self.scales(t)
        return a*b*(self.a_rate/a+self.b_rate/b)

    def geometric_conservation_residual(self,t):
        return self.jacobian_rate(t)-self.mesh_flux_divergence(t)
