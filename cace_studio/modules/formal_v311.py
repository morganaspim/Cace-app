from cace_studio.modules.formal_v301_320_common import *

class FormalV311(FormalStepModule):
    capability_key="311"
    module_id="formal311.formal_mesh_combinatorics"
    label='Formal Mesh Combinatorics'
    version="3.11.0"
    description='CACE formalization release: Formal Mesh Combinatorics.'
    evidence_kind=CAP["311"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE Formal",description,Maturity.EXPERIMENTAL,
        assumptions=("External Lean promotion requires a successful pinned lake build.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Lean NOT_RUN is not formal proof evidence."])

def register_formal_v311(registry):
    registry.register(FormalV311)
