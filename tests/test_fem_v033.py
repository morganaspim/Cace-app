import copy
from cace_studio.modules.fem_v033 import provenance_bundle, verify_bundle
def test_v033_bundle():
 r=provenance_bundle(); assert r['verified']
 bad=copy.deepcopy(r['items']); bad['diagnostics']['dimension']+=1; assert not verify_bundle(bad,r['manifest'])
