from cace_studio.modules.fem_v020 import v020_benchmark
from cace_studio.modules.fem_v025 import select_solver, v025_consolidated

def test_selector_only_uses_verified_candidates():
    b=v020_benchmark(7,7,2,1); s=select_solver(b); assert s['selected'] in s['eligible']; assert len(s['eligible'])==4

def test_v025_consolidated_scope_and_scaling():
    r=v025_consolidated(7,7,2,1); assert r['scaling']['all_certified']; assert not r['scope']['continuum_pde_formally_verified']; assert not r['selection']['gpu_full_solver_selected']
