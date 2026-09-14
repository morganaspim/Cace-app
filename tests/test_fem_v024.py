from cace_studio.modules.fem_v024 import scaling_suite

def test_scaling_suite_certifies_all_cases():
    s=scaling_suite((5,7,9)); assert s['dimensions_strictly_increasing']; assert s['all_certified']; assert len(s['rows'])==3
