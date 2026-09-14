from cace_studio.modules.next_v201_225_common import *

class NextV211(NextStepModule):
    capability_key="211"
    module_id="next211.dual_equilibrated_goal_bounds"
    label='Dual Equilibrated Goal Bounds'
    version="2.11.0"
    description='CACE next-step release: Dual Equilibrated Goal Bounds.'
    evidence_kind=CAP["211"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v2.x",description,Maturity.EXPERIMENTAL,
        assumptions=("Preserve evidence and theorem scope.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["No silent promotion of reviewed/numerical evidence."])

def register_next_v211(registry):
    registry.register(NextV211)
