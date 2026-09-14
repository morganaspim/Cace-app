from cace_studio.modules.formal_v301_320_common import *

class FormalV320(FormalStepModule):
    capability_key="320"
    module_id="formal320.continuum_prager_synge_roadmap_milestone"
    label='Continuum Prager-Synge Roadmap Milestone'
    version="3.20.0"
    description='CACE formalization release: Continuum Prager-Synge Roadmap Milestone.'
    evidence_kind=CAP["320"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE Formal",description,Maturity.EXPERIMENTAL,
        assumptions=("External Lean promotion requires a successful pinned lake build.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Lean NOT_RUN is not formal proof evidence."])

def register_formal_v320(registry):
    registry.register(FormalV320)
