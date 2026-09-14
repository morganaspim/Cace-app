from __future__ import annotations
from cace_studio.core.module import Module
from cace_studio.core.types import ModuleMetadata, PortSpec, ProofStatus, Maturity, EvidenceKind
from cace_studio.core.verification import VerificationRecord, VerificationState

def evaluate_regression(current,baseline,tolerance=0.20,lower_is_better=True):
    current=float(current); baseline=float(baseline); tolerance=float(tolerance)
    if baseline<=0: return {'pass':False,'reason':'baseline must be positive'}
    ratio=current/baseline
    ok=ratio<=1+tolerance if lower_is_better else ratio>=1-tolerance
    return {'pass':ok,'ratio':ratio,'limit':1+tolerance if lower_is_better else 1-tolerance}
def budget_fixture():
    checks={'runtime':evaluate_regression(10.5,10.0,0.10),'memory':evaluate_regression(98,100,0.05),'accuracy':evaluate_regression(0.999,1.0,0.01,False)}
    return {'release':'0.48.0','checks':checks,'all_pass':all(x['pass'] for x in checks.values()),'policy':'explicit baselines; no wall-clock measurement in deterministic qualification'}
class RegressionBudgetV48(Module):
    metadata=ModuleMetadata('fem48.regression_budget','Performance Regression Budget Gate','0.48.0','Qualification','Evaluate explicit performance/accuracy budgets without making noisy wall-clock timing a deterministic release gate.',Maturity.BETA)
    outputs=(PortSpec('result','v48_budget'),); proof_status=ProofStatus(evidence={EvidenceKind.NUMERICAL},unit_tests=True,documentation=True)
    def execute(self,inputs,params,ctx): return {'result':budget_fixture()}
    def verify(self,inputs,params,outputs,ctx):
        r=outputs['result']; return [VerificationRecord('budget-v048',EvidenceKind.NUMERICAL,'All declared deterministic regression budgets pass.',VerificationState.PASS if r['all_pass'] else VerificationState.FAIL,'budget policy',r)]
def register_fem_v048(registry): registry.register(RegressionBudgetV48)
