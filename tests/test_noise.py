import numpy as np
import pytest

from snakeoil2.dsp import noise


@pytest.mark.parametrize("color", noise.NOISE_COLORS)
def test_rms_is_the_same_for_every_colour(color):
    t = noise.table(color)
    assert np.sqrt(np.mean(t * t)) == pytest.approx(0.5, abs=1e-6)
    assert abs(t.mean()) < 1e-6


def test_tables_are_cached_and_unknown_colour_raises():
    assert noise.table("pink") is noise.table("pink")
    with pytest.raises(KeyError):
        noise.table("blue")


def test_brown_is_darker_than_white():
    def hf_ratio(t):
        s = np.abs(np.fft.rfft(t[:65536])) ** 2
        return s[len(s) // 2:].sum() / s.sum()

    assert hf_ratio(noise.table("brown")) < hf_ratio(noise.table("pink")) < hf_ratio(noise.table("white"))
