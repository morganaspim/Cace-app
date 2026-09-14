from cace_studio.modules.next_v226_250_common import *

class NextV249(Next50Module):
    capability_key="249"
    module_id="next50.249.fem_bem_coupling_interface"
    label='FEM-BEM coupling interface'
    version="2.49.0"
    description='CACE ranked next-step release: FEM-BEM coupling interface.'
    evidence_kind=CAP["249"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v2.5 Roadmap",description,Maturity.EXPERIMENTAL,
        assumptions=("Preserve capability and evidence scope.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Reference fixtures and theorem contracts are not whole-family proofs."])

def register_next_v249(registry):
    registry.register(NextV249)
