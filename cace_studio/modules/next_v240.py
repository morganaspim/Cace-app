from cace_studio.modules.next_v226_250_common import *

class NextV240(Next50Module):
    capability_key="240"
    module_id="next50.240.interval_parametric_pde_propagation"
    label='Interval-parametric PDE propagation'
    version="2.40.0"
    description='CACE ranked next-step release: Interval-parametric PDE propagation.'
    evidence_kind=CAP["240"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v2.5 Roadmap",description,Maturity.EXPERIMENTAL,
        assumptions=("Preserve capability and evidence scope.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Reference fixtures and theorem contracts are not whole-family proofs."])

def register_next_v240(registry):
    registry.register(NextV240)
