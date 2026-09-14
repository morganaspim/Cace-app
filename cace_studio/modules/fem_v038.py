from __future__ import annotations
from cace_studio.core.module import Module
from cace_studio.core.types import ModuleMetadata, PortSpec, ProofStatus, Maturity, EvidenceKind
from cace_studio.core.verification import VerificationRecord, VerificationState
from cace_studio.modules.fem_v024 import scaling_suite

def convergence_audit(sizes=(6,8,10)):
    s=scaling_suite(sizes); rows=s['rows']; ratios=[r['factor_nnz']/r['dimension'] for r in rows]
    return {'release':'0.38.0','rows':rows,'all_certified':s['all_certified'],'dimensions_increasing':s['dimensions_strictly_increasing'],'factor_nnz_per_dof':ratios,'finite_positive_ratios':all(x>0 and x<1e6 for x in ratios)}
class ConvergenceAuditV38(Module):
    metadata=ModuleMetadata('fem38.convergence_audit','Scaling/Convergence Audit','0.38.0','Benchmark','Audit monotone problem growth and exact-factor certification across a deterministic scaling sequence.',Maturity.BETA)
    outputs=(PortSpec('result','v38_audit'),); proof_status=ProofStatus(evidence={EvidenceKind.SYMBOLIC,EvidenceKind.NUMERICAL},unit_tests=True,documentation=True,limitations=['this is a structural scaling audit, not a PDE convergence theorem'])
    def execute(self,inputs,params,ctx): return {'result':convergence_audit()}
    def verify(self,inputs,params,outputs,ctx):
        r=outputs['result']; ok=r['all_certified'] and r['dimensions_increasing'] and r['finite_positive_ratios']
        return [VerificationRecord('audit-v038',EvidenceKind.SYMBOLIC,'Every audited scale retains exact sparse reconstruction and coherent structural metrics.',VerificationState.PASS if ok else VerificationState.FAIL,'scaling audit',{'cases':len(r['rows'])})]
def register_fem_v038(registry): registry.register(ConvergenceAuditV38)
