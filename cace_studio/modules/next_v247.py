from cace_studio.modules.next_v226_250_common import *

class NextV247(Next50Module):
    capability_key="247"
    module_id="next50.247.pde_constrained_optimization_with_adjoints"
    label='PDE-constrained optimization with adjoints'
    version="2.47.0"
    description='CACE ranked next-step release: PDE-constrained optimization with adjoints.'
    evidence_kind=CAP["247"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v2.5 Roadmap",description,Maturity.EXPERIMENTAL,
        assumptions=("Preserve capability and evidence scope.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Reference fixtures and theorem contracts are not whole-family proofs."])

def register_next_v247(registry):
    registry.register(NextV247)
