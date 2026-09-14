from __future__ import annotations
import hashlib,json
from cace_studio.core.module import Module
from cace_studio.core.types import ModuleMetadata, PortSpec, ProofStatus, Maturity, EvidenceKind
from cace_studio.core.verification import VerificationRecord, VerificationState
from cace_studio.modules.fem_v031 import stress_3d

def parameter_sweep(ns=(3,4)):
    rows=[stress_3d(n) for n in ns]; payload=json.dumps(rows,sort_keys=True,separators=(',',':')).encode()
    return {'release':'0.41.0','parameter':'n','values':list(ns),'rows':rows,'all_certified':all(r['certified'] for r in rows),'sha256':hashlib.sha256(payload).hexdigest()}
class ParameterSweepV41(Module):
    metadata=ModuleMetadata('fem41.parameter_sweep','Deterministic Parameter Sweep','0.41.0','Experiment','Execute a canonical parameter grid and bind ordered results to a digest.',Maturity.BETA)
    outputs=(PortSpec('result','v41_sweep'),); proof_status=ProofStatus(evidence={EvidenceKind.SYMBOLIC,EvidenceKind.NUMERICAL},unit_tests=True,documentation=True)
    def execute(self,inputs,params,ctx): return {'result':parameter_sweep()}
    def verify(self,inputs,params,outputs,ctx):
        r=outputs['result']; ok=r['all_certified'] and len(r['sha256'])==64
        return [VerificationRecord('sweep-v041',EvidenceKind.SYMBOLIC,'Every sweep point is certified and the ordered campaign is content-addressed.',VerificationState.PASS if ok else VerificationState.FAIL,'parameter sweep',{'sha256':r['sha256'],'cases':len(r['rows'])})]
def register_fem_v041(registry): registry.register(ParameterSweepV41)
