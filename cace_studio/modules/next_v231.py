from cace_studio.modules.next_v226_250_common import *

class NextV231(Next50Module):
    capability_key="231"
    module_id="next50.231.parabolic_equilibrated_space_time_certification"
    label='Parabolic equilibrated space-time certification'
    version="2.31.0"
    description='CACE ranked next-step release: Parabolic equilibrated space-time certification.'
    evidence_kind=CAP["231"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v2.5 Roadmap",description,Maturity.EXPERIMENTAL,
        assumptions=("Preserve capability and evidence scope.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Reference fixtures and theorem contracts are not whole-family proofs."])

def register_next_v231(registry):
    registry.register(NextV231)
