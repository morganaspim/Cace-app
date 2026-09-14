from __future__ import annotations
import time, numpy as np
from cace_studio.core.module import Module, ValidationError
from cace_studio.core.types import ModuleMetadata, PortSpec, ParameterSpec, ProofStatus, Maturity, EvidenceKind
from cace_studio.core.verification import VerificationRecord, VerificationState
from cace_studio.modules.fem_v020 import v020_benchmark

def dense_kernel_benchmark(n=96,repeats=3,seed=21):
    rng=np.random.default_rng(seed); A=rng.normal(size=(n,n)); B=rng.normal(size=(n,n))
    # warmup keeps lazy BLAS initialization out of timed samples
    C=A@B
    vals=[]
    for _ in range(max(1,repeats)):
        t=time.perf_counter(); C=A@B; vals.append((time.perf_counter()-t)*1e3)
    vals.sort(); ref=np.einsum('ik,kj->ij',A,B,optimize=True)
    err=float(np.max(np.abs(C-ref)))
    cfg=np.__config__
    info=str(cfg.show) if False else 'numpy.matmul (linked BLAS when available in NumPy build)'
    return {'n':n,'median_ms':vals[len(vals)//2],'max_abs_reference_error':err,'kernel':'numpy.matmul','backend_note':info,'flop_count':2*n**3,'gflops':(2*n**3)/(vals[len(vals)//2]*1e6) if vals[len(vals)//2]>0 else float('inf')}

def v021_benchmark(nx=14,ny=14,threads=4,repeats=2,dense_n=96):
    native=v020_benchmark(nx,ny,threads,max(1,repeats)); dense=dense_kernel_benchmark(dense_n,repeats)
    return {'native':native,'dense_kernel':dense,'policy':{'preferred_dense_kernel':'numpy.matmul/BLAS-backed reference benchmark','native_supernodal_kernel':'C++ dense-block loops','claim':'BLAS benchmark is a performance oracle; native structural correctness remains exact-rational'}}

class DenseKernelBenchmarkV21(Module):
    metadata=ModuleMetadata('fem21.dense_kernel_benchmark','BLAS Dense-Kernel Benchmark','0.21.0','Certified Linear Algebra','Benchmark a linked BLAS-backed dense kernel beside the native supernodal solve.',Maturity.BETA)
    parameters=(ParameterSpec('nx','integer',14),ParameterSpec('ny','integer',14),ParameterSpec('threads','integer',4),ParameterSpec('repeats','integer',2),ParameterSpec('dense_n','integer',96)); outputs=(PortSpec('benchmark','v21_benchmark'),)
    proof_status=ProofStatus(evidence={EvidenceKind.NUMERICAL,EvidenceKind.SYMBOLIC},unit_tests=True,benchmarked=True,documentation=True,limitations=['NumPy BLAS vendor is environment-dependent','native C++ supernodal kernel is not yet dynamically linked to vendor BLAS'])
    def execute(self,inputs,params,ctx): return {'benchmark':v021_benchmark(int(params['nx']),int(params['ny']),int(params['threads']),int(params['repeats']),int(params['dense_n']))}
    def verify(self,inputs,params,outputs,ctx):
        b=outputs['benchmark']; n=b['native']; ok=b['dense_kernel']['max_abs_reference_error']<=1e-10 and n['supernodal_thread_pool']['structure_matches_exact'] and n['supernodal_thread_pool']['max_solution_error']<=1e-10
        return [VerificationRecord('dense-kernel-v021',EvidenceKind.NUMERICAL,'BLAS-backed dense reference agrees numerically and native supernodal solve still matches the exact structural oracle.',VerificationState.PASS if ok else VerificationState.FAIL,'dense reference + native oracle comparison',{'dense_error':b['dense_kernel']['max_abs_reference_error'],'native_error':n['supernodal_thread_pool']['max_solution_error']})]

def register_fem_v021(registry): registry.register(DenseKernelBenchmarkV21)
