from cace_studio.modules.fem_v067 import fault_localization
def test_v067():
 r=fault_localization(); assert r['pass'] and r['fault_indices']==[5]
