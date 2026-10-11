"""One voice slot: bank A and bank B playing the same note."""
import numpy as np

from .bank import Bank
from .constants import FORCED_RELEASE_S


class Voice:
    def __init__(self, sr):
        self.a = Bank(sr)
        self.b = Bank(sr)
        self.note = -1
        self.gate = False
        self.order = 0

    @property
    def active(self):
        return self.a.active or self.b.active

    @property
    def level(self):
        return max(self.a.level, self.b.level)

    def note_on(self, note, velocity, order, stolen, rng):
        self.note = note
        self.gate = True
        self.order = order
        for bank in (self.a, self.b):
            bank.note_on(note, velocity, stolen and bank.active, rng)

    def note_off(self):
        self.gate = False
        self.a.note_off()
        self.b.note_off()

    def force_release(self, seconds=FORCED_RELEASE_S):
        self.gate = False
        self.a.force_release(seconds)
        self.b.force_release(seconds)

    def panic(self):
        self.gate = False
        self.a.panic()
        self.b.panic()

    def render(self, n, view_a, view_b, base_freq, cents_a, cents_b, gain_a, gain_b, pan_a, pan_b):
        """Render a (2, n) block. Pan uses the balance law: the far channel is attenuated."""
        left = np.zeros(n)
        right = np.zeros(n)
        for bank, view, cents, gain, pan in ((self.a, view_a, cents_a, gain_a, pan_a),
                                            (self.b, view_b, cents_b, gain_b, pan_b)):
            if not bank.active:
                continue
            out = bank.render(n, view, base_freq, cents) * gain
            left += out * (1.0 - max(0.0, pan))
            right += out * (1.0 + min(0.0, pan))
        return np.vstack([left, right])
