from __future__ import annotations
from cace_studio.core.module import Module
from cace_studio.core.types import ModuleMetadata, PortSpec, ParameterSpec, ProofStatus, Maturity, EvidenceKind
from cace_studio.core.verification import VerificationRecord, VerificationState
from cace_studio.modules.fem_v020 import v020_benchmark

def portfolio_score(nx=10,ny=10,threads=4,repeats=1,memory_weight=0.02):
    b=v020_benchmark(nx,ny,threads,repeats); names=['left_looking','scalar_multifrontal','supernodal_single_thread','supernodal_thread_pool']; scores={}; eligible={}
    for name in names:
        r=b[name]; ok=bool(r.get('structure_matches_exact')) and float(r.get('max_solution_error',1))<=1e-10 and float(r.get('residual_inf',1))<=1e-10
        if ok:
            mem=float(r.get('peak_workspace_entries',0))*8.0*max(1,int(r.get('thread_count',1)))
            score=float(r['wall_ms_median'])+float(memory_weight)*(mem/1024.0); scores[name]={'score':score,'wall_ms':r['wall_ms_median'],'workspace_kib':mem/1024.0}; eligible[name]=score
    selected=min(eligible,key=eligible.get)
    return {'release':'0.32.0','selected':selected,'scores':scores,'eligible':sorted(eligible),'memory_weight':memory_weight,'policy':'measured wall time + weighted observed workspace; correctness gate first','scope':'local empirical portfolio policy'}

class PortfolioPolicyV32(Module):
    metadata=ModuleMetadata('fem32.portfolio','Resource-Aware Solver Portfolio','0.32.0','Runtime','Score only correctness-eligible native solvers using local timing plus observed workspace cost.',Maturity.BETA)
    parameters=(ParameterSpec('nx','integer',10),ParameterSpec('ny','integer',10),ParameterSpec('threads','integer',4)); outputs=(PortSpec('result','v32_portfolio'),)
    proof_status=ProofStatus(evidence={EvidenceKind.NUMERICAL},unit_tests=True,documentation=True,limitations=['policy is machine-local and empirical','score weights are user-policy parameters, not theorem constants'])
    def execute(self,inputs,params,ctx): return {'result':portfolio_score(int(params['nx']),int(params['ny']),int(params['threads']))}
    def verify(self,inputs,params,outputs,ctx):
        r=outputs['result']; ok=r['selected'] in r['eligible'] and all(v['score']>=0 for v in r['scores'].values())
        return [VerificationRecord('portfolio-v032',EvidenceKind.NUMERICAL,'Portfolio selects only a solver that passed structure/solution/residual gates.',VerificationState.PASS if ok else VerificationState.FAIL,'correctness-gated resource score',r)]

def register_fem_v032(registry): registry.register(PortfolioPolicyV32)
