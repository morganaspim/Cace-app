from __future__ import annotations
import math
from cace_studio.core.module import Module
from cace_studio.core.types import ModuleMetadata, PortSpec, ProofStatus, Maturity, EvidenceKind
from cace_studio.core.verification import VerificationRecord, VerificationState

def kahan_sum(xs):
    s=0.0; c=0.0
    for x in xs:
        y=float(x)-c; t=s+y; c=(t-s)-y; s=t
    return s
def compensated_reduction_audit():
    xs=[1e16,1.0,-1e16]*1000
    naive=0.0
    for x in xs: naive += x
    compensated=kahan_sum(xs); exact=0.0  # classic Kahan is also audited, but Neumaier is the release gate here
    # Neumaier handles this severe cancellation case.
    s=0.0;c=0.0
    for x in xs:
        t=s+x
        if abs(s)>=abs(x): c+=(s-t)+x
        else: c+=(x-t)+s
        s=t
    neumaier=s+c; exact=1000.0
    return {'release':'0.40.0','naive':naive,'kahan':compensated,'neumaier':neumaier,'exact_reference':exact,'neumaier_error':abs(neumaier-exact),'naive_error':abs(naive-exact)}
class CompensatedReductionV40(Module):
    metadata=ModuleMetadata('fem40.compensated_reduction','Compensated Reduction Audit','0.40.0','Numerics','Expose cancellation sensitivity and provide a compensated scalar-reduction reference.',Maturity.BETA)
    outputs=(PortSpec('result','v40_reduction'),); proof_status=ProofStatus(evidence={EvidenceKind.NUMERICAL},unit_tests=True,documentation=True,limitations=['compensated summation improves rounding behavior but is not exact arithmetic'])
    def execute(self,inputs,params,ctx): return {'result':compensated_reduction_audit()}
    def verify(self,inputs,params,outputs,ctx):
        r=outputs['result']; ok=r['neumaier_error']<=r['naive_error'] and r['neumaier_error']==0.0
        return [VerificationRecord('reduction-v040',EvidenceKind.NUMERICAL,'Compensated reduction resolves the crafted catastrophic-cancellation case.',VerificationState.PASS if ok else VerificationState.FAIL,'Neumaier reduction regression',r)]
def register_fem_v040(registry): registry.register(CompensatedReductionV40)
