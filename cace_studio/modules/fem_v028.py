from __future__ import annotations
import hashlib, json
from cace_studio.core.module import Module
from cace_studio.core.types import ModuleMetadata, PortSpec, ProofStatus, Maturity, EvidenceKind
from cace_studio.core.verification import VerificationRecord, VerificationState
from cace_studio.modules.fem_v024 import scaling_suite

def _h(obj): return hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def checkpoint_chain(rows):
    prev='0'*64; out=[]
    for i,row in enumerate(rows):
        payload={'index':i,'previous':prev,'row':row}; digest=_h(payload); out.append({**payload,'digest':digest}); prev=digest
    return out

def verify_chain(chain):
    prev='0'*64
    for i,c in enumerate(chain):
        payload={'index':i,'previous':prev,'row':c['row']}
        if c.get('previous')!=prev or _h(payload)!=c.get('digest'): return False
        prev=c['digest']
    return True

def checkpoint_campaign():
    suite=scaling_suite((6,8,10)); chain=checkpoint_chain(suite['rows'])
    tampered=json.loads(json.dumps(chain)); tampered[1]['row']['fill']+=1
    return {'release':'0.28.0','checkpoints':chain,'chain_valid':verify_chain(chain),'tamper_detected':not verify_chain(tampered),'terminal_digest':chain[-1]['digest'],'all_certified':suite['all_certified']}

class CheckpointChainV28(Module):
    metadata=ModuleMetadata('fem28.checkpoint_chain','Hash-Chained Checkpoints','0.28.0','Provenance','Persist ordered experiment checkpoints in a tamper-evident SHA-256 hash chain.',Maturity.BETA)
    outputs=(PortSpec('result','v28_checkpoint_chain'),)
    proof_status=ProofStatus(evidence={EvidenceKind.SYMBOLIC},unit_tests=True,documentation=True,limitations=['hash chaining detects content changes; it is not external timestamping or signing'])
    def execute(self,inputs,params,ctx): return {'result':checkpoint_campaign()}
    def verify(self,inputs,params,outputs,ctx):
        r=outputs['result']; ok=r['chain_valid'] and r['tamper_detected'] and r['all_certified']
        return [VerificationRecord('checkpoint-v028',EvidenceKind.SYMBOLIC,'Checkpoint chain validates and deliberate row tampering is detected.',VerificationState.PASS if ok else VerificationState.FAIL,'SHA-256 chained checkpoints',{'terminal_digest':r['terminal_digest']})]

def register_fem_v028(registry): registry.register(CheckpointChainV28)
