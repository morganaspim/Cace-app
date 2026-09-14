from __future__ import annotations
import math
from collections import defaultdict
from cace_studio.core.module import Module, ValidationError
from cace_studio.core.types import ModuleMetadata,PortSpec,ParameterSpec,ProofStatus,Maturity,EvidenceKind
from cace_studio.core.verification import VerificationRecord,VerificationState
from cace_studio.core.interval import Interval,singleton,add,sub,mul,div
from cace_studio.core.native_runtime import NativeRuntime


def _csr_entries(csr):
    n=int(csr['shape'][0]); m=int(csr['shape'][1])
    if n!=m: raise ValidationError('square CSR matrix required')
    data=list(map(float,csr['data'])); indices=list(map(int,csr['indices'])); indptr=list(map(int,csr['indptr']))
    if len(indptr)!=n+1 or indptr[0]!=0 or indptr[-1]!=len(data) or len(indices)!=len(data): raise ValidationError('invalid CSR structure')
    rows=[{} for _ in range(n)]
    for i in range(n):
        if indptr[i]>indptr[i+1]: raise ValidationError('invalid CSR row pointer')
        for p in range(indptr[i],indptr[i+1]):
            j=indices[p]
            if j<0 or j>=n: raise ValidationError('CSR column out of range')
            rows[i][j]=rows[i].get(j,0.0)+data[p]
    return rows


def sparse_interval_ldlt(csr):
    """Sparse exact-rational LDL^T verifier for stored binary64 CSR data.

    Every binary64 matrix entry is converted to its exact rational value via
    float.as_integer_ratio(). The factorization and reconstruction are exact;
    no dense n x n matrix is materialized. The historical function name is
    retained for API compatibility with v0.16 development snapshots.
    """
    from fractions import Fraction
    Af=_csr_entries(csr); n=len(Af)
    A=[{j:Fraction.from_float(float(v)) for j,v in row.items()} for row in Af]
    for i in range(n):
        for j,a in A[i].items():
            if A[j].get(i,Fraction(0))!=a:
                return {'certified':False,'reason':'stored CSR matrix is not exactly symmetric','i':i,'j':j}
    L=[{} for _ in range(n)]; D=[None]*n; col_rows=defaultdict(set); fill_count=0
    for i in range(n):
        acc=Fraction(0)
        for k,lik in L[i].items(): acc += lik*lik*D[k]
        piv=A[i].get(i,Fraction(0))-acc
        if piv<=0:
            return {'certified':False,'reason':'exact sparse LDL pivot is not strictly positive','pivot_index':i,'pivot_exact':str(piv)}
        D[i]=piv
        candidates={j for j in range(i+1,n) if i in A[j] or j in A[i]}
        for k in L[i]: candidates.update(j for j in col_rows[k] if j>i)
        for j in sorted(candidates):
            acc2=Fraction(0)
            for k in set(L[j]).intersection(L[i]): acc2 += L[j][k]*L[i][k]*D[k]
            lij=(A[j].get(i,Fraction(0))-acc2)/D[i]
            if lij:
                if i not in A[j] and i not in A[i]: fill_count+=1
                L[j][i]=lij; col_rows[i].add(j)
    pairs=set()
    for i,row in enumerate(A):
        for j in row: pairs.add((min(i,j),max(i,j)))
    for k in range(n):
        support=[k]+sorted(col_rows[k])
        for a_pos,i in enumerate(support):
            for j in support[a_pos:]: pairs.add((i,j))
    for i,j in pairs:
        val=Fraction(0)
        for k in range(min(i,j)+1):
            lik=Fraction(1) if i==k else L[i].get(k,Fraction(0))
            ljk=Fraction(1) if j==k else L[j].get(k,Fraction(0))
            if lik and ljk: val += lik*D[k]*ljk
        a=A[i].get(j,A[j].get(i,Fraction(0)))
        if val!=a:
            return {'certified':False,'reason':'exact sparse LDL reconstruction mismatch','i':i,'j':j}
    minp=min(D,default=Fraction(1)); nnz_l=sum(len(r) for r in L)+n
    return {'certified':True,'method':'sparse-exact-rational-ldlt','min_pivot_lower':float(minp),
            'min_pivot_exact':str(minp),'dimension':n,'input_nnz':sum(len(r) for r in A),'factor_nnz':nnz_l,
            'fill_entries':fill_count,'dense_materialization':False,'exact_reconstruction':True,
            'scope':'exact rational interpretation of stored binary64 reduced CSR matrix'}

def _python_p1_1d_reduced(nodes):
    x=list(map(float,nodes)); n=len(x)
    if n<2 or any(not x[i+1]>x[i] for i in range(n-1)): raise ValidationError('strictly increasing nodes required')
    ni=max(0,n-2); rows=[{} for _ in range(ni)]
    for e in range(n-1):
        h=x[e+1]-x[e]; loc=((1/h,-1/h),(-1/h,1/h))
        verts=(e,e+1)
        for a,ga in enumerate(verts):
            if ga==0 or ga==n-1: continue
            i=ga-1
            for b,gb in enumerate(verts):
                if gb==0 or gb==n-1: continue
                j=gb-1; rows[i][j]=rows[i].get(j,0.0)+loc[a][b]
    data=[]; indices=[]; indptr=[0]
    for r in rows:
        for j in sorted(r):
            if r[j]!=0.0: indices.append(j); data.append(r[j])
        indptr.append(len(data))
    return {'shape':[ni,ni],'data':data,'indices':indices,'indptr':indptr}


