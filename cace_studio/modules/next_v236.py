from cace_studio.modules.next_v226_250_common import *

class NextV236(Next50Module):
    capability_key="236"
    module_id="next50.236.certified_reduced_basis_offline_online_engine"
    label='Certified reduced-basis offline/online engine'
    version="2.36.0"
    description='CACE ranked next-step release: Certified reduced-basis offline/online engine.'
    evidence_kind=CAP["236"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v2.5 Roadmap",description,Maturity.EXPERIMENTAL,
        assumptions=("Preserve capability and evidence scope.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Reference fixtures and theorem contracts are not whole-family proofs."])

def register_next_v236(registry):
    registry.register(NextV236)
