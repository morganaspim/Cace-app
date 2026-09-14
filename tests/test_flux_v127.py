from cace_studio.modules.flux_v126_130_common import hdiv_continuity_audit

def test_hdiv_shared_edge_signs():
    r=hdiv_continuity_audit()
    assert r["pass"] and r["normal_continuity"]
    assert r["interior_sign_pairs"] == [[1,-1]] or r["interior_sign_pairs"] == [[-1,1]]
