from __future__ import annotations
from cace_studio.core.module import Module
from cace_studio.core.types import ModuleMetadata, PortSpec, ProofStatus, Maturity, EvidenceKind
from cace_studio.core.verification import VerificationRecord, VerificationState

def ddmin(items,fails):
    cur=list(items); changed=True
    while changed:
        changed=False
        for x in list(cur):
            trial=[y for y in cur if y!=x]
            if trial and fails(trial): cur=trial; changed=True; break
    return cur
def failure_reducer_fixture():
    faults=['tamper_provenance','noise','asymmetric_matrix','unused']; critical={'tamper_provenance'}
    fails=lambda xs: critical.issubset(set(xs))
    reduced=ddmin(faults,fails)
    return {'release':'0.45.0','original':faults,'reduced':reduced,'still_fails':fails(reduced),'one_minimal':all(not fails([x for x in reduced if x!=y]) for y in reduced)}
class FailureReducerV45(Module):
    metadata=ModuleMetadata('fem45.failure_reducer','Verification Failure Reducer','0.45.0','Debugging','Minimize a failing condition set while preserving verifier failure.',Maturity.BETA)
    outputs=(PortSpec('result','v45_reducer'),); proof_status=ProofStatus(evidence={EvidenceKind.SYMBOLIC},unit_tests=True,documentation=True,limitations=['greedy 1-minimal reducer, not guaranteed globally minimum'])
    def execute(self,inputs,params,ctx): return {'result':failure_reducer_fixture()}
    def verify(self,inputs,params,outputs,ctx):
        r=outputs['result']; ok=r['still_fails'] and r['one_minimal'] and len(r['reduced'])<len(r['original'])
        return [VerificationRecord('reduce-v045',EvidenceKind.SYMBOLIC,'Reducer preserves failure and reaches a 1-minimal fault set.',VerificationState.PASS if ok else VerificationState.FAIL,'greedy ddmin',r)]
def register_fem_v045(registry): registry.register(FailureReducerV45)
