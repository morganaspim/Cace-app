"""Exact Vaidya metric: future-stationary apparent/event horizon comparison.

Ingoing Vaidya ds²=-(1-2m(v)/r)dv²+2dvdr+r²dΩ².
For m(v) constant after v=T, future EH generator has r(T)=2m(T) and
satisfies dr/dv=(1-2m(v)/r)/2 before T. This uses known full future
boundary conditions, unlike finite-domain ghost scalar marginal spheres.
This is a mathematical null-dust model, not an astrophysical observation.
"""
import numpy as np
from scipy.integrate import solve_ivp

def compact_mass(v, m0=.65, dm=.20, T=1.):
    v=np.asarray(v,dtype=float)
    s=np.clip(v/T,0.,1.)
    smooth=s*s*s*(10.+s*(-15.+6.*s))
    return m0+dm*smooth

def compact_mass_prime(v, dm=.20, T=1.):
    v=np.asarray(v,dtype=float)
    s=np.clip(v/T,0.,1.)
    return dm*30*s*s*(1-s)*(1-s)/T

def track_horizons(m0=.65, dm=.20, T=1., v_min=-.4, v_max=2.,
                   n_samples=241, rk4_step=.001):
    if (not np.isfinite([m0,dm,T,v_min,v_max,rk4_step]).all()
        or not (m0>0 and dm>0 and T>0 and v_min<0<T<v_max and
                n_samples>=40 and rk4_step>0)):
        raise ValueError('invalid finite Vaidya model')
    v=np.linspace(v_min,v_max,n_samples)
    R=2*(m0+dm)
    def f(z,y):
        return .5*(1.-2*compact_mass(z,m0,dm,T)/y)
    sol=solve_ivp(lambda z,y:[f(z,y[0])],(T,v_min),[R],method='DOP853',
                  rtol=1e-12,atol=1e-14,dense_output=True,max_step=.05)
    if not sol.success:raise RuntimeError(sol.message)
    r_event=np.where(v<T,sol.sol(np.minimum(v,T))[0],R)
    r_app=2*compact_mass(v,m0,dm,T)
    N=int(np.ceil((T-v_min)/rk4_step))
    step=(v_min-T)/N
    grid=np.linspace(T,v_min,N+1)
    values=np.empty(N+1);values[0]=R
    for i in range(N):
        z=grid[i];y=values[i]
        k1=f(z,y);k2=f(z+step/2,y+step*k1/2)
        k3=f(z+step/2,y+step*k2/2);k4=f(z+step,y+step*k3)
        values[i+1]=y+step*(k1+2*k2+2*k3+k4)/6
    r_rk4=np.where(v<T,np.interp(np.minimum(v,T),grid[::-1],values[::-1]),R)
    residual=((r_event[2:]-r_event[:-2])/(v[2:]-v[:-2])
              - .5*(1-2*compact_mass(v[1:-1],m0,dm,T)/r_event[1:-1]))
    return {'v':v,'r_event':r_event,'r_apparent':r_app,
            'max_two_integrator_disagreement':float(np.max(abs(r_rk4-r_event))),
            'max_geodesic_residual':float(np.max(abs(residual))),
            'event_horizon_future_stationary_assumption':True,
            'model_observed_astronomically':False,
            'physical_ghost_wormhole_stability_proved':False,
            'matter_model':'positive energy ingoing null dust, finite compact mass pulse'}

if __name__=='__main__':
    import json
    out=track_horizons()
    v=out['v'];gap=out['r_event']-out['r_apparent']
    print(json.dumps({
        'project':'MERLIN / MCFC-CACE',
        'iteration':40,
        'model':'exact future-stationary ingoing Vaidya with positive null dust',
        'event_horizon_condition':'backward outgoing null geodesic from r(T)=2m(T)',
        'marginal_horizon_condition':'r_apparent(v)=2m(v)',
        'sampled_event_minus_apparent_at_v0':float(np.interp(0.,v,gap)),
        'sampled_event_minus_apparent_at_vhalf':float(np.interp(.5,v,gap)),
        'max_two_integrator_disagreement':out['max_two_integrator_disagreement'],
        'max_geodesic_residual':out['max_geodesic_residual'],
        'known_full_future_boundary_required':True,
        'observed_astronomically':False,
        'wormhole_stability_proved':False
    },indent=2))
