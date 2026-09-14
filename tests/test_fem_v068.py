from cace_studio.modules.fem_v068 import certificate_dependency_graph
def test_v068():
 r=certificate_dependency_graph(); assert r['pass'] and r['unresolved']==['reliability_theorem'] and not r['promotable']['continuum']
