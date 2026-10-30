"""Stand-alone MERLIN/CACE free-runner physics gates.
Ricci = -dphi tensor dphi denotes an exotic ghost scalar convention.
Static Ellis: source-independent analytic Cauchy benchmark.
Vaidya: independent exact time-dependent null-dust metric benchmark.
No claim of traversability, collapse, stability or a global event horizon.
"""
import math
import numpy as np
import sympy as sp
from scipy.integrate import solve_ivp

def evolve_exact_ellis(dx=.06, t0=.6, t1=1.5, half_width=.36, b=1., scalar_factor=2.):
    if (not np.isfinite([dx,t0,t1,half_width,b,scalar_factor]).all()
        or not (dx>0 and b>0 and 0<half_width<t0<t1 and scalar_factor>=0)):
        raise ValueError('invalid Cauchy domain')
    n=int(round(2*half_width/dx))
    if n<4 or abs(n*dx-2*half_width)>1e-10:
        raise ValueError('grid must exactly divide domain')
    x=np.linspace(-half_width,half_width,n+1)

    def exact(xx):
        return np.array([np.sqrt(xx*xx+b*b), np.zeros_like(xx),
                         math.sqrt(2)*np.arctan(xx/b)])
    def rhs(t,state):
        fields,vel=state.reshape(2,3,n-1)
        full=np.concatenate([exact(x[:1]),fields,exact(x[-1:])],axis=1)
        interior=full[:,1:-1]
        if np.any(interior[0]<=0) or np.max(np.abs(interior[1]))>30:
            raise FloatingPointError('invalid radius / alpha')
        fx=(full[:,2:]-full[:,:-2])/(2*dx)
        fxx=(full[:,2:]-2*interior+full[:,:-2])/dx**2
        r,alpha,phi=interior
        rt,at,pt=vel
        rx,ax,px=fx
        rforce=-(rt*rt-rx*rx)/r-np.exp(2*alpha)/r
        aforce=-rforce/r+.5*(pt*pt-px*px)
        pforce=-scalar_factor*(rt*pt-rx*px)/r
        acceleration=fxx+np.array([rforce,aforce,pforce])
        return np.stack([vel,acceleration]).ravel()

    initial=exact(x[1:-1])
    y=np.stack([initial,np.zeros_like(initial)]).ravel()
    res=solve_ivp(rhs,(t0,t1),y,method='DOP853',rtol=3e-9,atol=1e-10,max_step=dx/4)
    if not res.success:raise RuntimeError(res.message)
    evolved=res.y[:,-1].reshape(2,3,n-1)[0]
    err=np.max(np.abs(evolved-exact(x[1:-1])),axis=1)
    return {'data_origin':'EXACT_ANALYTIC_NOT_CHARACTERISTIC',
            'errors':dict(zip(('r','alpha','phi'),map(float,err))),
            'dx':float(dx),'integration_steps':len(res.t)-1,
            'physical_black_hole_certified':False,'global_stability_proved':False}

def analytical_vaidya_check():
    """Compute the 4D spherical Ricci components from a 2D warped metric."""
    v,r=sp.symbols('v r',positive=True)
    m=sp.Function('m')(v)
    h=sp.Matrix([[-(1-2*m/r),1],[1,0]])
    g=h.inv()
    cs=(v,r)
    gamma=[[[sp.simplify(sum(g[k,l]*(sp.diff(h[l,j],cs[i])+
                         sp.diff(h[l,i],cs[j])-sp.diff(h[i,j],cs[l]))/2
                         for l in range(2))) for j in range(2)] for i in range(2)]
                         for k in range(2)]
    ric=sp.zeros(2)
    for i in range(2):
        for j in range(2):
            expr=0
            for k in range(2):
                expr+=sp.diff(gamma[k][i][j],cs[k])-sp.diff(gamma[k][i][k],cs[j])
                for l in range(2):
                    expr+=gamma[k][i][j]*gamma[l][k][l]-gamma[l][i][k]*gamma[k][j][l]
            ric[i,j]=sp.simplify(expr+2*gamma[1][i][j]/r)
    lap=-sum(g[i,j]*gamma[1][i][j] for i in range(2) for j in range(2))
    rtheta=sp.simplify(1-g[1,1]-r*lap)
    scalar=sp.simplify(sum(g[i,j]*ric[i,j] for i in range(2) for j in range(2))+
                       2*rtheta/r**2)
    return {'Rvv_minus_null_dust':sp.simplify(ric[0,0]-2*sp.diff(m,v)/r**2),
            'Rvr':ric[0,1],'Rrr':ric[1,1],
            'Rtheta':rtheta,'Rscalar':scalar}

if __name__=='__main__':
    import json
    grids={str(h):evolve_exact_ellis(dx=h) for h in (.12,.06,.03,.015)}
    vaidya=analytical_vaidya_check()
    if any(v!=0 for v in vaidya.values()):
        raise SystemExit('Vaidya Einstein identity failed')
    print(json.dumps({'project':'MERLIN / MCFC-CACE','iteration':40,
                      'ellis_static':grids,'vaidya_ricci_identity':'PASS',
                      'formal_nonlinear_stability_proof':False},indent=2))
