import argparse
import sys

from ..dsp.constants import SAMPLE_RATE
from ..dsp.engine import Engine
from ..patches import PatchError, PatchStore
from .events import EventQueue
from .paths import config_dir, patches_dir


def build_parser():
    p = argparse.ArgumentParser(prog="snakeoil2", description="SnakeOil2 dual-bank synthesizer")
    p.add_argument("--list", action="store_true", help="list MIDI inputs and audio outputs, then exit")
    p.add_argument("--input", action="append", default=[], help="MIDI input name (repeatable); default all")
    p.add_argument("--channel", type=int, choices=range(1, 17), metavar="1-16", default=None)
    p.add_argument("--device", default=None, help="audio output device name or index")
    p.add_argument("--hostapi", default=None, help="audio host API, e.g. ASIO or WASAPI")
    p.add_argument("--patch", default=None, help="patch to load at start")
    p.add_argument("--config-dir", default=None)
    p.add_argument("--no-gui", action="store_true")
    return p


def _list_devices():
    from .audio_backend import prepare_asio
    from .midi import MidiInput

    prepare_asio()
    import sounddevice as sd

    print("MIDI inputs:")
    for name in MidiInput.available_ports():
        print("  " + name)
    print("Audio:")
    print(sd.query_devices())


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.list:
        _list_devices()
        return 0
    config = config_dir(args.config_dir)
    store = PatchStore(patches_dir(config))
    from .audio_backend import default_samplerate, prepare_asio, resolve_output

    prepare_asio()          # must run before sounddevice is first imported
    import sounddevice as sd

    info = resolve_output(sd, args.hostapi, args.device)
    engine = Engine(sample_rate=int(default_samplerate(sd, info["device"], SAMPLE_RATE)))
    queue = EventQueue()
    name = args.patch or store.last_used()
    try:
        values, warnings = store.load(name)
    except PatchError as e:
        print("warning: %s; using the factory sound" % e, file=sys.stderr)
        name, (values, warnings) = "Init", store.load("Init")
    for w in warnings:
        print("warning: " + w, file=sys.stderr)
    for pid, value in values.items():
        if pid not in ("master_volume", "limiter_on"):
            engine.set_param(pid, value)

    from .audio import AudioOutput
    from .midi import MidiInput

    audio = AudioOutput(engine, queue, info)
    midi = MidiInput(queue, ports=args.input or None, channel=args.channel)
    audio.start()
    try:
        print("MIDI inputs:", ", ".join(midi.start()) or "none")
        if args.no_gui:
            print("Patch %s. Press Ctrl+C to quit." % name)
            try:
                while True:
                    import time
                    time.sleep(0.5)
            except KeyboardInterrupt:
                pass
        else:
            from .gui.app import run_gui
            return run_gui(engine, queue, store, name, audio, midi)
    finally:
        midi.stop()
        audio.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
