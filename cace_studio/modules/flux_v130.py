from cace_studio.modules.flux_v126_130_common import *

class FluxV130(FluxStepModule):
    capability_key="130"
    module_id="flux130.prager_synge_bound"
    label="Prager-Synge Guaranteed Bound"
    version="1.30.0"
    description="CACE equilibrated-flux step: Prager-Synge Guaranteed Bound."
    evidence_kind=CAP["130"][2]
    metadata=ModuleMetadata(module_id,label,version,"Equilibrated Flux",description,Maturity.EXPERIMENTAL,
        assumptions=("Conforming affine triangular mesh and declared flux/PDE conventions",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Reviewed external mathematics is not automatically formal evidence."])

def register_flux_v130(registry):
    registry.register(FluxV130)
