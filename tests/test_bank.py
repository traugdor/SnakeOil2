import numpy as np
import pytest

from snakeoil2.dsp.bank import Bank
from snakeoil2.dsp.params import BANK_KEYS, PARAMS

SR = 44100


def view(**over):
    d = {k: PARAMS.defaults()["a_" + k] for k in BANK_KEYS}
    d.update(over)
    return d


def run(p, blocks=8, n=256, note=60, velocity=1.0, seed=3):
    b = Bank(SR)
    b.note_on(note, velocity, False, np.random.default_rng(seed))
    out = [b.render(n, p, 261.6256, 0.0) for _ in range(blocks)]
    return b, np.concatenate(out)


def rms(x):
    return float(np.sqrt(np.mean(x * x)))


def test_default_bank_makes_sound_and_is_finite():
    _, y = run(view())
    assert rms(y) > 0.01 and np.all(np.isfinite(y))


def test_note_off_and_release_end_the_voice():
    b, _ = run(view(amp_release=0.02))
    b.note_off()
    for _ in range(10):
        b.render(256, view(amp_release=0.02), 261.6, 0.0)
    assert not b.active


def test_deterministic_with_the_same_seed():
    assert np.array_equal(run(view())[1], run(view())[1])


def test_osc2_only_when_osc1_toggles_are_both_off():
    p = view(osc1_saw=False, osc1_square=False, mod_mode="OFF", osc2_level=0.5)
    _, y = run(p)
    assert rms(y) > 0.01


@pytest.mark.parametrize("mode,expect", [("OFF", "sound"), ("FM", "sound"), ("AM", "half"),
                                         ("RING", "silent"), ("SYNC", "sound")])
def test_osc1_toggles_off_per_modulation_mode(mode, expect):
    free = view(osc1_saw=False, osc1_square=False, mod_mode="OFF", osc2_level=0.5, osc2_wave="sine",
                osc1_level=0.0, cutoff=20000.0)
    mod = dict(free, mod_mode=mode)
    _, ref = run(free)
    _, y = run(mod)
    if expect == "silent":
        assert rms(y) < 1e-9
    elif expect == "half":
        assert rms(y) == pytest.approx(0.5 * rms(ref), rel=0.02)
    else:
        assert rms(y) == pytest.approx(rms(ref), rel=0.02)


def test_ring_is_silent_when_osc1_level_is_irrelevant_but_osc1_live():
    p = view(osc1_saw=True, mod_mode="RING", osc1_level=0.0, osc2_level=0.5, cutoff=20000.0)
    _, y = run(p)
    assert rms(y) > 0.01        # OSC1 still modulates even though it is not audible


def test_osc1_level_zero_removes_osc1_from_the_mix():
    p = view(osc1_level=0.0, osc2_level=0.0)
    _, y = run(p)
    assert rms(y) == 0.0


def test_each_modulation_mode_changes_the_sound():
    base = dict(osc1_saw=True, osc2_level=0.8, osc1_level=0.0, osc2_wave="sine", cutoff=20000.0)
    outs = {m: run(view(mod_mode=m, **base))[1] for m in ("OFF", "FM", "AM", "RING", "SYNC")}
    keys = list(outs)
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            assert not np.allclose(outs[a], outs[b], atol=1e-6), (a, b)


def test_every_osc2_wave_renders():
    for wave in ("reverse saw", "inverted triangle", "sine", "square"):
        _, y = run(view(osc2_wave=wave, osc1_level=0.0))
        assert rms(y) > 0.005, wave


def test_layering_saw_and_square_is_louder_than_either_alone():
    base = dict(osc2_level=0.0, osc1_level=1.0, cutoff=20000.0)
    both = rms(run(view(osc1_saw=True, osc1_square=True, **base))[1])
    saw = rms(run(view(osc1_saw=True, osc1_square=False, **base))[1])
    square = rms(run(view(osc1_saw=False, osc1_square=True, **base))[1])
    assert both > saw and both > square


def test_layering_does_not_change_the_modulation_depth():
    base = dict(mod_mode="RING", osc2_level=0.8, osc1_level=0.0, osc2_wave="sine", cutoff=20000.0)
    peak = np.abs(run(view(osc1_saw=True, osc1_square=True, **base))[1]).max()
    # amp 0.22 x osc2 level 0.8 x modulator <= 1: a layer that reached 2 would exceed this bound
    assert peak <= 0.22 * 0.8 * 1.02


def test_filter_darkens_and_20k_is_bypass():
    _, dark = run(view(cutoff=300.0, osc2_level=0.0))
    _, bright = run(view(cutoff=20000.0, osc2_level=0.0))
    assert rms(dark) < rms(bright)
    assert np.all(np.isfinite(bright))


def test_filter_env_and_keytrack_move_the_cutoff():
    flat = run(view(cutoff=500.0, osc2_level=0.0))[1]
    env = run(view(cutoff=500.0, osc2_level=0.0, flt_amount=1.0, flt_sustain=1.0))[1]
    key = run(view(cutoff=500.0, osc2_level=0.0, keytrack=1.0), note=84)[1]
    assert rms(env) > rms(flat) and rms(key) > rms(flat)


def test_noise_goes_through_the_filter():
    p = view(osc1_level=0.0, osc2_level=0.0, noise_level=1.0)
    _, open_ = run(dict(p, cutoff=20000.0))
    _, shut = run(dict(p, cutoff=100.0))
    assert rms(open_) > 5 * rms(shut)


def test_noise_colours_differ():
    p = view(osc1_level=0.0, osc2_level=0.0, noise_level=1.0, cutoff=20000.0)
    w = run(dict(p, noise_color="white"))[1]
    b = run(dict(p, noise_color="brown"))[1]
    assert not np.allclose(w, b)


def test_pitch_follows_extra_cents():
    def peak_hz(cents):
        b = Bank(SR)
        b.note_on(60, 1.0, False, np.random.default_rng(1))
        p = view(osc1_saw=False, osc1_square=False, osc2_wave="sine", osc2_level=1.0,
                 osc2_octave_up=False, cutoff=20000.0, amp_attack=0.001, amp_decay=5.0, amp_sustain=1.0)
        y = np.concatenate([b.render(256, p, 220.0, cents) for _ in range(160)])
        spec = np.abs(np.fft.rfft(y * np.hanning(len(y))))
        return np.argmax(spec) * SR / len(y)

    assert peak_hz(0.0) == pytest.approx(220.0, abs=2.0)
    assert peak_hz(1200.0) == pytest.approx(440.0, abs=3.0)


def test_stolen_note_keeps_the_envelope_level():
    b, _ = run(view())
    level = b.env.level
    b.note_off()
    b.render(64, view(), 261.6, 0.0)
    before = b.env.level
    b.note_on(62, 1.0, True, np.random.default_rng(1))
    assert b.env.level == pytest.approx(before) and before < level + 1e-9


def test_extreme_settings_stay_finite():
    p = view(cutoff=20.0, resonance=1.0, flt_amount=1.0, keytrack=1.0, vel_cutoff=1.0, mod_mode="FM",
             osc2_level=1.0, osc1_level=1.0, noise_level=1.0, osc1_square=True)
    _, y = run(p, note=127)
    assert np.all(np.isfinite(y))
