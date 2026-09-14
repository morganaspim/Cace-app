from cace_studio.modules.formal_v301_320_common import *

class FormalV317(FormalStepModule):
    capability_key="317"
    module_id="formal317.upstream_ready_pde_lemmas"
    label='Upstream-Ready PDE Lemmas'
    version="3.17.0"
    description='CACE formalization release: Upstream-Ready PDE Lemmas.'
    evidence_kind=CAP["317"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE Formal",description,Maturity.EXPERIMENTAL,
        assumptions=("External Lean promotion requires a successful pinned lake build.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Lean NOT_RUN is not formal proof evidence."])

def register_formal_v317(registry):
    registry.register(FormalV317)
