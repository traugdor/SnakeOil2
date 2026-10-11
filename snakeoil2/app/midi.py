"""MIDI input: mido messages become engine events on an EventQueue."""
import time


def message_to_event(msg_type, **f):
    """Translate one MIDI message into an engine event tuple, or None to ignore it."""
    if msg_type == "note_on":
        return ("note_off", f["note"]) if f["velocity"] == 0 else ("note_on", f["note"], f["velocity"])
    if msg_type == "note_off":
        return ("note_off", f["note"])
    if msg_type == "control_change":
        return ("cc", f["control"], f["value"])
    if msg_type == "pitchwheel":
        return ("bend", max(-1.0, min(1.0, f["pitch"] / 8192.0)))
    if msg_type == "aftertouch":
        return ("aftertouch", f["value"] / 127.0)
    if msg_type == "clock":
        return ("clock_pulse",)
    if msg_type in ("start", "stop", "continue"):
        return (msg_type,)
    return None


class MidiInput:
    """Opens the chosen (default: all) MIDI input ports and feeds an EventQueue."""

    def __init__(self, queue, ports=None, channel=None):
        self.queue = queue
        self.ports = ports
        self.channel = channel
        self._open = []

    @staticmethod
    def available_ports():
        import mido
        return mido.get_input_names()

    def _on_message(self, msg):
        if self.channel is not None and hasattr(msg, "channel") and msg.channel != self.channel - 1:
            return
        fields = {k: getattr(msg, k) for k in ("note", "velocity", "control", "value", "pitch") if hasattr(msg, k)}
        event = message_to_event(msg.type, **fields)
        if event is None:
            return
        if event == ("clock_pulse",):
            event = ("clock", time.perf_counter())
        self.queue.put(event)

    def start(self):
        import mido
        names = self.ports if self.ports else mido.get_input_names()
        for name in names:
            self._open.append(mido.open_input(name, callback=self._on_message))
        return list(names)

    def stop(self):
        for port in self._open:
            port.close()
        self._open = []
