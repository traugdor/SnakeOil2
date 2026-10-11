import numpy as np

from snakeoil2.dsp.allocator import allocate
from snakeoil2.dsp.constants import PLAYABLE_VOICES, POOL_SIZE
from snakeoil2.dsp.params import BANK_KEYS, PARAMS
from snakeoil2.dsp.voice import Voice

SR = 44100
RNG = np.random.default_rng(1)


def pool():
    return [Voice(SR) for _ in range(POOL_SIZE)]


def start(voices, note, order):
    v, stolen, forced = allocate(voices, PLAYABLE_VOICES, 0.010)
    v.note_on(note, 1.0, order, stolen, RNG)
    return v, stolen, forced


def test_first_notes_take_free_slots_without_stealing():
    voices = pool()
    for i in range(PLAYABLE_VOICES):
        v, stolen, forced = start(voices, 60 + i, i)
        assert not stolen and not forced


def test_seventh_note_force_releases_the_oldest_held():
    voices = pool()
    for i in range(PLAYABLE_VOICES):
        start(voices, 60 + i, i)
    v, stolen, forced = start(voices, 80, 99)
    assert [f.note for f in forced] == [60]
    assert not stolen
    assert sum(1 for x in voices if x.gate) == PLAYABLE_VOICES


def test_pool_never_exceeds_18_and_held_never_exceeds_6():
    voices = pool()
    for i in range(200):
        start(voices, 30 + i % 60, i)
        for x in voices:
            x.render(64, {k: PARAMS.defaults()["a_" + k] for k in BANK_KEYS},
                     {k: PARAMS.defaults()["b_" + k] for k in BANK_KEYS}, 261.6, 0, 0, 1, 1, 0, 0)
        assert sum(1 for x in voices if x.gate) <= PLAYABLE_VOICES
        assert len(voices) == POOL_SIZE


def test_full_pool_steals_the_quietest_release_tail_first():
    voices = pool()
    for i in range(POOL_SIZE):
        v, _, _ = start(voices, 40 + i, i)
        v.a.env.level = 1.0
        v.b.env.level = 1.0
    for v in voices:
        v.gate = False
        v.a.gate = v.b.gate = False
    voices[5].a.env.level = voices[5].b.env.level = 0.1
    v, stolen, _ = allocate(voices, PLAYABLE_VOICES, 0.010)
    assert stolen and v is voices[5]
