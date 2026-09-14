from cace_studio.modules.fem_v073 import reproducibility_capsule
def test_v073():
 a=reproducibility_capsule(); b=reproducibility_capsule(); assert a['pass'] and a['sha256']==b['sha256']
