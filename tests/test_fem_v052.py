from cace_studio.modules.fem_v052 import deterministic_substreams
def test_v052():
 r=deterministic_substreams(); assert r['pass'] and r['stream_count']==4
