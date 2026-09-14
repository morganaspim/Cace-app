from cace_studio.modules.fem_v034 import fault_injection_suite
def test_v034_faults_rejected():
 r=fault_injection_suite(); assert r['baseline_certified'] and r['all_faults_detected']
