import numpy as np

from snakeoil2.dsp.params import BANK_KEYS, PARAMS
from snakeoil2.dsp.voice import Voice

SR = 44100


def views(**over_a):
    a = {k: PARAMS.defaults()["a_" + k] for k in BANK_KEYS}
    a.update(over_a)
    b = {k: PARAMS.defaults()["b_" + k] for k in BANK_KEYS}
    return a, b


def make(note=60):
    v = Voice(SR)
    v.note_on(note, 1.0, 1, False, np.random.default_rng(1))
    return v


def test_centered_banks_are_mono():
    v = make()
    a, b = views()
    out = np.concatenate([v.render(256, a, b, 261.6, 0, 0, 0.7, 0.7, 0.0, 0.0) for _ in range(6)], axis=1)
    assert np.array_equal(out[0], out[1]) and np.abs(out).max() > 0.01


def test_width_pans_bank_a_left_and_bank_b_right():
    v = make()
    a, b = views()
    out = np.concatenate([v.render(256, a, b, 261.6, 0, 0, 1, 0, -1.0, 1.0) for _ in range(6)], axis=1)
    assert np.abs(out[0]).max() > 0.01 and np.abs(out[1]).max() < 1e-12
    v = make()
    out = np.concatenate([v.render(256, a, b, 261.6, 0, 0, 0, 1, -1.0, 1.0) for _ in range(6)], axis=1)
    assert np.abs(out[1]).max() > 0.01 and np.abs(out[0]).max() < 1e-12


def test_voice_is_active_until_both_banks_finish():
    v = make()
    a, b = views(amp_release=0.001)
    b["amp_release"] = 0.5
    v.render(256, a, b, 261.6, 0, 0, 1, 1, 0, 0)
    v.note_off()
    for _ in range(8):
        v.render(256, a, b, 261.6, 0, 0, 1, 1, 0, 0)
    assert not v.a.active and v.b.active and v.active


def test_level_is_the_loudest_bank_envelope():
    v = make()
    a, b = views()
    v.render(256, a, b, 261.6, 0, 0, 1, 1, 0, 0)
    assert v.level == max(v.a.env.level, v.b.env.level)
