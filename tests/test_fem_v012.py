import json, shutil, subprocess
import numpy as np
from pathlib import Path
from cace_studio.core.module import ExecutionContext
from cace_studio.core.native_runtime import NativeRuntime
from cace_studio.modules.fem_nd import SimplexMeshND,P1SimplexSpaceND,PoissonAssemblyND,LinearSolverND
from cace_studio.modules.fem_v011 import CertifiedAdaptiveSolveLoop2D
from cace_studio.modules.fem_v012 import RuntimeBackendAudit,NativeSparseEquivalence,NativeAdaptiveMarkingEquivalence,GPUReferenceEquivalence

def ctx(): return ExecutionContext(run_id='test-v012')
def mesh():
 p={'vertices':json.dumps([[0,0],[1,0],[1,1],[0,1],[.5,.5]]),'elements':json.dumps([[0,1,4],[1,2,4],[2,3,4],[3,0,4]])}; m=SimplexMeshND(); return m.execute({},p,ctx())['mesh']
def system_solution():
 m=mesh(); sp=P1SimplexSpaceND().execute({'mesh':m},{},ctx())['space']; sy=PoissonAssemblyND().execute({'mesh':m,'space':sp},{'source':1.0},ctx())['system']; sol=LinearSolverND().execute({'system':sy},{},ctx())['solution']; return sy,sol

def test_native_runtime_cabi_available_and_kernels():
 rt=NativeRuntime(); assert rt.status.available and tuple(map(int,rt.status.version.split('.'))) >= (0,12,0)
 csr={'shape':[2,2],'data':[2.,-1.,-1.,2.],'indices':[0,1,0,1],'indptr':[0,2,4]}; x=[1.,2.]
 assert np.allclose(rt.csr_matvec(csr,x),[0.,3.]); assert rt.csr_residual_inf(csr,x,[0.,3.])==0.0
 assert rt.dorfler_mark([1.,2.,.5],.5)==[1]

def test_cpp_header_smoke_compiles_and_runs(tmp_path):
 if not shutil.which('g++'): return
 root=Path(__file__).resolve().parents[1]; exe=tmp_path/'smoke'
 subprocess.run(['g++','-std=c++20','-O2',str(root/'cpp/tests/runtime_smoke.cpp'),'-I'+str(root/'cpp/include'),'-o',str(exe)],check=True)
 out=subprocess.check_output([str(exe)],text=True); assert 'PASS' in out

def test_native_sparse_equivalence():
 sy,sol=system_solution(); mod=NativeSparseEquivalence(); out=mod.execute({'system':sy,'solution':sol},{'atol':1e-13},ctx()); assert out['equivalence']['ran']; assert mod.verify({}, {}, out, ctx())[0].passed

def test_native_adaptive_marking_equivalence():
 m=mesh(); adapt=CertifiedAdaptiveSolveLoop2D(); out=adapt.execute({'mesh':m},{'source':1.0,'theta':.5,'max_iterations':3,'stop_mode':'estimator_upper','tolerance':0.0},ctx())
 mod=NativeAdaptiveMarkingEquivalence(); eq=mod.execute({'adaptive_run':out['adaptive_run']},{'theta':.5},ctx()); assert eq['equivalence']['ran'] and eq['equivalence']['all_match']; assert mod.verify({}, {}, eq, ctx())[0].passed

def test_gpu_equivalence_is_pass_or_not_run():
 sy,sol=system_solution(); mod=GPUReferenceEquivalence(); out=mod.execute({'system':sy,'solution':sol},{'atol':1e-11},ctx()); rec=mod.verify({}, {}, out, ctx())[0]
 assert rec.state.value in ('pass','not-run')

def test_backend_audit_reports_native():
 mod=RuntimeBackendAudit(); out=mod.execute({}, {}, ctx()); assert out['backend_status']['native_available']; assert mod.verify({}, {}, out, ctx())[0].passed
