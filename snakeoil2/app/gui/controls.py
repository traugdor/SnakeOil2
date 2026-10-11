"""Build one labelled GUI control for a ParamDef; every control writes through the Controller."""
from PySide6.QtCore import Qt
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


def build_control(controller, p, compact=False):
    """One labelled control. ``compact`` packs it tightly for the grid layout (no label on combos)."""
    box = QWidget()
    lay = QVBoxLayout(box)
    m = 0 if compact else 2
    lay.setContentsMargins(m, m, m, m)
    lay.setSpacing(0 if compact else 2)
    label = QLabel(p.label)
    label.setToolTip(p.id)
    if compact:
        label.setAlignment(Qt.AlignHCenter)
        label.setStyleSheet("font-size: 10px; color: #8f98ad;")
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
        if not compact:
            lay.addWidget(label)
        w.setToolTip(p.id + ": " + p.label)
        lay.addWidget(w)
    else:
        if p.id.startswith("mod") and p.id.endswith("_scale"):
            w = BipolarSlider(controller.values[p.id])
        elif p.label in ("A", "D", "S", "R"):
            w = ValueSlider(p.lo, p.hi, controller.values[p.id], _format(p), log=p.scale == "log")
        else:
            w = Knob(p.lo, p.hi, controller.values[p.id], _format(p), log=p.scale == "log")
        if compact and isinstance(w, Knob):
            w.setMinimumSize(0, 0)
            w.setFixedSize(54, 62)
        elif compact and isinstance(w, ValueSlider):
            w._slider.setFixedHeight(54)
            box.setMinimumWidth(50)
        elif compact and isinstance(w, BipolarSlider):
            w.setMaximumWidth(150)
        w.valueChanged.connect(lambda v: controller.set_param(p.id, float(v)))
        holder["get"], holder["set"] = w.value, w.setValue
        lay.addWidget(w)
        if not (compact and isinstance(w, BipolarSlider)):
            lay.addWidget(label)

    def follow(pid):
        if pid == p.id and holder["get"]() != controller.values[p.id]:
            w.blockSignals(True)
            holder["set"](controller.values[p.id])
            w.blockSignals(False)

    controller.changed.connect(follow)
    box._follow = follow          # keep a reference alive for the lifetime of the widget
    return box
