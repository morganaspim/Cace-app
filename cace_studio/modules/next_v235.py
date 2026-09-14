from cace_studio.modules.next_v226_250_common import *

class NextV235(Next50Module):
    capability_key="235"
    module_id="next50.235.general_sparse_verified_spectral_enclosures"
    label='General sparse verified spectral enclosures'
    version="2.35.0"
    description='CACE ranked next-step release: General sparse verified spectral enclosures.'
    evidence_kind=CAP["235"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v2.5 Roadmap",description,Maturity.EXPERIMENTAL,
        assumptions=("Preserve capability and evidence scope.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Reference fixtures and theorem contracts are not whole-family proofs."])

def register_next_v235(registry):
    registry.register(NextV235)