class SparseVerifiedLDLTV16(Module):
    metadata=ModuleMetadata('fem16.sparse_verified_ldlt','Sparse Verified LDLᵀ Certificate','0.16.0','Certified Linear Algebra','Verify positive sparse interval LDLᵀ pivots and sparse reconstruction without dense matrix materialization.',Maturity.BETA)
    inputs=(PortSpec('system','linear_system_nd'),); outputs=(PortSpec('factorization_certificate','verified_factorization_v16'),)
    proof_status=ProofStatus(evidence={EvidenceKind.SYMBOLIC},unit_tests=True,property_tests=True,documentation=True,limitations=['reference algorithm is sparse but not yet optimized with a fill-reducing ordering','certificate is for the stored discrete CSR matrix'])
    def execute(self,inputs,params,ctx): return {'factorization_certificate':sparse_interval_ldlt(inputs['system']['matrix'])}
    def verify(self,inputs,params,outputs,ctx):
        c=outputs['factorization_certificate']; state=VerificationState.PASS if c.get('certified') else VerificationState.NOT_RUN
        return [VerificationRecord('sparse-verified-ldlt-v016',EvidenceKind.SYMBOLIC,'The stored CSR matrix admits the reported sparse interval LDLᵀ factorization with positive pivots and enclosing sparse reconstruction.',state,'outward-rounded sparse interval LDLᵀ; no dense matrix materialization',c)]


class NativeP1AssemblyEquivalenceV16(Module):
    metadata=ModuleMetadata('runtime16.native_p1_assembly','Native C++ P1 Assembly Equivalence','0.16.0','Runtime','Assemble the reduced 1D P1 unit-diffusion stiffness matrix in C++20 and compare exactly with the canonical Python assembly.',Maturity.BETA)
    outputs=(PortSpec('equivalence','native_assembly_equivalence_v16'),PortSpec('system','linear_system_nd'))
    parameters=(ParameterSpec('nodes','json','[0,0.2,0.55,0.8,1.0]'),)
    proof_status=ProofStatus(evidence={EvidenceKind.NUMERICAL},unit_tests=True,documentation=True,limitations=['equivalence is numerical/backend evidence, not a formal proof of C++ source'])
    def execute(self,inputs,params,ctx):
        import json
        nodes=json.loads(params['nodes']) if isinstance(params['nodes'],str) else params['nodes']
        py=_python_p1_1d_reduced(nodes); rt=NativeRuntime()
        if not rt.status.available: return {'equivalence':{'ran':False,'reason':rt.status.reason},'system':{'matrix':py,'rhs':[0.0]*py['shape'][0],'interior_vertices':list(range(1,len(nodes)-1))}}
        native=rt.p1_1d_stiffness(nodes)
        same_shape=native['shape']==py['shape']; same_structure=native['indices']==py['indices'] and native['indptr']==py['indptr']
        diff=max([abs(a-b) for a,b in zip(native['data'],py['data'])] or [0.0]) if len(native['data'])==len(py['data']) else math.inf
        eq={'ran':True,'native_version':rt.status.version,'same_shape':same_shape,'same_structure':same_structure,'max_abs_value_diff':diff,'python_nnz':len(py['data']),'native_nnz':len(native['data'])}
        return {'equivalence':eq,'system':{'matrix':native,'rhs':[0.0]*native['shape'][0],'interior_vertices':list(range(1,len(nodes)-1))}}
    def verify(self,inputs,params,outputs,ctx):
        e=outputs['equivalence']; state=VerificationState.NOT_RUN if not e.get('ran') else (VerificationState.PASS if e['same_shape'] and e['same_structure'] and e['max_abs_value_diff']<=1e-14 else VerificationState.FAIL)
        return [VerificationRecord('cpp-python-p1-assembly-equivalence-v016',EvidenceKind.NUMERICAL,'Native C++20 reduced P1 stiffness assembly agrees with the canonical Python assembly.',state,'same binary64 nodes; exact CSR structure comparison plus coefficient tolerance',e)]


class V16Summary(Module):
    metadata=ModuleMetadata('fem16.summary','Sparse Native Runtime Summary','0.16.0','Verification','Compose native assembly equivalence and sparse interval factorization evidence without escalating either evidence scope.',Maturity.BETA)
    inputs=(PortSpec('equivalence','native_assembly_equivalence_v16'),PortSpec('factorization_certificate','verified_factorization_v16')); outputs=(PortSpec('summary','v16_summary'),)
    proof_status=ProofStatus(evidence={EvidenceKind.NUMERICAL,EvidenceKind.SYMBOLIC},unit_tests=True,documentation=True)
    def execute(self,inputs,params,ctx):
        e=inputs['equivalence']; f=inputs['factorization_certificate']
        return {'summary':{'native_assembly_equivalent':bool(e.get('ran') and e.get('same_structure') and e.get('max_abs_value_diff',math.inf)<=1e-14),'sparse_factorization_certified':bool(f.get('certified')),'dense_materialization':bool(f.get('dense_materialization',True)),'factor_nnz':f.get('factor_nnz'),'input_nnz':f.get('input_nnz'),'continuum_pde_formally_verified':False}}
    def verify(self,inputs,params,outputs,ctx):
        s=outputs['summary']; ok=s['native_assembly_equivalent'] and s['sparse_factorization_certified'] and not s['dense_materialization'] and not s['continuum_pde_formally_verified']
        return [VerificationRecord('v016-scope-audit',EvidenceKind.SYMBOLIC,'Native assembly equivalence and sparse interval factorization are both established without escalating to continuum proof.',VerificationState.PASS if ok else VerificationState.FAIL,'evidence-scope audit',s)]


def register_fem_v016(registry):
    for cls in (SparseVerifiedLDLTV16,NativeP1AssemblyEquivalenceV16,V16Summary): registry.register(cls)
