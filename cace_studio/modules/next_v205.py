from cace_studio.modules.next_v201_225_common import *

class NextV205(NextStepModule):
    capability_key="205"
    module_id="next205.mixed_rt0_poisson_solve"
    label='Mixed RT0 Poisson Solve'
    version="2.05.0"
    description='CACE next-step release: Mixed RT0 Poisson Solve.'
    evidence_kind=CAP["205"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v2.x",description,Maturity.EXPERIMENTAL,
        assumptions=("Preserve evidence and theorem scope.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["No silent promotion of reviewed/numerical evidence."])

def register_next_v205(registry):
    registry.register(NextV205)
