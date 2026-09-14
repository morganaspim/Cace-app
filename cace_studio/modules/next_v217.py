from cace_studio.modules.next_v201_225_common import *

class NextV217(NextStepModule):
    capability_key="217"
    module_id="next217.newton_kantorovich_nonlinear_fixture"
    label='Newton-Kantorovich Nonlinear Fixture'
    version="2.17.0"
    description='CACE next-step release: Newton-Kantorovich Nonlinear Fixture.'
    evidence_kind=CAP["217"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v2.x",description,Maturity.EXPERIMENTAL,
        assumptions=("Preserve evidence and theorem scope.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["No silent promotion of reviewed/numerical evidence."])

def register_next_v217(registry):
    registry.register(NextV217)
