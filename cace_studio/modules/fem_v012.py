from __future__ import annotations
import math, os
import numpy as np
from cace_studio.core.module import Module
from cace_studio.core.native_runtime import NativeRuntime
from cace_studio.core.types import ModuleMetadata, PortSpec, ParameterSpec, ProofStatus, Maturity, EvidenceKind
from cace_studio.core.verification import VerificationRecord, VerificationState
from cace_studio.modules.fem_nd import _dense


def _dorfler_reference(eta,theta):
    e=[float(x) for x in eta]; w=[x*x for x in e]; target=float(theta)*sum(w); order=sorted(range(len(e)),key=lambda i:(-w[i],i)); out=[]; acc=0.0
    for i in order:
        out.append(i); acc+=w[i]
        if acc>=target: break
    return sorted(out)

class RuntimeBackendAudit(Module):
    metadata=ModuleMetadata('runtime12.backend_audit','Native/GPU Backend Audit','0.12.0','Runtime',
        'Report which accelerated backends are actually available. Availability is provenance only and creates no mathematical proof evidence.',Maturity.BETA)
    outputs=(PortSpec('backend_status','backend_status_v12'),)
    proof_status=ProofStatus(evidence={EvidenceKind.EXPERIMENTAL},unit_tests=True,documentation=True,limitations=['backend availability is not a correctness certificate'])
    def execute(self,inputs,params,ctx):
        rt=NativeRuntime()
        try:
            import cupy as cp; gpu=cp.cuda.runtime.getDeviceCount()>0; cupy_version=cp.__version__
        except Exception as e:
            gpu=False; cupy_version=''; gpu_reason=str(e)
        else: gpu_reason=''
        return {'backend_status':{'native_available':rt.status.available,'native_backend':rt.status.backend,'native_version':rt.status.version,'native_path':rt.status.path,'native_reason':rt.status.reason,
            'gpu_available':bool(gpu),'gpu_backend':'cupy-cuda' if gpu else 'unavailable','cupy_version':cupy_version,'gpu_reason':gpu_reason}}
    def verify(self,inputs,params,outputs,ctx):
        s=outputs['backend_status']; ok=bool(s['native_available'])
        return [VerificationRecord('native-runtime-load-smoke-v012',EvidenceKind.EXPERIMENTAL,'C++20 C ABI runtime can be loaded and reports its version',VerificationState.PASS if ok else VerificationState.NOT_RUN,'dynamic-library load plus exported version symbol',s)]

class NativeSparseEquivalence(Module):
    metadata=ModuleMetadata('runtime12.sparse_equivalence','C++/Python Sparse Kernel Equivalence','0.12.0','Runtime',
        'Compare C++20 CSR matvec/residual kernels with the Python/NumPy reference path on the exact stored discrete system.',Maturity.BETA,
        assumptions=('same binary64 CSR data is supplied to both backends',))
    inputs=(PortSpec('system','linear_system_nd'),PortSpec('solution','fem_solution_nd'))
    outputs=(PortSpec('equivalence','backend_equivalence_v12'),)
    parameters=(ParameterSpec('atol','number',1e-13),)
    proof_status=ProofStatus(evidence={EvidenceKind.NUMERICAL},unit_tests=True,property_tests=True,documentation=True,limitations=['numerical backend equivalence is not formal proof of the C++ implementation'])
    def execute(self,inputs,params,ctx):
        rt=NativeRuntime(); csr=inputs['system']['matrix']; x=np.asarray(inputs['solution']['interior'],float); b=np.asarray(inputs['system']['rhs'],float); A=_dense(csr)
        py_y=A@x; py_r=float(np.linalg.norm(py_y-b,np.inf)) if len(b) else 0.0
        if not rt.status.available:
            return {'equivalence':{'ran':False,'reason':rt.status.reason,'native_status':rt.status.__dict__}}
        native_y=rt.csr_matvec(csr,x); native_r=rt.csr_residual_inf(csr,x,b); diff=float(np.max(np.abs(native_y-py_y))) if len(py_y) else 0.0
        return {'equivalence':{'ran':True,'native_version':rt.status.version,'matvec_max_abs_diff':diff,'python_residual_inf':py_r,'native_residual_inf':native_r,
            'residual_abs_diff':abs(native_r-py_r),'atol':float(params['atol']),'nnz':len(csr['data']),'rows':int(csr['shape'][0])}}
    def verify(self,inputs,params,outputs,ctx):
        e=outputs['equivalence']
        if not e.get('ran'): return [VerificationRecord('cpp-python-sparse-equivalence-v012',EvidenceKind.NUMERICAL,'native sparse backend was unavailable',VerificationState.NOT_RUN,'backend availability gate',e)]
        ok=e['matvec_max_abs_diff']<=e['atol'] and e['residual_abs_diff']<=e['atol']
        return [VerificationRecord('cpp-python-sparse-equivalence-v012',EvidenceKind.NUMERICAL,'C++ CSR matvec and residual agree with the NumPy reference path within the declared tolerance',VerificationState.PASS if ok else VerificationState.FAIL,'independent execution of identical stored CSR data',e)]

