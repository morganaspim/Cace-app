from cace_studio.modules.next_v226_250_common import *

class NextV228(Next50Module):
    capability_key="228"
    module_id="next50.228.3d_rt0_h_div_global_assembly"
    label='3D RT0/H(div) global assembly'
    version="2.28.0"
    description='CACE ranked next-step release: 3D RT0/H(div) global assembly.'
    evidence_kind=CAP["228"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v2.5 Roadmap",description,Maturity.EXPERIMENTAL,
        assumptions=("Preserve capability and evidence scope.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Reference fixtures and theorem contracts are not whole-family proofs."])

def register_next_v228(registry):
    registry.register(NextV228)
