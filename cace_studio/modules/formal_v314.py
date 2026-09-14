from cace_studio.modules.formal_v301_320_common import *

class FormalV314(FormalStepModule):
    capability_key="314"
    module_id="formal314.proof_producing_frozen_signatures"
    label='Proof-Producing Frozen Signatures'
    version="3.14.0"
    description='CACE formalization release: Proof-Producing Frozen Signatures.'
    evidence_kind=CAP["314"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE Formal",description,Maturity.EXPERIMENTAL,
        assumptions=("External Lean promotion requires a successful pinned lake build.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Lean NOT_RUN is not formal proof evidence."])

def register_formal_v314(registry):
    registry.register(FormalV314)
