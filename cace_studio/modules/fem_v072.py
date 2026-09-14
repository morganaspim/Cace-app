from __future__ import annotations
from cace_studio.modules.fem_v051_075_common import ResultModule
from cace_studio.core.types import ModuleMetadata,Maturity,EvidenceKind,ProofStatus

def solver_fallback_chain(capabilities=None):
    capabilities=capabilities or {'gpu':False,'supernodal':True,'left_looking':True,'dense':True}
    order=['gpu','supernodal','left_looking','dense']; selected=next((x for x in order if capabilities.get(x)),None)
    trace=[{'solver':x,'available':bool(capabilities.get(x))} for x in order]
    return {'pass':selected is not None,'selected':selected,'trace':trace}
class SolverFallbackV72(ResultModule):
    fn=staticmethod(solver_fallback_chain); module_id='fem72.fallback'; label='Audited Solver Fallback Chain'; version='0.72.0'; description='Deterministic solver fallback with an explicit availability trace; unavailable accelerators never count as passes.'; evidence_kind=EvidenceKind.NUMERICAL
    metadata=ModuleMetadata(module_id,label,version,'Runtime',description,Maturity.BETA); proof_status=ProofStatus(evidence={EvidenceKind.NUMERICAL},unit_tests=True,regression_tests=True,documentation=True)
def register_fem_v072(registry): registry.register(SolverFallbackV72)
