"""Future-stationary Vaidya horizon dynamics, exact spacetime model."""
import numpy as np
import pytest
from vaidya_horizons import compact_mass, compact_mass_prime, track_horizons

def test_stationary_before_and_after_flux():
    v=np.array([-1.,0.,.5,1.,3.])
    m=compact_mass(v)
    dm=compact_mass_prime(v)
    assert m[0] == m[1] == .65
    assert np.allclose(m[-2:], .85, rtol=0, atol=1e-14)
    assert abs(m[2]-.75)<1e-14
    assert dm[0] == dm[1] == dm[3] == dm[4] == 0.
    assert np.all(dm>=0)

def test_teleological_event_horizon_outside_apparent_horizon():
    out=track_horizons()
    v=out['v'];gap=out['r_event']-out['r_apparent']
    assert np.max(abs(gap[v>=1.])) < 2e-10
    assert min(gap[(v>=0)&(v<1)]) > 0
    assert gap[abs(v).argmin()] > .01
    assert out['event_horizon_future_stationary_assumption'] is True
    assert out['model_observed_astronomically'] is False

def test_independent_rk4_and_ivp_agree():
    out=track_horizons()
    assert out['max_two_integrator_disagreement'] < 3e-6
    assert out['max_geodesic_residual'] < 1e-4

def test_forbidden_nonpositive_initial_mass():
    with pytest.raises(ValueError):
        track_horizons(m0=0)
