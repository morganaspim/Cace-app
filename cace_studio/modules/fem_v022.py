from __future__ import annotations
from cace_studio.core.module import Module
from cace_studio.core.types import ModuleMetadata, PortSpec, ParameterSpec, ProofStatus, Maturity, EvidenceKind
from cace_studio.core.verification import VerificationRecord, VerificationState
from cace_studio.modules.fem_v021 import v021_benchmark

def arena_plan(supernode_sizes, alignment=64, scalar_bytes=8):
    offsets=[]; cursor=0; peak=0
    for k in supernode_sizes:
        need=max(1,k*k)*scalar_bytes
        cursor=((cursor+alignment-1)//alignment)*alignment
        offsets.append(cursor); cursor+=need; peak=max(peak,cursor)
    return {'alignment':alignment,'scalar_bytes':scalar_bytes,'offsets':offsets,'reserved_bytes':cursor,'peak_reserved_bytes':peak,'blocks':len(supernode_sizes)}

def v022_memory_audit(nx=14,ny=14,threads=4,repeats=1):
    b=v021_benchmark(nx,ny,threads,repeats,32); sn=b['native']['symbolic_supernodes']; sizes=sn.get('sizes',[]) or [sn['max_size']]*sn['count']
    plan=arena_plan(sizes)
    rt=b['native']['supernodal_thread_pool']; runtime_peak=int(rt['peak_workspace_entries'])*8*max(1,int(rt['thread_count']))
    return {'benchmark':b,'arena_plan':plan,'runtime_workspace_upper_bytes':runtime_peak,'reuse_ratio':rt['workspace_reallocations']/max(1,rt['scheduled_tasks']),'claims':{'arena':'deterministic aligned planning model','runtime':'thread-local workspace instrumentation from native solver','rss':'not an OS RSS measurement'}}

class MemoryArenaAuditV22(Module):
    metadata=ModuleMetadata('fem22.memory_arena','Memory Arena + Workspace Audit','0.22.0','Runtime','Plan aligned supernode arenas and audit native thread-local workspace reuse.',Maturity.BETA)
    parameters=(ParameterSpec('nx','integer',14),ParameterSpec('ny','integer',14),ParameterSpec('threads','integer',4)); outputs=(PortSpec('audit','v22_memory_audit'),)
    proof_status=ProofStatus(evidence={EvidenceKind.NUMERICAL,EvidenceKind.SYMBOLIC},unit_tests=True,documentation=True,limitations=['arena is a deterministic planning model, not OS RSS','native runtime still uses thread-local vector workspaces'])
    def execute(self,inputs,params,ctx): return {'audit':v022_memory_audit(int(params['nx']),int(params['ny']),int(params['threads']))}
    def verify(self,inputs,params,outputs,ctx):
        a=outputs['audit']; p=a['arena_plan']; ok=p['blocks']>0 and all(x%p['alignment']==0 for x in p['offsets']) and 0<=a['reuse_ratio']<=1
        return [VerificationRecord('arena-v022',EvidenceKind.NUMERICAL,'Aligned arena plan is internally consistent and native workspace growth remains below per-task allocation.',VerificationState.PASS if ok else VerificationState.FAIL,'arena invariants + runtime counters',{'blocks':p['blocks'],'reuse_ratio':a['reuse_ratio']})]

def register_fem_v022(registry): registry.register(MemoryArenaAuditV22)
