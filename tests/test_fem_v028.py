from cace_studio.modules.fem_v028 import checkpoint_campaign, verify_chain
def test_v028_chain_and_tamper():
 r=checkpoint_campaign(); assert r['chain_valid'] and r['tamper_detected']
