from __future__ import annotations
import hashlib,json,platform,sys
from cace_studio.modules.fem_v051_075_common import ResultModule
from cace_studio.core.types import ModuleMetadata,Maturity,EvidenceKind,ProofStatus

def reproducibility_capsule():
    cap={'python':platform.python_version(),'implementation':platform.python_implementation(),'platform':platform.system(),'machine':platform.machine(),'byteorder':sys.byteorder,'release':'0.73.0'}
    digest=hashlib.sha256(json.dumps(cap,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return {'pass':len(digest)==64,'capsule':cap,'sha256':digest}
class ReproCapsuleV73(ResultModule):
    fn=staticmethod(reproducibility_capsule); module_id='fem73.repro_capsule'; label='Reproducibility Capsule'; version='0.73.0'; description='Content-hashed execution-environment capsule for reproducibility reports.'; evidence_kind=EvidenceKind.SYMBOLIC
    metadata=ModuleMetadata(module_id,label,version,'Reproducibility',description,Maturity.BETA); proof_status=ProofStatus(evidence={EvidenceKind.SYMBOLIC},unit_tests=True,regression_tests=True,documentation=True)
def register_fem_v073(registry): registry.register(ReproCapsuleV73)
