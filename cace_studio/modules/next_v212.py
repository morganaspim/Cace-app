from cace_studio.modules.next_v201_225_common import *

class NextV212(NextStepModule):
    capability_key="212"
    module_id="next212.parabolic_equilibrated_flux_bounds"
    label='Parabolic Equilibrated-Flux Bounds'
    version="2.12.0"
    description='CACE next-step release: Parabolic Equilibrated-Flux Bounds.'
    evidence_kind=CAP["212"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v2.x",description,Maturity.EXPERIMENTAL,
        assumptions=("Preserve evidence and theorem scope.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["No silent promotion of reviewed/numerical evidence."])

def register_next_v212(registry):
    registry.register(NextV212)
