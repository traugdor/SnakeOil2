import numpy as np
import pytest

from snakeoil2.dsp.engine import Engine


def rms(x):
    return float(np.sqrt(np.mean(x * x)))


def render(e, blocks=40):
    return np.concatenate([e.process(256) for _ in range(blocks)])


def row(e, i, src, scale, dst):
    e.set_param("mod%d_src" % i, src)
    e.set_param("mod%d_scale" % i, scale)
    e.set_param("mod%d_dst" % i, dst)


def test_empty_matrix_is_bit_identical_to_no_matrix():
    a = Engine(seed=2); b = Engine(seed=2)
    row(b, 1, "LFO 1", 0.0, "A: Cutoff")           # inactive row (scale 0)
    for e in (a, b):
        e.note_on(60, 100)
    assert np.array_equal(render(a, 10), render(b, 10))


def test_lfo_without_a_matrix_row_changes_nothing():
    a = Engine(seed=2); b = Engine(seed=2)
    b.set_param("lfo1_rate", 12.0); b.set_param("lfo1_wave", "square")
    for e in (a, b):
        e.note_on(60, 100)
    assert np.array_equal(render(a, 10), render(b, 10))


def test_mod_wheel_opens_the_filter_on_one_bank():
    def loud(wheel):
        e = Engine(seed=2)
        e.set_param("a_cutoff", 400.0); e.set_param("b_volume", 0.0)
        row(e, 1, "Mod Wheel", 1.0, "A: Cutoff")
        e.set_mod_wheel(wheel)
        e.note_on(60, 100)
        return rms(render(e, 30))

    assert loud(1.0) > loud(0.0) * 1.2


def test_lfo_pitch_row_makes_vibrato():
    def band_energy(scale):
        e = Engine(seed=2)
        for b in "ab":
            e.set_param(b + "_osc1_saw", False); e.set_param(b + "_osc1_level", 0.0)
            e.set_param(b + "_osc2_wave", "sine"); e.set_param(b + "_osc2_level", 1.0)
            e.set_param(b + "_cutoff", 20000.0); e.set_param(b + "_amp_sustain", 1.0)
        e.set_param("b_volume", 0.0)
        e.set_param("lfo1_rate", 6.0)
        row(e, 1, "LFO 1", scale, "A: Pitch")
        e.note_on(57, 127)
        y = render(e, 150)[:, 0]
        spec = np.abs(np.fft.rfft(y * np.hanning(len(y))))
        return float((spec > 0.1 * spec.max()).sum())

    assert band_energy(1.0) > band_energy(0.0)


def test_mix_destination_crossfades():
    e = Engine(seed=2)
    row(e, 1, "Aftertouch", 1.0, "Mix")
    e.set_param("a_volume", 0.8); e.set_param("b_volume", 0.0)
    e.note_on(60, 100)
    e.aftertouch(0.0); first = rms(render(e, 20))
    e2 = Engine(seed=2)
    row(e2, 1, "Aftertouch", 1.0, "Mix")
    e2.set_param("b_volume", 0.0)
    e2.aftertouch(1.0); e2.note_on(60, 100)
    # mix 0.5 base * (1 + 1) = 1.0 -> all bank B, which is muted
    for _ in range(10):
        e2.process(256)
    assert rms(render(e2, 20)) < 0.2 * first


def test_note_number_row_is_per_voice():
    def loud(note, with_row):
        e = Engine(seed=2)
        e.set_param("b_volume", 0.0); e.set_param("a_cutoff", 300.0)
        if with_row:
            row(e, 1, "Note Number", 1.0, "A: Cutoff")
        e.note_on(note, 100)
        return rms(render(e, 20))

    # a high note opens the filter (cutoff x1.6), a low note closes it (cutoff x0.6), at the same pitch
    assert loud(96, True) > loud(96, False)
    assert loud(36, True) < loud(36, False)


def test_lfo_rate_cross_modulation_runs():
    e = Engine(seed=2)
    row(e, 1, "LFO 2", 1.0, "LFO 1 Rate")
    row(e, 2, "LFO 1", 1.0, "A: Cutoff")
    e.set_param("lfo2_rate", 3.0)
    e.note_on(60, 100)
    assert np.all(np.isfinite(render(e, 50)))


def test_changing_a_row_back_to_none_restores_the_sound():
    a = Engine(seed=2)
    b = Engine(seed=2)
    row(b, 1, "Mod Wheel", 1.0, "A: Cutoff")
    row(b, 1, "none", 1.0, "A: Cutoff")
    for e in (a, b):
        e.set_mod_wheel(1.0); e.note_on(60, 100)
    assert np.array_equal(render(a, 6), render(b, 6))


def test_extreme_scales_stay_finite():
    e = Engine(seed=2)
    for i in range(1, 9):
        row(e, i, "LFO %d" % (1 + i % 2), 1.0, ["A: Cutoff", "B: Resonance", "A: Pitch", "Mix", "Detune",
                                              "Width", "A: Amp Attack", "B: Flt Release"][i - 1])
    e.set_param("lfo1_wave", "random"); e.set_param("lfo2_wave", "random-glide")
    for n in range(40, 90, 7):
        e.note_on(n, 120)
    assert np.all(np.isfinite(render(e, 60)))
