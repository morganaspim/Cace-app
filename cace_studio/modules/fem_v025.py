from __future__ import annotations
from cace_studio.core.module import Module
from cace_studio.core.types import ModuleMetadata, PortSpec, ParameterSpec, ProofStatus, Maturity, EvidenceKind
from cace_studio.core.verification import VerificationRecord, VerificationState
from cace_studio.modules.fem_v020 import v020_benchmark
from cace_studio.modules.fem_v022 import v022_memory_audit
from cace_studio.modules.fem_v023 import gpu_dense_equivalence
from cace_studio.modules.fem_v024 import scaling_suite

def select_solver(benchmark, gpu=None, memory_budget_bytes=None):
    candidates={
      'left_looking':benchmark['left_looking']['wall_ms_median'],
      'scalar_multifrontal':benchmark['scalar_multifrontal']['wall_ms_median'],
      'supernodal_single_thread':benchmark['supernodal_single_thread']['wall_ms_median'],
      'supernodal_thread_pool':benchmark['supernodal_thread_pool']['wall_ms_median']}
    eligible={k:v for k,v in candidates.items() if benchmark[k]['structure_matches_exact'] and benchmark[k]['max_solution_error']<=1e-10 and benchmark[k]['residual_inf']<=1e-10}
    choice=min(eligible,key=eligible.get)
    reasons=['candidate passed exact-structure and known-solution checks','selected by measured median wall time among eligible native CPU paths']
    if memory_budget_bytes is not None:
        est=benchmark['supernodal_thread_pool']['peak_workspace_entries']*8*benchmark['supernodal_thread_pool']['thread_count']
        if choice=='supernodal_thread_pool' and est>memory_budget_bytes:
            choice=min({k:v for k,v in eligible.items() if k!='supernodal_thread_pool'},key=lambda k:eligible[k]); reasons.append('thread-pool supernodal rejected by declared workspace budget')
    if gpu and gpu.get('available') and gpu.get('passed'): reasons.append('GPU dense-kernel equivalence is available, but v0.25 does not auto-route the full sparse solve to GPU')
    return {'selected':choice,'eligible':eligible,'reasons':reasons,'gpu_full_solver_selected':False}

def v025_consolidated(nx=14,ny=14,threads=4,repeats=1):
    b=v020_benchmark(nx,ny,threads,repeats); mem=v022_memory_audit(nx,ny,threads,repeats); gpu=gpu_dense_equivalence(24); stress=scaling_suite((7,10,14)); sel=select_solver(b,gpu)
    return {'release':'0.25.0','benchmark':b,'memory':mem,'gpu':gpu,'scaling':stress,'selection':sel,'scope':{'continuum_pde_formally_verified':False,'native_backend_evidence':'numerical','exact_sparse_factor_evidence':'symbolic/exact'}}

class AutoSolverPolicyV25(Module):
    metadata=ModuleMetadata('fem25.auto_solver','Evidence-Aware Solver Selection','0.25.0','Runtime','Select among verified native CPU solver paths using measured performance and declared resource constraints.',Maturity.BETA)
    parameters=(ParameterSpec('nx','integer',14),ParameterSpec('ny','integer',14),ParameterSpec('threads','integer',4)); outputs=(PortSpec('report','v25_report'),)
    proof_status=ProofStatus(evidence={EvidenceKind.NUMERICAL,EvidenceKind.SYMBOLIC},unit_tests=True,regression_tests=True,documentation=True,benchmarked=True,limitations=['selection uses local benchmark timing','full sparse GPU solve is not auto-selected','PDE formal status is unchanged'])
    def execute(self,inputs,params,ctx): return {'report':v025_consolidated(int(params['nx']),int(params['ny']),int(params['threads']))}
    def verify(self,inputs,params,outputs,ctx):
        r=outputs['report']; s=r['selection']; ok=s['selected'] in s['eligible'] and r['scaling']['all_certified'] and not r['scope']['continuum_pde_formally_verified']
        return [VerificationRecord('auto-solver-v025',EvidenceKind.NUMERICAL,'Solver selection considers only paths that pass exact-structure and known-solution checks.',VerificationState.PASS if ok else VerificationState.FAIL,'evidence-gated policy',{'selected':s['selected'],'eligible':list(s['eligible'])})]

def register_fem_v025(registry): registry.register(AutoSolverPolicyV25)
