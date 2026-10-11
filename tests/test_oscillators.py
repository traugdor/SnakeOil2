import numpy as np
import pytest

from snakeoil2.dsp import oscillators as O
from tests.helpers import alias_power, naive_phase

SR = 44100


def test_duty_from_pwm_is_25_to_75_percent():
    assert O.duty_from_pwm(0.0) == pytest.approx(0.25)
    assert O.duty_from_pwm(0.5) == pytest.approx(0.5)
    assert O.duty_from_pwm(1.0) == pytest.approx(0.75)
    assert O.duty_from_pwm(-3) == pytest.approx(0.25)
    assert O.duty_from_pwm(9) == pytest.approx(0.75)


def test_phase_accumulator_is_continuous_across_blocks():
    a, b = O.Phase(), O.Phase()
    whole = a.advance(440.0, SR, 1000)
    parts = np.concatenate([b.advance(440.0, SR, 300), b.advance(440.0, SR, 700)])
    assert np.allclose(whole, parts, atol=1e-9)


@pytest.mark.parametrize("name,fn,naive", [
    ("saw", lambda t, dt: O.saw(t, dt), lambda t: 2 * t - 1),
    ("reverse saw", lambda t, dt: O.reverse_saw(t, dt), lambda t: 1 - 2 * t),
    ("inverted triangle", lambda t, dt: O.inverted_triangle(t, dt),
     lambda t: 4 * np.abs(np.mod(t + 0.25, 1.0) - 0.5) - 1),
    ("square", lambda t, dt: O.pulse(t, dt, 0.5), lambda t: np.where(t < 0.5, 1.0, -1.0)),
])
def test_band_limited_waves_alias_less_than_naive(name, fn, naive):
    f = 3000
    t, dt = naive_phase(f, SR)
    assert alias_power(fn(t, dt), f, SR) < 0.5 * alias_power(naive(t), f, SR)


@pytest.mark.parametrize("duty", [0.25, 0.4, 0.5, 0.6, 0.75])
def test_pulse_is_bounded_and_dc_free(duty):
    t, dt = naive_phase(220, SR)
    y = O.pulse(t, dt, duty)
    assert np.abs(y).max() <= 1.0 + 1e-9
    assert abs(float(y.mean())) < 0.01


def test_pulse_duty_is_the_high_fraction():
    t, dt = naive_phase(100, SR)
    y = O.pulse(t, dt, 0.25)
    assert (y > 0).mean() == pytest.approx(0.25, abs=0.01)
    y = O.pulse(t, dt, 0.75)
    assert (y > 0).mean() == pytest.approx(0.75, abs=0.01)


def test_waveform_shapes():
    t = np.array([0.0, 0.25, 0.5, 0.75])
    assert np.allclose(O.sine(t), [0.0, 1.0, 0.0, -1.0], atol=1e-12)
    # inverted triangle: starts at 0, falls to -1 at t=0.25, back to 0, up to +1 at t=0.75
    tri = O.inverted_triangle(t, 1e-9)
    assert np.allclose(tri, [0.0, -1.0, 0.0, 1.0], atol=1e-6)
    # reverse saw falls from +1 to -1
    rs = O.reverse_saw(np.array([0.1, 0.5, 0.9]), 1e-9)
    assert rs[0] > rs[1] > rs[2]


def test_osc2_shape_dispatch_and_unknown_wave():
    t, dt = naive_phase(220, SR)
    for wave in ("reverse saw", "inverted triangle", "sine", "square"):
        y = O.osc2_shape(wave, t, dt, 0.5)
        assert y.shape == t.shape and np.all(np.isfinite(y))
    with pytest.raises(ValueError):
        O.osc2_shape("nope", t, dt, 0.5)


def test_all_waves_stay_finite_at_extreme_frequencies():
    for f in (1, 20000, 22050 * 0.9):
        t, dt = naive_phase(int(f), SR)
        for fn in (O.saw, O.reverse_saw, O.inverted_triangle, O.sine):
            assert np.all(np.isfinite(fn(t, dt)))
        assert np.all(np.isfinite(O.pulse(t, dt, 0.25)))
