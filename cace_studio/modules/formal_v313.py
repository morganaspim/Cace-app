from cace_studio.modules.formal_v301_320_common import *

class FormalV313(FormalStepModule):
    capability_key="313"
    module_id="formal313.certificate_to_lean_bridge"
    label='Certificate-to-Lean Bridge'
    version="3.13.0"
    description='CACE formalization release: Certificate-to-Lean Bridge.'
    evidence_kind=CAP["313"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE Formal",description,Maturity.EXPERIMENTAL,
        assumptions=("External Lean promotion requires a successful pinned lake build.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Lean NOT_RUN is not formal proof evidence."])

def register_formal_v313(registry):
    registry.register(FormalV313)
