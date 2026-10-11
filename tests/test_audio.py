import numpy as np

from snakeoil2.app.audio import render_callback
from snakeoil2.app.events import EventQueue
from snakeoil2.app.main import build_parser
from snakeoil2.app.paths import config_dir, patches_dir
from snakeoil2.dsp.engine import Engine


def test_callback_applies_events_and_fills_stereo():
    e, q = Engine(), EventQueue()
    q.put(("note_on", 60, 100))
    out = np.zeros((512, 2), dtype=np.float32)
    for _ in range(4):
        render_callback(e, q, out, 512, 0.0)
    assert np.abs(out).max() > 0.01


def test_callback_handles_mono_and_many_channel_devices():
    e, q = Engine(), EventQueue()
    q.put(("note_on", 60, 100))
    mono = np.zeros((256, 1), dtype=np.float32)
    for _ in range(4):
        render_callback(e, q, mono, 256, 0.0)
    assert np.abs(mono).max() > 0.01
    e, q = Engine(), EventQueue()
    q.put(("note_on", 60, 100))
    six = np.ones((256, 6), dtype=np.float32)
    for _ in range(4):
        render_callback(e, q, six, 256, 0.0)
    assert np.abs(six[:, :2]).max() > 0.01 and not six[:, 2:].any()


def test_callback_never_raises(monkeypatch):
    e, q = Engine(), EventQueue()
    monkeypatch.setattr(e, "process", lambda *a, **k: 1 / 0)
    out = np.ones((256, 2), dtype=np.float32)
    render_callback(e, q, out, 256, 0.0)
    assert not out.any()


def test_callback_accepts_any_block_length():
    e, q = Engine(), EventQueue()
    q.put(("note_on", 60, 100))
    for frames in (1, 7, 100, 1000, 4096):
        out = np.zeros((frames, 2), dtype=np.float32)
        render_callback(e, q, out, frames, 0.0)
        assert np.all(np.isfinite(out))


def test_paths(tmp_path):
    assert config_dir(str(tmp_path)) == tmp_path
    assert patches_dir(tmp_path) == tmp_path / "patches" and (tmp_path / "patches").is_dir()


def test_parser_defaults_and_options():
    p = build_parser().parse_args([])
    assert p.channel is None and p.input == [] and not p.no_gui and not p.list
    p = build_parser().parse_args(["--input", "A", "--input", "B", "--channel", "3", "--no-gui", "--patch", "X"])
    assert p.input == ["A", "B"] and p.channel == 3 and p.no_gui and p.patch == "X"
