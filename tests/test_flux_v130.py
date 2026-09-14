from cace_studio.modules.flux_v126_130_common import prager_synge_certificate, prager_synge_contract

def test_prager_synge_guarantee_fixture():
    r=prager_synge_certificate()
    assert r["pass"] and r["guaranteed"]
    assert r["admissibility"]["exact_cell_equilibrium"]
    assert r["admissibility"]["hdiv_normal_continuity"]
    assert r["guaranteed_energy_error_upper_float"] > 0

def test_prager_synge_contract_refuses_missing_equilibrium():
    c=prager_synge_contract()
    good={"conforming_primal":True,"hdiv_flux":True,"exact_equilibrium":True,"homogeneous_dirichlet":True,"spd_diffusion":True}
    ok,miss=c.match(good); assert ok and not miss
    bad=dict(good); bad["exact_equilibrium"]=False
    ok,miss=c.match(bad); assert not ok and "exact_equilibrium" in miss
