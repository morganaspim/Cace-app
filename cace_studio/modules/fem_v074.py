from __future__ import annotations
from cace_studio.modules.fem_v051 import provenance_dag_root
from cace_studio.modules.fem_v053 import interval_dot
from cace_studio.modules.fem_v055 import stopping_policy
from cace_studio.modules.fem_v058 import cache_integrity
from cace_studio.modules.fem_v068 import certificate_dependency_graph
from cace_studio.modules.fem_v051_075_common import ResultModule
from cace_studio.core.types import ModuleMetadata,Maturity,EvidenceKind,ProofStatus

def qualification_v074():
    gates={'provenance':provenance_dag_root()['pass'],'interval_dot':interval_dot()['pass'],'stopping':stopping_policy()['pass'],'cache':cache_integrity()['pass'],'dependencies':certificate_dependency_graph()['pass']}
    return {'pass':all(gates.values()),'gates':gates,'passed':sum(gates.values()),'total':len(gates)}
class QualificationV74(ResultModule):
    fn=staticmethod(qualification_v074); module_id='fem74.qualification'; label='v0.74 Qualification Matrix'; version='0.74.0'; description='Cross-layer deterministic qualification matrix for v0.51-v0.73 capabilities.'; evidence_kind=EvidenceKind.SYMBOLIC
    metadata=ModuleMetadata(module_id,label,version,'Qualification',description,Maturity.BETA); proof_status=ProofStatus(evidence={EvidenceKind.SYMBOLIC,EvidenceKind.NUMERICAL,EvidenceKind.INTERVAL},unit_tests=True,regression_tests=True,documentation=True)
def register_fem_v074(registry): registry.register(QualificationV74)
