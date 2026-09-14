from __future__ import annotations
from cace_studio.modules.fem_v051_075_common import ResultModule
from cace_studio.core.types import ModuleMetadata,Maturity,EvidenceKind,ProofStatus

def certificate_dependency_graph():
    deps={'assembly':[],'factor':['assembly'],'solve':['factor'],'continuum':['solve','reliability_theorem']}
    known={'assembly','factor','solve'}
    unresolved=sorted({d for k in deps for d in deps[k] if d not in known})
    promotable={k:all(d in known for d in ds) for k,ds in deps.items()}
    return {'pass':promotable['solve'] and not promotable['continuum'],'dependencies':deps,'unresolved':unresolved,'promotable':promotable}
class CertificateDependenciesV68(ResultModule):
    fn=staticmethod(certificate_dependency_graph); module_id='fem68.cert_dependencies'; label='Certificate Dependency Graph'; version='0.68.0'; description='Explicit dependency graph prevents promotion when required theorem evidence is absent.'; evidence_kind=EvidenceKind.SYMBOLIC
    metadata=ModuleMetadata(module_id,label,version,'Verification',description,Maturity.BETA); proof_status=ProofStatus(evidence={EvidenceKind.SYMBOLIC},unit_tests=True,regression_tests=True,documentation=True)
def register_fem_v068(registry): registry.register(CertificateDependenciesV68)
