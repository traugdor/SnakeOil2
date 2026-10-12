from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (QApplication, QComboBox, QGridLayout, QGroupBox, QHBoxLayout, QInputDialog, QLabel, QMessageBox,
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

    def _cell(self, prefix, keys):
        """A vertical stack of compact controls (for example Saw over Square)."""
        cell = QWidget()
        lay = QVBoxLayout(cell)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(1)
        lay.setAlignment(Qt.AlignTop)
        for key in keys:
            pid = prefix + key
            w = build_control(self.controller, PARAMS.by_id[pid], compact=True)
            self.controls[pid] = w
            lay.addWidget(w)
        return cell

    def _table(self, title, groups, banks=True):
        """A group box with column headers once. With ``banks`` the same cells repeat for bank A and bank B."""
        box = QGroupBox(title)
        grid = QGridLayout(box)
        grid.setContentsMargins(4, 4, 4, 2)
        grid.setHorizontalSpacing(3)
        grid.setVerticalSpacing(2)
        rows = (("A", "a_"), ("B", "b_")) if banks else (("", ""),)
        col = 1 if banks else 0
        for head, cells in groups:
            label = QLabel(head)
            label.setObjectName("colhead")
            label.setAlignment(Qt.AlignCenter)
            grid.addWidget(label, 0, col, 1, len(cells))
            for cell in cells:
                for r, (_, prefix) in enumerate(rows, start=1):
                    grid.addWidget(self._cell(prefix, cell), r, col, Qt.AlignTop | Qt.AlignHCenter)
                col += 1
        if banks:
            for r, (letter, _) in enumerate(rows, start=1):
                tag = QLabel(letter)
                tag.setObjectName("bank" + letter)
                grid.addWidget(tag, r, 0, Qt.AlignTop | Qt.AlignHCenter)
        grid.setColumnStretch(col, 1)
        grid.setRowStretch(len(rows) + 1, 1)     # spare height goes below the controls
        box.next_col = col
        return box

    def _build_body(self):
        osc = self._table("Oscillators", (
            ("OSC1", (("osc1_saw", "osc1_square", "osc1_octave_down"), ("osc1_pwm",), ("osc1_square_level",),
                      ("osc1_level",))),
            ("Mod", (("mod_mode",),)),
            ("OSC2", (("osc2_wave", "osc2_octave_up"), ("osc2_pwm",), ("osc2_level",), ("osc2_coarse",),
                      ("osc2_fine",))),
            ("Noise", (("noise_color",), ("noise_level",))),
            ("Out", (("volume",),)),
        ))
        filt = self._table("Filter and envelopes", (
            ("Filter", (("cutoff",), ("resonance",), ("flt_amount",), ("keytrack",), ("vel_cutoff",))),
            ("Filter Env", (("flt_attack",), ("flt_decay",), ("flt_sustain",), ("flt_release",))),
            ("Amp Env", (("amp_attack",), ("amp_decay",), ("amp_sustain",), ("amp_release",))),
        ))
        mixer = self._table("Mix and master", (
            ("Banks", (("mix",), ("detune",), ("width",))),
            ("Master", (("master_volume",), ("velocity_on", "limiter_on"))),
        ), banks=False)
        mixer.layout().addWidget(self.meter, 1, mixer.next_col)
        mixer.layout().addWidget(self.gr_label, 2, mixer.next_col)
        lfo = self._table("LFOs", (
            ("LFO 1", (("lfo1_rate",), ("lfo1_wave",))),
            ("LFO 2", (("lfo2_rate",), ("lfo2_wave",))),
        ), banks=False)
        mm = QGroupBox("Mod matrix")
        mm_lay = QVBoxLayout(mm)
        mm_lay.setContentsMargins(4, 4, 4, 2)
        mm_lay.addWidget(self.matrix)
        fx = self._table("Effects and tempo", (
            ("Chorus", (("fx_chorus_on",), ("fx_chorus_depth",))),
            ("Delay", (("fx_delay_on", "fx_delay_pingpong", "fx_delay_sync"), ("fx_delay_time",),
                       ("fx_delay_feedback",), ("fx_delay_tone",), ("fx_delay_division",))),
            ("Reverb", (("fx_reverb_on",), ("fx_reverb_amount",), ("fx_reverb_size",), ("fx_reverb_damp",))),
            ("Tempo", (("tempo_bpm",),)),
        ), banks=False)

        left = QVBoxLayout()
        left.setSpacing(2)
        left.addWidget(osc)
        left.addWidget(filt)
        right = QVBoxLayout()
        right.setSpacing(2)
        right.addWidget(mixer)
        right.addWidget(lfo)
        right.addWidget(mm)
        top = QHBoxLayout()
        top.setAlignment(Qt.AlignTop)
        top.addLayout(left)
        top.addLayout(right)
        body = QWidget()
        outer = QVBoxLayout(body)
        outer.setContentsMargins(4, 2, 4, 2)
        outer.setSpacing(2)
        outer.addLayout(top)
        outer.addWidget(fx)
        outer.addStretch(1)
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

    def fit_to_content(self, margin=10, max_size=None):
        """Open at the smallest size that shows every control without scrollbars, plus ``margin``.

        Qt's size hints are inflated until the stylesheet fonts are applied, so instead of trusting a hint this
        shows the window (invisibly) and searches for the smallest width and height with no scrollbar. The
        result is capped to ``max_size`` (default: the screen)."""
        if max_size is None:
            screen = self.screen()
            area = screen.availableGeometry() if screen else None
            max_size = (area.width(), area.height()) if area else (4000, 4000)
        scroll = self.centralWidget()
        was_visible = self.isVisible()
        if not was_visible:
            self.setWindowOpacity(0.0)
            self.show()
        max_w, max_h = max_size

        def needs_bar(width, height, bar):
            self.resize(width, height)
            QApplication.processEvents()
            return bar().isVisible()

        lo, hi = 300, max_w                       # narrowest width with no horizontal bar, at full height
        while lo < hi:
            mid = (lo + hi) // 2
            if needs_bar(mid, max_h, scroll.horizontalScrollBar):
                lo = mid + 1
            else:
                hi = mid
        width = lo
        lo, hi = 200, max_h                       # shortest height with no vertical bar, at that width
        while lo < hi:
            mid = (lo + hi) // 2
            if needs_bar(width, mid, scroll.verticalScrollBar):
                lo = mid + 1
            else:
                hi = mid
        self.resize(min(width + margin, max_w), min(lo + margin, max_h))
        QApplication.processEvents()
        if not was_visible:
            self.setWindowOpacity(1.0)

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
