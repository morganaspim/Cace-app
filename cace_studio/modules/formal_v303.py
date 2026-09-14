from cace_studio.modules.formal_v301_320_common import *

class FormalV303(FormalStepModule):
    capability_key="303"
    module_id="formal303.abstract_hilbert_hypercircle"
    label='Abstract Hilbert Hypercircle'
    version="3.03.0"
    description='CACE formalization release: Abstract Hilbert Hypercircle.'
    evidence_kind=CAP["303"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE Formal",description,Maturity.EXPERIMENTAL,
        assumptions=("External Lean promotion requires a successful pinned lake build.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Lean NOT_RUN is not formal proof evidence."])

def register_formal_v303(registry):
    registry.register(FormalV303)
