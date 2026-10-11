import pytest

from snakeoil2.dsp.tempo import TempoTracker


def test_clock_gives_bpm_and_times_out():
    t = TempoTracker()
    step = 60.0 / (120.0 * 24)
    for i in range(60):
        t.on_clock(i * step)
    assert t.external_bpm(now=60 * step) == pytest.approx(120.0, abs=0.5)
    assert t.external_bpm(now=60 * step + 5.0) is None
    assert t.effective_bpm(90.0, now=60 * step + 5.0) == 90.0
