from cace_studio.modules.next_v201_225_common import *

class NextV201(NextStepModule):
    capability_key="201"
    module_id="next201.global_rt1_topology"
    label='Global RT1 Topology'
    version="2.01.0"
    description='CACE next-step release: Global RT1 Topology.'
    evidence_kind=CAP["201"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v2.x",description,Maturity.EXPERIMENTAL,
        assumptions=("Preserve evidence and theorem scope.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["No silent promotion of reviewed/numerical evidence."])

def register_next_v201(registry):
    registry.register(NextV201)
