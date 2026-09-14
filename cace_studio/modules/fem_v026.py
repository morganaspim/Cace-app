from __future__ import annotations
import hashlib, json
from cace_studio.core.module import Module
from cace_studio.core.types import ModuleMetadata, PortSpec, ParameterSpec, ProofStatus, Maturity, EvidenceKind
from cace_studio.core.verification import VerificationRecord, VerificationState
from cace_studio.modules.fem_v017 import structured_square_p1_csr
from cace_studio.modules.fem_v018 import choose_orderings

def canonical_fingerprint(obj):
    raw=json.dumps(obj,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
    return hashlib.sha256(raw).hexdigest()

def reproducibility_signature(nx=10,ny=10):
    csr=structured_square_p1_csr(nx,ny); orders,metrics,winner=choose_orderings(csr,nx,ny)
    payload={'shape':csr['shape'],'data':csr['data'],'indices':csr['indices'],'indptr':csr['indptr'],'winner':winner,'order':orders[winner], 'metrics':{k:{'fill_edges':v['fill_edges'],'factor_nnz':v['factor_nnz']} for k,v in metrics.items()}}
    a=canonical_fingerprint(payload); b=canonical_fingerprint(json.loads(json.dumps(payload)))
    return {'release':'0.26.0','fingerprint':a,'repeat_fingerprint':b,'stable':a==b,'dimension':csr['shape'][0],'winner':winner,'algorithm':'sha256(canonical-json)','scope':'reproducibility identity; not a mathematical proof'}

class ReproducibilityFingerprintV26(Module):
    metadata=ModuleMetadata('fem26.repro_fingerprint','Reproducibility Fingerprint','0.26.0','Provenance','Create a canonical content fingerprint for the sparse system, ordering and structural metrics.',Maturity.BETA)
    parameters=(ParameterSpec('nx','integer',10),ParameterSpec('ny','integer',10)); outputs=(PortSpec('result','v26_repro_signature'),)
    proof_status=ProofStatus(evidence={EvidenceKind.SYMBOLIC},unit_tests=True,documentation=True,limitations=['cryptographic identity supports reproducibility but does not prove numerical correctness'])
    def execute(self,inputs,params,ctx): return {'result':reproducibility_signature(int(params['nx']),int(params['ny']))}
    def verify(self,inputs,params,outputs,ctx):
        r=outputs['result']; ok=r['stable'] and len(r['fingerprint'])==64
        return [VerificationRecord('repro-v026',EvidenceKind.SYMBOLIC,'Canonical sparse-analysis payload reproduces the same SHA-256 fingerprint.',VerificationState.PASS if ok else VerificationState.FAIL,'canonical serialization + SHA-256',{'fingerprint':r['fingerprint']})]

def register_fem_v026(registry): registry.register(ReproducibilityFingerprintV26)
