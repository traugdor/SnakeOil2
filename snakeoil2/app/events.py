"""Thread-safe event queue between the shell (GUI/MIDI threads) and the audio thread."""
import queue


class EventQueue:
    def __init__(self):
        self._q = queue.SimpleQueue()

    def put(self, event):
        self._q.put(event)

    def drain(self):
        out = []
        try:
            while True:
                out.append(self._q.get_nowait())
        except queue.Empty:
            return out


def apply_event(engine, event):
    """Apply one event to the engine. Malformed events are ignored: this runs on the audio thread."""
    try:
        kind = event[0]
        if kind == "note_on":
            engine.note_on(event[1], event[2])
        elif kind == "note_off":
            engine.note_off(event[1])
        elif kind == "cc":
            engine.cc(event[1], event[2])
        elif kind == "bend":
            engine.pitch_bend(event[1])
        elif kind == "aftertouch":
            engine.aftertouch(event[1])
        elif kind == "param":
            engine.set_param(event[1], event[2])
        elif kind == "load":
            for pid, value in event[1].items():
                try:
                    engine.set_param(pid, value)
                except (KeyError, ValueError):
                    pass
            engine.reset_limiter()
        elif kind == "clock":
            engine.midi_clock(event[1])
        elif kind == "start":
            engine.midi_start()
        elif kind == "stop":
            engine.midi_stop()
        elif kind == "continue":
            engine.midi_continue()
        elif kind == "panic":
            engine.panic()
        elif kind == "reset_limiter":
            engine.reset_limiter()
    except Exception:
        pass
