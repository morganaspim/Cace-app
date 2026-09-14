from cace_studio.modules.flux_v126_130_common import rt0_reference_audit, qjson

def test_rt0_kronecker_flux_and_divergence():
    r=rt0_reference_audit()
    assert r["pass"]
    assert r["edge_flux_matrix"] == [["1","0","0"],["0","1","0"],["0","0","1"]]
    assert qjson({"a":1}).endswith("\n\n")
