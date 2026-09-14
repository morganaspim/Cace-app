from cace_studio.modules.next_v201_225_common import *

class NextV223(NextStepModule):
    capability_key="223"
    module_id="next223.parametric_interval_propagation"
    label='Parametric Interval Propagation'
    version="2.23.0"
    description='CACE next-step release: Parametric Interval Propagation.'
    evidence_kind=CAP["223"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v2.x",description,Maturity.EXPERIMENTAL,
        assumptions=("Preserve evidence and theorem scope.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["No silent promotion of reviewed/numerical evidence."])

def register_next_v223(registry):
    registry.register(NextV223)
