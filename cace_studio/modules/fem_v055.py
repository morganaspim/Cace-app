from __future__ import annotations
from cace_studio.modules.fem_v051_075_common import ResultModule
from cace_studio.core.types import ModuleMetadata,Maturity,EvidenceKind,ProofStatus

def stopping_policy(mode='certified_discrete', value=1e-9, tolerance=1e-8):
    supported={'certified_discrete':'certified discrete enclosure radius','residual_witness':'exact/numerical residual witness'}
    if mode not in supported:
        return {'pass':True,'decision':'REFUSED','mode':mode,'reason':'requested stopping claim lacks a certified predicate'}
    return {'pass':True,'decision':'STOP' if value<=tolerance else 'CONTINUE','mode':mode,'predicate':supported[mode],'value':value,'tolerance':tolerance}
class StoppingPolicyV55(ResultModule):
    fn=staticmethod(stopping_policy); module_id='fem55.stopping_policy'; label='Evidence-Gated Stopping Policy'; version='0.55.0'; description='Stopping decisions are permitted only for declared certified predicates; unsupported continuum claims are refused.'; evidence_kind=EvidenceKind.SYMBOLIC
    metadata=ModuleMetadata(module_id,label,version,'Policy',description,Maturity.BETA); proof_status=ProofStatus(evidence={EvidenceKind.SYMBOLIC},unit_tests=True,regression_tests=True,documentation=True)
def register_fem_v055(registry): registry.register(StoppingPolicyV55)
