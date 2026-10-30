import pytest
from free_runner_physics import evolve_exact_ellis, analytical_vaidya_check

def test_static_ellis_source_independent():
    result=evolve_exact_ellis(dx=.06)
    assert result['data_origin']=='EXACT_ANALYTIC_NOT_CHARACTERISTIC'
    assert result['errors']['r'] < .0003
    assert result['errors']['phi'] < .0001
    assert result['errors']['alpha'] < .0005

def test_second_order_grid_convergence():
    coarse=evolve_exact_ellis(dx=.12)
    middle=evolve_exact_ellis(dx=.06)
    fine=evolve_exact_ellis(dx=.03)
    for field in ('r','alpha','phi'):
        e0,e1,e2=(result['errors'][field] for result in (coarse,middle,fine))
        assert e0 > 3*e1
        assert e1 > 3*e2

def test_scalar_coefficient_negative_control():
    right=evolve_exact_ellis(dx=.06,scalar_factor=2)
    wrong=evolve_exact_ellis(dx=.06,scalar_factor=1)
    assert wrong['errors']['phi'] > right['errors']['phi'] * 30

def test_nonfinite_inputs_are_rejected():
    for bad in (0,-1,float('nan'),float('inf')):
        with pytest.raises(ValueError):
            evolve_exact_ellis(dx=bad)

def test_dynamic_vaidya_symbolically_solves_einstein_null_dust():
    residuals=analytical_vaidya_check()
    assert all(value==0 for value in residuals.values())
