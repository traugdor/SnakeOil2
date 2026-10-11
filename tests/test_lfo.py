import numpy as np
import pytest

from snakeoil2.dsp.lfo import LFO

SR = 44100


@pytest.mark.parametrize("wave", ["sine", "triangle", "saw", "square", "random", "random-glide"])
def test_values_are_bounded_and_deterministic(wave):
    def run():
        l = LFO(seed=3)
        return [l.next_block(256, SR, 5.0, wave)[0] for _ in range(400)]

    a = run()
    assert a == run()
    assert all(-1.0 - 1e-9 <= v <= 1.0 + 1e-9 for v in a)


def test_sine_period():
    l = LFO(seed=1)
    vals = [l.next_block(441, SR, 10.0, "sine")[0] for _ in range(100)]    # 1 s
    assert max(vals) > 0.99 and min(vals) < -0.99


def test_array_output_matches_length():
    _, s = LFO(seed=1).next_block(256, SR, 5.0, "triangle", want_array=True)
    assert s.shape == (256,)
