from __future__ import annotations
from cace_studio.modules.fem_v051_075_common import ResultModule
from cace_studio.core.types import ModuleMetadata,Maturity,EvidenceKind,ProofStatus

def permutation_roundtrip(v=(10,20,30,40),p=(2,0,3,1)):
    pv=[v[i] for i in p]; inv=[0]*len(p)
    for j,i in enumerate(p): inv[i]=j
    recovered=[pv[inv[i]] for i in range(len(v))]
    return {'pass':recovered==list(v) and sorted(p)==list(range(len(p))),'permuted':pv,'inverse':inv,'recovered':recovered}
class PermutationRoundtripV63(ResultModule):
    fn=staticmethod(permutation_roundtrip); module_id='fem63.permutation'; label='Sparse Permutation Roundtrip'; version='0.63.0'; description='Exact permutation/inverse-permutation roundtrip invariant used by reordered sparse solves.'; evidence_kind=EvidenceKind.SYMBOLIC
    metadata=ModuleMetadata(module_id,label,version,'Sparse Algebra',description,Maturity.BETA); proof_status=ProofStatus(evidence={EvidenceKind.SYMBOLIC},unit_tests=True,regression_tests=True,documentation=True)
def register_fem_v063(registry): registry.register(PermutationRoundtripV63)
