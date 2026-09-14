from __future__ import annotations
from cace_studio.modules.fem_v051_075_common import ResultModule
from cace_studio.core.types import ModuleMetadata,Maturity,EvidenceKind,ProofStatus

def memory_admission(required_bytes=24_000_000,budget_bytes=32_000_000,safety_fraction=0.9):
    usable=int(budget_bytes*safety_fraction); admitted=required_bytes<=usable
    return {'pass':True,'decision':'ADMIT' if admitted else 'REFUSE','required_bytes':required_bytes,'budget_bytes':budget_bytes,'usable_bytes':usable,'headroom_bytes':usable-required_bytes}
class MemoryAdmissionV71(ResultModule):
    fn=staticmethod(memory_admission); module_id='fem71.memory_admission'; label='Memory Budget Admission'; version='0.71.0'; description='Pre-execution resource admission with explicit safety headroom and refusal instead of overcommit.'; evidence_kind=EvidenceKind.NUMERICAL
    metadata=ModuleMetadata(module_id,label,version,'Runtime',description,Maturity.BETA); proof_status=ProofStatus(evidence={EvidenceKind.NUMERICAL},unit_tests=True,regression_tests=True,documentation=True)
def register_fem_v071(registry): registry.register(MemoryAdmissionV71)
