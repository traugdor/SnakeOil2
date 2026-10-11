import numpy as np
import pytest

from snakeoil2.dsp.filters import LowPass, lpf_coefficients

SR = 44100


def _gain(freq, cutoff, reso):
    t = np.arange(SR) / SR
    x = np.sin(2 * np.pi * freq * t)
    y = LowPass(SR).process(x, lpf_coefficients(cutoff, reso, SR))
    return np.abs(y[SR // 2:]).max()


def test_passes_lows_and_cuts_highs_at_12_db_per_octave():
    assert _gain(100, 1000, 0.0) == pytest.approx(1.0, abs=0.02)
    assert _gain(4000, 1000, 0.0) < 0.1       # two octaves up: about -24 dB
    assert _gain(8000, 1000, 0.0) < 0.03      # three octaves up: about -36 dB


def test_resonance_peaks_at_the_cutoff():
    assert _gain(1000, 1000, 1.0) > 5.0
    assert _gain(1000, 1000, 0.0) < 1.0


def test_block_processing_matches_one_shot():
    rng = np.random.default_rng(1)
    x = rng.standard_normal(5000)
    c = lpf_coefficients(1500, 0.6, SR)
    whole = LowPass(SR).process(x, c)
    f = LowPass(SR)
    parts = np.concatenate([f.process(x[:1234], c), f.process(x[1234:], c)])
    assert np.allclose(whole, parts, atol=1e-12)


def test_extreme_coefficients_are_finite_and_stable():
    for cutoff in (-5.0, 20.0, 19000.0, 1e9):
        for reso in (-1.0, 0.0, 1.0, 5.0):
            c = lpf_coefficients(cutoff, reso, SR)
            y = LowPass(SR).process(np.ones(2000), c)
            assert np.all(np.isfinite(y)) and np.abs(y).max() < 50
