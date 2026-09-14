from cace_studio.modules.fem_v057 import graph_diff
def test_v057():
 r=graph_diff(); assert r['pass'] and r['added_nodes']==['z'] and r['changed_nodes']==['y']
