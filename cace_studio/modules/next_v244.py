from cace_studio.modules.next_v226_250_common import *

class NextV244(Next50Module):
    capability_key="244"
    module_id="next50.244.linear_elasticity_certification"
    label='Linear elasticity certification'
    version="2.44.0"
    description='CACE ranked next-step release: Linear elasticity certification.'
    evidence_kind=CAP["244"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v2.5 Roadmap",description,Maturity.EXPERIMENTAL,
        assumptions=("Preserve capability and evidence scope.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Reference fixtures and theorem contracts are not whole-family proofs."])

def register_next_v244(registry):
    registry.register(NextV244)
