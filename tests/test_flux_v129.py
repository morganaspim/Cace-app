from cace_studio.modules.flux_v126_130_common import global_equilibrium_audit

def test_global_hdiv_equilibrium_exact():
    r=global_equilibrium_audit()
    assert r["pass"]
    assert r["hdiv_normal_continuity"]
    assert r["max_exact_equilibrium_residual"] == "0"
