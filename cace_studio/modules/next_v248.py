from cace_studio.modules.next_v226_250_common import *

class NextV248(Next50Module):
    capability_key="248"
    module_id="next50.248.stochastic_galerkin_uncertainty"
    label='Stochastic Galerkin uncertainty'
    version="2.48.0"
    description='CACE ranked next-step release: Stochastic Galerkin uncertainty.'
    evidence_kind=CAP["248"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v2.5 Roadmap",description,Maturity.EXPERIMENTAL,
        assumptions=("Preserve capability and evidence scope.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Reference fixtures and theorem contracts are not whole-family proofs."])

def register_next_v248(registry):
    registry.register(NextV248)
