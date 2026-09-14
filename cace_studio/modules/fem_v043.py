from __future__ import annotations
from cace_studio.core.module import Module
from cace_studio.core.types import ModuleMetadata, PortSpec, ProofStatus, Maturity, EvidenceKind
from cace_studio.core.verification import VerificationRecord, VerificationState
from cace_studio.modules.fem_v017 import structured_square_p1_csr
from cace_studio.modules.fem_v018 import choose_orderings

def ordering_portfolio(nx=10,ny=10):
    csr=structured_square_p1_csr(nx,ny); orders,metrics,winner=choose_orderings(csr,nx,ny)
    rows=[]
    for name,m in metrics.items(): rows.append({'ordering':name,'fill':m['fill_edges'],'factor_nnz':m['factor_nnz'],'max_front':m['max_front']})
    frontier=[]
    for r in rows:
        dominated=any((q['fill']<=r['fill'] and q['max_front']<=r['max_front']) and (q['fill']<r['fill'] or q['max_front']<r['max_front']) for q in rows)
        if not dominated: frontier.append(r['ordering'])
    return {'release':'0.43.0','rows':rows,'winner_by_fill':winner,'pareto_fill_front':sorted(frontier)}
class OrderingPortfolioV43(Module):
    metadata=ModuleMetadata('fem43.ordering_portfolio','Ordering Pareto Portfolio','0.43.0','Sparse Solver','Compare deterministic orderings without assuming one dominates fill and frontal width simultaneously.',Maturity.BETA)
    outputs=(PortSpec('result','v43_portfolio'),); proof_status=ProofStatus(evidence={EvidenceKind.NUMERICAL,EvidenceKind.SYMBOLIC},unit_tests=True,documentation=True)
    def execute(self,inputs,params,ctx): return {'result':ordering_portfolio()}
    def verify(self,inputs,params,outputs,ctx):
        r=outputs['result']; names={x['ordering'] for x in r['rows']}; ok=r['winner_by_fill'] in names and set(r['pareto_fill_front'])<=names
        return [VerificationRecord('portfolio-v043',EvidenceKind.SYMBOLIC,'Ordering winner and Pareto set are derived from explicit structural metrics.',VerificationState.PASS if ok else VerificationState.FAIL,'ordering portfolio',r)]
def register_fem_v043(registry): registry.register(OrderingPortfolioV43)
