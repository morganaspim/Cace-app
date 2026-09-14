from cace_studio.modules.formal_v301_320_common import *

class FormalV302(FormalStepModule):
    capability_key="302"
    module_id="formal302.dedicated_cace_formal_project"
    label='Dedicated CACE Formal Project'
    version="3.02.0"
    description='CACE formalization release: Dedicated CACE Formal Project.'
    evidence_kind=CAP["302"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE Formal",description,Maturity.EXPERIMENTAL,
        assumptions=("External Lean promotion requires a successful pinned lake build.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Lean NOT_RUN is not formal proof evidence."])

def register_formal_v302(registry):
    registry.register(FormalV302)
