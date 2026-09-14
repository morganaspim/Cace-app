from cace_studio.modules.fem_v072 import solver_fallback_chain
def test_v072():
 r=solver_fallback_chain(); assert r['pass'] and r['selected']=='supernodal'; assert solver_fallback_chain({'dense':True})['selected']=='dense'
