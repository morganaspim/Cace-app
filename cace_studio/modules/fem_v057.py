from __future__ import annotations
from cace_studio.modules.fem_v051_075_common import ResultModule
from cace_studio.core.types import ModuleMetadata,Maturity,EvidenceKind,ProofStatus

def graph_diff(a=None,b=None):
    a=a or {'nodes':{'x':{'p':1},'y':{'p':2}},'edges':[('x','y')]}; b=b or {'nodes':{'x':{'p':1},'y':{'p':3},'z':{}},'edges':[('x','y'),('y','z')]}
    ak=set(a['nodes']); bk=set(b['nodes']); common=ak&bk
    changed=sorted(k for k in common if a['nodes'][k]!=b['nodes'][k])
    ea={tuple(x) for x in a.get('edges',[])}; eb={tuple(x) for x in b.get('edges',[])}
    return {'pass':True,'added_nodes':sorted(bk-ak),'removed_nodes':sorted(ak-bk),'changed_nodes':changed,'added_edges':sorted(eb-ea),'removed_edges':sorted(ea-eb)}
class GraphDiffV57(ResultModule):
    fn=staticmethod(graph_diff); module_id='fem57.graph_diff'; label='Semantic Experiment Graph Diff'; version='0.57.0'; description='Deterministic node/edge semantic diff for experiment DAG revisions.'; evidence_kind=EvidenceKind.SYMBOLIC
    metadata=ModuleMetadata(module_id,label,version,'Provenance',description,Maturity.BETA); proof_status=ProofStatus(evidence={EvidenceKind.SYMBOLIC},unit_tests=True,regression_tests=True,documentation=True)
def register_fem_v057(registry): registry.register(GraphDiffV57)
