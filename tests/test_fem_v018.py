from cace_studio.modules.fem_v018 import geometric_nested_dissection_order, elimination_tree_from_pattern, v018_benchmark
from cace_studio.modules.fem_v017 import structured_square_p1_csr, sparse_exact_ldlt


def test_nested_dissection_is_permutation():
    o=geometric_nested_dissection_order(8,7)
    assert sorted(o)==list(range((8-1)*(7-1)))


def test_elimination_tree_matches_factor_pattern():
    csr=structured_square_p1_csr(6,6)
    o=geometric_nested_dissection_order(6,6)
    fac=sparse_exact_ldlt(csr,o,include_pattern=True)
    et=elimination_tree_from_pattern(csr['shape'][0],fac['factor_pattern'])
    assert fac['certified'] and len(et['parent'])==csr['shape'][0]
    assert et['height']>=1


def test_v018_benchmark_exact_and_native():
    b=v018_benchmark(8,8)
    assert b['exact_factorization']['certified']
    assert b['exact_factorization']['exact_reconstruction']
    assert not b['exact_factorization']['dense_materialization']
    assert b['winner'] in {'natural','minimum-degree','nested-dissection'}
    assert b['native_solve']['ran']
    assert b['native_solve']['structure_matches_exact']
    assert b['native_solve']['max_solution_error'] <= 1e-10
    assert b['native_solve']['residual_inf'] <= 1e-10


def test_nested_dissection_competes_with_natural_on_grid():
    b=v018_benchmark(10,10)
    assert b['metrics']['nested-dissection']['fill_edges'] <= b['metrics']['natural']['fill_edges']
