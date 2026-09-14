from cace_studio.modules.fem_v071 import memory_admission
def test_v071():
 assert memory_admission()['decision']=='ADMIT'; assert memory_admission(40_000_000,32_000_000)['decision']=='REFUSE'
