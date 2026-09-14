from cace_studio.modules.next_v201_225_common import *

class NextV203(NextStepModule):
    capability_key="203"
    module_id="next203.rt1_affine_source_global_fixture"
    label='RT1 Affine Source Global Fixture'
    version="2.03.0"
    description='CACE next-step release: RT1 Affine Source Global Fixture.'
    evidence_kind=CAP["203"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v2.x",description,Maturity.EXPERIMENTAL,
        assumptions=("Preserve evidence and theorem scope.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["No silent promotion of reviewed/numerical evidence."])

def register_next_v203(registry):
    registry.register(NextV203)
