from __future__ import annotations
from cace_studio.core.module import Module
from cace_studio.core.types import ModuleMetadata, PortSpec, ProofStatus, Maturity, EvidenceKind
from cace_studio.core.verification import VerificationRecord, VerificationState
from cace_studio.modules.fem_v036 import replay_fingerprint
from cace_studio.modules.fem_v037 import certificate_fixture
from cace_studio.modules.fem_v038 import convergence_audit
from cace_studio.modules.fem_v039 import operator_health
from cace_studio.modules.fem_v040 import compensated_reduction_audit
from cace_studio.modules.fem_v041 import parameter_sweep
from cace_studio.modules.fem_v042 import scheduler_fixture
from cace_studio.modules.fem_v043 import ordering_portfolio
from cace_studio.modules.fem_v044 import factor_replay
from cace_studio.modules.fem_v045 import failure_reducer_fixture
from cace_studio.modules.fem_v046 import ledger_fixture
from cace_studio.modules.fem_v047 import scaling_3d
from cace_studio.modules.fem_v048 import budget_fixture

def qualification_matrix():
    parts={'replay':replay_fingerprint(),'schema':certificate_fixture(),'scaling':convergence_audit(),'health':operator_health(),'reduction':compensated_reduction_audit(),'sweep':parameter_sweep(),'scheduler':scheduler_fixture(),'ordering':ordering_portfolio(),'factor_replay':factor_replay(),'reducer':failure_reducer_fixture(),'ledger':ledger_fixture(),'scale3d':scaling_3d(),'budget':budget_fixture()}
    gates={'replay':parts['replay']['replay_equal'],'schema':parts['schema']['validation']['valid'],'scaling':parts['scaling']['all_certified'],'health':parts['health']['exact_spd_certificate'],'reduction':parts['reduction']['neumaier_error']==0,'sweep':parts['sweep']['all_certified'],'scheduler':parts['scheduler']['schedule'][-1]=='verify','ordering':bool(parts['ordering']['pareto_fill_front']),'factor_replay':parts['factor_replay']['stable'],'reducer':parts['reducer']['one_minimal'],'ledger':parts['ledger']['verified'],'scale3d':parts['scale3d']['all_certified'],'budget':parts['budget']['all_pass']}
    return {'release':'0.49.0','gates':gates,'all_pass':all(gates.values()),'parts':parts}
class QualificationMatrixV49(Module):
    metadata=ModuleMetadata('fem49.qualification','Release Qualification Matrix','0.49.0','Qualification','Compose v0.36-v0.48 deterministic gates without upgrading their evidence categories.',Maturity.BETA)
    outputs=(PortSpec('result','v49_qualification'),); proof_status=ProofStatus(evidence={EvidenceKind.SYMBOLIC,EvidenceKind.NUMERICAL},unit_tests=True,regression_tests=True,documentation=True)
    def execute(self,inputs,params,ctx): return {'result':qualification_matrix()}
    def verify(self,inputs,params,outputs,ctx):
        r=outputs['result']; return [VerificationRecord('qualification-v049',EvidenceKind.SYMBOLIC,'All deterministic release gates pass.',VerificationState.PASS if r['all_pass'] else VerificationState.FAIL,'qualification matrix',r['gates'])]
def register_fem_v049(registry): registry.register(QualificationMatrixV49)
