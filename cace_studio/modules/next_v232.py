from cace_studio.modules.next_v226_250_common import *

class NextV232(Next50Module):
    capability_key="232"
    module_id="next50.232.certified_nonlinear_newton_kantorovich_solve"
    label='Certified nonlinear Newton-Kantorovich solve'
    version="2.32.0"
    description='CACE ranked next-step release: Certified nonlinear Newton-Kantorovich solve.'
    evidence_kind=CAP["232"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v2.5 Roadmap",description,Maturity.EXPERIMENTAL,
        assumptions=("Preserve capability and evidence scope.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Reference fixtures and theorem contracts are not whole-family proofs."])

def register_next_v232(registry):
    registry.register(NextV232)
