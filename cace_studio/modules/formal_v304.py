from cace_studio.modules.formal_v301_320_common import *

class FormalV304(FormalStepModule):
    capability_key="304"
    module_id="formal304.abstract_operator_prager_synge"
    label='Abstract Operator Prager-Synge'
    version="3.04.0"
    description='CACE formalization release: Abstract Operator Prager-Synge.'
    evidence_kind=CAP["304"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE Formal",description,Maturity.EXPERIMENTAL,
        assumptions=("External Lean promotion requires a successful pinned lake build.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Lean NOT_RUN is not formal proof evidence."])

def register_formal_v304(registry):
    registry.register(FormalV304)
