from cace_studio.modules.next_v201_225_common import *

class NextV204(NextStepModule):
    capability_key="204"
    module_id="next204.mixed_rt0_poisson_assembly"
    label='Mixed RT0 Poisson Assembly'
    version="2.04.0"
    description='CACE next-step release: Mixed RT0 Poisson Assembly.'
    evidence_kind=CAP["204"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v2.x",description,Maturity.EXPERIMENTAL,
        assumptions=("Preserve evidence and theorem scope.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["No silent promotion of reviewed/numerical evidence."])

def register_next_v204(registry):
    registry.register(NextV204)
