from cace_studio.modules.formal_v301_320_common import *

class FormalV316(FormalStepModule):
    capability_key="316"
    module_id="formal316.formal_dependency_blueprint"
    label='Formal Dependency Blueprint'
    version="3.16.0"
    description='CACE formalization release: Formal Dependency Blueprint.'
    evidence_kind=CAP["316"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE Formal",description,Maturity.EXPERIMENTAL,
        assumptions=("External Lean promotion requires a successful pinned lake build.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Lean NOT_RUN is not formal proof evidence."])

def register_formal_v316(registry):
    registry.register(FormalV316)
