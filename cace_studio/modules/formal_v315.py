from cace_studio.modules.formal_v301_320_common import *

class FormalV315(FormalStepModule):
    capability_key="315"
    module_id="formal315.formal_proof_ci_gate"
    label='Formal Proof CI Gate'
    version="3.15.0"
    description='CACE formalization release: Formal Proof CI Gate.'
    evidence_kind=CAP["315"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE Formal",description,Maturity.EXPERIMENTAL,
        assumptions=("External Lean promotion requires a successful pinned lake build.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Lean NOT_RUN is not formal proof evidence."])

def register_formal_v315(registry):
    registry.register(FormalV315)