class NativeAdaptiveMarkingEquivalence(Module):
    metadata=ModuleMetadata('runtime12.adaptive_marking_equivalence','C++/Python Dörfler Marking Equivalence','0.12.0','Runtime',
        'Replay every adaptive iteration through the native Dörfler-marking kernel and compare selected cells with the Python reference history.',Maturity.BETA)
    inputs=(PortSpec('adaptive_run','certified_adaptive_history'),)
    outputs=(PortSpec('equivalence','adaptive_backend_equivalence_v12'),)
    parameters=(ParameterSpec('theta','number',0.5),)
    proof_status=ProofStatus(evidence={EvidenceKind.NUMERICAL},unit_tests=True,documentation=True)
    def execute(self,inputs,params,ctx):
        rt=NativeRuntime(); theta=float(params['theta']); hist=inputs['adaptive_run']['iterations']
        if not rt.status.available: return {'equivalence':{'ran':False,'reason':rt.status.reason}}
        rec=[]; all_match=True
        for r in hist:
            native=rt.dorfler_mark(r['element_eta'],theta); reference=_dorfler_reference(r['element_eta'],theta); stored=sorted(map(int,r.get('marked_cells',[])))
            match=(native==reference==stored); all_match &= match
            rec.append({'iteration':r['iteration'],'native':native,'reference':reference,'stored':stored,'match':match})
        return {'equivalence':{'ran':True,'all_match':all_match,'theta':theta,'iterations':rec,'native_version':rt.status.version}}
    def verify(self,inputs,params,outputs,ctx):
        e=outputs['equivalence']; state=VerificationState.NOT_RUN if not e.get('ran') else (VerificationState.PASS if e['all_match'] else VerificationState.FAIL)
        return [VerificationRecord('cpp-python-dorfler-equivalence-v012',EvidenceKind.NUMERICAL,'native Dörfler marking selects exactly the same cells as the Python reference and stored adaptive history',state,'iteration-by-iteration replay',e)]

class GPUReferenceEquivalence(Module):
    metadata=ModuleMetadata('runtime12.gpu_equivalence','GPU/CPU Linear Algebra Equivalence','0.12.0','Runtime',
        'When CUDA/CuPy is available, compare GPU and CPU matvec/residual results on the same stored FEM system.',Maturity.BETA)
    inputs=(PortSpec('system','linear_system_nd'),PortSpec('solution','fem_solution_nd'))
    outputs=(PortSpec('equivalence','backend_equivalence_v12'),)
    parameters=(ParameterSpec('atol','number',1e-11),)
    supports_gpu=True
    proof_status=ProofStatus(evidence={EvidenceKind.NUMERICAL},unit_tests=True,documentation=True,limitations=['GPU equivalence is numerical evidence, not interval or formal evidence'])
    def execute(self,inputs,params,ctx):
        try:
            import cupy as cp
            if cp.cuda.runtime.getDeviceCount()<1: raise RuntimeError('no CUDA device')
        except Exception as e: return {'equivalence':{'ran':False,'reason':str(e),'backend':'cupy-cuda'}}
        A=_dense(inputs['system']['matrix']); x=np.asarray(inputs['solution']['interior'],float); b=np.asarray(inputs['system']['rhs'],float)
        cpu=A@x; gpu=cp.asnumpy(cp.asarray(A)@cp.asarray(x)); cpu_r=float(np.linalg.norm(cpu-b,np.inf)) if len(b) else 0.0; gpu_r=float(cp.asnumpy(cp.linalg.norm(cp.asarray(gpu)-cp.asarray(b),ord=cp.inf))) if len(b) else 0.0
        diff=float(np.max(np.abs(cpu-gpu))) if len(cpu) else 0.0
        return {'equivalence':{'ran':True,'backend':'cupy-cuda','matvec_max_abs_diff':diff,'cpu_residual_inf':cpu_r,'gpu_residual_inf':gpu_r,'residual_abs_diff':abs(cpu_r-gpu_r),'atol':float(params['atol'])}}
    def verify(self,inputs,params,outputs,ctx):
        e=outputs['equivalence']; state=VerificationState.NOT_RUN if not e.get('ran') else (VerificationState.PASS if e['matvec_max_abs_diff']<=e['atol'] and e['residual_abs_diff']<=e['atol'] else VerificationState.FAIL)
        return [VerificationRecord('gpu-cpu-equivalence-v012',EvidenceKind.NUMERICAL,'CUDA/CuPy matvec and residual agree with the CPU reference within the declared tolerance',state,'same stored matrix/vector evaluated on both backends',e)]

class BackendEquivalenceSummary(Module):
    metadata=ModuleMetadata('runtime12.equivalence_summary','Runtime Equivalence Summary','0.12.0','Verification','Summarize native sparse, adaptive-marking, and GPU equivalence without elevating evidence.',Maturity.BETA)
    inputs=(PortSpec('sparse','backend_equivalence_v12'),PortSpec('adaptive','adaptive_backend_equivalence_v12'),PortSpec('gpu','backend_equivalence_v12'))
    outputs=(PortSpec('summary','runtime_equivalence_summary_v12'),)
    proof_status=ProofStatus(evidence={EvidenceKind.NUMERICAL},unit_tests=True,documentation=True)
    def execute(self,inputs,params,ctx):
        states={k:('pass' if v.get('ran') and v.get('all_match',v.get('matvec_max_abs_diff',math.inf)<=v.get('atol',-1) and v.get('residual_abs_diff',math.inf)<=v.get('atol',-1)) else ('not-run' if not v.get('ran') else 'fail')) for k,v in inputs.items()}
        return {'summary':{'states':states,'all_available_backends_agree':all(s!='fail' for s in states.values()),'note':'not-run backends contribute no equivalence evidence'}}
    def verify(self,inputs,params,outputs,ctx):
        s=outputs['summary']; ok=s['all_available_backends_agree']
        return [VerificationRecord('runtime-equivalence-summary-v012',EvidenceKind.NUMERICAL,'every accelerated backend that actually ran agrees with its reference path; unavailable backends remain not-run',VerificationState.PASS if ok else VerificationState.FAIL,'summary of backend-specific verifier results',s)]

def register_fem_v012(registry):
    for cls in (RuntimeBackendAudit,NativeSparseEquivalence,NativeAdaptiveMarkingEquivalence,GPUReferenceEquivalence,BackendEquivalenceSummary): registry.register(cls)
