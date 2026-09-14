from __future__ import annotations
import math
from cace_studio.core.module import Module, ValidationError
from cace_studio.core.types import ModuleMetadata, PortSpec, ParameterSpec, ProofStatus, Maturity, EvidenceKind
from cace_studio.core.verification import VerificationRecord, VerificationState
from cace_studio.core.native_runtime import NativeRuntime
from cace_studio.modules.fem_v017 import (
    structured_square_p1_csr, symbolic_elimination, minimum_degree_ordering,
    sparse_exact_ldlt, _symbolic_lower_pattern,
)


def geometric_nested_dissection_order(nx:int, ny:int):
    """Nested-dissection order for the (nx-1)x(ny-1) interior structured grid.
    Subdomains are eliminated before separators; tie-breaking is deterministic.
    """
    mx,my=nx-1,ny-1
    if mx<1 or my<1: return []
    def idx(i,j): return (j-1)*mx+(i-1)
    def rec(xs,ys):
        if not xs or not ys: return []
        if len(xs)*len(ys)<=4:
            return [idx(i,j) for j in ys for i in xs]
        if len(xs)>=len(ys):
            k=len(xs)//2; sep=xs[k]
            left=xs[:k]; right=xs[k+1:]
            return rec(left,ys)+rec(right,ys)+[idx(sep,j) for j in ys]
        k=len(ys)//2; sep=ys[k]
        bot=ys[:k]; top=ys[k+1:]
        return rec(xs,bot)+rec(xs,top)+[idx(i,sep) for i in xs]
    out=rec(list(range(1,nx)),list(range(1,ny)))
    if sorted(out)!=list(range(mx*my)): raise RuntimeError('nested dissection failed to generate permutation')
    return out


def elimination_tree_from_pattern(n:int, factor_pattern):
    # factor_pattern entries are [row, col] with row>col.
    col_rows=[[] for _ in range(n)]
    for i,j in factor_pattern:
        if i>j: col_rows[j].append(i)
    parent=[-1]*n
    for j,rows in enumerate(col_rows):
        if rows: parent[j]=min(rows)
    children=[[] for _ in range(n)]
    roots=[]
    for j,p in enumerate(parent):
        if p<0: roots.append(j)
        else: children[p].append(j)
    def depth(v):
        d=0; seen=set()
        while parent[v]>=0:
            if v in seen: raise RuntimeError('cycle in elimination tree')
            seen.add(v);v=parent[v];d+=1
        return d
    depths=[depth(i) for i in range(n)]
    return {'parent':parent,'roots':roots,'height':max(depths,default=0)+1,'max_children':max((len(c) for c in children),default=0)}


def symbolic_supernodes(n:int, factor_pattern, parent):
    cols=[set() for _ in range(n)]
    for i,j in factor_pattern:
        if i>j: cols[j].add(i)
    groups=[]; j=0
    while j<n:
        g=[j]
        while j+1<n:
            # classical structural sufficient condition for merging consecutive cols
            if parent[j] != j+1: break
            tail_j={r for r in cols[j] if r>j+1}
            tail_next={r for r in cols[j+1] if r>j+1}
            if tail_j != tail_next: break
            j+=1;g.append(j)
        groups.append(g);j+=1
    return {'groups':groups,'count':len(groups),'max_size':max((len(g) for g in groups),default=0),'mean_size':(sum(map(len,groups))/len(groups) if groups else 0.0)}


def choose_orderings(csr,nx,ny):
    n=csr['shape'][0]
    orders={
        'natural':list(range(n)),
        'minimum-degree':minimum_degree_ordering(csr),
        'nested-dissection':geometric_nested_dissection_order(nx,ny),
    }
    metrics={k:symbolic_elimination(csr,o) for k,o in orders.items()}
    winner=min(orders,key=lambda k:(metrics[k]['fill_edges'],metrics[k]['factor_nnz'],k))
    return orders,metrics,winner


def matvec(csr,x):
    y=[]
    for i in range(csr['shape'][0]):
        s=0.0
        for p in range(csr['indptr'][i],csr['indptr'][i+1]): s+=csr['data'][p]*x[csr['indices'][p]]
        y.append(s)
    return y


def v018_benchmark(nx=12,ny=12):
    csr=structured_square_p1_csr(nx,ny)
    orders,metrics,winner=choose_orderings(csr,nx,ny)
    exact=sparse_exact_ldlt(csr,orders[winner],include_pattern=True)
    if not exact.get('certified'): raise ValidationError(f'exact factorization failed: {exact.get("reason")}')
    etree=elimination_tree_from_pattern(csr['shape'][0],exact['factor_pattern'])
    supers=symbolic_supernodes(csr['shape'][0],exact['factor_pattern'],etree['parent'])
    x_true=[1.0+0.01*((17*i)%31) for i in range(csr['shape'][0])]
    b=matvec(csr,x_true)
    rt=NativeRuntime(); native={'ran':False,'reason':rt.status.reason}
    if rt.status.available:
        try:
            sol=rt.sparse_ldlt_solve(csr,orders[winner],b)
            err=max((abs(a-bb) for a,bb in zip(sol['x'],x_true)),default=0.0)
            resid=max((abs(v) for v in [a-bb for a,bb in zip(matvec(csr,sol['x']),b)]),default=0.0)
            native={'ran':True,'version':rt.status.version,**sol,'max_solution_error':err,'residual_inf':resid,
                    'structure_matches_exact':sol['factor_nnz']==exact['factor_nnz'] and sol['fill_edges']==exact['fill_entries']}
        except Exception as e: native={'ran':False,'reason':str(e)}
    return {'dimension':csr['shape'][0],'input_nnz':len(csr['data']),'nx':nx,'ny':ny,
            'orders':orders,'metrics':metrics,'winner':winner,'exact_factorization':exact,
            'elimination_tree':etree,'supernodes':supers,'native_solve':native,'system':csr}


