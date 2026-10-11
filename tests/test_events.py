import threading

from snakeoil2.app.events import EventQueue, apply_event
from snakeoil2.dsp.engine import Engine


def test_queue_is_fifo_and_drain_empties_it():
    q = EventQueue()
    q.put(("a",)); q.put(("b",))
    assert q.drain() == [("a",), ("b",)] and q.drain() == []


def test_queue_accepts_events_from_many_threads():
    q = EventQueue()
    ts = [threading.Thread(target=lambda: [q.put(("x",)) for _ in range(500)]) for _ in range(4)]
    [t.start() for t in ts]; [t.join() for t in ts]
    assert len(q.drain()) == 2000


def test_apply_event_drives_the_engine():
    e = Engine()
    apply_event(e, ("note_on", 60, 100)); assert e.held_count == 1
    apply_event(e, ("note_off", 60)); assert e.held_count == 0
    apply_event(e, ("param", "mix", 0.2)); assert e.get_param("mix") == 0.2
    apply_event(e, ("bend", 0.5)); assert e.bend == 0.5
    apply_event(e, ("aftertouch", 0.4)); assert e.aftertouch_value == 0.4
    apply_event(e, ("cc", 1, 127)); assert e.mod_wheel == 1.0
    apply_event(e, ("clock", 1.0))
    apply_event(e, ("start",)); apply_event(e, ("stop",)); apply_event(e, ("continue",))
    apply_event(e, ("panic",)); apply_event(e, ("reset_limiter",))


def test_bad_events_never_raise():
    e = Engine()
    for ev in (("param", "nope", 1), ("param", "mix", float("nan")), ("note_on", "x", 1), ("bogus",), (),
               ("load", {"mix": "bad", "zzz": 1}), ("note_on",), None):
        apply_event(e, ev)
    assert e.get_param("mix") == 0.5


def test_load_event_sets_many_params():
    e = Engine()
    apply_event(e, ("load", {"mix": 0.9, "a_mod_mode": "FM", "detune": 20.0}))
    assert e.get_param("mix") == 0.9 and e.get_param("a_mod_mode") == "FM" and e.get_param("detune") == 20.0
