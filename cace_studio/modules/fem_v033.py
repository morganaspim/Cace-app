from __future__ import annotations
import hashlib, json
from cace_studio.core.module import Module
from cace_studio.core.types import ModuleMetadata, PortSpec, ProofStatus, Maturity, EvidenceKind
from cace_studio.core.verification import VerificationRecord, VerificationState
from cace_studio.modules.fem_v026 import reproducibility_signature
from cace_studio.modules.fem_v029 import matrix_diagnostics

def _sha(b): return hashlib.sha256(b).hexdigest()
def provenance_bundle():
    items={'repro':reproducibility_signature(8,8),'diagnostics':matrix_diagnostics(8,8)}
    leaves={k:_sha(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()) for k,v in items.items()}
    root=_sha(''.join(f'{k}:{leaves[k]}' for k in sorted(leaves)).encode())
    manifest={'schema':'cace-content-bundle-v1','leaves':leaves,'root':root}
    return {'release':'0.33.0','items':items,'manifest':manifest,'verified':verify_bundle(items,manifest)}
def verify_bundle(items,manifest):
    leaves={k:_sha(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()) for k,v in items.items()}
    root=_sha(''.join(f'{k}:{leaves[k]}' for k in sorted(leaves)).encode())
    return leaves==manifest.get('leaves') and root==manifest.get('root')

class ProvenanceBundleV33(Module):
    metadata=ModuleMetadata('fem33.provenance_bundle','Content-Addressed Provenance Bundle','0.33.0','Provenance','Bundle heterogeneous experiment artifacts behind leaf hashes and a deterministic root digest.',Maturity.BETA)
    outputs=(PortSpec('result','v33_bundle'),)
    proof_status=ProofStatus(evidence={EvidenceKind.SYMBOLIC},unit_tests=True,documentation=True,limitations=['root digest is content addressing, not a digital signature'])
    def execute(self,inputs,params,ctx): return {'result':provenance_bundle()}
    def verify(self,inputs,params,outputs,ctx):
        r=outputs['result']; ok=r['verified'] and len(r['manifest']['root'])==64
        return [VerificationRecord('bundle-v033',EvidenceKind.SYMBOLIC,'Bundle leaf hashes and deterministic root digest verify against their content.',VerificationState.PASS if ok else VerificationState.FAIL,'content-addressed manifest',r['manifest'])]

def register_fem_v033(registry): registry.register(ProvenanceBundleV33)
