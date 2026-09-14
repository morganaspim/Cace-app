from __future__ import annotations
from cace_studio.modules.fem_v051_075_common import ResultModule
from cace_studio.core.types import ModuleMetadata,Maturity,EvidenceKind,ProofStatus

def evidence_lattice():
    # Partial, scope-aware relation: no blanket ordering between formal and interval evidence.
    supports={'experimental':set(),'numerical':{'experimental'},'symbolic':{'experimental'},'interval-certified':{'numerical','experimental'},'formally-verified':{'symbolic','experimental'}}
    incomparable=('interval-certified' not in supports['formally-verified'] and 'formally-verified' not in supports['interval-certified'])
    return {'pass':incomparable,'supports':{k:sorted(v) for k,v in supports.items()},'formal_interval_incomparable':incomparable}
class EvidenceLatticeV69(ResultModule):
    fn=staticmethod(evidence_lattice); module_id='fem69.evidence_lattice'; label='Scope-Aware Evidence Lattice'; version='0.69.0'; description='Partial evidence relation that avoids treating formal and interval evidence as universally interchangeable.'; evidence_kind=EvidenceKind.SYMBOLIC
    metadata=ModuleMetadata(module_id,label,version,'Trust',description,Maturity.BETA); proof_status=ProofStatus(evidence={EvidenceKind.SYMBOLIC},unit_tests=True,regression_tests=True,documentation=True)
def register_fem_v069(registry): registry.register(EvidenceLatticeV69)
