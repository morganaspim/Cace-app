from cace_studio.modules.fem_v026 import reproducibility_signature, canonical_fingerprint
def test_v026_stable():
 r=reproducibility_signature(6,6); assert r['stable'] and len(r['fingerprint'])==64
def test_v026_order_independent_json_keys():
 assert canonical_fingerprint({'b':1,'a':2})==canonical_fingerprint({'a':2,'b':1})
