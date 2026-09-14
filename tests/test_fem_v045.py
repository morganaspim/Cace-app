from cace_studio.modules.fem_v045 import failure_reducer_fixture
def test_v045_reducer():
 r=failure_reducer_fixture(); assert r['still_fails'] and r['one_minimal']; assert r['reduced']==['tamper_provenance']
