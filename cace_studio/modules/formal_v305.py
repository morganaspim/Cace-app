from cace_studio.modules.formal_v301_320_common import *

class FormalV305(FormalStepModule):
    capability_key="305"
    module_id="formal305.spd_weighted_energy_layer"
    label='SPD Weighted Energy Layer'
    version="3.05.0"
    description='CACE formalization release: SPD Weighted Energy Layer.'
    evidence_kind=CAP["305"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE Formal",description,Maturity.EXPERIMENTAL,
        assumptions=("External Lean promotion requires a successful pinned lake build.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Lean NOT_RUN is not formal proof evidence."])

def register_formal_v305(registry):
    registry.register(FormalV305)
