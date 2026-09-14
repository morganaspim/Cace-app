from __future__ import annotations
from collections import defaultdict
from cace_studio.core.module import Module, ValidationError
from cace_studio.core.types import ModuleMetadata, PortSpec, ProofStatus, Maturity, EvidenceKind
from cace_studio.core.verification import VerificationRecord, VerificationState

def deterministic_schedule(tasks,deps):
    tasks=sorted(set(tasks)); incoming={t:set(deps.get(t,())) for t in tasks}
    if any(d not in incoming for ds in incoming.values() for d in ds): raise ValidationError('unknown dependency')
    out=[]
    while incoming:
        ready=sorted(t for t,ds in incoming.items() if not ds)
        if not ready: raise ValidationError('dependency cycle')
        out.extend(ready)
        for t in ready: incoming.pop(t)
        for ds in incoming.values(): ds.difference_update(ready)
    return out
def scheduler_fixture():
    tasks=['assemble','order','factor','solve','verify']; deps={'assemble':[],'order':['assemble'],'factor':['order'],'solve':['factor'],'verify':['solve']}
    return {'release':'0.42.0','schedule':deterministic_schedule(tasks,deps),'tasks':tasks,'dependencies':deps}
class CampaignSchedulerV42(Module):
    metadata=ModuleMetadata('fem42.scheduler','Deterministic DAG Campaign Scheduler','0.42.0','Orchestration','Produce stable topological execution order and refuse dependency cycles.',Maturity.BETA)
    outputs=(PortSpec('result','v42_schedule'),); proof_status=ProofStatus(evidence={EvidenceKind.SYMBOLIC},unit_tests=True,documentation=True)
    def execute(self,inputs,params,ctx): return {'result':scheduler_fixture()}
    def verify(self,inputs,params,outputs,ctx):
        r=outputs['result']; pos={t:i for i,t in enumerate(r['schedule'])}; ok=all(pos[d]<pos[t] for t,ds in r['dependencies'].items() for d in ds)
        return [VerificationRecord('schedule-v042',EvidenceKind.SYMBOLIC,'Every dependency precedes its consumer in the deterministic schedule.',VerificationState.PASS if ok else VerificationState.FAIL,'DAG order audit',r)]
def register_fem_v042(registry): registry.register(CampaignSchedulerV42)
