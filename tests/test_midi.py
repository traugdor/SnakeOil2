from snakeoil2.app.midi import message_to_event


def test_note_messages_and_velocity_zero():
    assert message_to_event("note_on", note=60, velocity=100) == ("note_on", 60, 100)
    assert message_to_event("note_on", note=60, velocity=0) == ("note_off", 60)
    assert message_to_event("note_off", note=60, velocity=0) == ("note_off", 60)


def test_controllers():
    assert message_to_event("control_change", control=64, value=127) == ("cc", 64, 127)
    assert message_to_event("pitchwheel", pitch=-8192) == ("bend", -1.0)
    assert message_to_event("pitchwheel", pitch=0) == ("bend", 0.0)
    assert message_to_event("aftertouch", value=127) == ("aftertouch", 1.0)


def test_realtime_and_ignored():
    assert message_to_event("clock") == ("clock_pulse",)
    assert message_to_event("start") == ("start",)
    assert message_to_event("stop") == ("stop",)
    assert message_to_event("continue") == ("continue",)
    assert message_to_event("polytouch", note=60, value=10) is None
    assert message_to_event("sysex") is None
