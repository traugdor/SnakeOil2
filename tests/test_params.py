import json
import math

import pytest

from snakeoil2.dsp import constants as C
from snakeoil2.dsp.destinations import DEST_BY_NAME, DEST_NAMES, DESTINATIONS, PITCH
from snakeoil2.dsp.params import BANK_KEYS, PARAMS


def test_ids_are_unique_and_banks_are_symmetric():
    ids = [p.id for p in PARAMS]
    assert len(ids) == len(set(ids))
    a = sorted(p.id[2:] for p in PARAMS if p.id.startswith("a_"))
    b = sorted(p.id[2:] for p in PARAMS if p.id.startswith("b_"))
    assert a == b == sorted(BANK_KEYS)


def test_defaults_are_inside_their_ranges():
    for p in PARAMS:
        d = PARAMS.defaults()[p.id]
        if p.kind == "continuous":
            assert p.lo <= d <= p.hi, p.id
        elif p.kind == "choice":
            assert d in p.choices, p.id
        else:
            assert isinstance(d, bool), p.id


def test_spec_defaults():
    d = PARAMS.defaults()
    assert d["a_mod_mode"] == "OFF" and d["b_mod_mode"] == "OFF"
    assert d["a_osc1_pwm"] == 0.5 and d["b_osc2_pwm"] == 0.5
    assert d["a_osc1_square_level"] == 0.5 and d["b_osc1_square_level"] == 0.5     # V1 default Sq Level
    assert d["mix"] == 0.5 and d["detune"] == 0.0 and d["width"] == 0.0
    assert d["a_cutoff"] == 2000.0
    assert d["a_amp_attack"] == pytest.approx(0.006)
    assert d["a_flt_sustain"] == pytest.approx(0.30)
    assert d["a_osc2_octave_up"] is True and d["a_osc1_octave_down"] is True
    assert d["a_noise_level"] == 0.0 and d["a_noise_color"] == "white"
    assert d["tempo_bpm"] == 120.0


def test_there_is_no_lfo_depth_and_no_bitcrush():
    ids = set(PARAMS.ids)
    assert not any("depth" in i and i.startswith("lfo") for i in ids)
    assert not any("bitcrush" in i or "crush" in i for i in ids)
    assert "lfo1_rate" in ids and "lfo1_wave" in ids


def test_coerce_clamps_and_rejects():
    assert PARAMS.coerce("mix", 5.0) == 1.0
    assert PARAMS.coerce("mix", -5) == 0.0
    assert PARAMS.coerce("a_osc1_saw", 1) is True
    assert PARAMS.coerce("a_mod_mode", "RING") == "RING"
    for bad in (float("nan"), float("inf"), "x", None, True):
        with pytest.raises(ValueError):
            PARAMS.coerce("mix", bad)
    with pytest.raises(ValueError):
        PARAMS.coerce("a_mod_mode", "BOGUS")
    with pytest.raises(ValueError):
        PARAMS.coerce("a_osc1_saw", "yes")
    with pytest.raises(KeyError):
        PARAMS.coerce("nope", 1)


def test_every_destination_points_at_a_real_param():
    for d in DESTINATIONS:
        if d.kind == PITCH:
            assert d.param_id == ""
        else:
            assert d.param_id in PARAMS, d.name
    assert DEST_NAMES[0] == "none"
    assert "A: Pitch" in DEST_BY_NAME and "B: Cutoff" in DEST_BY_NAME
    assert "Mix" in DEST_BY_NAME and "LFO 1 Rate" in DEST_BY_NAME
    assert "A: OSC1 Sq Level" in DEST_BY_NAME and "B: OSC1 Sq Level" in DEST_BY_NAME


def test_mod_rows_exist():
    for i in range(1, C.MOD_SLOTS + 1):
        assert f"mod{i}_src" in PARAMS and f"mod{i}_scale" in PARAMS and f"mod{i}_dst" in PARAMS
    assert PARAMS.by_id["mod1_dst"].choices == DEST_NAMES


def test_export_is_json_serialisable():
    data = PARAMS.export()
    json.dumps(data)
    assert {"id", "label", "group", "kind", "default"} <= set(data[0])


def test_pitch_helpers():
    from snakeoil2.dsp.pitch import midi_note_to_freq, semitones_to_ratio

    assert midi_note_to_freq(69) == pytest.approx(440.0)
    assert midi_note_to_freq(81) == pytest.approx(880.0)
    assert semitones_to_ratio(12) == pytest.approx(2.0)
    assert semitones_to_ratio(0, 100) == pytest.approx(2 ** (1 / 12))
    assert math.isfinite(midi_note_to_freq(0))
