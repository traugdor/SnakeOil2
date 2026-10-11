import numpy as np

from snakeoil2.dsp.limiter import Limiter


def test_peaks_never_exceed_the_ceiling_and_the_hold_stays():
    l = Limiter(44100)
    x = np.zeros((2, 100)); x[:, 50] = 4.0
    y, peak = l.process(x)
    assert np.abs(y).max() <= 0.98 + 1e-9 and peak == 4.0
    hold = l.h
    y2, _ = l.process(np.full((2, 10), 0.1))
    assert l.h == hold and np.allclose(y2, 0.1 * (1.0 - hold))
    l.reset()
    y3, _ = l.process(np.full((2, 10), 0.1))
    assert np.array_equal(y3, np.full((2, 10), 0.1))
