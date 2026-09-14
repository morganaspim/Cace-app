from __future__ import annotations
import hashlib, json, random
from cace_studio.core.module import Module
from cace_studio.core.types import ModuleMetadata, PortSpec, ParameterSpec, ProofStatus, Maturity, EvidenceKind
from cace_studio.core.verification import VerificationRecord, VerificationState

def _canon(x): return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def replay_fingerprint(seed=2026036, draws=32):
    rng=random.Random(int(seed)); values=[rng.uniform(-1.0,1.0) for _ in range(int(draws))]
    payload={'seed':int(seed),'draws':int(draws),'values':values}
    digest=hashlib.sha256(_canon(payload)).hexdigest()
    rng2=random.Random(int(seed)); values2=[rng2.uniform(-1.0,1.0) for _ in range(int(draws))]
    return {'release':'0.36.0','payload':payload,'sha256':digest,'replay_equal':values==values2,'replay_sha256':hashlib.sha256(_canon({'seed':int(seed),'draws':int(draws),'values':values2})).hexdigest()}
class ReplayFingerprintV36(Module):
    metadata=ModuleMetadata('fem36.replay','Deterministic Replay Fingerprint','0.36.0','Provenance','Bind deterministic pseudo-random inputs to a canonical replay digest.',Maturity.BETA)
    parameters=(ParameterSpec('seed','integer',2026036),); outputs=(PortSpec('result','v36_replay'),)
    proof_status=ProofStatus(evidence={EvidenceKind.SYMBOLIC},unit_tests=True,documentation=True,limitations=['Python random algorithm/version is part of the replay environment'])
    def execute(self,inputs,params,ctx): return {'result':replay_fingerprint(int(params['seed']))}
    def verify(self,inputs,params,outputs,ctx):
        r=outputs['result']; ok=r['replay_equal'] and r['sha256']==r['replay_sha256']
        return [VerificationRecord('replay-v036',EvidenceKind.SYMBOLIC,'Seeded canonical replay reproduces the same byte-level digest.',VerificationState.PASS if ok else VerificationState.FAIL,'deterministic replay',{'sha256':r['sha256']})]
def register_fem_v036(registry): registry.register(ReplayFingerprintV36)
