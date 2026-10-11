from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget

from ...dsp.constants import PLAYABLE_VOICES, TAIL_SLOTS

_COLORS = {"off": QColor("#2a2f36"), "held": QColor("#3ddc84"), "tail": QColor("#ffb300")}


class _Led(QWidget):
    def __init__(self):
        super().__init__()
        self.state = "off"
        self.setFixedSize(QSize(14, 14))

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setBrush(_COLORS[self.state])
        p.setPen(Qt.NoPen)
        p.drawEllipse(1, 1, 12, 12)


class VoiceLeds(QWidget):
    """Six LEDs for the playable voices: green = key held, amber = released note still ringing."""

    def __init__(self):
        super().__init__()
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        self._leds = [_Led() for _ in range(PLAYABLE_VOICES)]
        for led in self._leds:
            lay.addWidget(led)
        self.tails_label = QLabel("Tails 0/%d" % TAIL_SLOTS)
        lay.addWidget(self.tails_label)

    def set_activity(self, held, tails):
        for i, led in enumerate(self._leds):
            led.state = "held" if i < held else ("tail" if i < held + tails else "off")
            led.update()
        self.tails_label.setText("Tails %d/%d" % (tails, TAIL_SLOTS))

    def states(self):
        return [led.state for led in self._leds]
