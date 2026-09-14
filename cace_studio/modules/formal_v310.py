from cace_studio.modules.formal_v301_320_common import *

class FormalV310(FormalStepModule):
    capability_key="310"
    module_id="formal310.discrete_prager_synge_closure"
    label='Discrete Prager-Synge Closure'
    version="3.10.0"
    description='CACE formalization release: Discrete Prager-Synge Closure.'
    evidence_kind=CAP["310"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE Formal",description,Maturity.EXPERIMENTAL,
        assumptions=("External Lean promotion requires a successful pinned lake build.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Lean NOT_RUN is not formal proof evidence."])

def register_formal_v310(registry):
    registry.register(FormalV310)
