from __future__ import annotations
import hashlib,json
from cace_studio.modules.fem_v051_075_common import ResultModule
from cace_studio.core.types import ModuleMetadata, Maturity, EvidenceKind, ProofStatus, PortSpec

def _canon(x): return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def provenance_dag_root(nodes=None, edges=None):
    nodes = nodes or [{'id':'mesh','sha256':'a'*64},{'id':'solve','sha256':'b'*64},{'id':'verify','sha256':'c'*64}]
    edges = edges or [('mesh','solve'),('solve','verify')]
    ids={n['id'] for n in nodes}; valid=all(a in ids and b in ids for a,b in edges)
    payload={'nodes':sorted(nodes,key=lambda n:n['id']),'edges':sorted([list(e) for e in edges])}
    return {'pass':valid,'root':hashlib.sha256(_canon(payload)).hexdigest(),'node_count':len(nodes),'edge_count':len(edges)}
class ProvenanceDAGV51(ResultModule):
    fn=staticmethod(provenance_dag_root); module_id='fem51.provenance_dag'; label='Provenance DAG Root'; version='0.51.0'; description='Canonical content root for a provenance DAG.'; evidence_kind=EvidenceKind.SYMBOLIC
    metadata=ModuleMetadata(module_id,label,version,'Provenance',description,Maturity.BETA); proof_status=ProofStatus(evidence={EvidenceKind.SYMBOLIC},unit_tests=True,regression_tests=True,documentation=True)
def register_fem_v051(registry): registry.register(ProvenanceDAGV51)
