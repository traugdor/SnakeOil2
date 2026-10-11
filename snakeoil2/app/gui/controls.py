"""Build one labelled GUI control for a ParamDef; every control writes through the Controller."""
from PySide6.QtWidgets import QComboBox, QLabel, QPushButton, QVBoxLayout, QWidget

from ...dsp.params import CHOICE, TOGGLE
from .hslider import BipolarSlider
from .knob import Knob
from .slider import ValueSlider


def _hz(v):
    return "%d Hz" % round(v) if v < 1000 else "%.1f kHz" % (v / 1000.0)


def _seconds(v):
    return "%d ms" % round(v * 1000.0) if v < 1.0 else "%.2f s" % v


def _format(p):
    if p.id.endswith("cutoff"):
        return _hz
    if p.id.endswith(("attack", "decay", "release")):
        return _seconds
    if p.id == "fx_delay_time":
        return lambda v: "%d ms" % round(v)
    return None


def build_control(controller, p):
    box = QWidget()
    lay = QVBoxLayout(box)
    lay.setContentsMargins(2, 2, 2, 2)
    lay.setSpacing(2)
    label = QLabel(p.label)
    label.setToolTip(p.id)
    holder = {}

    if p.kind == TOGGLE:
        w = QPushButton(p.label)
        w.setCheckable(True)
        w.setChecked(controller.values[p.id])
        w.toggled.connect(lambda on: controller.set_param(p.id, bool(on)))
        holder["get"], holder["set"] = w.isChecked, lambda v: w.setChecked(bool(v))
        lay.addWidget(w)
    elif p.kind == CHOICE:
        w = QComboBox()
        w.addItems(list(p.choices))
        w.setCurrentText(controller.values[p.id])
        w.currentTextChanged.connect(lambda text: controller.set_param(p.id, text))
        holder["get"], holder["set"] = w.currentText, w.setCurrentText
        lay.addWidget(label)
        lay.addWidget(w)
    else:
        if p.id.startswith("mod") and p.id.endswith("_scale"):
            w = BipolarSlider(controller.values[p.id])
        elif p.label in ("A", "D", "S", "R"):
            w = ValueSlider(p.lo, p.hi, controller.values[p.id], _format(p), log=p.scale == "log")
        else:
            w = Knob(p.lo, p.hi, controller.values[p.id], _format(p), log=p.scale == "log")
        w.valueChanged.connect(lambda v: controller.set_param(p.id, float(v)))
        holder["get"], holder["set"] = w.value, w.setValue
        lay.addWidget(w)
        lay.addWidget(label)

    def follow(pid):
        if pid == p.id and holder["get"]() != controller.values[p.id]:
            w.blockSignals(True)
            holder["set"](controller.values[p.id])
            w.blockSignals(False)

    controller.changed.connect(follow)
    box._follow = follow          # keep a reference alive for the lifetime of the widget
    return box
