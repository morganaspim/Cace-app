from __future__ import annotations
from fractions import Fraction
from cace_studio.modules.fem_v051_075_common import ResultModule
from cace_studio.core.types import ModuleMetadata,Maturity,EvidenceKind,ProofStatus

def exact_residual_witness(A=None,x=None,b=None):
    A=A or [[2.0,-1.0],[-1.0,2.0]]; x=x or [1.0,2.0]; b=b or [0.0,3.0]
    Af=[[Fraction.from_float(v) for v in row] for row in A]; xf=[Fraction.from_float(v) for v in x]; bf=[Fraction.from_float(v) for v in b]
    r=[sum(Af[i][j]*xf[j] for j in range(len(xf)))-bf[i] for i in range(len(Af))]
    return {'pass':all(v==0 for v in r),'residual':[str(v) for v in r],'dimension':len(r)}
class ExactResidualV54(ResultModule):
    fn=staticmethod(exact_residual_witness); module_id='fem54.exact_residual'; label='Exact Residual Witness'; version='0.54.0'; description='Exact rational residual witness for the stored binary64 linear system.'; evidence_kind=EvidenceKind.SYMBOLIC
    metadata=ModuleMetadata(module_id,label,version,'Verification',description,Maturity.BETA); proof_status=ProofStatus(evidence={EvidenceKind.SYMBOLIC},unit_tests=True,regression_tests=True,documentation=True)
def register_fem_v054(registry): registry.register(ExactResidualV54)
