from cace_studio.modules.fem_v055 import stopping_policy
def test_v055():
 assert stopping_policy()['decision']=='STOP'; r=stopping_policy('continuum_error',0,1); assert r['pass'] and r['decision']=='REFUSED'
