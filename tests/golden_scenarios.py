def _hold(note, t0=0.0, t1=0.6, velocity=100):
    return [{"t": t0, "type": "note_on", "note": note, "velocity": velocity},
            {"t": t1, "type": "note_off", "note": note}]


def _scn(params=None, events=None, seconds=1.0):
    return {"seconds": seconds, "block": 256, "seed": 1, "params": params or {}, "events": events or _hold(60)}


def _bank(prefix, **kw):
    return {prefix + k: v for k, v in kw.items()}


SCENARIOS = {
    "default": _scn(),
    "chord": _scn(events=_hold(48) + _hold(55) + _hold(60) + _hold(64)),
    "saw_square_layer": _scn(_bank("a_", osc1_square=True, osc1_pwm=0.2)),
    "osc2_reverse_saw": _scn(_bank("a_", osc2_wave="reverse saw", osc2_level=0.8)),
    "osc2_inverted_triangle": _scn(_bank("a_", osc2_wave="inverted triangle", osc2_level=0.8)),
    "osc2_sine": _scn(_bank("a_", osc2_wave="sine", osc2_level=0.8)),
    "osc2_pwm": _scn(_bank("a_", osc2_wave="square", osc2_pwm=0.1, osc2_level=0.8)),
    "mod_fm": _scn(_bank("a_", mod_mode="FM", osc2_wave="sine", osc2_level=0.8)),
    "mod_am": _scn(_bank("a_", mod_mode="AM", osc2_level=0.8)),
    "mod_ring": _scn(_bank("a_", mod_mode="RING", osc2_level=0.8)),
    "mod_sync": _scn(_bank("a_", mod_mode="SYNC", osc2_coarse=7, osc2_level=0.8)),
    "osc1_live_but_muted_ring": _scn(_bank("a_", osc1_level=0.0, mod_mode="RING", osc2_level=0.8)),
    "noise_pink": _scn(_bank("a_", noise_level=0.5, noise_color="pink", osc1_level=0.0, osc2_level=0.0)),
    "filter_env": _scn(_bank("a_", cutoff=300.0, resonance=0.5, flt_amount=1.0, flt_decay=0.2, flt_sustain=0.1)),
    "keytrack_velocity": _scn(_bank("a_", cutoff=500.0, keytrack=1.0, vel_cutoff=1.0),
                              _hold(36, 0, 0.4, 40) + _hold(84, 0.5, 0.9, 120)),
    "banks_mix_detune_width": _scn({"mix": 0.3, "detune": 30.0, "width": 0.8}),
    "lfo_vibrato": _scn({"lfo1_rate": 5.0, "mod1_src": "LFO 1", "mod1_scale": 0.5, "mod1_dst": "A: Pitch"}),
    "lfo_filter_both": _scn({"lfo2_wave": "triangle", "mod1_src": "LFO 2", "mod1_scale": 0.8, "mod1_dst": "A: Cutoff",
                             "mod2_src": "LFO 2", "mod2_scale": -0.8, "mod2_dst": "B: Cutoff"}),
    "wheel_mix": _scn({"mod1_src": "Mod Wheel", "mod1_scale": 1.0, "mod1_dst": "Mix"},
                      [{"t": 0, "type": "cc", "control": 1, "value": 127}] + _hold(60)),
    "chorus": _scn({"fx_chorus_on": True, "fx_chorus_depth": 0.8}),
    "delay_pingpong": _scn({"fx_delay_on": True, "fx_delay_pingpong": True, "fx_delay_time": 180.0}, seconds=1.5),
    "delay_synced": _scn({"fx_delay_on": True, "fx_delay_sync": True, "fx_delay_division": "1/8."}, seconds=1.5),
    "reverb": _scn({"fx_reverb_on": True, "fx_reverb_amount": 0.6}, seconds=1.5),
    "limiter": _scn({"limiter_on": True, "master_volume": 1.2, **_bank("a_", osc1_level=1.0, osc2_level=1.0),
                     **_bank("b_", osc1_level=1.0, osc2_level=1.0)},
                    _hold(48) + _hold(55) + _hold(60) + _hold(64) + _hold(67)),
    "pedal_and_bend": _scn(events=[{"t": 0, "type": "cc", "control": 64, "value": 127},
                                   {"t": 0.0, "type": "note_on", "note": 60, "velocity": 100},
                                   {"t": 0.2, "type": "note_off", "note": 60},
                                   {"t": 0.3, "type": "bend", "value": 1.0},
                                   {"t": 0.6, "type": "cc", "control": 64, "value": 0}]),
    "voice_stealing": _scn(events=[e for i in range(10)
                                   for e in _hold(50 + 3 * i, 0.05 * i, 0.9, 90)], seconds=1.2),
}
