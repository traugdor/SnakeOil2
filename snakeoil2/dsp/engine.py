"""The SnakeOil2 engine: notes, controllers and parameters in, (n, 2) float32 blocks out.

Single-threaded and lock-free. The shell must call every method from the thread that calls ``process``
(it does so by draining an event queue at the start of each audio block).
"""
import math

import numpy as np

from .allocator import allocate
from .constants import (BLOCK_SIZE, FIXED_VELOCITY, FORCED_RELEASE_S, PITCH_BEND_RANGE, PLAYABLE_VOICES,
                        POOL_SIZE, SAMPLE_RATE)
from .destinations import RATE, SRC_LFO1, SRC_LFO2
from .lfo import LFO
from .modmatrix import ModMatrix, note_source, smooth
from .params import BANK_KEYS, PARAMS
from .pitch import midi_note_to_freq
from .voice import Voice


class Engine:
    def __init__(self, sample_rate=SAMPLE_RATE, block_size=BLOCK_SIZE, seed=1):
        self.sr = sample_rate
        self.block_size = block_size
        self.table = PARAMS
        self.params = PARAMS.defaults()
        self.voices = [Voice(sample_rate) for _ in range(POOL_SIZE)]
        self._rng = np.random.default_rng(seed)
        self._order = 0
        self._last_note = None
        self.sustain = False
        self._sustained = set()
        self.bend = 0.0
        self.mod_wheel = 0.0
        self.aftertouch_value = 0.0
        self.steal_count = 0
        self.forced_releases = 0
        self.matrix = ModMatrix(PARAMS)
        self.lfo = (LFO(seed=1), LFO(seed=2))
        self.lfo_values = [0.0, 0.0]
        self._wheel_s = 0.0
        self._at_s = 0.0

    # ---- parameters -------------------------------------------------------------------------------

    def set_param(self, pid, value):
        value = self.table.coerce(pid, value)
        self.params[pid] = value
        self._param_changed(pid, value)

    def get_param(self, pid):
        return self.params[pid]

    def _param_changed(self, pid, value):
        if pid.startswith("mod") and pid[3].isdigit():
            i = int(pid[3:pid.index("_")])
            self.matrix.set_row(i, self.params["mod%d_src" % i], self.params["mod%d_scale" % i],
                                self.params["mod%d_dst" % i])

    # ---- notes and controllers ---------------------------------------------------------------------

    @property
    def held_count(self):
        return sum(1 for v in self.voices if v.gate)

    @property
    def tail_count(self):
        return sum(1 for v in self.voices if v.active and not v.gate)

    def note_on(self, note, velocity=100):
        if not isinstance(note, (int, np.integer)) or not 0 <= note <= 127:
            return
        velocity = int(min(max(velocity, 0), 127))
        if velocity == 0:
            self.note_off(note)
            return
        self._sustained.discard(note)
        for v in self.voices:
            if v.gate and v.note == note:
                v.note_off()
        voice, stolen, forced = allocate(self.voices, PLAYABLE_VOICES, FORCED_RELEASE_S)
        self.forced_releases += len(forced)
        self.steal_count += int(stolen)
        self._order += 1
        vel = velocity / 127.0 if self.params["velocity_on"] else FIXED_VELOCITY
        voice.note_on(note, vel, self._order, stolen, self._rng)
        self._last_note = note

    def note_off(self, note):
        if self.sustain:
            if any(v.gate and v.note == note for v in self.voices):
                self._sustained.add(note)
            return
        for v in self.voices:
            if v.gate and v.note == note:
                v.note_off()

    def all_notes_off(self):
        self._sustained.clear()
        for v in self.voices:
            if v.active:
                v.note_off()

    def all_sound_off(self):
        self.panic()

    def panic(self):
        for v in self.voices:
            v.panic()
        self._sustained.clear()
        self.sustain = False

    def set_sustain(self, on):
        self.sustain = bool(on)
        if not self.sustain:
            deferred, self._sustained = self._sustained, set()
            for v in self.voices:
                if v.gate and v.note in deferred:
                    v.note_off()

    def pitch_bend(self, x):
        x = float(x)
        self.bend = min(max(x, -1.0), 1.0) if math.isfinite(x) else 0.0

    def set_mod_wheel(self, v):
        v = float(v)
        self.mod_wheel = min(max(v, 0.0), 1.0) if math.isfinite(v) else 0.0

    def aftertouch(self, v):
        v = float(v)
        self.aftertouch_value = min(max(v, 0.0), 1.0) if math.isfinite(v) else 0.0

    def reset_controllers(self):
        self.bend = 0.0
        self.mod_wheel = 0.0
        self.aftertouch_value = 0.0
        self.set_sustain(False)

    def cc(self, control, value):
        if control == 1:
            self.set_mod_wheel(value / 127.0)
        elif control == 64:
            self.set_sustain(value >= 64)
        elif control == 120:
            self.all_sound_off()
        elif control == 121:
            self.reset_controllers()
        elif control == 123:
            self.all_notes_off()

    # ---- rendering ---------------------------------------------------------------------------------

    def _bank_view(self, prefix, overrides):
        p = self.params
        return {k: overrides.get(prefix + k, p[prefix + k]) for k in BANK_KEYS}

    def _eval_block(self, n):
        """Advance the LFOs and evaluate the matrix once for this block."""
        p = self.params
        self._wheel_s = smooth(self._wheel_s, self.mod_wheel)
        self._at_s = smooth(self._at_s, self.aftertouch_value)
        sources = [0.0, 0.0, self.lfo_values[0], self.lfo_values[1], self._wheel_s, self._at_s]
        last = note_source(self._last_note)
        rates = self.matrix.evaluate(p, sources, last, kinds=(RATE,)).values
        for i in (0, 1):
            rate = rates.get("lfo%d_rate" % (i + 1), p["lfo%d_rate" % (i + 1)])
            self.lfo_values[i] = self.lfo[i].next_block(n, self.sr, rate, p["lfo%d_wave" % (i + 1)])[0]
        sources[SRC_LFO1], sources[SRC_LFO2] = self.lfo_values
        common = self.matrix.evaluate(p, sources, last)
        return common, sources

    def process(self, n=None, now=None):
        n = self.block_size if n is None else int(n)
        p = self.params
        common, sources = self._eval_block(n)

        def g(pid):
            return common.values.get(pid, p[pid])

        mix = g("mix")
        gain_a = math.cos(mix * math.pi / 2.0)
        gain_b = math.sin(mix * math.pi / 2.0)
        detune, width = g("detune"), g("width")
        shared = None
        if not self.matrix.uses_note:
            shared = (self._bank_view("a_", common.values), self._bank_view("b_", common.values), common.pitch)
        bend_ratio = 2.0 ** (self.bend * PITCH_BEND_RANGE / 12.0)
        out = np.zeros((2, n))
        for v in self.voices:
            if not v.active:
                continue
            if shared is not None:
                view_a, view_b, pitch = shared
            else:
                mods = self.matrix.evaluate(p, sources, note_source(v.note))
                view_a = self._bank_view("a_", mods.values)
                view_b = self._bank_view("b_", mods.values)
                pitch = mods.pitch
            out += v.render(n, view_a, view_b, midi_note_to_freq(v.note) * bend_ratio,
                            -detune / 2.0 + 100.0 * pitch["a"], detune / 2.0 + 100.0 * pitch["b"],
                            gain_a * view_a["volume"], gain_b * view_b["volume"], -width, width)
        out = out * p["master_volume"]
        return np.ascontiguousarray(np.tanh(out).T).astype(np.float32)
