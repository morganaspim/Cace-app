from cace_studio.modules.next_v226_250_common import *

class NextV234(Next50Module):
    capability_key="234"
    module_id="next50.234.production_maxwell_nedelec_curl_curl_assembly"
    label='Production Maxwell/Nedelec curl-curl assembly'
    version="2.34.0"
    description='CACE ranked next-step release: Production Maxwell/Nedelec curl-curl assembly.'
    evidence_kind=CAP["234"][2]
    metadata=ModuleMetadata(module_id,label,version,"CACE v2.5 Roadmap",description,Maturity.EXPERIMENTAL,
        assumptions=("Preserve capability and evidence scope.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Reference fixtures and theorem contracts are not whole-family proofs."])

def register_next_v234(registry):
    registry.register(NextV234)
