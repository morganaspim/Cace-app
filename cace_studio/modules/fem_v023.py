from __future__ import annotations
import numpy as np
from cace_studio.core.module import Module
from cace_studio.core.types import ModuleMetadata, PortSpec, ParameterSpec, ProofStatus, Maturity, EvidenceKind
from cace_studio.core.verification import VerificationRecord, VerificationState

def gpu_dense_equivalence(n=48,seed=23):
    rng=np.random.default_rng(seed); A=rng.normal(size=(n,n)); B=rng.normal(size=(n,n)); cpu=A@B
    try:
        import cupy as cp
        gpu=cp.asnumpy(cp.asarray(A)@cp.asarray(B)); err=float(np.max(np.abs(cpu-gpu)))
        return {'available':True,'backend':'cupy/cuda','n':n,'max_abs_error':err,'passed':err<=1e-10}
    except Exception as e:
        return {'available':False,'backend':'cupy/cuda','n':n,'reason':str(e),'passed':False}

class GPUFrontalEquivalenceV23(Module):
    metadata=ModuleMetadata('fem23.gpu_frontal_equivalence','Optional GPU Dense-Frontal Equivalence','0.23.0','Backend Equivalence','Compare CPU dense-block products with CuPy/CUDA when available.',Maturity.EXPERIMENTAL)
    parameters=(ParameterSpec('n','integer',48),); outputs=(PortSpec('result','gpu_equivalence_v23'),)
    proof_status=ProofStatus(evidence={EvidenceKind.NUMERICAL},unit_tests=True,documentation=True,limitations=['GPU evidence is conditional on CuPy/CUDA availability','dense product equivalence is not a full sparse-solver proof'])
    def execute(self,inputs,params,ctx): return {'result':gpu_dense_equivalence(int(params['n']))}
    def verify(self,inputs,params,outputs,ctx):
        r=outputs['result']
        if not r['available']:
            return [VerificationRecord('gpu-v023',EvidenceKind.NUMERICAL,'GPU frontal equivalence was not run because CuPy/CUDA is unavailable.',VerificationState.NOT_RUN,'conditional GPU backend',{'reason':r.get('reason','unavailable')})]
        return [VerificationRecord('gpu-v023',EvidenceKind.NUMERICAL,'GPU and CPU dense frontal kernels agree within tolerance.',VerificationState.PASS if r['passed'] else VerificationState.FAIL,'CPU↔GPU comparison',{'max_abs_error':r['max_abs_error']})]

def register_fem_v023(registry): registry.register(GPUFrontalEquivalenceV23)
