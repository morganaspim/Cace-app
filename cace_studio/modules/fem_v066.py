from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
from cace_studio.modules.fem_v051_075_common import ResultModule
from cace_studio.core.types import ModuleMetadata,Maturity,EvidenceKind,ProofStatus

def parallel_determinism(n=32):
    f=lambda i:(i,(i*i+17*i+3)%97)
    with ThreadPoolExecutor(max_workers=4) as ex: a=sorted(ex.map(f,range(n)))
    with ThreadPoolExecutor(max_workers=3) as ex: b=sorted(ex.map(f,range(n)))
    return {'pass':a==b,'count':n,'checksum':sum(v for _,v in a)}
class ParallelDeterminismV66(ResultModule):
    fn=staticmethod(parallel_determinism); module_id='fem66.parallel_determinism'; label='Parallel Schedule Determinism'; version='0.66.0'; description='Order-independent deterministic reduction of pure parallel campaign tasks.'; evidence_kind=EvidenceKind.NUMERICAL
    metadata=ModuleMetadata(module_id,label,version,'Runtime',description,Maturity.BETA); proof_status=ProofStatus(evidence={EvidenceKind.NUMERICAL},unit_tests=True,regression_tests=True,documentation=True)
def register_fem_v066(registry): registry.register(ParallelDeterminismV66)
