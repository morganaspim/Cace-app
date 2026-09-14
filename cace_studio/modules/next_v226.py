from cace_studio.modules.next_v226_250_common import *

class NextV226(Next50Module):
    capability_key="226"
    module_id="next50.226.global_rt1_equilibrated_flux_assembly"
    label='Global RT1 equilibrated-flux assembly'
    version="2.26.0"
    description='CACE ranked next-step release: Global RT1 equilibrated-flux assembly.'
    evidence_kind=CAP["226"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v2.5 Roadmap",description,Maturity.EXPERIMENTAL,
        assumptions=("Preserve capability and evidence scope.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Reference fixtures and theorem contracts are not whole-family proofs."])

def register_next_v226(registry):
    registry.register(NextV226)
