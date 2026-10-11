"""Regression tests for the final whole-branch review findings."""
import ast
import json
import pathlib

import numpy as np
import pytest

from snakeoil2.dsp.engine import Engine
from snakeoil2.dsp.params import PARAMS
from snakeoil2.patches import PatchError, PatchStore, validate_name

DSP = pathlib.Path(__file__).resolve().parents[1] / "snakeoil2" / "dsp"


# 1. hostile patch values and files must raise the documented errors, never anything else
def test_huge_integer_value_is_a_value_error_not_an_overflow():
    with pytest.raises(ValueError):
        PARAMS.coerce("mix", 10 ** 400)


def test_patch_with_a_huge_integer_loads_with_a_warning(tmp_path):
    (tmp_path / "Big.json").write_text(json.dumps({"version": 1, "name": "Big", "params": {"mix": 10 ** 400}}))
    values, warnings = PatchStore(tmp_path).load("Big")
    assert values["mix"] == 0.5 and warnings


def test_deeply_nested_json_is_a_patch_error(tmp_path):
    (tmp_path / "Deep.json").write_text("[" * 100000)
    with pytest.raises(PatchError):
        PatchStore(tmp_path).load("Deep")


# 2. the settings file name is reserved
@pytest.mark.parametrize("name", ["patch_settings", "Patch_Settings"])
def test_settings_file_name_cannot_be_a_patch_name(name):
    with pytest.raises(PatchError):
        validate_name(name)


# 3. effects must not replay stale echoes when switched back on
def test_delay_switched_on_after_a_pause_has_no_stale_echoes():
    e = Engine(seed=2)
    e.set_param("fx_delay_on", True); e.set_param("fx_delay_time", 2000.0)
    e.set_param("fx_delay_feedback", 0.9)
    e.note_on(60, 100)
    for _ in range(20):
        e.process(256)
    e.note_off(60); e.panic()
    for _ in range(int(2.5 * 44100 / 256)):      # let the echoes circulate in the 2 s buffer
        e.process(256)
    e.set_param("fx_delay_on", False)
    for _ in range(int(2.3 * 44100 / 256)):
        e.process(256)
    e.set_param("fx_delay_on", True)
    out = np.concatenate([e.process(256) for _ in range(int(2.3 * 44100 / 256))])   # a full buffer length
    assert np.abs(out).max() < 1e-6


def test_reverb_and_chorus_switched_on_after_a_pause_start_clean():
    e = Engine(seed=2)
    e.set_param("fx_reverb_on", True); e.set_param("fx_reverb_amount", 1.0); e.set_param("fx_chorus_on", True)
    e.note_on(60, 100)
    for _ in range(20):
        e.process(256)
    e.note_off(60); e.panic()
    e.set_param("fx_reverb_on", False); e.set_param("fx_chorus_on", False)
    e.process(256)
    e.set_param("fx_reverb_on", True); e.set_param("fx_chorus_on", True)
    out = np.concatenate([e.process(256) for _ in range(4)])
    assert np.abs(out).max() < 1e-6


# 4. no click when the filter leaves and re-enters bypass
def test_filter_reentering_from_bypass_does_not_click():
    from snakeoil2.dsp.bank import Bank
    from snakeoil2.dsp.params import BANK_KEYS

    def worst_jump(cutoffs):
        view = {k: PARAMS.defaults()["a_" + k] for k in BANK_KEYS}
        view.update(osc1_saw=False, osc1_level=0.0, osc2_wave="sine", osc2_level=1.0, osc2_octave_up=False,
                    amp_attack=0.001, amp_sustain=1.0)
        b = Bank(44100)
        b.note_on(36, 1.0, False, np.random.default_rng(1))
        out = np.concatenate([b.render(256, dict(view, cutoff=c), 65.4, 0.0) for c in cutoffs])
        return float(np.abs(np.diff(out[256:])).max())

    steady = worst_jump([10000.0] * 30)
    crossing = worst_jump([10000.0] * 10 + [20000.0] * 10 + [10000.0] * 10)
    assert crossing < 2.0 * steady


# 5. a numeric --device value is an index
def test_numeric_device_string_is_an_index():
    from snakeoil2.app.audio_backend import _resolve_device_index

    class FakeSd:
        def query_devices(self, index=None):
            if index is None:
                return [{"name": "USB 3.0 Speakers", "max_output_channels": 2},
                        {"name": "Other", "max_output_channels": 2},
                        {"name": "Third", "max_output_channels": 2},
                        {"name": "Fourth", "max_output_channels": 2}]
            return self.query_devices()[index]

    assert _resolve_device_index(FakeSd(), "3") == 3
    assert _resolve_device_index(FakeSd(), 2) == 2


# 6. the core must not use the wall clock, threads or locks
FORBIDDEN = {"time", "threading", "random", "PySide6", "sounddevice", "mido", "queue", "os", "pathlib"}


@pytest.mark.parametrize("path", sorted(DSP.glob("*.py")), ids=lambda p: p.name)
def test_dsp_module_imports_nothing_forbidden(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names.add(node.module.split(".")[0])
    assert not names & FORBIDDEN, (path.name, names & FORBIDDEN)


def test_tempo_needs_an_explicit_clock():
    from snakeoil2.dsp.tempo import TempoTracker

    t = TempoTracker()
    step = 60.0 / (120.0 * 24)
    for i in range(60):
        t.on_clock(i * step)
    assert t.external_bpm(60 * step) == pytest.approx(120.0, abs=0.5)
    assert t.effective_bpm(90.0, 60 * step + 5.0) == 90.0


# 7. one MIDI port that cannot be opened must not stop the others
def test_midi_input_skips_ports_that_fail_to_open(monkeypatch, capsys):
    import sys
    import types

    from snakeoil2.app.events import EventQueue
    from snakeoil2.app.midi import MidiInput

    opened = []

    def open_input(name, callback=None):
        if name == "busy":
            raise OSError("port in use")
        opened.append(name)
        return types.SimpleNamespace(close=lambda: None)

    fake = types.SimpleNamespace(get_input_names=lambda: ["busy", "ok"], open_input=open_input)
    monkeypatch.setitem(sys.modules, "mido", fake)
    m = MidiInput(EventQueue())
    assert m.start() == ["ok"] and opened == ["ok"]
    assert "busy" in capsys.readouterr().err


# 8. a bad event must not drop the rest of the batch
def test_one_bad_event_does_not_lose_the_following_note_off():
    from snakeoil2.app.audio import render_callback
    from snakeoil2.app.events import EventQueue

    e, q = Engine(), EventQueue()
    q.put(("note_on", 60, 100))
    q.put(("param", "mix", 10 ** 400))
    q.put(("note_off", 60))
    render_callback(e, q, np.zeros((64, 2), dtype=np.float32), 64, 0.0)
    assert e.held_count == 0
