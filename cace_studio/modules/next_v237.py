from cace_studio.modules.next_v226_250_common import *

class NextV237(Next50Module):
    capability_key="237"
    module_id="next50.237.verified_multigrid_hierarchy"
    label='Verified multigrid hierarchy'
    version="2.37.0"
    description='CACE ranked next-step release: Verified multigrid hierarchy.'
    evidence_kind=CAP["237"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v2.5 Roadmap",description,Maturity.EXPERIMENTAL,
        assumptions=("Preserve capability and evidence scope.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Reference fixtures and theorem contracts are not whole-family proofs."])

def register_next_v237(registry):
    registry.register(NextV237)
