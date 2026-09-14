from cace_studio.modules.next_v201_225_common import *

class NextV209(NextStepModule):
    capability_key="209"
    module_id="next209.certified_eigenvalue_bisection_fixture"
    label='Certified Eigenvalue Bisection Fixture'
    version="2.09.0"
    description='CACE next-step release: Certified Eigenvalue Bisection Fixture.'
    evidence_kind=CAP["209"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v2.x",description,Maturity.EXPERIMENTAL,
        assumptions=("Preserve evidence and theorem scope.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["No silent promotion of reviewed/numerical evidence."])

def register_next_v209(registry):
    registry.register(NextV209)
