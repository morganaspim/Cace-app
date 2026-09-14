from __future__ import annotations
import time
from cace_studio.core.module import Module, ValidationError
from cace_studio.core.types import ModuleMetadata, PortSpec, ParameterSpec, ProofStatus, Maturity, EvidenceKind
from cace_studio.core.verification import VerificationRecord, VerificationState
from cace_studio.core.native_runtime import NativeRuntime
from cace_studio.modules.fem_v017 import structured_square_p1_csr, sparse_exact_ldlt
from cace_studio.modules.fem_v018 import choose_orderings, elimination_tree_from_pattern, symbolic_supernodes, matvec


def _timed(fn, repeats=3):
    vals=[]; out=None
    for _ in range(max(1,repeats)):
        t=time.perf_counter(); out=fn(); vals.append((time.perf_counter()-t)*1000.0)
    vals.sort()
    return out, vals[len(vals)//2]


def v019_benchmark(nx=14, ny=14, parallel_depth=10, repeats=3):
    csr=structured_square_p1_csr(nx,ny)
    orders,metrics,winner=choose_orderings(csr,nx,ny)
    order=orders[winner]
    exact=sparse_exact_ldlt(csr,order,include_pattern=True)
    if not exact.get('certified') or not exact.get('exact_reconstruction'):
        raise ValidationError('exact sparse oracle failed')
    etree=elimination_tree_from_pattern(csr['shape'][0],exact['factor_pattern'])
    supers=symbolic_supernodes(csr['shape'][0],exact['factor_pattern'],etree['parent'])
    x_true=[1.0+0.01*((17*i)%31) for i in range(csr['shape'][0])]
    b=matvec(csr,x_true)
    rt=NativeRuntime()
    if not rt.status.available:
        raise ValidationError(f'native runtime unavailable: {rt.status.reason}')
    left,left_ms=_timed(lambda:rt.sparse_ldlt_solve(csr,order,b),repeats)
    mf_seq,mf_seq_ms=_timed(lambda:rt.sparse_multifrontal_ldlt_solve(csr,order,b,0),repeats)
    mf_par,mf_par_ms=_timed(lambda:rt.sparse_multifrontal_ldlt_solve(csr,order,b,int(parallel_depth)),repeats)

    def diag(sol, wall_ms):
        err=max((abs(a-bb) for a,bb in zip(sol['x'],x_true)),default=0.0)
        resid=max((abs(a-bb) for a,bb in zip(matvec(csr,sol['x']),b)),default=0.0)
        # portable storage proxies; not process RSS measurements.
        factor_storage_bytes=(int(sol['factor_nnz'])*12)+(csr['shape'][0]*8)
        d={**sol,'wall_ms_median':wall_ms,'max_solution_error':err,'residual_inf':resid,
           'structure_matches_exact':int(sol['factor_nnz'])==int(exact['factor_nnz']) and int(sol['fill_edges'])==int(exact['fill_entries']),
           'factor_storage_proxy_bytes':factor_storage_bytes}
        if 'peak_front_size' in sol:
            d['peak_front_dense_proxy_bytes']=int(sol['peak_front_size'])**2*8
            d['front_work_proxy_entries']=int(sol['total_front_entries'])
        return d
    left=diag(left,left_ms); mf_seq=diag(mf_seq,mf_seq_ms); mf_par=diag(mf_par,mf_par_ms)
    return {
        'dimension':csr['shape'][0],'input_nnz':len(csr['data']),'nx':nx,'ny':ny,
        'winner_ordering':winner,'ordering_metrics':metrics,'exact_factorization':exact,
        'elimination_tree':etree,'supernodes':supers,'native_version':rt.status.version,
        'left_looking':left,'multifrontal_sequential':mf_seq,'multifrontal_parallel':mf_par,
        'parallel_depth':int(parallel_depth),'repeats':int(repeats),'system':csr,
        'claims':{
            'numeric_kernel':'scalar multifrontal LDLT with elimination-tree Schur contribution assembly',
            'supernodes':'symbolic structural aggregation only; numeric dense-block supernodal factorization is not claimed',
            'parallelism':'independent elimination-tree child subtrees may execute via std::async',
            'timing':'median Python-observed wall time over repeats; benchmark evidence, not a performance theorem',
            'memory':'portable structural proxies, not operating-system peak RSS'
        }
    }


def render_v019_benchmark(benchmark, path):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    labels=['Left-looking','MF sequential','MF parallel']
    times=[benchmark['left_looking']['wall_ms_median'],benchmark['multifrontal_sequential']['wall_ms_median'],benchmark['multifrontal_parallel']['wall_ms_median']]
    fig,ax=plt.subplots(figsize=(8,5))
    bars=ax.bar(labels,times)
    ax.set_ylabel('Median wall time (ms)')
    ax.set_title('CACE v0.19 native sparse solve benchmark')
    for bar,val in zip(bars,times): ax.text(bar.get_x()+bar.get_width()/2,bar.get_height(),f'{val:.2f}',ha='center',va='bottom')
    fig.tight_layout(); fig.savefig(path,dpi=140); plt.close(fig)
    return {'path':str(path),'times_ms':dict(zip(labels,times))}


class MultifrontalBenchmarkV19(Module):
    metadata=ModuleMetadata('fem19.multifrontal_benchmark','Native Multifrontal Benchmark','0.19.0','Certified Linear Algebra','Compare native left-looking and scalar multifrontal sparse LDLT on the exact-oracle factor structure, including sequential and parallel subtree execution.',Maturity.BETA)
    parameters=(ParameterSpec('nx','integer',14),ParameterSpec('ny','integer',14),ParameterSpec('parallel_depth','integer',20),ParameterSpec('repeats','integer',3))
    outputs=(PortSpec('benchmark','multifrontal_benchmark_v19'),)
    proof_status=ProofStatus(evidence={EvidenceKind.SYMBOLIC,EvidenceKind.NUMERICAL},unit_tests=True,regression_tests=True,documentation=True,benchmarked=True,limitations=['multifrontal numeric kernel is scalar-front, not dense-block supernodal','timing is machine-dependent','memory values are structural proxies rather than peak RSS'])
    def execute(self,inputs,params,ctx): return {'benchmark':v019_benchmark(int(params['nx']),int(params['ny']),int(params['parallel_depth']),int(params['repeats']))}
    def verify(self,inputs,params,outputs,ctx):
        b=outputs['benchmark']; paths=[b['left_looking'],b['multifrontal_sequential'],b['multifrontal_parallel']]
        ok=b['exact_factorization']['certified'] and b['exact_factorization']['exact_reconstruction'] and all(p['structure_matches_exact'] and p['max_solution_error']<=1e-10 and p['residual_inf']<=1e-10 for p in paths)
        return [VerificationRecord('multifrontal-v019',EvidenceKind.NUMERICAL,'Native left-looking, sequential multifrontal, and parallel-subtree multifrontal solves agree with the exact symbolic factor structure and deterministic known solution.',VerificationState.PASS if ok else VerificationState.FAIL,'exact-rational structure oracle + native solve comparison',{'dimension':b['dimension'],'ordering':b['winner_ordering'],'left_ms':b['left_looking']['wall_ms_median'],'mf_seq_ms':b['multifrontal_sequential']['wall_ms_median'],'mf_par_ms':b['multifrontal_parallel']['wall_ms_median'],'parallel_tasks':b['multifrontal_parallel'].get('parallel_tasks',0)})]


class FrontTreeAnalysisV19(Module):
    metadata=ModuleMetadata('fem19.front_tree_analysis','Elimination Tree + Supernode Analysis','0.19.0','Verification','Record elimination-tree depth, symbolic supernodes, front working-set proxies, and subtree parallelism metrics for the certified factor pattern.',Maturity.BETA)
    inputs=(PortSpec('benchmark','multifrontal_benchmark_v19'),); outputs=(PortSpec('analysis','front_tree_analysis_v19'),)
    proof_status=ProofStatus(evidence={EvidenceKind.SYMBOLIC},unit_tests=True,documentation=True,limitations=['supernodes are symbolic groups only'])
    def execute(self,inputs,params,ctx):
        b=inputs['benchmark']; p=b['multifrontal_parallel']; return {'analysis':{'tree_height':b['elimination_tree']['height'],'tree_max_children':b['elimination_tree']['max_children'],'supernode_count':b['supernodes']['count'],'max_supernode_size':b['supernodes']['max_size'],'mean_supernode_size':b['supernodes']['mean_size'],'peak_front_size':p['peak_front_size'],'total_front_entries':p['total_front_entries'],'parallel_tasks':p['parallel_tasks'],'factor_nnz':p['factor_nnz'],'fill_edges':p['fill_edges']}}
    def verify(self,inputs,params,outputs,ctx):
        a=outputs['analysis']; ok=a['tree_height']>=1 and a['supernode_count']>=1 and a['peak_front_size']>=1 and a['total_front_entries']>=a['peak_front_size']**2
        return [VerificationRecord('front-tree-v019',EvidenceKind.SYMBOLIC,'Elimination-tree, symbolic-supernode, and frontal working-set metrics are derived from the exact certified factor pattern.',VerificationState.PASS if ok else VerificationState.FAIL,'symbolic factor pattern analysis',a)]


class V19Summary(Module):
    metadata=ModuleMetadata('fem19.summary','v0.19 Multifrontal Summary','0.19.0','Verification','Summarize exact structural evidence and native multifrontal benchmark evidence without escalating backend results to formal or continuum-PDE proof.',Maturity.BETA)
    inputs=(PortSpec('benchmark','multifrontal_benchmark_v19'),PortSpec('analysis','front_tree_analysis_v19')); outputs=(PortSpec('summary','v19_summary'),)
    proof_status=ProofStatus(evidence={EvidenceKind.SYMBOLIC,EvidenceKind.NUMERICAL},unit_tests=True,documentation=True)
    def execute(self,inputs,params,ctx):
        b=inputs['benchmark']; a=inputs['analysis']; return {'summary':{'dimension':b['dimension'],'ordering':b['winner_ordering'],'fill_edges':b['exact_factorization']['fill_entries'],'factor_nnz':b['exact_factorization']['factor_nnz'],'left_ms':b['left_looking']['wall_ms_median'],'multifrontal_sequential_ms':b['multifrontal_sequential']['wall_ms_median'],'multifrontal_parallel_ms':b['multifrontal_parallel']['wall_ms_median'],'parallel_tasks':a['parallel_tasks'],'peak_front_size':a['peak_front_size'],'supernodes':a['supernode_count'],'native_multifrontal_verified_against_exact_structure':True,'numeric_supernodal_factorization_implemented':False,'continuum_pde_formally_verified':False}}
    def verify(self,inputs,params,outputs,ctx):
        s=outputs['summary']; ok=s['native_multifrontal_verified_against_exact_structure'] and not s['numeric_supernodal_factorization_implemented'] and not s['continuum_pde_formally_verified']
        return [VerificationRecord('v019-scope-audit',EvidenceKind.SYMBOLIC,'v0.19 claims scalar multifrontal numeric factorization and symbolic supernode analysis only; continuum PDE formal status is unchanged.',VerificationState.PASS if ok else VerificationState.FAIL,'scope audit',s)]


def register_fem_v019(registry):
    for cls in (MultifrontalBenchmarkV19,FrontTreeAnalysisV19,V19Summary): registry.register(cls)
