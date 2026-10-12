import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication, QComboBox

from snakeoil2.app.controller import Controller
from snakeoil2.app.events import EventQueue
from snakeoil2.app.gui.main_window import MainWindow
from snakeoil2.dsp.engine import Engine
from snakeoil2.dsp.params import PARAMS
from snakeoil2.patches import PatchStore

app = QApplication.instance() or QApplication([])


def make(tmp_path):
    e, q = Engine(), EventQueue()
    c = Controller(q, PatchStore(tmp_path))
    return MainWindow(c, e), c, e, q


def test_window_builds_and_every_parameter_has_a_widget(tmp_path):
    w, c, e, q = make(tmp_path)
    w.show()
    assert set(w.controls) == set(PARAMS.ids)


def test_mod_matrix_has_eight_rows_of_three_controls(tmp_path):
    w, *_ = make(tmp_path)
    assert len(w.matrix.rows) == 8
    combos = w.matrix.findChildren(QComboBox)
    assert len(combos) == 16


def test_changing_a_control_reaches_the_event_queue(tmp_path):
    w, c, e, q = make(tmp_path)
    c.set_param("mix", 0.1)
    assert ("param", "mix", 0.1) in q.drain()


def test_title_marks_unsaved_changes(tmp_path):
    w, c, *_ = make(tmp_path)
    w.refresh()
    assert "Init" in w.windowTitle() and not w.windowTitle().endswith("*")
    c.set_param("mix", 0.1)
    w.refresh()
    assert w.windowTitle().endswith("*")


def test_refresh_updates_leds_and_meter(tmp_path):
    w, c, e, q = make(tmp_path)
    e.note_on(60, 100); e.note_on(64, 100)
    for _ in range(10):
        e.process(256)
    w.refresh()
    assert w.leds.states()[:2] == ["held", "held"]


def test_save_as_roundtrip_through_the_window_actions(tmp_path):
    w, c, *_ = make(tmp_path)
    c.set_param("mix", 0.9)
    w.save_as("Mine")
    assert "Mine" in [w.patch_combo.itemText(i) for i in range(w.patch_combo.count())]
    w.patch_combo.setCurrentText("Init")
    assert c.values["mix"] == 0.5 and c.current_patch == "Init"
    w.patch_combo.setCurrentText("Mine")
    assert c.values["mix"] == 0.9


def test_init_patch_disables_save_rename_delete(tmp_path):
    w, *_ = make(tmp_path)
    assert not w.act_save.isEnabled() and not w.act_rename.isEnabled() and not w.act_delete.isEnabled()


def test_fit_to_content_leaves_no_scrollbars(tmp_path):
    w, *_ = make(tmp_path)
    w.fit_to_content(max_size=(4000, 4000))      # the offscreen test screen is only 800 px wide
    w.show()
    app.processEvents()
    scroll = w.centralWidget()
    assert not scroll.horizontalScrollBar().isVisible()
    assert not scroll.verticalScrollBar().isVisible()


def test_fit_to_content_is_capped_to_the_screen(tmp_path):
    w, *_ = make(tmp_path)
    w.fit_to_content(max_size=(400, 300))
    assert w.width() <= 400 and w.height() <= 300


def test_fit_to_content_is_tight(tmp_path):
    """The fitted window is the smallest without scrollbars (plus a small margin), not a padded hint."""
    w, *_ = make(tmp_path)
    w.fit_to_content(max_size=(4000, 4000), margin=10)
    app.processEvents()
    scroll = w.centralWidget()
    assert not scroll.horizontalScrollBar().isVisible() and not scroll.verticalScrollBar().isVisible()
    w.resize(w.width() - 40, w.height())
    app.processEvents()
    assert scroll.horizontalScrollBar().isVisible()          # 40 px narrower needs a scrollbar again
    w.fit_to_content(max_size=(4000, 4000), margin=10)
    w.resize(w.width(), w.height() - 40)
    app.processEvents()
    assert scroll.verticalScrollBar().isVisible()


def test_fit_to_content_ignores_an_inflated_size_hint(tmp_path):
    w, *_ = make(tmp_path)
    body = w.centralWidget().widget()
    w.show()
    app.processEvents()
    real = body.minimumSizeHint()          # measured once the window is shown and styled
    body.sizeHint = lambda: real * 2                           # what a mis-measured hint looks like
    w.fit_to_content(max_size=(4000, 4000), margin=10)
    app.processEvents()
    assert w.width() < real.width() * 1.3 and w.height() < real.height() * 1.3 + 100
