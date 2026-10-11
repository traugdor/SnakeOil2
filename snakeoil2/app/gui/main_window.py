from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (QComboBox, QGridLayout, QGroupBox, QHBoxLayout, QInputDialog, QLabel, QMessageBox,
                               QScrollArea, QToolBar, QVBoxLayout, QWidget, QMainWindow)

from ...dsp.params import PARAMS
from ...patches import INIT_NAME, PatchError
from .controls import build_control
from .leds import VoiceLeds
from .matrix_table import MatrixTable
from .meter import ClickableLabel, LevelMeter
from .style import STYLE

BANK_PARTS = ("OSC1", "OSC2", "Modulation", "Noise", "Filter", "Filter Env", "Amp Env", "Output")


class MainWindow(QMainWindow):
    def __init__(self, controller, engine):
        super().__init__()
        self.controller, self.engine = controller, engine
        self.setStyleSheet(STYLE)
        self.controls = {}
        self.matrix = MatrixTable(controller)
        self.controls.update(self.matrix.controls)
        self.leds = VoiceLeds()
        self.meter = LevelMeter()
        self.gr_label = ClickableLabel("GR off", engine.reset_limiter)
        self._build_toolbar()
        self._build_body()
        self.status = self.statusBar()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(33)
        self._reload_patch_list(controller.current_patch)
        self.refresh()

    # ---- layout ------------------------------------------------------------------------------------

    def _group_box(self, title, group):
        box = QGroupBox(title)
        grid = QGridLayout(box)
        grid.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        col = 0
        for p in PARAMS:
            if p.group != group or p.id in self.controls:
                continue
            w = build_control(self.controller, p)
            self.controls[p.id] = w
            grid.addWidget(w, 0, col)
            col += 1
        return box

    def _bank_box(self, letter):
        outer = QGroupBox("Bank %s" % letter)
        lay = QGridLayout(outer)
        lay.setAlignment(Qt.AlignTop)
        for i, part in enumerate(BANK_PARTS):
            lay.addWidget(self._group_box(part, "Bank %s / %s" % (letter, part)), i // 2, i % 2)
        return outer

    def _build_body(self):
        body = QWidget()
        row = QHBoxLayout(body)
        row.setAlignment(Qt.AlignTop)
        row.addWidget(self._bank_box("A"))
        centre = QVBoxLayout()
        centre.addWidget(self._group_box("Banks", "Banks"))
        master = self._group_box("Master", "Master")
        master.layout().addWidget(self.meter, 0, 3)
        master.layout().addWidget(self.gr_label, 1, 3)
        centre.addWidget(master)
        centre.addStretch(1)
        row.addLayout(centre)
        row.addWidget(self._bank_box("B"))
        right = QVBoxLayout()
        for title in ("LFO 1", "LFO 2"):
            right.addWidget(self._group_box(title, title))
        mm = QGroupBox("Mod Matrix")
        QVBoxLayout(mm).addWidget(self.matrix)
        right.addWidget(mm)
        right.addWidget(self._group_box("Tempo", "Tempo"))
        right.addWidget(self._group_box("Effects", "Effects"))
        right.addStretch(1)
        row.addLayout(right)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(body)
        self.setCentralWidget(scroll)

    def _build_toolbar(self):
        tb = QToolBar("Patches")
        tb.setMovable(False)
        self.addToolBar(tb)
        tb.addWidget(QLabel(" Patch "))
        self.patch_combo = QComboBox()
        self.patch_combo.setMinimumWidth(180)
        self.patch_combo.currentTextChanged.connect(self._choose)
        tb.addWidget(self.patch_combo)
        self.act_save = QAction("Save", self, triggered=self._save)
        self.act_save_as = QAction("Save As...", self, triggered=self._save_as_dialog)
        self.act_rename = QAction("Rename", self, triggered=self._rename_dialog)
        self.act_delete = QAction("Delete", self, triggered=self._delete)
        for a in (self.act_save, self.act_save_as, self.act_rename, self.act_delete):
            tb.addAction(a)
        spacer = QWidget()
        spacer.setSizePolicy(spacer.sizePolicy().horizontalPolicy().Expanding, spacer.sizePolicy().verticalPolicy())
        tb.addWidget(spacer)
        tb.addWidget(self.leds)

    # ---- patch actions -----------------------------------------------------------------------------

    def _reload_patch_list(self, select):
        self.patch_combo.blockSignals(True)
        self.patch_combo.clear()
        self.patch_combo.addItems(self.controller.store.names())
        self.patch_combo.setCurrentText(select)
        self.patch_combo.blockSignals(False)
        editable = select != INIT_NAME
        for a in (self.act_save, self.act_rename, self.act_delete):
            a.setEnabled(editable)

    def _warn(self, text):
        QMessageBox.warning(self, "SnakeOil2", text)

    def _choose(self, name):
        try:
            warnings = self.controller.load_patch(name)
        except PatchError as e:
            self._warn(str(e))
            self._reload_patch_list(self.controller.current_patch)
            return
        self._reload_patch_list(name)
        if warnings:
            self._warn("\n".join(warnings))

    def save_as(self, name):
        try:
            self.controller.save_patch(name)
        except PatchError as e:
            self._warn(str(e))
            return
        self._reload_patch_list(name)

    def _save(self):
        try:
            self.controller.save_current()
        except PatchError as e:
            self._warn(str(e))

    def _save_as_dialog(self):
        name, ok = QInputDialog.getText(self, "Save patch as", "Name:")
        if ok and name.strip():
            self.save_as(name.strip())

    def _rename_dialog(self):
        name, ok = QInputDialog.getText(self, "Rename patch", "New name:", text=self.controller.current_patch)
        if ok and name.strip():
            try:
                self.controller.rename_patch(name.strip())
            except PatchError as e:
                self._warn(str(e))
                return
            self._reload_patch_list(name.strip())

    def _delete(self):
        if QMessageBox.question(self, "Delete patch", "Delete %s?" % self.controller.current_patch) \
                == QMessageBox.Yes:
            try:
                self.controller.delete_patch()
            except PatchError as e:
                self._warn(str(e))
                return
            self._reload_patch_list(self.controller.current_patch)

    # ---- periodic refresh --------------------------------------------------------------------------

    def refresh(self):
        c = self.controller
        self.setWindowTitle("SnakeOil2 - %s%s" % (c.current_patch, " *" if c.dirty else ""))
        held, tails = self.engine.take_activity()
        self.leds.set_activity(held, tails)
        left, right, clip = self.engine.take_meter()
        self.meter.update_levels(left, right, clip)
        gr = self.engine.limiter_reduction_db()
        self.gr_label.setText("GR off" if not self.engine.params["limiter_on"] else "GR -%.1f dB" % gr)
        self.status.showMessage("Voices %d/6   Tails %d/12" % (held, tails))
