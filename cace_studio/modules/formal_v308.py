from cace_studio.modules.formal_v301_320_common import *

class FormalV308(FormalStepModule):
    capability_key="308"
    module_id="formal308.elementwise_green_and_face_cancellation"
    label='Elementwise Green and Face Cancellation'
    version="3.08.0"
    description='CACE formalization release: Elementwise Green and Face Cancellation.'
    evidence_kind=CAP["308"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE Formal",description,Maturity.EXPERIMENTAL,
        assumptions=("External Lean promotion requires a successful pinned lake build.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Lean NOT_RUN is not formal proof evidence."])

def register_formal_v308(registry):
    registry.register(FormalV308)
