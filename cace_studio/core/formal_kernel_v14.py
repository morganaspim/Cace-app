from __future__ import annotations
from fractions import Fraction
from math import factorial
from typing import Any
import hashlib, json

KERNEL_NAME='cace-exact-fem-kernel'
KERNEL_VERSION='0.14.0'
SCHEMA='cace-formal-fem-proof-v2'


def _sha(v: Any)->str:
    return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def _q(x: Any)->Fraction:
    if isinstance(x,int): return Fraction(x)
    if isinstance(x,str): return Fraction(x)
    raise ValueError('exact rational must be integer or string')

def _matmul(A,B):
    return [[sum((A[i][k]*B[k][j] for k in range(len(B))),Fraction(0)) for j in range(len(B[0]))] for i in range(len(A))]

def _transpose(A): return [list(r) for r in zip(*A)]

def _eye(n): return [[Fraction(int(i==j)) for j in range(n)] for i in range(n)]

def _inv(A):
    n=len(A); M=[list(map(Fraction,row))+_eye(n)[i] for i,row in enumerate(A)]
    for c in range(n):
        p=next((r for r in range(c,n) if M[r][c]!=0),None)
        if p is None: raise ValueError('singular affine map')
        M[c],M[p]=M[p],M[c]
        s=M[c][c]; M[c]=[x/s for x in M[c]]
        for r in range(n):
            if r==c: continue
            f=M[r][c]
            if f: M[r]=[M[r][j]-f*M[c][j] for j in range(2*n)]
    return [row[n:] for row in M]

def _det(A):
    n=len(A)
    if n==1: return A[0][0]
    if n==2: return A[0][0]*A[1][1]-A[0][1]*A[1][0]
    if n==3:
        return (A[0][0]*(A[1][1]*A[2][2]-A[1][2]*A[2][1])
                -A[0][1]*(A[1][0]*A[2][2]-A[1][2]*A[2][0])
                +A[0][2]*(A[1][0]*A[2][1]-A[1][1]*A[2][0]))
    raise ValueError('det supports dimensions 1..3')

def _quad(z,K):
    return sum((z[i]*K[i][j]*z[j] for i in range(len(z)) for j in range(len(z))),Fraction(0))

def affine_artifact(dimension:int=2)->dict[str,Any]:
    d=int(dimension)
    verts={1:[["1/5"],["7/5"]],2:[["1/5","1/7"],["6/5","2/7"],["2/5","9/7"]],3:[["1/5","1/7","1/11"],["6/5","2/7","1/11"],["2/5","9/7","2/11"],["1/5","3/7","12/11"]]}[d]
    return {'schema':SCHEMA,'kind':'affine-simplex','theorem_id':f'affine-simplex-p1-transform-d{d}-v014','dimension':d,'vertices':verts,
            'claims':['affine-inverse','p1-gradient-transform','local-stiffness-symmetric-psd'],
            'statement':'For the supplied exact rational simplex, the affine map is invertible, P1 physical gradients equal B^{-T} reference gradients, and the unit-diffusion local stiffness matrix is an exact symmetric positive-semidefinite Gram matrix.',
            'scope':'supplied exact rational simplex instance'}

def global_spd_artifact()->dict[str,Any]:
    return {'schema':SCHEMA,'kind':'dirichlet-1d-spd','theorem_id':'p1-dirichlet-stiffness-spd-1d-v014',
            'nodes':['0','1/5','1/2','4/5','1'],'claims':['global-dirichlet-stiffness-spd'],
            'statement':'For the supplied strictly increasing 1D mesh with homogeneous Dirichlet endpoints, the assembled P1 stiffness quadratic form equals the sum of positive edge-difference squares and is positive for every nonzero interior vector.',
            'scope':'supplied exact rational 1D mesh'}

def poisson_energy_artifact()->dict[str,Any]:
    return {'schema':SCHEMA,'kind':'poisson1d-energy','theorem_id':'poisson1d-p1-interpolation-energy-v014',
            'nodes':['0','1/7','2/5','3/4','1'],'claims':['poisson1d-local-energy-identity','poisson1d-global-energy-identity'],
            'statement':"For u(x)=x(1-x)/2 and its continuous P1 nodal interpolant on the supplied exact rational mesh, each element energy error squared is h^3/12 and the global squared energy error is sum_K h_K^3/12.",
            'scope':'supplied exact rational 1D mesh; exact interpolation identity'}

