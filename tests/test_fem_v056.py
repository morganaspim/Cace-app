from cace_studio.modules.fem_v056 import migrate_experiment_schema
def test_v056():
 r=migrate_experiment_schema(); assert r['pass'] and r['to']==2 and r['document']['nodes'][0]['params']=={}
