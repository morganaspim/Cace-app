from cace_studio.modules.next_v201_225_common import *

class NextV208(NextStepModule):
    capability_key="208"
    module_id="next208.exact_ldlt_inertia_fixture"
    label='Exact LDLT Inertia Fixture'
    version="2.08.0"
    description='CACE next-step release: Exact LDLT Inertia Fixture.'
    evidence_kind=CAP["208"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v2.x",description,Maturity.EXPERIMENTAL,
        assumptions=("Preserve evidence and theorem scope.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["No silent promotion of reviewed/numerical evidence."])

def register_next_v208(registry):
    registry.register(NextV208)
