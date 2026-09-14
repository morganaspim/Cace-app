from __future__ import annotations
import time
from cace_studio.core.module import Module
from cace_studio.core.types import ModuleMetadata, PortSpec, ParameterSpec, ProofStatus, Maturity, EvidenceKind
from cace_studio.core.verification import VerificationRecord, VerificationState
from cace_studio.modules.fem_v017 import structured_square_p1_csr, sparse_exact_ldlt
from cace_studio.modules.fem_v018 import choose_orderings

def scaling_suite(sizes=(7,10,14,18)):
    rows=[]
    for s in sizes:
        csr=structured_square_p1_csr(s,s); t=time.perf_counter(); orders,metrics,winner=choose_orderings(csr,s,s); exact=sparse_exact_ldlt(csr,orders[winner],include_pattern=False); ms=(time.perf_counter()-t)*1e3
        rows.append({'grid':s,'dimension':csr['shape'][0],'input_nnz':len(csr['data']),'winner':winner,'fill':exact['fill_entries'],'factor_nnz':exact['factor_nnz'],'certified':bool(exact['certified'] and exact['exact_reconstruction']),'analysis_ms':ms})
    monotonic=all(rows[i]['dimension']<rows[i+1]['dimension'] for i in range(len(rows)-1))
    return {'rows':rows,'dimensions_strictly_increasing':monotonic,'all_certified':all(r['certified'] for r in rows),'scope':'structured 2D P1 stress suite; not a 3D continuum theorem'}

class ScalingStressV24(Module):
    metadata=ModuleMetadata('fem24.scaling_stress','Sparse Scaling Stress Suite','0.24.0','Benchmark','Run exact sparse-factor/order analysis across increasing structured 2D FEM systems.',Maturity.BETA)
    outputs=(PortSpec('suite','v24_scaling_suite'),)
    proof_status=ProofStatus(evidence={EvidenceKind.NUMERICAL,EvidenceKind.SYMBOLIC},unit_tests=True,regression_tests=True,benchmarked=True,documentation=True,limitations=['stress suite is structured 2D','timings are machine-dependent'])
    def execute(self,inputs,params,ctx): return {'suite':scaling_suite()}
    def verify(self,inputs,params,outputs,ctx):
        s=outputs['suite']; ok=s['dimensions_strictly_increasing'] and s['all_certified']
        return [VerificationRecord('scaling-v024',EvidenceKind.SYMBOLIC,'Every scaling case retains an exact sparse reconstruction certificate.',VerificationState.PASS if ok else VerificationState.FAIL,'multi-size exact factor regression',{'cases':len(s['rows']),'max_dimension':max(r['dimension'] for r in s['rows'])})]

def register_fem_v024(registry): registry.register(ScalingStressV24)