class OrderingAndTreeV18(Module):
    metadata=ModuleMetadata('fem18.ordering_tree','Nested Dissection + Elimination Tree','0.18.0','Certified Linear Algebra','Benchmark natural, minimum-degree, and geometric nested-dissection orderings; certify the winner with exact sparse LDLᵀ and derive elimination-tree/supernode structure.',Maturity.BETA)
    parameters=(ParameterSpec('nx','integer',12),ParameterSpec('ny','integer',12)); outputs=(PortSpec('benchmark','ordering_benchmark_v18'),)
    proof_status=ProofStatus(evidence={EvidenceKind.SYMBOLIC,EvidenceKind.NUMERICAL},unit_tests=True,documentation=True,limitations=['nested dissection is geometric for structured 2D grids','minimum-degree is not AMD','supernodes are symbolic structural groups, not a supernodal numeric factorization'])
    def execute(self,inputs,params,ctx): return {'benchmark':v018_benchmark(int(params['nx']),int(params['ny']))}
    def verify(self,inputs,params,outputs,ctx):
        b=outputs['benchmark']; f=b['exact_factorization']; et=b['elimination_tree']; ok=f['certified'] and f['exact_reconstruction'] and not f['dense_materialization'] and len(et['parent'])==b['dimension'] and sorted(b['orders'][b['winner']])==list(range(b['dimension']))
        return [VerificationRecord('ordering-tree-v018',EvidenceKind.SYMBOLIC,'Winning sparse ordering has an exact reconstructed LDLᵀ factor; elimination tree and symbolic supernodes are derived from that certified factor pattern.',VerificationState.PASS if ok else VerificationState.FAIL,'symbolic elimination + exact rational LDLT',{'winner':b['winner'],'fills':{k:v['fill_edges'] for k,v in b['metrics'].items()},'tree_height':et['height'],'supernodes':b['supernodes']['count']})]


class NativeSparseSolveV18(Module):
    metadata=ModuleMetadata('fem18.native_sparse_solve','Native C++ Sparse LDL Solve','0.18.0','Runtime','Run the C++20 permuted sparse LDLᵀ solve and compare its factor structure, solution, and residual against an exact-factor oracle and deterministic known solution.',Maturity.BETA)
    inputs=(PortSpec('benchmark','ordering_benchmark_v18'),);outputs=(PortSpec('native','native_sparse_solve_v18'),)
    proof_status=ProofStatus(evidence={EvidenceKind.NUMERICAL},unit_tests=True,documentation=True,limitations=['native numeric factorization is left-looking sparse LDLT, not multifrontal','exact-rational Python verifier remains authoritative'])
    def execute(self,inputs,params,ctx): return {'native':inputs['benchmark']['native_solve']}
    def verify(self,inputs,params,outputs,ctx):
        n=outputs['native']; ok=bool(n.get('ran')) and bool(n.get('structure_matches_exact')) and float(n.get('max_solution_error',1.0))<=1e-10 and float(n.get('residual_inf',1.0))<=1e-10
        return [VerificationRecord('native-sparse-solve-v018',EvidenceKind.NUMERICAL,'C++20 sparse solve matches the certified symbolic factor structure and recovers the deterministic solution with small residual.',VerificationState.PASS if ok else VerificationState.FAIL,'native C++ sparse LDLT solve vs exact symbolic structure',n)]


class V18Summary(Module):
    metadata=ModuleMetadata('fem18.summary','v0.18 Ordering + Native Solve Summary','0.18.0','Verification','Summarize ordering, elimination-tree, supernode, exact-factor, and native-solve evidence without escalating it to a continuum PDE theorem.',Maturity.BETA)
    inputs=(PortSpec('benchmark','ordering_benchmark_v18'),PortSpec('native','native_sparse_solve_v18'));outputs=(PortSpec('summary','v18_summary'),)
    proof_status=ProofStatus(evidence={EvidenceKind.SYMBOLIC,EvidenceKind.NUMERICAL},unit_tests=True,documentation=True)
    def execute(self,inputs,params,ctx):
        b=inputs['benchmark']; n=inputs['native']; return {'summary':{'dimension':b['dimension'],'winner':b['winner'],'fill':{k:v['fill_edges'] for k,v in b['metrics'].items()},'factor_nnz':b['exact_factorization']['factor_nnz'],'tree_height':b['elimination_tree']['height'],'supernodes':b['supernodes'],'native_ran':n.get('ran',False),'native_solution_error':n.get('max_solution_error'),'continuum_pde_formally_verified':False}}
    def verify(self,inputs,params,outputs,ctx):
        s=outputs['summary'];ok=s['native_ran'] and not s['continuum_pde_formally_verified']
        return [VerificationRecord('v018-scope-audit',EvidenceKind.SYMBOLIC,'Ordering and native sparse-solve evidence stays scoped to the stored discrete linear system.',VerificationState.PASS if ok else VerificationState.FAIL,'scope audit',s)]


def register_fem_v018(registry):
    for cls in (OrderingAndTreeV18,NativeSparseSolveV18,V18Summary): registry.register(cls)
