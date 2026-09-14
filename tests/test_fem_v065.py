from cace_studio.modules.fem_v065 import checkpoint_resume_equivalence
def test_v065():
 r=checkpoint_resume_equivalence(); assert r['pass'] and len(r['checkpoint']['prefix_hash'])==64
