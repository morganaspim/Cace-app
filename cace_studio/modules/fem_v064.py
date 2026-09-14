from __future__ import annotations
import numpy as np
from cace_studio.modules.fem_v051_075_common import ResultModule
from cace_studio.core.types import ModuleMetadata,Maturity,EvidenceKind,ProofStatus

def solve_residual_witness():
    A=np.array([[4.,-1.,0.],[-1.,4.,-1.],[0.,-1.,3.]]); x_ref=np.array([1.,2.,-1.]); b=A@x_ref; x=np.linalg.solve(A,b); r=A@x-b
    return {'pass':float(np.linalg.norm(r,np.inf))<1e-13 and float(np.max(np.abs(x-x_ref)))<1e-13,'residual_inf':float(np.linalg.norm(r,np.inf)),'solution_error_inf':float(np.max(np.abs(x-x_ref)))}
class SolveWitnessV64(ResultModule):
    fn=staticmethod(solve_residual_witness); module_id='fem64.solve_witness'; label='Solve Residual Witness'; version='0.64.0'; description='Deterministic known-solution and residual witness for a small SPD solve.'; evidence_kind=EvidenceKind.NUMERICAL
    metadata=ModuleMetadata(module_id,label,version,'Sparse Algebra',description,Maturity.BETA); proof_status=ProofStatus(evidence={EvidenceKind.NUMERICAL},unit_tests=True,regression_tests=True,documentation=True)
def register_fem_v064(registry): registry.register(SolveWitnessV64)
