from cace_studio.modules.next_v226_250_common import *

class NextV239(Next50Module):
    capability_key="239"
    module_id="next50.239.anisotropic_metric_adaptive_meshing"
    label='Anisotropic metric adaptive meshing'
    version="2.39.0"
    description='CACE ranked next-step release: Anisotropic metric adaptive meshing.'
    evidence_kind=CAP["239"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v2.5 Roadmap",description,Maturity.EXPERIMENTAL,
        assumptions=("Preserve capability and evidence scope.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Reference fixtures and theorem contracts are not whole-family proofs."])

def register_next_v239(registry):
    registry.register(NextV239)
