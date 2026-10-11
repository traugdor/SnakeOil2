from snakeoil2.dsp.engine import Engine


def test_activity_reports_the_maximum_since_the_last_call():
    e = Engine()
    e.note_on(60, 100); e.note_on(64, 100)
    e.process(64)
    e.note_off(60); e.note_off(64)
    e.process(64)
    held, tails = e.take_activity()
    assert held == 2 and tails >= 0
    assert e.take_activity() == (0, tails) or e.take_activity() == (0, 0)


def test_short_note_still_registers():
    e = Engine()
    e.set_param("a_amp_release", 0.001); e.set_param("b_amp_release", 0.001)
    e.note_on(60, 100); e.process(32); e.note_off(60)
    for _ in range(20):
        e.process(256)
    assert e.take_activity()[0] == 1
