from cace_studio.modules.flux_v126_130_common import *

class FluxV127(FluxStepModule):
    capability_key="127"
    module_id="flux127.hdiv_assembly"
    label="Global H(div) Edge Assembly"
    version="1.27.0"
    description="CACE equilibrated-flux step: Global H(div) Edge Assembly."
    evidence_kind=CAP["127"][2]
    metadata=ModuleMetadata(module_id,label,version,"Equilibrated Flux",description,Maturity.EXPERIMENTAL,
        assumptions=("Conforming affine triangular mesh and declared flux/PDE conventions",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Reviewed external mathematics is not automatically formal evidence."])

def register_flux_v127(registry):
    registry.register(FluxV127)
