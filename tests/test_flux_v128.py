from cace_studio.modules.flux_v126_130_common import local_reconstruction_audit

def test_local_equilibrium_exact():
    r=local_reconstruction_audit()
    assert r["pass"]
    assert r["balance_residual"] == "0"
