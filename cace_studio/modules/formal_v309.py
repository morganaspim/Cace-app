from cace_studio.modules.formal_v301_320_common import *

class FormalV309(FormalStepModule):
    capability_key="309"
    module_id="formal309.finite_mesh_hdiv_admissibility"
    label='Finite-Mesh Hdiv Admissibility'
    version="3.09.0"
    description='CACE formalization release: Finite-Mesh Hdiv Admissibility.'
    evidence_kind=CAP["309"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE Formal",description,Maturity.EXPERIMENTAL,
        assumptions=("External Lean promotion requires a successful pinned lake build.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Lean NOT_RUN is not formal proof evidence."])

def register_formal_v309(registry):
    registry.register(FormalV309)
