from cace_studio.modules.formal_v310 import *
from cace_studio.core.module import ExecutionContext

def test_formal_v310():
    m=FormalV310()
    out=m.execute({},m.resolved_params({}),ExecutionContext(run_id="v310"))
    r=out["result"]
    assert r.get("pass",True) is not False
    assert r["exact_checker"]["passed"] is True
    assert r["general_discrete_theorem_lean_checked"] is False

def test_formal_v310_rejects_tampered_orthogonality():
    from cace_studio.modules.formal_v301_320_common import discrete_ps_artifact
    from cace_studio.core.prager_synge_bridge import invoke_prager_synge_checker
    a=discrete_ps_artifact(); a['dual_error']=['1','2/5']
    r=invoke_prager_synge_checker(a)
    assert r['passed'] is False
    assert any('orthogonality' in e for e in r['errors'])

def test_formal_v310_rejects_broken_equilibrium():
    from cace_studio.modules.formal_v301_320_common import discrete_ps_artifact
    from cace_studio.core.prager_synge_bridge import invoke_prager_synge_checker
    a=discrete_ps_artifact(); a['flux_dofs'][0]='0'
    r=invoke_prager_synge_checker(a)
    assert r['passed'] is False
    assert any('equilibrium' in e for e in r['errors'])

def test_formal_v310_checker_is_cwd_independent(tmp_path, monkeypatch):
    from cace_studio.modules.formal_v301_320_common import discrete_ps_artifact
    from cace_studio.core.prager_synge_bridge import invoke_prager_synge_checker
    monkeypatch.chdir(tmp_path)
    r = invoke_prager_synge_checker(discrete_ps_artifact())
    assert r["passed"] is True
    assert r["cwd_independent"] is True
