import pytest

from snakeoil2.dsp.destinations import SRC_AFTERTOUCH, SRC_LFO1, SRC_LFO2, SRC_NOTE, SRC_WHEEL
from snakeoil2.dsp.modmatrix import ModMatrix, effective, note_source, smooth
from snakeoil2.dsp.params import PARAMS

BASE = PARAMS.defaults()
ZERO = (0.0,) * 6


def src(**kw):
    s = [0.0] * 6
    for k, v in kw.items():
        s[{"lfo1": SRC_LFO1, "lfo2": SRC_LFO2, "wheel": SRC_WHEEL, "at": SRC_AFTERTOUCH}[k]] = v
    return s


def test_effective_is_relative_and_clamped():
    assert effective(1000.0, 0.5, 20.0, 20000.0) == pytest.approx(1500.0)
    assert effective(1000.0, -2.0, 20.0, 20000.0) == 20.0
    assert effective(0.0, 1.0, 0.0, 1.0) == 0.0           # a base of 0 stays 0
    assert effective(0.9, 1.0, 0.0, 1.0) == 1.0


def test_note_source_and_smooth():
    assert note_source(60) == 0.0 and note_source(120) == 1.0 and note_source(0) == -1.0
    assert note_source(None) == 0.0
    assert smooth(0.0, 1.0, 0.3) == pytest.approx(0.3)


def test_empty_matrix_does_nothing():
    m = ModMatrix(PARAMS)
    assert m.empty and not m.uses_note
    r = m.evaluate(BASE, ZERO, 0.0)
    assert r.values == {} and r.pitch == {"a": 0.0, "b": 0.0}


def test_relative_destination_per_bank():
    m = ModMatrix(PARAMS)
    m.set_row(1, "Mod Wheel", 0.5, "A: Cutoff")
    r = m.evaluate(BASE, src(wheel=1.0), 0.0)
    assert r.values == {"a_cutoff": pytest.approx(3000.0)}      # bank B untouched


def test_rows_on_one_destination_add_their_percentages():
    m = ModMatrix(PARAMS)
    m.set_row(1, "LFO 1", 0.25, "B: Cutoff")
    m.set_row(2, "Mod Wheel", 0.25, "B: Cutoff")
    r = m.evaluate(BASE, src(lfo1=1.0, wheel=1.0), 0.0)
    assert r.values["b_cutoff"] == pytest.approx(3000.0)


def test_zero_scale_none_source_and_none_destination_are_inactive():
    m = ModMatrix(PARAMS)
    m.set_row(1, "LFO 1", 0.0, "A: Cutoff")
    m.set_row(2, "none", 1.0, "A: Cutoff")
    m.set_row(3, "LFO 1", 1.0, "none")
    assert m.empty


def test_pitch_is_additive_semitones():
    m = ModMatrix(PARAMS)
    m.set_row(1, "LFO 1", 1.0, "A: Pitch")
    m.set_row(2, "LFO 2", -0.5, "B: Pitch")
    r = m.evaluate(BASE, src(lfo1=1.0, lfo2=1.0), 0.0)
    assert r.pitch["a"] == pytest.approx(2.0) and r.pitch["b"] == pytest.approx(-1.0)
    assert r.values == {}


def test_lfo_rate_destination_is_exponential_and_clamped():
    m = ModMatrix(PARAMS)
    m.set_row(1, "LFO 2", 1.0, "LFO 1 Rate")
    r = m.evaluate(BASE, src(lfo2=1.0), 0.0, kinds=("rate",))
    assert r.values["lfo1_rate"] == pytest.approx(5.0 * 4.0)
    r = m.evaluate(BASE, src(lfo2=-1.0), 0.0, kinds=("rate",))
    assert r.values["lfo1_rate"] == pytest.approx(5.0 / 4.0)
    m.set_row(2, "LFO 2", 1.0, "LFO 1 Rate")
    r = m.evaluate(BASE, src(lfo2=1.0), 0.0)
    assert r.values["lfo1_rate"] == 40.0


def test_kinds_filter():
    m = ModMatrix(PARAMS)
    m.set_row(1, "LFO 1", 1.0, "A: Pitch")
    m.set_row(2, "LFO 1", 1.0, "LFO 2 Rate")
    assert m.evaluate(BASE, src(lfo1=1.0), 0.0, kinds=("rate",)).pitch == {"a": 0.0, "b": 0.0}


def test_note_number_source_is_per_call():
    m = ModMatrix(PARAMS)
    m.set_row(1, "Note Number", 1.0, "A: Cutoff")
    assert m.uses_note
    lo = m.evaluate(BASE, ZERO, -1.0).values["a_cutoff"]
    hi = m.evaluate(BASE, ZERO, 1.0).values["a_cutoff"]
    assert lo == 20.0 and hi == pytest.approx(4000.0)


def test_global_destinations():
    m = ModMatrix(PARAMS)
    m.set_row(1, "Aftertouch", 1.0, "Mix")
    assert m.evaluate(BASE, src(at=1.0), 0.0).values["mix"] == 1.0
    m.set_row(1, "Aftertouch", 1.0, "Tempo")
    assert m.evaluate(BASE, src(at=0.5), 0.0).values["tempo_bpm"] == pytest.approx(180.0)


def test_unknown_names_raise():
    m = ModMatrix(PARAMS)
    with pytest.raises(ValueError):
        m.set_row(1, "bogus", 1.0, "A: Cutoff")
    with pytest.raises(ValueError):
        m.set_row(1, "LFO 1", 1.0, "bogus")
    with pytest.raises(ValueError):
        m.set_row(9, "LFO 1", 1.0, "A: Cutoff")
