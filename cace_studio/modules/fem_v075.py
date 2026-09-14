from __future__ import annotations
import hashlib,json
from cace_studio.modules.fem_v050 import milestone_v050
from cace_studio.modules.fem_v074 import qualification_v074
from cace_studio.modules.fem_v073 import reproducibility_capsule
from cace_studio.modules.fem_v051_075_common import ResultModule
from cace_studio.core.types import ModuleMetadata,Maturity,EvidenceKind,ProofStatus

def milestone_v075():
    prior=milestone_v050(); q=qualification_v074(); cap=reproducibility_capsule()
    boundaries={'general_2d_reliability_formal':False,'tetrahedral_continuum_formal':False,'gpu_unconditional':False,'native_numerics_formal':False}
    summary={'v050_pass':prior['all_pass'],'v074_pass':q['pass'],'repro_capsule':cap['sha256'],'boundaries':boundaries,'new_release_span':'0.51-0.75'}
    digest=hashlib.sha256(json.dumps(summary,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return {'release':'0.75.0','pass':prior['all_pass'] and q['pass'] and not any(boundaries.values()),'summary':summary,'sha256':digest}
class MilestoneV75(ResultModule):
    fn=staticmethod(milestone_v075); module_id='fem75.milestone'; label='v0.75 Verified Research Milestone'; version='0.75.0'; description='Consolidated v0.1-v0.75 milestone preserving unresolved theorem and backend boundaries.'; evidence_kind=EvidenceKind.SYMBOLIC
    metadata=ModuleMetadata(module_id,label,version,'Qualification',description,Maturity.BETA); proof_status=ProofStatus(evidence={EvidenceKind.SYMBOLIC,EvidenceKind.NUMERICAL,EvidenceKind.INTERVAL},unit_tests=True,regression_tests=True,documentation=True,limitations=['Does not promote unresolved continuum or GPU claims.'])
def register_fem_v075(registry): registry.register(MilestoneV75)
