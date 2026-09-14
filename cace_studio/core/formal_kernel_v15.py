from __future__ import annotations
from fractions import Fraction
from typing import Any
import hashlib,json

KERNEL_NAME='cace-exact-assembly-kernel'
KERNEL_VERSION='0.15.0'
SCHEMA='cace-formal-assembly-proof-v3'

def _sha(v:Any)->str:
    return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def _q(x):
    if isinstance(x,int): return Fraction(x)
    if isinstance(x,str): return Fraction(x)
    raise ValueError('exact rational must be integer or string')
def _zero(n,m=None):
    m=n if m is None else m
    return [[Fraction(0) for _ in range(m)] for _ in range(n)]
def _transpose(A): return [list(r) for r in zip(*A)]
def _matvec(A,x): return [sum((a*b for a,b in zip(row,x)),Fraction(0)) for row in A]
def _quad(A,x): return sum((x[i]*A[i][j]*x[j] for i in range(len(x)) for j in range(len(x))),Fraction(0))

def assembly_artifact()->dict[str,Any]:
    return {
      'schema':SCHEMA,'kind':'p1-assembly-1d','theorem_id':'p1-global-assembly-invariants-1d-v015',
      'nodes':['0','1/6','2/5','3/4','1'],
      'claims':['local-row-sum-zero','global-symmetry','global-constant-nullspace','dirichlet-reduction-spd'],
      'statement':'Exact P1 element matrices assemble to a symmetric global stiffness matrix with constant nullspace before boundary elimination; homogeneous endpoint Dirichlet elimination yields an SPD interior matrix.',
      'scope':'supplied strictly increasing exact rational 1D mesh; unit diffusion'
    }

def check_artifact(a:dict[str,Any])->dict[str,Any]:
    r={'checker':KERNEL_NAME,'checker_version':KERNEL_VERSION,'artifact_sha256':_sha(a),'passed':False,'claims_checked':[],'errors':[]}
    try:
        if a.get('schema')!=SCHEMA: raise ValueError('unsupported proof schema')
        if a.get('kind')!='p1-assembly-1d': raise ValueError('unsupported proof kind')
        x=[_q(v) for v in a['nodes']]
        if len(x)<3 or any(x[i+1]<=x[i] for i in range(len(x)-1)): raise ValueError('mesh nodes must be strictly increasing')
        n=len(x); K=_zero(n); locals_out=[]
        for e,(aa,bb) in enumerate(zip(x[:-1],x[1:])):
            h=bb-aa
            ke=[[1/h,-1/h],[-1/h,1/h]]
            if any(sum(row,Fraction(0))!=0 for row in ke): raise ValueError('local row sum identity failed')
            locals_out.append([[str(v) for v in row] for row in ke])
            K[e][e]+=ke[0][0]; K[e][e+1]+=ke[0][1]; K[e+1][e]+=ke[1][0]; K[e+1][e+1]+=ke[1][1]
        r['claims_checked'].append('local-row-sum-zero')
        if K!=_transpose(K): raise ValueError('global symmetry failed')
        r['claims_checked'].append('global-symmetry')
        one=[Fraction(1)]*n
        if any(v!=0 for v in _matvec(K,one)): raise ValueError('constant nullspace failed')
        r['claims_checked'].append('global-constant-nullspace')
        Kr=[row[1:-1] for row in K[1:-1]]; m=n-2
        # Exact LDL^T positivity proves SPD for this reduced matrix.
        L=_zero(m); D=[Fraction(0)]*m
        for i in range(m):
            L[i][i]=Fraction(1)
            D[i]=Kr[i][i]-sum((L[i][k]*L[i][k]*D[k] for k in range(i)),Fraction(0))
            if D[i]<=0: raise ValueError('nonpositive exact LDL pivot after Dirichlet elimination')
            for j in range(i+1,m):
                num=Kr[j][i]-sum((L[j][k]*L[i][k]*D[k] for k in range(i)),Fraction(0))
                L[j][i]=num/D[i]
        # Reconstruct exactly.
        rec=_zero(m)
        for i in range(m):
            for j in range(m):
                rec[i][j]=sum((L[i][k]*D[k]*L[j][k] for k in range(min(i,j)+1)),Fraction(0))
        if rec!=Kr: raise ValueError('exact LDL reconstruction failed')
        r['claims_checked'].append('dirichlet-reduction-spd')
        if sorted(a.get('claims',[]))!=sorted(r['claims_checked']): raise ValueError('artifact claim set does not exactly match checked claims')
        r.update({'passed':True,'theorem_id':a.get('theorem_id'),'kind':a.get('kind'),
                  'local_matrices':locals_out,'global_stiffness':[[str(v) for v in row] for row in K],
                  'reduced_stiffness':[[str(v) for v in row] for row in Kr],
                  'ldlt_pivots':[str(v) for v in D],
                  'proof_method':'exact rational element assembly + matrix identities + exact LDL^T positive pivots'})
    except Exception as exc: r['errors'].append(str(exc))
    return r
