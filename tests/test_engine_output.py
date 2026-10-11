import numpy as np
import pytest

from snakeoil2.dsp.engine import Engine


def render(e, blocks, n=256):
    return np.concatenate([e.process(n) for _ in range(blocks)])


def loud_engine():
    e = Engine(seed=2)
    e.set_param("master_volume", 1.2)
    for b in "ab":
        e.set_param(b + "_osc1_level", 1.0); e.set_param(b + "_osc2_level", 1.0)
        e.set_param(b + "_volume", 1.0); e.set_param(b + "_cutoff", 20000.0)
    for n in (48, 55, 60, 64, 67, 72):
        e.note_on(n, 127)
    return e


def test_output_is_always_inside_plus_minus_one():
    out = render(loud_engine(), 20)
    assert np.abs(out).max() <= 1.0 and np.all(np.isfinite(out))


def test_meter_reports_peaks_and_clip_then_resets():
    e = loud_engine()
    render(e, 10)
    l, r, clip = e.take_meter()
    assert l > 0.3 and r > 0.3
    assert e.take_meter() == (0.0, 0.0, False)


def test_limiter_holds_gain_reduction_and_reset_clears_it():
    e = loud_engine()
    e.set_param("limiter_on", True)
    out = render(e, 20)
    assert e.limiter_reduction_db() > 0.0
    assert np.abs(out).max() < 0.99
    e.reset_limiter()
    assert e.limiter_reduction_db() == 0.0


def test_limiter_resets_after_half_a_second_of_silence():
    e = loud_engine()
    e.set_param("limiter_on", True)
    render(e, 10)
    e.panic()
    render(e, 140)           # about 0.8 s of silence
    assert e.limiter_reduction_db() == 0.0


def test_effects_toggle_changes_the_sound_and_tail_rings():
    dry = Engine(seed=2); wet = Engine(seed=2)
    wet.set_param("fx_reverb_on", True); wet.set_param("fx_reverb_amount", 1.0)
    for e in (dry, wet):
        e.note_on(60, 100)
    a, b = render(dry, 10), render(wet, 10)
    assert not np.allclose(a, b)
    for e in (dry, wet):
        e.note_off(60); e.panic()
    tail_dry, tail_wet = render(dry, 30), render(wet, 30)
    assert np.abs(tail_wet).max() > np.abs(tail_dry).max()


def test_delay_sync_follows_manual_bpm_and_midi_clock():
    e = Engine()
    e.set_param("fx_delay_on", True); e.set_param("fx_delay_sync", True)
    e.set_param("fx_delay_division", "1/4"); e.set_param("tempo_bpm", 120.0)
    e.process(256)
    assert e.effects.delay.time_ms == pytest.approx(500.0, abs=1.0)
    step = 60.0 / (60.0 * 24)
    for i in range(60):
        e.midi_clock(i * step)
    e.process(256, now=60 * step)
    assert e.effective_bpm(now=60 * step) == pytest.approx(60.0, abs=0.5)
    for _ in range(4):
        e.process(256, now=60 * step)
    assert e.effects.delay.time_ms == pytest.approx(1000.0, abs=2.0)


def test_delay_time_and_dials_reach_the_effects():
    e = Engine()
    e.set_param("fx_delay_on", True); e.set_param("fx_delay_time", 123.0)
    e.set_param("fx_delay_feedback", 0.5); e.set_param("fx_chorus_on", True)
    e.process(256)
    assert e.effects.delay.enabled and e.effects.delay.time_ms == pytest.approx(123.0, abs=0.5)
    assert e.effects.delay.feedback == 0.5 and e.effects.chorus.enabled


def test_extreme_effect_settings_are_finite():
    e = loud_engine()
    e.set_param("fx_delay_on", True); e.set_param("fx_delay_time", 1.0); e.set_param("fx_delay_feedback", 0.95)
    e.set_param("fx_reverb_on", True); e.set_param("fx_reverb_size", 0.98); e.set_param("fx_reverb_amount", 1.0)
    e.set_param("fx_chorus_on", True); e.set_param("fx_chorus_depth", 1.0)
    out = render(e, 30)
    assert np.all(np.isfinite(out)) and np.abs(out).max() <= 1.0


def test_matrix_drives_global_effect_dials():
    e = Engine()
    e.set_param("fx_delay_on", True)
    e.set_param("mod1_src", "Mod Wheel"); e.set_param("mod1_scale", 1.0); e.set_param("mod1_dst", "Delay Time")
    e.set_mod_wheel(1.0)
    for _ in range(40):
        e.process(256)
    assert e.effects.delay.time_ms > 400.0           # 300 ms base x (1 + 1 x smoothed wheel)
