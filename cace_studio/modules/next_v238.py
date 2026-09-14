from cace_studio.modules.next_v226_250_common import *

class NextV238(Next50Module):
    capability_key="238"
    module_id="next50.238.verified_domain_decomposition_engine"
    label='Verified domain-decomposition engine'
    version="2.38.0"
    description='CACE ranked next-step release: Verified domain-decomposition engine.'
    evidence_kind=CAP["238"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v2.5 Roadmap",description,Maturity.EXPERIMENTAL,
        assumptions=("Preserve capability and evidence scope.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Reference fixtures and theorem contracts are not whole-family proofs."])

def register_next_v238(registry):
    registry.register(NextV238)
