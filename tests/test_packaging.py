import snakeoil2


def test_version():
    assert snakeoil2.__version__ == "0.1.0"


def test_dsp_does_not_import_the_shell():
    import importlib
    import sys

    for name in ("PySide6", "sounddevice", "mido"):
        sys.modules.pop(name, None)
    importlib.import_module("snakeoil2.dsp")
    for name in ("PySide6", "sounddevice", "mido"):
        assert name not in sys.modules
