"""ADSR envelope (ported unchanged from V1; processes whole blocks, split-invariant)."""
import numpy as np

ATTACK, DECAY, SUSTAIN, RELEASE, IDLE = range(5)


class Envelope:
    def __init__(self, sr, attack=0.006, decay=0.120, sustain=0.75, release=0.180):
        self.sr = sr
        self.set_shape(attack, decay, sustain, release)
        self.stage = IDLE
        self.level = 0.0
        self.release_override = None

    def set_shape(self, attack, decay, sustain, release):
        self.attack = max(attack, 1.0 / self.sr)
        self.decay = max(decay, 1.0 / self.sr)
        self.sustain = min(max(sustain, 0.0), 1.0)
        self.release = max(release, 1.0 / self.sr)

    def note_on(self, keep_level=False):
        self.stage = ATTACK
        self.release_override = None
        if self.level >= 1.0 and not keep_level:
            self.level = 0.0

    def note_off(self, release_s=None):
        """Start the release; ``release_s`` overrides the release time until
        the envelope restarts or goes idle."""
        if self.stage != IDLE:
            self.stage = RELEASE
            if release_s is not None:
                self.release_override = max(release_s, 1.0 / self.sr)

    @property
    def active(self):
        return self.stage != IDLE

    @staticmethod
    def _ramp(level, inc, count):
        """Levels after 1..count repeated ``level += inc`` steps (bit-exact)."""
        steps = np.full(count, inc, dtype=np.float64)
        steps[0] += level
        return np.cumsum(steps)

    def process(self, n):
        out = np.empty(n, dtype=np.float64)
        att_inc = 1.0 / (self.attack * self.sr)
        dec_inc = (1.0 - self.sustain) / (self.decay * self.sr)
        release = self.release if self.release_override is None else self.release_override
        rel_inc = 1.0 / (release * self.sr)
        level = self.level
        stage = self.stage
        sustain = self.sustain
        pos = 0
        while pos < n:
            remaining = n - pos
            if stage == ATTACK:
                seg = self._ramp(level, att_inc, remaining)
                hit = seg >= 1.0
                target, nxt = 1.0, DECAY
            elif stage == DECAY:
                seg = self._ramp(level, -dec_inc, remaining)
                hit = seg <= sustain
                target, nxt = sustain, SUSTAIN
            elif stage == RELEASE:
                seg = self._ramp(level, -rel_inc, remaining)
                hit = seg <= 0.0
                target, nxt = 0.0, IDLE
            else:
                out[pos:] = sustain if stage == SUSTAIN else level
                if stage == SUSTAIN:
                    level = sustain
                break
            k = int(np.argmax(hit))
            if hit[k]:
                out[pos:pos + k] = seg[:k]
                out[pos + k] = target
                level = target
                stage = nxt
                if nxt == IDLE:
                    self.release_override = None
                pos += k + 1
            else:
                out[pos:] = seg
                level = float(seg[-1])
                pos = n
        self.level = level
        self.stage = stage
        return out
