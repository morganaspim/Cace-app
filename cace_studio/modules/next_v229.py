from cace_studio.modules.next_v226_250_common import *

class NextV229(Next50Module):
    capability_key="229"
    module_id="next50.229.3d_guaranteed_equilibrated_energy_bounds"
    label='3D guaranteed equilibrated energy bounds'
    version="2.29.0"
    description='CACE ranked next-step release: 3D guaranteed equilibrated energy bounds.'
    evidence_kind=CAP["229"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v2.5 Roadmap",description,Maturity.EXPERIMENTAL,
        assumptions=("Preserve capability and evidence scope.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Reference fixtures and theorem contracts are not whole-family proofs."])

def register_next_v229(registry):
    registry.register(NextV229)
