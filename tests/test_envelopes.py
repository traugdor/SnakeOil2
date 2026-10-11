import numpy as np
import pytest

from snakeoil2.dsp.envelopes import ATTACK, IDLE, Envelope

SR = 44100


def test_adsr_shape():
    e = Envelope(SR, 0.01, 0.02, 0.5, 0.05)
    e.note_on()
    out = e.process(int(0.01 * SR) + 5)
    assert out.max() == pytest.approx(1.0)
    out = e.process(int(0.05 * SR))
    assert out[-1] == pytest.approx(0.5)
    e.note_off()
    rel = e.process(int(0.06 * SR))
    assert rel[-1] == 0.0 and e.stage == IDLE and not e.active


def test_block_split_is_identical():
    a, b = Envelope(SR, 0.01, 0.02, 0.5, 0.05), Envelope(SR, 0.01, 0.02, 0.5, 0.05)
    a.note_on(); b.note_on()
    whole = a.process(3000)
    parts = np.concatenate([b.process(1), b.process(1499), b.process(1500)])
    assert np.array_equal(whole, parts)


def test_forced_release_is_short():
    e = Envelope(SR, 0.001, 0.001, 1.0, 5.0)
    e.note_on(); e.process(500)
    e.note_off(release_s=0.010)
    out = e.process(int(0.011 * SR))
    assert out[-1] == 0.0


def test_retrigger_keeps_level_when_asked():
    e = Envelope(SR, 0.05, 0.1, 0.5, 0.5)
    e.note_on(); e.process(1000)
    level = e.level
    e.note_on(keep_level=True)
    assert e.stage == ATTACK and e.level == level
