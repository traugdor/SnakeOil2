import numpy as np
import pytest

from snakeoil2.dsp.constants import PLAYABLE_VOICES, POOL_SIZE
from snakeoil2.dsp.engine import Engine

SR = 44100


def render(e, blocks, n=256):
    return np.concatenate([e.process(n) for _ in range(blocks)])


def test_silent_when_idle_and_output_shape_dtype():
    e = Engine()
    out = e.process()
    assert out.shape == (256, 2) and out.dtype == np.float32 and not out.any()


def test_note_on_makes_sound_and_note_off_ends_it():
    e = Engine()
    e.set_param("a_amp_release", 0.02); e.set_param("b_amp_release", 0.02)
    e.note_on(60, 100)
    assert np.abs(render(e, 10)).max() > 0.01 and e.held_count == 1
    e.note_off(60)
    render(e, 20)
    assert e.held_count == 0 and e.tail_count == 0
    assert not e.process().any()


def test_velocity_zero_is_note_off():
    e = Engine()
    e.note_on(60, 100); render(e, 2)
    e.note_on(60, 0)
    assert e.held_count == 0


def test_out_of_range_notes_and_velocities_are_ignored_or_clamped():
    e = Engine()
    e.note_on(-1, 100); e.note_on(128, 100); e.note_on(300, 100)
    assert e.held_count == 0
    e.note_on(60, 500)
    out = render(e, 4)
    assert np.all(np.isfinite(out)) and e.held_count == 1


def test_set_param_validation_leaves_state_unchanged():
    e = Engine()
    before = e.get_param("mix")
    for bad in (float("nan"), float("inf"), "x", None):
        with pytest.raises(ValueError):
            e.set_param("mix", bad)
    with pytest.raises(KeyError):
        e.set_param("nope", 1)
    assert e.get_param("mix") == before
    e.set_param("mix", 9.0)
    assert e.get_param("mix") == 1.0


def test_mix_selects_the_banks():
    def loudness(mix):
        e = Engine()
        e.set_param("mix", mix)
        e.set_param("b_volume", 0.0)
        e.note_on(60, 100)
        return np.abs(render(e, 8)).max()

    only_a, centre, only_b = loudness(0.0), loudness(0.5), loudness(1.0)
    assert only_a > centre > 0 and only_b < 1e-9     # bank B volume is 0 (cos(pi/2) is not exactly 0)


def test_both_bank_volumes_zero_is_silent():
    e = Engine()
    e.set_param("a_volume", 0.0); e.set_param("b_volume", 0.0)
    e.note_on(60, 100)
    assert not render(e, 6).any()


def test_detune_separates_the_banks_in_pitch():
    def spectrum_peaks(detune):
        e = Engine()
        for b in "ab":
            e.set_param(b + "_osc1_saw", False); e.set_param(b + "_osc1_level", 0.0)
            e.set_param(b + "_osc2_wave", "sine"); e.set_param(b + "_osc2_level", 1.0)
            e.set_param(b + "_osc2_octave_up", False); e.set_param(b + "_cutoff", 20000.0)
            e.set_param(b + "_amp_sustain", 1.0); e.set_param(b + "_amp_attack", 0.001)
        e.set_param("detune", detune)
        e.note_on(57, 127)                       # 220 Hz
        y = render(e, 200)[:, 0]
        spec = np.abs(np.fft.rfft(y * np.hanning(len(y))))
        return int((spec > 0.2 * spec.max()).sum())

    assert spectrum_peaks(50.0) > spectrum_peaks(0.0)


def test_width_moves_banks_apart():
    e = Engine()
    e.set_param("b_volume", 0.0); e.set_param("width", 1.0)
    e.note_on(60, 100)
    out = render(e, 6)
    assert np.abs(out[:, 0]).max() > 0.01 and np.abs(out[:, 1]).max() < 1e-6


def test_pitch_bend_extremes_are_finite_and_shift_pitch():
    e = Engine()
    e.note_on(60, 100)
    e.pitch_bend(1.0); a = render(e, 4)
    e.pitch_bend(-1.0); b = render(e, 4)
    e.pitch_bend(50.0); c = render(e, 4)
    assert all(np.all(np.isfinite(x)) for x in (a, b, c))


def test_sustain_pedal_defers_note_off_and_releases_after():
    e = Engine()
    e.set_sustain(True)
    e.note_on(60, 100); e.note_off(60)
    assert e.held_count == 1
    e.set_sustain(False)
    assert e.held_count == 0


def test_cc_handlers():
    e = Engine()
    e.note_on(60, 100)
    e.cc(64, 127); e.note_off(60); assert e.held_count == 1
    e.cc(64, 0); assert e.held_count == 0
    e.note_on(61, 100); e.note_on(62, 100)
    e.cc(123, 0); assert e.held_count == 0
    e.note_on(63, 100); render(e, 2)
    e.cc(120, 0); assert e.held_count == 0 and e.tail_count == 0
    e.pitch_bend(1.0); e.set_sustain(True); e.cc(121, 0)
    assert e.sustain is False


def test_polyphony_limits_hold_under_a_note_storm():
    e = Engine()
    rng = np.random.default_rng(7)
    for i in range(400):
        e.note_on(int(rng.integers(20, 100)), int(rng.integers(1, 128)))
        if i % 3 == 0:
            e.note_off(int(rng.integers(20, 100)))
        out = e.process(64)
        assert np.all(np.isfinite(out)) and np.abs(out).max() <= 1.0
        assert e.held_count <= PLAYABLE_VOICES
        assert e.held_count + e.tail_count <= POOL_SIZE
    assert e.steal_count > 0 and e.forced_releases > 0


def test_repeated_same_note_never_double_holds():
    e = Engine()
    for _ in range(20):
        e.note_on(60, 100); e.process(32)
    assert e.held_count == 1


def test_steal_does_not_click():
    e = Engine()
    e.set_param("a_amp_release", 5.0); e.set_param("b_amp_release", 5.0)
    prev = None
    worst = 0.0
    for i in range(60):
        e.note_on(40 + i % 20, 100)
        if i % 2:
            e.note_off(40 + (i - 1) % 20)
        out = e.process(256)[:, 0]
        if prev is not None:
            worst = max(worst, abs(float(out[0]) - prev))
        prev = float(out[-1])
    assert worst < 0.6


def test_block_size_invariance_without_modulation():
    def run(sizes):
        e = Engine()
        e.set_param("a_mod_mode", "FM"); e.set_param("b_mod_mode", "RING")
        e.set_param("detune", 12.0); e.set_param("width", 0.4)
        e.note_on(60, 100); e.note_on(67, 90)
        return np.concatenate([e.process(n) for n in sizes])

    whole = run([1024])
    parts = run([64, 64, 128, 256, 512])
    assert np.allclose(whole, parts, atol=1e-5)


def test_determinism():
    def go():
        e = Engine(seed=5)
        e.note_on(60, 100); e.note_on(64, 100)
        return render(e, 8)

    assert np.array_equal(go(), go())


def test_voice_counts_property_types():
    e = Engine()
    assert isinstance(e.held_count, int) and isinstance(e.tail_count, int)
