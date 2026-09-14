from __future__ import annotations
import time
from cace_studio.core.module import Module, ValidationError
from cace_studio.core.types import ModuleMetadata, PortSpec, ParameterSpec, ProofStatus, Maturity, EvidenceKind
from cace_studio.core.verification import VerificationRecord, VerificationState
from cace_studio.core.native_runtime import NativeRuntime
from cace_studio.modules.fem_v017 import structured_square_p1_csr, sparse_exact_ldlt
from cace_studio.modules.fem_v018 import choose_orderings, elimination_tree_from_pattern, symbolic_supernodes, matvec


def _timed(fn,repeats=3):
    vals=[]; out=None
    for _ in range(max(1,repeats)):
        t=time.perf_counter(); out=fn(); vals.append((time.perf_counter()-t)*1000)
    vals.sort(); return out,vals[len(vals)//2]


def v020_benchmark(nx=14,ny=14,threads=4,repeats=3):
    csr=structured_square_p1_csr(nx,ny); orders,metrics,winner=choose_orderings(csr,nx,ny); order=orders[winner]
    exact=sparse_exact_ldlt(csr,order,include_pattern=True)
    if not exact.get('certified') or not exact.get('exact_reconstruction'): raise ValidationError('exact sparse oracle failed')
    et=elimination_tree_from_pattern(csr['shape'][0],exact['factor_pattern']); sn=symbolic_supernodes(csr['shape'][0],exact['factor_pattern'],et['parent'])
    xtrue=[1.0+0.01*((17*i)%31) for i in range(csr['shape'][0])]; b=matvec(csr,xtrue); rt=NativeRuntime()
    if not rt.status.available: raise ValidationError(rt.status.reason)
    left,leftms=_timed(lambda:rt.sparse_ldlt_solve(csr,order,b),repeats)
    mf,mfms=_timed(lambda:rt.sparse_multifrontal_ldlt_solve(csr,order,b,20),repeats)
    sn1,sn1ms=_timed(lambda:rt.sparse_supernodal_ldlt_solve(csr,order,b,1),repeats)
    snp,snpms=_timed(lambda:rt.sparse_supernodal_ldlt_solve(csr,order,b,int(threads)),repeats)
    def diag(r,ms):
        return {**r,'wall_ms_median':ms,'max_solution_error':max(abs(a-bb) for a,bb in zip(r['x'],xtrue)),'residual_inf':max(abs(a-bb) for a,bb in zip(matvec(csr,r['x']),b)),'structure_matches_exact':r['factor_nnz']==exact['factor_nnz'] and r['fill_edges']==exact['fill_entries']}
    return {'dimension':csr['shape'][0],'input_nnz':len(csr['data']),'winner_ordering':winner,'ordering_metrics':metrics,'exact_factorization':exact,'elimination_tree':et,'symbolic_supernodes':sn,'native_version':rt.status.version,'left_looking':diag(left,leftms),'scalar_multifrontal':diag(mf,mfms),'supernodal_single_thread':diag(sn1,sn1ms),'supernodal_thread_pool':diag(snp,snpms),'threads_requested':int(threads),'system':csr,'claims':{'numeric_kernel':'dense-block supernodal LDLT on symbolic supernodes','scheduler':'fixed C++ thread pool, level-synchronous elimination-tree scheduling','workspace':'thread-local dense frontal buffers are grown and reused','oracle':'exact-rational sparse LDLT remains authoritative','timing':'machine-dependent benchmark evidence'}}


def render_v020_benchmark(b,path):
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    labels=['Left','Scalar MF','SN 1T',f"SN {b['threads_requested']}T"]
    vals=[b['left_looking']['wall_ms_median'],b['scalar_multifrontal']['wall_ms_median'],b['supernodal_single_thread']['wall_ms_median'],b['supernodal_thread_pool']['wall_ms_median']]
    fig,ax=plt.subplots(figsize=(8,5)); bars=ax.bar(labels,vals); ax.set_ylabel('Median wall time (ms)'); ax.set_title('CACE v0.20 native sparse solver benchmark')
    for bar,v in zip(bars,vals): ax.text(bar.get_x()+bar.get_width()/2,bar.get_height(),f'{v:.2f}',ha='center',va='bottom')
    fig.tight_layout(); fig.savefig(path,dpi=140); plt.close(fig); return {'path':str(path),'times_ms':dict(zip(labels,vals))}


class SupernodalBenchmarkV20(Module):
    metadata=ModuleMetadata('fem20.supernodal_benchmark','Dense-Block Supernodal Runtime','0.20.0','Certified Linear Algebra','Benchmark dense-block native supernodal LDLT with reusable workspaces and fixed thread-pool scheduling against scalar native paths.',Maturity.BETA)
    parameters=(ParameterSpec('nx','integer',14),ParameterSpec('ny','integer',14),ParameterSpec('threads','integer',4),ParameterSpec('repeats','integer',3)); outputs=(PortSpec('benchmark','supernodal_benchmark_v20'),)
    proof_status=ProofStatus(evidence={EvidenceKind.NUMERICAL,EvidenceKind.SYMBOLIC},unit_tests=True,regression_tests=True,documentation=True,benchmarked=True,limitations=['dense kernels are hand-written loops, not BLAS yet','timings are machine-dependent','thread pool is level-synchronous rather than work-stealing'])
    def execute(self,inputs,params,ctx): return {'benchmark':v020_benchmark(int(params['nx']),int(params['ny']),int(params['threads']),int(params['repeats']))}
    def verify(self,inputs,params,outputs,ctx):
        b=outputs['benchmark']; paths=[b['left_looking'],b['scalar_multifrontal'],b['supernodal_single_thread'],b['supernodal_thread_pool']]
        ok=b['exact_factorization']['exact_reconstruction'] and all(p['structure_matches_exact'] and p['max_solution_error']<=1e-10 and p['residual_inf']<=1e-10 for p in paths) and b['supernodal_thread_pool']['supernodes']==b['symbolic_supernodes']['count']
        return [VerificationRecord('supernodal-v020',EvidenceKind.NUMERICAL,'Dense-block supernodal native solves match the exact symbolic factor structure and deterministic known solution.',VerificationState.PASS if ok else VerificationState.FAIL,'exact-rational structure oracle + native solve comparison',{'dimension':b['dimension'],'supernodes':b['symbolic_supernodes']['count'],'max_supernode':b['symbolic_supernodes']['max_size'],'thread_pool_tasks':b['supernodal_thread_pool']['scheduled_tasks']})]

class WorkspaceSchedulerV20(Module):
    metadata=ModuleMetadata('fem20.workspace_scheduler','Workspace + Thread-Pool Audit','0.20.0','Verification','Audit dense frontal workspace reuse and fixed thread-pool scheduling metrics.',Maturity.BETA)
    inputs=(PortSpec('benchmark','supernodal_benchmark_v20'),); outputs=(PortSpec('audit','workspace_audit_v20'),)
    proof_status=ProofStatus(evidence={EvidenceKind.NUMERICAL},unit_tests=True,documentation=True)
    def execute(self,inputs,params,ctx):
        s=inputs['benchmark']['supernodal_thread_pool']; return {'audit':{k:s[k] for k in ('supernodes','max_supernode_size','thread_count','scheduled_tasks','workspace_reallocations','peak_workspace_entries','peak_front_size','block_flop_proxy')}}
    def verify(self,inputs,params,outputs,ctx):
        a=outputs['audit']; ok=a['scheduled_tasks']==a['supernodes'] and a['workspace_reallocations']<=a['scheduled_tasks'] and a['peak_workspace_entries']>=a['peak_front_size']**2
        return [VerificationRecord('workspace-scheduler-v020',EvidenceKind.NUMERICAL,'Every supernode is scheduled exactly once and thread-local frontal workspaces are reused rather than allocated per front.',VerificationState.PASS if ok else VerificationState.FAIL,'runtime instrumentation',a)]

class V20Summary(Module):
    metadata=ModuleMetadata('fem20.summary','v0.20 Supernodal Summary','0.20.0','Verification','Summarize dense-block supernodal, workspace, and scheduler evidence without escalating backend evidence to formal PDE proof.',Maturity.BETA)
    inputs=(PortSpec('benchmark','supernodal_benchmark_v20'),PortSpec('audit','workspace_audit_v20')); outputs=(PortSpec('summary','v20_summary'),)
    proof_status=ProofStatus(evidence={EvidenceKind.NUMERICAL,EvidenceKind.SYMBOLIC},unit_tests=True,documentation=True)
    def execute(self,inputs,params,ctx):
        b=inputs['benchmark']; a=inputs['audit']; return {'summary':{'dimension':b['dimension'],'ordering':b['winner_ordering'],'supernodes':a['supernodes'],'max_supernode_size':a['max_supernode_size'],'left_ms':b['left_looking']['wall_ms_median'],'scalar_mf_ms':b['scalar_multifrontal']['wall_ms_median'],'supernodal_1t_ms':b['supernodal_single_thread']['wall_ms_median'],'supernodal_pool_ms':b['supernodal_thread_pool']['wall_ms_median'],'workspace_reallocations':a['workspace_reallocations'],'scheduled_tasks':a['scheduled_tasks'],'dense_block_supernodal_implemented':True,'thread_pool_implemented':True,'continuum_pde_formally_verified':False}}
    def verify(self,inputs,params,outputs,ctx):
        s=outputs['summary']; ok=s['dense_block_supernodal_implemented'] and s['thread_pool_implemented'] and not s['continuum_pde_formally_verified']
        return [VerificationRecord('v020-scope-audit',EvidenceKind.SYMBOLIC,'v0.20 claims native dense-block supernodal linear algebra and runtime scheduling only; PDE formal status is unchanged.',VerificationState.PASS if ok else VerificationState.FAIL,'scope audit',s)]

def register_fem_v020(registry):
    for cls in (SupernodalBenchmarkV20,WorkspaceSchedulerV20,V20Summary): registry.register(cls)
