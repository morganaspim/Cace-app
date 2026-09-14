from cace_studio.modules.next_v226_250_common import *

class NextV230(Next50Module):
    capability_key="230"
    module_id="next50.230.goal_oriented_equilibrated_primal_dual_certification"
    label='Goal-oriented equilibrated primal/dual certification'
    version="2.30.0"
    description='CACE ranked next-step release: Goal-oriented equilibrated primal/dual certification.'
    evidence_kind=CAP["230"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v2.5 Roadmap",description,Maturity.EXPERIMENTAL,
        assumptions=("Preserve capability and evidence scope.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Reference fixtures and theorem contracts are not whole-family proofs."])

def register_next_v230(registry):
    registry.register(NextV230)
