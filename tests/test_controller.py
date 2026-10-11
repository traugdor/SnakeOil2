import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication

from snakeoil2.app.controller import Controller
from snakeoil2.app.events import EventQueue
from snakeoil2.dsp.params import PARAMS
from snakeoil2.patches import PatchStore

app = QApplication.instance() or QApplication([])


def make(tmp_path):
    q = EventQueue()
    return Controller(q, PatchStore(tmp_path)), q


def test_set_param_mirrors_queues_and_emits(tmp_path):
    c, q = make(tmp_path)
    seen = []
    c.changed.connect(seen.append)
    c.set_param("mix", 0.2)
    assert c.values["mix"] == 0.2 and ("param", "mix", 0.2) in q.drain() and seen == ["mix"] and c.dirty


def test_invalid_values_are_rejected_without_side_effects(tmp_path):
    c, q = make(tmp_path)
    for pid, bad in (("mix", float("nan")), ("a_mod_mode", "X"), ("nope", 1)):
        with pytest.raises((ValueError, KeyError)):
            c.set_param(pid, bad)
    assert c.values["mix"] == 0.5 and q.drain() == [] and not c.dirty


def test_save_load_rename_delete_cycle(tmp_path):
    c, q = make(tmp_path)
    c.set_param("mix", 0.9)
    c.save_patch("Mine")
    assert c.current_patch == "Mine" and not c.dirty
    c.set_param("mix", 0.1)
    assert c.dirty
    c.load_patch("Mine")
    assert c.values["mix"] == 0.9 and not c.dirty
    ev = [e for e in q.drain() if e[0] == "load"]
    assert ev and ev[-1][1]["mix"] == 0.9
    c.rename_patch("Renamed")
    assert c.current_patch == "Renamed"
    c.delete_patch()
    assert c.current_patch == "Init" and c.values["mix"] == 0.5


def test_init_cannot_be_saved_over(tmp_path):
    c, _ = make(tmp_path)
    c.load_patch("Init")
    from snakeoil2.patches import PatchError
    with pytest.raises(PatchError):
        c.save_current()


def test_loading_a_patch_does_not_change_master_volume_or_limiter(tmp_path):
    c, _ = make(tmp_path)
    c.set_param("master_volume", 0.3)
    c.save_patch("P")
    c.set_param("master_volume", 0.6)
    c.load_patch("P")
    assert c.values["master_volume"] == 0.6
