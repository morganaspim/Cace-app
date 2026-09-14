from __future__ import annotations
import hashlib,json
from cace_studio.core.module import Module
from cace_studio.core.types import ModuleMetadata, PortSpec, ProofStatus, Maturity, EvidenceKind
from cace_studio.core.verification import VerificationRecord, VerificationState

def _h(x): return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def build_ledger(events):
    chain=[]; prev='0'*64
    for i,e in enumerate(events):
        rec={'index':i,'prev':prev,'event':e}; digest=_h(rec); chain.append({**rec,'sha256':digest}); prev=digest
    return chain
def verify_ledger(chain):
    prev='0'*64
    for i,r in enumerate(chain):
        body={'index':i,'prev':prev,'event':r['event']}
        if r.get('index')!=i or r.get('prev')!=prev or r.get('sha256')!=_h(body): return False
        prev=r['sha256']
    return True
def ledger_fixture():
    c=build_ledger([{'kind':'assemble','status':'PASS'},{'kind':'factor','status':'PASS'},{'kind':'solve','status':'PASS'}])
    return {'release':'0.46.0','chain':c,'verified':verify_ledger(c),'head':c[-1]['sha256']}
class EvidenceLedgerV46(Module):
    metadata=ModuleMetadata('fem46.evidence_ledger','Append-Only Evidence Ledger','0.46.0','Provenance','Hash-chain verification events so mutation/reordering invalidates the ledger.',Maturity.BETA)
    outputs=(PortSpec('result','v46_ledger'),); proof_status=ProofStatus(evidence={EvidenceKind.SYMBOLIC},unit_tests=True,documentation=True,limitations=['hash chain provides integrity, not external identity/authentication'])
    def execute(self,inputs,params,ctx): return {'result':ledger_fixture()}
    def verify(self,inputs,params,outputs,ctx):
        r=outputs['result']; ok=r['verified'] and len(r['head'])==64
        return [VerificationRecord('ledger-v046',EvidenceKind.SYMBOLIC,'Evidence hash chain verifies from genesis through head.',VerificationState.PASS if ok else VerificationState.FAIL,'hash-chain ledger',{'head':r['head']})]
def register_fem_v046(registry): registry.register(EvidenceLedgerV46)
