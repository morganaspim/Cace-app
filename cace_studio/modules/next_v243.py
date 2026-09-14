from cace_studio.modules.next_v226_250_common import *

class NextV243(Next50Module):
    capability_key="243"
    module_id="next50.243.supg_convection_diffusion"
    label='SUPG convection-diffusion'
    version="2.43.0"
    description='CACE ranked next-step release: SUPG convection-diffusion.'
    evidence_kind=CAP["243"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v2.5 Roadmap",description,Maturity.EXPERIMENTAL,
        assumptions=("Preserve capability and evidence scope.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Reference fixtures and theorem contracts are not whole-family proofs."])

def register_next_v243(registry):
    registry.register(NextV243)
