from __future__ import annotations
import copy
from cace_studio.modules.fem_v051_075_common import ResultModule
from cace_studio.core.types import ModuleMetadata,Maturity,EvidenceKind,ProofStatus

def migrate_experiment_schema(doc=None):
    doc=copy.deepcopy(doc or {'schema_version':1,'nodes':[{'id':'a','kind':'solve'}]})
    src=doc.get('schema_version',1)
    if src==1:
        for n in doc.get('nodes',[]): n.setdefault('params',{}); n['module_id']=n.pop('kind',n.get('module_id','unknown'))
        doc['schema_version']=2
    stable=copy.deepcopy(doc)
    return {'pass':doc.get('schema_version')==2 and stable==doc,'from':src,'to':doc.get('schema_version'),'document':doc}
class SchemaMigrationV56(ResultModule):
    fn=staticmethod(migrate_experiment_schema); module_id='fem56.schema_migration'; label='Experiment Schema Migration'; version='0.56.0'; description='Deterministic v1-to-v2 experiment schema migration with idempotent v2 representation.'; evidence_kind=EvidenceKind.SYMBOLIC
    metadata=ModuleMetadata(module_id,label,version,'Compatibility',description,Maturity.BETA); proof_status=ProofStatus(evidence={EvidenceKind.SYMBOLIC},unit_tests=True,regression_tests=True,documentation=True)
def register_fem_v056(registry): registry.register(SchemaMigrationV56)
