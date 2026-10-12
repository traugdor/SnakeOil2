import sys

from PySide6.QtWidgets import QApplication

from ..controller import Controller
from .main_window import MainWindow


def run_gui(engine, queue, store, patch_name, audio, midi):
    app = QApplication.instance() or QApplication(sys.argv)
    controller = Controller(queue, store)
    # The engine already holds the patch loaded in main(); mirror it into the controller without re-queueing.
    controller.load_patch(patch_name)
    window = MainWindow(controller, engine)
    window.resize(1180, 690)
    window.show()
    return app.exec()
