from cace_studio.modules.flux_v126_130_common import *

class FluxV128(FluxStepModule):
    capability_key="128"
    module_id="flux128.local_equilibration"
    label="Local Equilibrated Flux Reconstruction"
    version="1.28.0"
    description="CACE equilibrated-flux step: Local Equilibrated Flux Reconstruction."
    evidence_kind=CAP["128"][2]
    metadata=ModuleMetadata(module_id,label,version,"Equilibrated Flux",description,Maturity.EXPERIMENTAL,
        assumptions=("Conforming affine triangular mesh and declared flux/PDE conventions",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Reviewed external mathematics is not automatically formal evidence."])

def register_flux_v128(registry):
    registry.register(FluxV128)
