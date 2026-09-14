from __future__ import annotations
import statistics
from cace_studio.modules.fem_v051_075_common import ResultModule
from cace_studio.core.types import ModuleMetadata,Maturity,EvidenceKind,ProofStatus

def ensemble_consensus(values=(1.0,1.0000002,0.9999999,1.0000001), tolerance=5e-7):
    med=statistics.median(values); dev=max(abs(v-med) for v in values)
    return {'pass':dev<=tolerance,'median':med,'max_deviation':dev,'count':len(values),'tolerance':tolerance}
class EnsembleConsensusV61(ResultModule):
    fn=staticmethod(ensemble_consensus); module_id='fem61.ensemble'; label='Independent-Method Consensus'; version='0.61.0'; description='Tolerance-based consensus diagnostic across independent numerical estimates.'; evidence_kind=EvidenceKind.NUMERICAL
    metadata=ModuleMetadata(module_id,label,version,'Diagnostics',description,Maturity.BETA); proof_status=ProofStatus(evidence={EvidenceKind.NUMERICAL},unit_tests=True,regression_tests=True,documentation=True,limitations=['Consensus is corroboration, not proof.'])
def register_fem_v061(registry): registry.register(EnsembleConsensusV61)