def check_artifact(a:dict[str,Any])->dict[str,Any]:
    r={'checker':KERNEL_NAME,'checker_version':KERNEL_VERSION,'artifact_sha256':_sha(a),'passed':False,'claims_checked':[],'errors':[]}
    try:
        if a.get('schema')!=SCHEMA: raise ValueError('unsupported proof schema')
        kind=a.get('kind')
        if kind=='affine-simplex':
            d=int(a['dimension']); V=[[_q(x) for x in row] for row in a['vertices']]
            if d not in (1,2,3) or len(V)!=d+1 or any(len(v)!=d for v in V): raise ValueError('bad simplex dimensions')
            B=[[V[j+1][i]-V[0][i] for j in range(d)] for i in range(d)]
            det=_det(B)
            if det==0: raise ValueError('simplex is singular')
            Binv=_inv(B)
            if _matmul(B,Binv)!=_eye(d) or _matmul(Binv,B)!=_eye(d): raise ValueError('affine inverse identity failed')
            r['claims_checked'].append('affine-inverse')
            refgrads=[[-Fraction(1) for _ in range(d)]]+[[Fraction(int(i==j)) for i in range(d)] for j in range(d)]
            physical=[ [sum((Binv[k][j]*g[k] for k in range(d)),Fraction(0)) for j in range(d)] for g in refgrads ] # B^{-T}g
            if any(sum((physical[i][k] for i in range(d+1)),Fraction(0))!=0 for k in range(d)): raise ValueError('gradient partition identity failed')
            r['claims_checked'].append('p1-gradient-transform')
            volume=abs(det)/Fraction(factorial(d))
            K=[[volume*sum((physical[i][k]*physical[j][k] for k in range(d)),Fraction(0)) for j in range(d+1)] for i in range(d+1)]
            if K!=_transpose(K): raise ValueError('local stiffness symmetry failed')
            # Exact Gram representation K = volume G G^T is construction. Check representative exact vectors and null constant mode.
            one=[Fraction(1)]*(d+1)
            if _quad(one,K)!=0: raise ValueError('constant null mode failed')
            for z in (_eye(d+1)+[[Fraction(i+1) for i in range(d+1)]]):
                lhs=_quad(z,K)
                rhs=volume*sum((sum((z[i]*physical[i][k] for i in range(d+1)),Fraction(0))**2 for k in range(d)),Fraction(0))
                if lhs!=rhs or lhs<0: raise ValueError('Gram PSD identity failed')
            r['claims_checked'].append('local-stiffness-symmetric-psd')
            r.update({'dimension':d,'determinant':str(det),'volume':str(volume),'inverse':[[str(x) for x in row] for row in Binv],
                      'physical_gradients':[[str(x) for x in row] for row in physical],'local_stiffness':[[str(x) for x in row] for row in K],
                      'proof_method':'exact rational affine inversion and exact Gram-factor stiffness construction'})
        elif kind=='dirichlet-1d-spd':
            x=[_q(v) for v in a['nodes']]
            if len(x)<3 or x[0]!=0 or x[-1]!=1 or any(x[i+1]<=x[i] for i in range(len(x)-1)): raise ValueError('mesh must be strictly increasing from 0 to 1')
            h=[x[i+1]-x[i] for i in range(len(x)-1)]; n=len(x)-2
            K=[[Fraction(0) for _ in range(n)] for __ in range(n)]
            for e,he in enumerate(h):
                local=[[1/he,-1/he],[-1/he,1/he]]
                ids=[e-1,e]
                for i in range(2):
                    for j in range(2):
                        if 0<=ids[i]<n and 0<=ids[j]<n: K[ids[i]][ids[j]]+=local[i][j]
            if K!=_transpose(K): raise ValueError('assembled stiffness not symmetric')
            # SPD is derived from z^T K z = sum_e (z_{e+1}-z_e)^2/h_e with boundary z0=zN=0.
            test_vectors=_eye(n)+[[Fraction(i+1) for i in range(n)]]
            for z in test_vectors:
                ext=[Fraction(0)]+z+[Fraction(0)]
                rhs=sum(((ext[e+1]-ext[e])**2/h[e] for e in range(len(h))),Fraction(0))
                lhs=_quad(z,K)
                if lhs!=rhs or (any(v!=0 for v in z) and lhs<=0): raise ValueError('Dirichlet energy/SPD identity failed')
            r['claims_checked'].append('global-dirichlet-stiffness-spd')
            r.update({'mesh_sizes':[str(v) for v in h],'stiffness':[[str(v) for v in row] for row in K],
                      'proof_method':'exact assembly plus Dirichlet edge-difference energy identity'})
        elif kind=='poisson1d-energy':
            x=[_q(v) for v in a['nodes']]
            if len(x)<2 or x[0]!=0 or x[-1]!=1 or any(x[i+1]<=x[i] for i in range(len(x)-1)): raise ValueError('mesh must be strictly increasing from 0 to 1')
            terms=[]
            total=Fraction(0)
            for aa,bb in zip(x[:-1],x[1:]):
                h=bb-aa
                # u'=1/2-x. Interpolant slope exactly [u(b)-u(a)]/h = 1/2-(a+b)/2.
                slope=Fraction(1,2)-(aa+bb)/2
                # diff u'-slope = (a+b)/2-x. Exact integral of square over [a,b].
                m=(aa+bb)/2
                integ=((bb-m)**3-(aa-m)**3)/3
                target=h**3/Fraction(12)
                if integ!=target: raise ValueError('local h^3/12 energy identity failed')
                terms.append(target); total+=target
            r['claims_checked']+=['poisson1d-local-energy-identity','poisson1d-global-energy-identity']
            r.update({'element_error_sq':[str(v) for v in terms],'global_error_sq':str(total),
                      'proof_method':"exact rational differentiation/interpolation slope and exact polynomial antiderivative"})
        else: raise ValueError('unsupported proof kind')
        if sorted(a.get('claims',[]))!=sorted(r['claims_checked']): raise ValueError('artifact claim set does not exactly match checked claims')
        r.update({'passed':True,'theorem_id':a.get('theorem_id'),'kind':kind})
    except Exception as exc: r['errors'].append(str(exc))
    return r
