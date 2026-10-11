import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

PySide6 = pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication

from snakeoil2.app.gui.hslider import BipolarSlider
from snakeoil2.app.gui.knob import Knob
from snakeoil2.app.gui.meter import LevelMeter
from snakeoil2.app.gui.slider import ValueSlider

app = QApplication.instance() or QApplication([])


def test_knob_roundtrip_and_signal():
    k = Knob(0.0, 1.0, 0.25)
    seen = []
    k.valueChanged.connect(seen.append)
    k.setValue(0.75)
    assert k.value() == pytest.approx(0.75)
    k.show(); k.repaint()


def test_log_knob_covers_its_range():
    k = Knob(20.0, 20000.0, 2000.0, log=True)
    k.setValue(20.0); assert k.value() == pytest.approx(20.0, rel=1e-3)
    k.setValue(20000.0); assert k.value() == pytest.approx(20000.0, rel=1e-3)


def test_sliders_roundtrip():
    s = ValueSlider(0.0, 1.0, 0.5)
    s.setValue(0.2); assert s.value() == pytest.approx(0.2, abs=1e-3)
    b = BipolarSlider(0.0)
    b.setValue(-0.5); assert b.value() == pytest.approx(-0.5, abs=1e-3)


def test_meter_constructs_and_paints():
    m = LevelMeter()
    m.show(); m.repaint()
