from __future__ import annotations
from cace_studio.modules.fem_v051_075_common import ResultModule
from cace_studio.core.types import ModuleMetadata,Maturity,EvidenceKind,ProofStatus

def monotonicity_audit(xs=(0,0.25,0.5,0.75,1.0)):
    ys=[x*x+x for x in xs]; violations=[i for i in range(len(ys)-1) if ys[i+1]<ys[i]]
    return {'pass':not violations,'x':list(xs),'y':ys,'violations':violations}
class MonotonicityAuditV60(ResultModule):
    fn=staticmethod(monotonicity_audit); module_id='fem60.monotonicity'; label='Monotonicity Audit'; version='0.60.0'; description='Deterministic sampled monotonicity audit; explicitly a finite-grid diagnostic, not a global theorem.'; evidence_kind=EvidenceKind.NUMERICAL
    metadata=ModuleMetadata(module_id,label,version,'Diagnostics',description,Maturity.BETA); proof_status=ProofStatus(evidence={EvidenceKind.NUMERICAL},unit_tests=True,regression_tests=True,documentation=True,limitations=['Finite-grid monotonicity does not prove global monotonicity.'])
def register_fem_v060(registry): registry.register(MonotonicityAuditV60)
