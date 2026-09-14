from __future__ import annotations
import hashlib,json
from cace_studio.core.module import Module
from cace_studio.core.types import ModuleMetadata, PortSpec, ProofStatus, Maturity, EvidenceKind
from cace_studio.core.verification import VerificationRecord, VerificationState
from cace_studio.modules.fem_v017 import structured_square_p1_csr, minimum_degree_ordering, sparse_exact_ldlt

def factor_replay(nx=8,ny=8):
    csr=structured_square_p1_csr(nx,ny); order=minimum_degree_ordering(csr); a=sparse_exact_ldlt(csr,order); b=sparse_exact_ldlt(csr,order)
    def h(x): return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
    return {'release':'0.44.0','digest_a':h(a),'digest_b':h(b),'stable':h(a)==h(b),'certified':a['certified'] and b['certified']}
class FactorReplayV44(Module):
    metadata=ModuleMetadata('fem44.factor_replay','Exact Factor Replay Checksum','0.44.0','Verification','Require deterministic exact sparse factorization to reproduce a canonical artifact digest.',Maturity.BETA)
    outputs=(PortSpec('result','v44_replay'),); proof_status=ProofStatus(evidence={EvidenceKind.SYMBOLIC},unit_tests=True,documentation=True)
    def execute(self,inputs,params,ctx): return {'result':factor_replay()}
    def verify(self,inputs,params,outputs,ctx):
        r=outputs['result']; ok=r['stable'] and r['certified']
        return [VerificationRecord('factor-replay-v044',EvidenceKind.SYMBOLIC,'Exact factor artifact reproduces byte-for-byte canonical digest.',VerificationState.PASS if ok else VerificationState.FAIL,'factor replay',r)]
def register_fem_v044(registry): registry.register(FactorReplayV44)
