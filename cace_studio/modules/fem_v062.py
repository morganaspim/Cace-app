from __future__ import annotations
import math
from cace_studio.modules.fem_v051_075_common import ResultModule
from cace_studio.core.types import ModuleMetadata,Maturity,EvidenceKind,ProofStatus

def uncertainty_budget(components=None, limit=0.05):
    components=components or {'discretization':0.02,'algebraic':0.005,'roundoff':0.001,'parameter':0.01}
    rss=math.sqrt(sum(v*v for v in components.values())); worst=sum(abs(v) for v in components.values())
    return {'pass':worst<=limit,'components':components,'rss':rss,'worst_case':worst,'limit':limit,'combination_rule':'worst-case gate; RSS informational'}
class UncertaintyBudgetV62(ResultModule):
    fn=staticmethod(uncertainty_budget); module_id='fem62.uncertainty_budget'; label='Uncertainty Budget'; version='0.62.0'; description='Composable uncertainty budget with a conservative absolute-sum acceptance gate.'; evidence_kind=EvidenceKind.NUMERICAL
    metadata=ModuleMetadata(module_id,label,version,'Uncertainty',description,Maturity.BETA); proof_status=ProofStatus(evidence={EvidenceKind.NUMERICAL},unit_tests=True,regression_tests=True,documentation=True)
def register_fem_v062(registry): registry.register(UncertaintyBudgetV62)
