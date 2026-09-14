from cace_studio.modules.fem_v051 import provenance_dag_root
def test_v051():
 a=provenance_dag_root(); b=provenance_dag_root(); assert a['pass'] and a['root']==b['root'] and len(a['root'])==64
