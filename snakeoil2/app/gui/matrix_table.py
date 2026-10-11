from PySide6.QtWidgets import QGridLayout, QLabel, QWidget

from ...dsp.constants import MOD_SLOTS
from ...dsp.params import PARAMS
from .controls import build_control


class MatrixTable(QWidget):
    """Eight rows: Source | Scale | Destination."""

    def __init__(self, controller):
        super().__init__()
        grid = QGridLayout(self)
        grid.setContentsMargins(2, 2, 2, 2)
        for col, title in enumerate(("Source", "Scale", "Destination")):
            grid.addWidget(QLabel(title), 0, col)
        self.rows = []
        self.controls = {}
        for i in range(1, MOD_SLOTS + 1):
            row = []
            for col, key in enumerate(("src", "scale", "dst")):
                pid = "mod%d_%s" % (i, key)
                w = build_control(controller, PARAMS.by_id[pid])
                self.controls[pid] = w
                grid.addWidget(w, i, col)
                row.append(w)
            self.rows.append(row)
