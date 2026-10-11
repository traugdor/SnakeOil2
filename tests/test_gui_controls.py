import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication, QComboBox, QPushButton

from snakeoil2.app.controller import Controller
from snakeoil2.app.events import EventQueue
from snakeoil2.app.gui.controls import build_control
from snakeoil2.app.gui.leds import VoiceLeds
from snakeoil2.dsp.params import PARAMS
from snakeoil2.patches import PatchStore

app = QApplication.instance() or QApplication([])


def ctl(tmp_path):
    return Controller(EventQueue(), PatchStore(tmp_path))


def test_every_parameter_gets_a_control(tmp_path):
    c = ctl(tmp_path)
    for p in PARAMS:
        w = build_control(c, p)
        assert w is not None, p.id


def test_toggle_and_choice_write_through(tmp_path):
    c = ctl(tmp_path)
    t = build_control(c, PARAMS.by_id["a_osc1_square"])
    btn = t.findChild(QPushButton)
    btn.click()
    assert c.values["a_osc1_square"] is True
    ch = build_control(c, PARAMS.by_id["a_mod_mode"])
    combo = ch.findChild(QComboBox)
    combo.setCurrentText("RING")
    assert c.values["a_mod_mode"] == "RING"


def test_controls_follow_external_changes(tmp_path):
    c = ctl(tmp_path)
    ch = build_control(c, PARAMS.by_id["a_mod_mode"])
    c.set_param("a_mod_mode", "FM")
    assert ch.findChild(QComboBox).currentText() == "FM"
    t = build_control(c, PARAMS.by_id["a_osc1_saw"])
    c.set_param("a_osc1_saw", False)
    assert not t.findChild(QPushButton).isChecked()


def test_voice_leds(tmp_path):
    leds = VoiceLeds()
    leds.set_activity(2, 3)
    assert leds.states() == ["held", "held", "tail", "tail", "tail", "off"]
    leds.set_activity(6, 12)
    assert leds.states() == ["held"] * 6
    assert leds.tails_label.text() == "Tails 12/12"
    leds.set_activity(0, 0)
    assert leds.states() == ["off"] * 6
